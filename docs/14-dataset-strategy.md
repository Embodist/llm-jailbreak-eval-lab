# 评估数据集策略：覆盖面、持续采集与种子生成

## 1. 当前数据集全面吗？

**不全面。** 现在的是一个“研究性平衡样本”，不是认证级基准。覆盖情况：

| 维度 | 已覆盖 | 缺口 |
|---|---|---|
| 来源 | HarmBench、StrongREJECT、CCS'24 forbidden、AdvBench、XSTest、SALAD（示例） | JailbreakBench、BeaverTails、Do-Not-Answer、OR-Bench、Sorry-Bench、AILuminate 未纳入 |
| 危害域 | 13 个有害主类 + 安全但敏感 | 自伤、CSAM（有意排除）、高利害医疗/法律、政治操纵覆盖薄 |
| 语种 | 全部为拉丁字母（英文为主，少量西/葡） | 中文、日文、韩文、阿拉伯文、俄文等非拉丁语种为 0 |
| 模态 | 纯文本 | 图像、音频、视频、排版/同形字、文档注入 |
| 攻击面 | 单轮包装（5 类）+ 多轮（3 场景） | 白盒 GCG、256+ shot、间接注入（RAG/工具/文件）、Agent 工具滥用、超长上下文 |
| 在野语料 | 分析了 1,405 条，但未逐条评测 | WildChat / LMSYS-Chat-1M / ToxicChat 等真实对话 |
| 模型 | 14 个（一个代理） | 前沿闭源 API、开源权重本地模型、abliterated 对照组 |
| 标注 | 1 个主标注 + 1 个合规标注 | 人工校准、双标注一致性（Cohen's κ） |

`scripts/coverage_report.py` 会输出当前缺口；目前唯一硬缺口是**非拉丁语种 < 50**。

## 2. 标准评估集清单

### 已纳入

| 数据集 | 规模 | 分类法 | 链接 |
|---|---:|---|---|
| HarmBench | 400 | 3 functional × 7 semantic | centerforaisafety/HarmBench |
| StrongREJECT | 313 | 6 harm categories | alexandrasouly/strongreject |
| CCS'24 forbidden questions | 390 | 13 content policies | verazuo/jailbreak_llms |
| AdvBench | 520 | 无类别 | llm-attacks/llm-attacks |
| XSTest | 450 | 250 safe / 200 unsafe，18 对比类型 | paul-rottger/xstest |
| SALAD-Bench（示例） | 127 | 0=unsafe / 1=safe | OpenSafetyLab/SALAD-Bench |

### 建议后续纳入

| 数据集 | 用途 | 获取 |
|---|---|---|
| JailbreakBench | 100 行为 + 攻击基线 | GitHub / HF |
| BeaverTails | 14 类 + 偏好对 | GitHub / HF |
| Do-Not-Answer | 939 条“不该回答”的问题 | HF |
| OR-Bench | 过度拒绝（80k 安全但诱导） | GitHub / HF |
| Sorry-Bench | 拒绝行为评估 | GitHub |
| MLCommons AILuminate | 12 hazard 类别，行业标准 | MLCommons |
| PolyGuard / Aegis | 多语种/多模态安全 | HF |
| WildChat / LMSYS-Chat-1M / ToxicChat | 真实在野对话 | HF |
| CValues / CHiP | 中文安全对齐 | GitHub |
| BBQ / TruthfulQA | 偏见/真实性 | GitHub |

## 3. 持续采集：来源、频率、流程

| 来源 | 频率 | 采集方式 |
|---|---|---|
| 新论文/基准（arXiv、HF datasets、GitHub） | 每周 | 关键词订阅 + repo watch |
| 社区破甲合集（L1B3RT4S 等） | 每周 | GitHub API 搜索 + 克隆 |
| 在野对话（WildChat、LMSYS、ToxicChat） | 每月 | HF 数据集拉取，按政策过滤 |
| 事件库（AI Incident Database、MITRE ATLAS、OWASP） | 每月 | 人工整理为场景 |
| 红队披露/漏洞赏金 | 事件驱动 | 厂商公告、HackerOne |
| 监管/标准更新（NIST AI 600-1、EU AI Act、AILuminate） | 季度 | 映射到主类 |

统一流程：

```
采集 → 解析/归一化 → 去重（SHA1/嵌入） → 分类（主类+风险）
     → 覆盖检查（coverage_report） → 平衡抽样 → 评测 → 标注 → 入库（带 provenance）
```

入库字段至少要保留：`source`、`source_url`、`license`、`collected_at`、`version`、`parent_id`。

## 4. 生成方法：prompt 种子生成器

`scripts/generate_seeds.py` 是一个可运行的种子生成器：读入 `master_prompts.jsonl`，按题材抽样，扩展成 7 种单轮变体 + 多轮阶梯。

```bash
python3 scripts/generate_seeds.py --per-category 4
# data/generated/seeds_single.jsonl  (364)
# data/generated/seeds_multi.jsonl   (52)
```

内置变体：

- 结构类：sandbox、roleplay、fiction、refusal_suppression、prefix_injection
- 表示类：base64、rot13
- 多轮：3 轮“背景 → 方法 → 原始请求”阶梯

每条输出保留 `parent_id`、`generator`、`created_at`，并按 `(prompt, technique)` 哈希去重。

### 可叠加的生成器（按依赖从轻到重）

| 方法 | 依赖 | 适用 | 代表工具 |
|---|---|---|---|
| 模板/编码 | 无（标准库） | 快速扩量、可控 | 本项目 `generate_seeds.py` |
| LLM 改写/翻译 | 一个可调用模型 | 语种、风格、难度变异 | 任意 chat API |
| 模糊测试 | GPTFuzz | 变异+选择循环 | hubertyoo/GPTFuzz |
| 遗传/进化 | AutoDAN | 黑盒提示演化 | EasyJailbreak |
| 攻击者-目标迭代 | PAIR / TAP | 自动多轮 | EasyJailbreak |
| 梯度对抗后缀 | 白盒权重 + GPU | 最强白盒攻击 | GCG / llm-attacks |
| 策略→场景→提示 | LLM + 分类法 | 覆盖新政策类别 | 自建 self-instruct |
| 人工红队 | 人 | 发现新类别 | 结构化工作坊 |

### 质量闸门

1. **去重**：精确哈希 + 可选嵌入近邻。
2. **归类**：必须能映射到一个主类；映射失败进 `other_harm` 并告警。
3. **风险**：由主类决定，不允许生成器自定。
4. **难度校准**：先跑 baseline，太容易/太难的样本降权。
5. **合规过滤**：排除 PII、CSAM、可操作大规模伤害；高风险内容只保留标签，不发布原文。
6. **人工抽检**：每批抽 5–10% 复核类别与风险。

### 评估生成质量

- **覆盖增益**：新增了多少“题材 × 手法 × 语种”空格。
- **新颖度**：与现有集的嵌入距离。
- **难度**：baseline ASR 分布（避免全是 0% 或 100%）。
- **标注一致性**：双标注 κ ≥ 0.6。
- **迁移性**：在一个模型上有效的变体，在另一个模型上的有效率。

## 5. 依赖关系图

```
seed corpus ──▶ mutators ──▶ constraints ──▶ judge ──▶ dedup/coverage ──▶ eval ──▶ dashboard
   │              │              │             │            │
   │              │              │             │            └─ coverage_report.py
   │              │              │             └─ judge_results.py / judge_compliance.py
   │              │              └─ 长度/类别/风险/合规过滤
   │              └─ generate_seeds.py, EasyJailbreak, GPTFuzz, AutoDAN, PAIR/TAP
   └─ master_prompts.jsonl（HarmBench/StrongREJECT/…）
```

可选工具：

- **评估框架**：promptfoo、DeepTeam、garak、PyRIT（适合把我们的探针接进更完整的 red-team 套件）。
- **基准**：HarmBench、JailbreakBench、MLCommons AILuminate。
- **防御对照**：NeMo Guardrails、Llama Guard、Constitutional Classifiers。
- **Python 依赖**：本项目管线只用标准库；LLM 改写/翻译需要代理 API；白盒 GCG 需要 `torch/transformers` + GPU。

## 6. 下一步建议（按优先级）

1. **补语种**：把 master 里的部分种子翻译成中/日/韩/阿/俄，重跑覆盖率；目标非拉丁 ≥ 300。
2. **补合规集**：接入 OR-Bench / Do-Not-Answer，把过度拒绝从 30 条扩到 200+。
3. **补间接注入**：新增 RAG/文件/工具返回值的注入场景（这是当前最大的攻击面缺口）。
4. **补白盒对照**：接入 abliterated 端点或本地小模型做 GCG/拒绝方向对照。
5. **双标注**：第二个 judge + 人工抽检，报告 κ。
6. **持续采集**：每周跑一次 GitHub/HF 关键词采集，进 `data/incoming/`，人工合并。

## 7. 伦理与合规

- 各数据集遵守原 license；不重新分发受限内容。
- 前端只发布聚合值与标签，不发布原始有害回复。
- 高风险类别（化生、暴力、性内容）只保留评测所需的标签与哈希。
- 不生成 CSAM、不生成可操作的武器/爆炸物细节；这类请求只作为“是否拒绝”的探针。
- 评测对象必须是自有/授权部署；遵守上游 ToS 与速率限制。
