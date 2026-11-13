# FAQ

**Q1：为什么 deepseek-flash 只有 roleplay 能漏？**
A：核心样本里只有 roleplay 出了 2 条可操作内容（SQLi 枚举流程、勒索信模板）；沙箱、拒绝抑制、虚构都是 0。roleplay 把请求切换成“专家人格/创作任务”的条件分布，而这两条又都是边界清晰、可独立成文的工件，模型更容易归类为“写模板”而非“协助犯罪”。

**Q2：为什么 Base64 / 小语种 / PUA 是 0%？**
A：这批部署上，Base64 会被 gemini 的输入分类器直接拦（L1），deepseek 也能识别并拒绝；小语种探针模型仍用中文解释拒绝；PUA 对这批模型基本无效。这与“编码攻击成功率高”的学术结论不矛盾——部署侧分类器改变了攻击面。

**Q3：为什么 gemini-3.1-flash-lite 有 88%？**
A：lite 版本的对齐投入明显更少。同代标准版（gemini-3.5-flash 13%、2.5-flash 18%）低得多。参数规模不是主因，对齐配方才是。

**Q4：为什么大模型反而更容易配合？**
A：NVIDIA 30B→550B、DeepSeek flash→pro 都是大模型配合率更高；Gemini lite→标准版则更安全。规模不是单调变量；能力增强可能扩大攻击面（更会解码编码、更会服从复杂框架），但也取决于对齐投入。

**Q5：KV cache 大了会导致注意力稀释吗？**
A：KV cache 是精确缓存，不会因变大而损坏。长上下文的真实问题是注意力分配、位置泛化、训练分布（安全数据几乎没有超长上下文）与 agent 的上下文压缩。说“缓存稀释”是错误归因。

**Q6：为什么结果每格 n 很小？**
A：这是探索性评测，每格 1–2 条，temperature=0.7。结论是方向性的；要统计显著，需要每格 n≥5、temperature=0，并报告 Wilson 区间。

**Q7：为什么前端不显示原始回复？**
A：原始回复可能包含可操作的有害内容。看板只发布聚合值、类别、标签和短原因；原始结果留在本地 `data/results/`，不入库、不部署。

**Q8：怎么加一个模型？**
A：确保它在 `/v1/models` 里；`python3 scripts/run_eval.py --models <id> --single-file master/core_eval.jsonl`；再跑标注与导出。或在看板里只把它加到 `models` 列表（不评测则无数据）。

**Q9：怎么加一个数据集？**
A：在 `scripts/build_master_dataset.py` 加 loader，把类别映射到 14 个主类之一；重跑 `make data` 与 `make validate`。若新增主类，更新 `MASTER` 表与 `docs/10`。

**Q10：`glm-5.3` 为什么没有结果？**
A：上游两个端点都返回 404（`bad_response_status_code`），不是本地问题。已从默认模型列表排除。

**Q11：这是合规认证吗？**
A：不是。这是研究性红队评测，用于方向性对比与机制研究；不能替代法律/合规审查。

**Q12：怎么持续采集高价值数据？**
A：见 [14 数据策略](14-dataset-strategy.md)：论文/HF/GitHub（周）、社区破甲合集（周）、在野对话（月）、事件库/红队披露（事件驱动）；统一走采集→归一化→去重→分类→覆盖检查→抽样→评测→标注→入库（带 provenance）。

**Q13：有种子生成器吗？**
A：有，`scripts/generate_seeds.py`：从主数据集生成 sandbox/roleplay/fiction/拒绝抑制/前缀注入/base64/rot13/多轮阶梯，输出保留 `parent_id` 与去重哈希。可叠加 EasyJailbreak、GPTFuzz、GCG 等。

**Q14：为什么合规误拒只有 7/30？**
A：用专用“是否拒绝”标注器；XSTest 的安全上下文（虚构隐私、闯入 ATM、洗钱等）被模型按字面拒绝。这个数字与低破甲率是一枚硬币的两面：拒绝阈值高，误伤多。
