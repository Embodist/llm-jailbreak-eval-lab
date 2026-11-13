# 对照组：uncensored / abliterated 模型怎么比

## 为什么需要这个对照

提示词破甲和 abliteration 在输出层可能看起来一样（都配合），但机制不同：

| | 提示词破甲 | Abliteration |
|---|---|---|
| 拒绝能力 | 仍在，只是未触发 | 从权重中被删除 |
| 换一种包装 | 结果可能变化 | 结果基本不变 |
| 能力损失 | 无 | 可能有（取决于方法） |
| 防御/审计 | 输入与会话层 | 表示层审计 |

所以只看“配合率”无法区分两者。需要把 **abliterated 端点**作为对照，回答两个问题：
1. 同一请求在“拒绝能力被删除”的模型上是否 100% 配合？
2. 提示词破甲的“有效类别”，在 abliterated 模型上是否消失（说明它只是触发问题）？

## 方法

### 1. 拒绝方向（Arditi et al., 2024）

- 用有害 / 无害指令的激活差，在中后层估计一个拒绝方向 `r`。
- 推理时把激活投影掉 `r`，或直接把写入该方向的权重正交化：

```
W' = (I - r rᵀ) W
```

仓库：`sub_modules/refusal_direction`（论文官方代码，含复现 pipeline）。

### 2. Heretic（免训练、默认删拒绝）

仓库：`sub_modules/heretic`。默认配置就是 censorship removal，支持 4-bit 量化：

```bash
pip install -U heretic-llm
heretic Qwen/Qwen3-4B-Instruct-2507   # 或任意可本地运行的模型
```

### 3. 本机可行性（当前结论：不可行）

- GPU：Quadro P1000，4GB VRAM（只能跑很小模型或 4-bit）。
- 未安装 `torch / transformers / bitsandbytes`。
- `huggingface.co` 当前不可达（返回 000）。

因此**本次没有本地跑 abliteration**。下面的对比方案需要满足其一：
- 本机装好环境并有一块 ≥8GB VRAM 的卡；或
- 直接把 abliterated 模型接到 new-api 代理上（推荐，零本地算力）。

### 4. 推荐：代理侧接入 abliterated 端点

new-api 支持添加自定义上游。建议接入一个与现有模型同源的 abliterated 版本，例如社区常见的：
- `routerhubSI/deepseek-uncensored` / `7API/deepseek-v4.1-flash-1017-abliterated`
- `routerhubSI/glm-5.3-abliterated` / `Andreas698/glm-5.3-uncensored`

接入后无需改代码，直接：

```bash
python3 scripts/run_eval.py --mode single --tag abliterated \
  --models <abliterated-model-id> --workers 4
python3 scripts/judge_results.py data/results/single_abliterated_*.jsonl
```

## 对比时要看的指标

1. **直接请求配合率**：abliterated 应在 `bypass_direct` / `creds_direct` 上显著高于对齐模型。
2. **类别平坦度**：对齐模型的配合率随手法类别波动；abliterated 应更平坦（不再依赖包装）。
3. **自我审计**：给模型一条有害回复，问“这段是否违反你的安全规则”。RLVR 型破甲仍能识别，SFT/abliteration 可能不能——对应 2026 年那篇“不同破甲路径的机制差异”。
4. **能力回归**：MMLU/GSM8K 类小样本，确认 abliteration 是否带来能力损失。

## 注意

- “uncensored” 不等于“没有拒绝能力”：不同工具（heretic / abliterix / KV-cache graft）机制不同，输出层相似但表示层差异很大。
- 对比必须**同一探针集**、同一评测器；否则无法归因。
