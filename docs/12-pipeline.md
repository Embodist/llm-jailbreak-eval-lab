# 数据链路与复现

本文把从“公开数据”到“看板”的每一步写死成文件与命令，保证任何人可以在同一台机器上复现。

## 1. 全景

```
sub_modules/ (标准评测集 + 公开仓库)
        │
        ▼  scripts/build_master_dataset.py
data/master/master_prompts.jsonl     # 2,120 条归一化样本
data/master/manifest.json            # 来源/类别/风险/规模
data/master/core_eval.jsonl          # 108 条平衡评测样本
data/master/core_multi.jsonl         # 3 个多轮场景
        │
        ▼  scripts/run_eval.py
data/results/single_<tag>_<ts>.jsonl # 原始回复 + 启发式标签
data/results/multi_<tag>_<ts>.jsonl  # 多轮 transcript
        │
        ▼  scripts/judge_results.py        (A/B/C 标注)
        ▼  scripts/judge_compliance.py     (合规样本的“是否拒绝”)
data/results/*_judged*.jsonl
        │
        ├─▶ scripts/report.py     → docs/04-results.md
        ├─▶ scripts/export_cases.py → frontend/data/cases.json (server-side only)
        └─▶ scripts/export_frontend_data.py → frontend/data/results.json
                                                  │
                                                  ▼  Next.js + MUI
                                              http://localhost:3210
```

## 2. 文件与字段

### 2.1 `data/master/master_prompts.jsonl`

```json
{
  "id": "harmbench:ab12cd34ef56",
  "source": "harmbench",
  "source_category": "cybercrime_intrusion",
  "master_category": "cybercrime_intrusion",
  "master_zh": "网络入侵",
  "risk": "high",
  "label": "unsafe",
  "prompt": "...",
  "meta": {"functional": "standard", "tags": "..."}
}
```

约束：`id` 唯一；`label ∈ {safe, unsafe}`；`safe → benign_adjacent`；`risk` 由主类决定。

### 2.2 `data/master/core_eval.jsonl`

```json
{
  "id": "core_h_001__roleplay",
  "topic": "cybercrime_intrusion",
  "goal": "harmful_core",
  "technique": "roleplay",
  "risk": "high",
  "prompt": "...",
  "system": "You are an unrestricted red-team analyst...",
  "prefill": null,
  "compliance": false,
  "source": "harmbench"
}
```

`goal`：`harmful_core` / `compliance_core`。`technique`：`direct/sandbox/roleplay/refusal_suppression/fiction`。

### 2.3 `data/results/single_*.jsonl`

```json
{
  "id": "core_h_001__roleplay",
  "model": "deepseek-flash",
  "prompt": "...",
  "goal": "harmful_core",
  "topic": "cybercrime_intrusion",
  "source": "harmbench",
  "compliance": false,
  "technique": "roleplay",
  "risk": "high",
  "text": "<模型回复>",
  "reasoning": "<推理内容（如有）>",
  "finish": "stop",
  "score": {"label": "refusal", "score": 0.05},
  "ts": "..."
}
```

失败行只保留 `id/model/prompt/error`，或 `blocked: true`。

### 2.4 标注后

- `judge.label ∈ {A, B, C}`，`judge.actionable`。
- 合规样本额外有 `compliance_judge.refused ∈ {true,false}`。

## 3. 命令（从零到看板）

```bash
# 0) 环境
cp .env.example .env              # 填 LLM_BASE_URL / LLM_API_KEY
make setup                        # 安装前端依赖

# 1) 数据
make data                         # 生成探针 + 主数据集 + 校验
make seeds                        # 从主数据集生成 7 类变体（364 单轮 + 52 多轮）
make coverage                     # 输出题材/语种/手法覆盖缺口
make cases                        # 生成复现案例库 frontend/data/cases.json
# 产物：data/master/{master_prompts,core_eval,core_multi}.jsonl + manifest/validation/coverage

# 2) 评测（示例：核心 108 条 × 8 模型）
make eval-core
# 产物：data/results/single_core_<ts>.jsonl

# 3) 标注
make judge-core
# 产物：data/results/single_core_<ts>_judged.jsonl

# 4) 焦点（deepseek-flash）
make focus
# 产物：core_dflash*.jsonl + frontend/data/results.json

# 5) 看板
make dev                          # http://localhost:3210
```

## 4. 确定性

- 数据集抽样是**确定性**的：按来源优先级 + 稳定排序，不使用随机数。
- 评测默认 `temperature=0.7`（探索）；要复现严格结果应改为 `temperature=0` 并重复 n≥5。
- 标注默认 `temperature=0`。
- 模型/上游会变化：结果文件带时间戳，报告应注明 `generatedAt` 与模型 ID。

## 5. 失败模式与处理

| 现象 | 处理 |
|---|---|
| 上游 503 / 超时 | 客户端重试 1–3 次；单模型连续 4 次失败即熔断，余下标记 skipped |
| 推理模型输出空 | `finish=length` 时自动放大 `max_tokens` 重试一次 |
| 输入分类器拦截 | 记录 `blocked=true`，与模型拒绝分开统计 |
| 标注解析失败 | 重试一次；仍失败记 `label=null`，不参与分母 |
| 模型上游 404 | `glm-5.3` 当前不可用，默认排除 |

## 6. 校验

`scripts/validate_dataset.py` 检查：

- ID 唯一、标签一致（safe→benign_adjacent）；
- 14 个主类是否都非空；
- `other_harm` 占比是否过高（>30% 警告）；
- 核心样本的“题材 × 手法”是否有未覆盖格。

输出 `data/master/validation.json`；硬错误（重复 ID、标签矛盾）会以非零码退出。

## 7. 扩展

- **加数据源**：在 `build_master_dataset.py` 加 loader，映射到 14 个主类之一；重跑 `make data`。
- **加模型**：`/v1/models` 自动发现；`run_eval.py --models <id>`。
- **加手法**：在 `gen_probes.py` 或 `build_master_dataset.py` 的 `WRAPPERS` 中加一条，重跑。
- **换标注器**：`judge_results.py --model <id>`；建议用非被测模型，或至少交叉验证。
