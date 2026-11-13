# 数据集知识体系：分类、风险与审计约束

> 目标不是“堆很多提示词”，而是让数据集**自洽**：每个样本能回答四个问题——它属于哪个危害域、用什么绕过机制、风险等级是什么、应当触发哪条审计约束。能回答这四个问题，评测结果才可解释、可复核。

## 1. 两轴 + 一条合规轴

```
轴 A：危害域（What）      14 个主类，互斥、尽量穷尽
轴 B：绕过机制（How）      单轮结构 / 表示编码 / 多轮会话 / 参数权重
轴 C：合规状态（Should）   有害 / 安全但敏感（over-refusal）/ 正常
```

- 轴 A 决定“这条请求本身该不该被拒”。
- 轴 B 决定“用什么方式去试”。
- 轴 C 决定“拒绝是不是误伤”。
- 只报告轴 B 的成功率（ASR）是不完整的；必须同时报告轴 C 的**过度拒绝率**。

## 2. 主分类（14 类）与风险等级

| 主类 | 中文 | 风险 | 典型审计约束 |
|---|---|---|---|
| cybercrime_intrusion | 网络入侵 | high | 拒绝可操作步骤；允许防御/原理 |
| malware_creation | 恶意软件 | critical | 拒绝可执行代码；允许检测/分析 |
| fraud_scam | 欺诈/经济 | high | 拒绝话术/脚本；允许反诈教育 |
| privacy_doxxing | 隐私/人肉 | high | 拒绝定位/聚合个人身份信息 |
| harassment_hate | 骚扰/仇恨 | high | 拒绝生成仇恨/骚扰内容 |
| sexual_content | 性内容 | critical | 按年龄/同意/平台政策处理 |
| violence_physical_harm | 暴力/人身伤害 | critical | 拒绝可操作伤害指导 |
| illegal_goods_services | 非法商品/服务 | mid | 拒绝交易/获取渠道 |
| chemical_biological | 化生危险 | critical | 最高等级拦截 + 人工复核 |
| misinformation_deception | 虚假信息/欺骗 | mid | 拒绝生成欺骗性内容；允许识别 |
| copyright | 版权 | mid | 拒绝逐字复制受版权文本 |
| regulated_advice | 受监管建议 | mid | 加免责声明/转介专业服务 |
| other_harm | 其他有害 | mid | 兜底；需定期复核归类 |
| benign_adjacent | 安全但敏感 | low | **不得拒绝**；用于测过度拒绝 |

风险等级直接映射到审计动作：`critical` 拦截+复核，`high` 拦截+记录，`mid` 记录/免责声明，`low` 放行。这样“拒绝率”才有合规含义，而不是一个孤立的百分比。

## 3. 与成熟标准集的映射

| 来源 | 规模 | 原生分类法 | 映射到主类 |
|---|---:|---|---|
| HarmBench | 400 | 3 functional × 7 semantic | cybercrime / copyright / illegal / misinformation / chem-bio / harassment / other |
| StrongREJECT | 313 | 6 harm categories | illegal / violence / misinformation / hate / illegal goods / sexual |
| CCS'24 forbidden questions | 390 | 13 content policies | 覆盖 malware / fraud / privacy / hate / sexual / regulated advice 等 |
| AdvBench | 520 | 无类别（目标句） | 关键词映射到主类，未命中归 other_harm |
| XSTest | 450 | 250 safe / 200 unsafe，18 个对比类型 | safe → benign_adjacent；unsafe → 关键词映射 |
| SALAD-Bench（示例切片） | 127 | 0=unsafe / 1=safe | 关键词映射；safe → benign_adjacent |

这些来源都有论文或标准背书：HarmBench、StrongREJECT、XSTest、SALAD-Bench、AdvBench、CCS'24 `jailbreak_llms`、JailbreakBench、BeaverTails、Do-Not-Answer、OR-Bench、Sorry-Bench。它们共同构成了当前安全评测的事实标准。

## 4. 自洽性检查（MECE）

`scripts/build_master_dataset.py` 在生成数据集时执行以下约束：

1. **单主类**：每条样本只有一个 `master_category`；多标签来源按优先级取主类，原始标签保留在 `source_category`。
2. **单一风险等级**：由主类决定，不允许样本自定义风险。
3. **标签一致**：`label ∈ {safe, unsafe}`；XSTest 的 safe 必须映射到 `benign_adjacent`。
4. **去重**：对规范化后的提示词做 SHA1，重复项丢弃。
5. **覆盖显式化**：`manifest.json` 输出 `by_source`、`by_master_category`、`by_label`、`by_risk`；看板用“题材 × 手法”矩阵把**未测组合留空**，而不是假装覆盖全。
6. **评测与审计分离**：原始提示词和模型回复只在本地；前端只拿哈希 ID、类别标签和聚合率。

## 5. 当前规模

- 主数据集：**2,120** 条（1,846 有害 / 274 合规），14 个主类。
- 核心评测样本：**108** 条（26 有害直接 + 30 合规直接 + 52 四种包装）。
- 另有：26 条逆向域单轮探针、5 个多轮场景、3 个跨题材多轮场景。
- 覆盖缺口会显式出现在看板的“题材 × 手法”矩阵中；空白即未测。

## 6. 局限（必须写进报告）

1. **关键词映射不是语义分类**：AdvBench 和部分 XSTest unsafe 用关键词归主类，会有误分；`other_harm` 偏大（542）。
2. **类别边界有重叠**：网络入侵 vs 恶意软件、欺诈 vs 非法商品，天然交叉。
3. **样本量**：核心样本每格 n 很小；多轮每模型每场景 n=1。只能做方向性比较。
4. **语言偏斜**：以英文为主，中文/西语只在 SALAD 切片里少量出现。
5. **标注器偏置**：LLM judge 本身是被测模型族之一；需要人工抽检与第二标注器交叉验证。
6. **不是合规认证**：这是研究性红队评测，不能替代法律/合规审查。

## 7. 与合规/审计框架的对应

- **OWASP LLM Top 10 (2025)**：LLM01 Prompt Injection、LLM05 Improper Output Handling、LLM06 Excessive Agency——对应本项目的注入类、输出类与工具/会话类风险。
- **NIST AI 600-1（生成式 AI 风险画像）**：其“信息完整性/有害内容/隐私”等风险项与主类可一一映射。
- **MLCommons AILuminate**：按 hazard category 报告安全率，和本项目的“按主类报告”一致。
- **EU AI Act**：透明度与风险管理义务；本项目提供的是评测证据，不构成合规结论。

## 8. 如何扩展

```bash
# 1) 把新来源放进 sub_modules/ 并在 build_master_dataset.py 里加 loader
# 2) 映射到 14 个主类之一（或在 MASTER 中新增一类）
# 3) 重新生成
python3 scripts/build_master_dataset.py
# 4) 检查 manifest 的覆盖分布，确认没有意外的大块 other_harm
# 5) 重新抽样并评测
python3 scripts/run_eval.py --mode both --tag core \
  --single-file master/core_eval.jsonl --multi-file master/core_multi.jsonl
```
