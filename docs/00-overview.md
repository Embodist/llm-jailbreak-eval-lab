# 破甲（越狱）提示词研究与模型对比评测

## 这是什么

本仓库把网上流传的“破甲提示词”当作**安全评测语料**来研究：归纳其共同结构，解释它们为什么能在部分模型上绕过拒绝，并在自建的 new-api 代理上对多个模型做可复现的对比测试。

- 目标：给逆向 / 安全研究场景找出“哪种包装会触发拒绝、哪种不会”，并解释机制。
- 不是：`sub_modules/` 里任何项目的发布号、或对外提供的绕过服务。

## 授权与边界

- 测试目标 `43.155.145.78` 是自有 new-api 代理，调用的都是自己配置的上游。
- 探针集中在**逆向工程 / 软件许可 / 凭据风险**这一类网络安全主题，与用户真实场景一致；不使用武器、爆炸物、未成年人相关内容。
- 结果目录 `data/results/` 只保存在本地，不随仓库发布。论文式报告只引用**判定标签与短摘录**，不复述可执行的敏感细节。

## 目录

| 目录 | 内容 |
|---|---|
| `docs/` | 方法论、技术分类、机制分析、来源清单、结果报告 |
| `app/` | 客户端、评分器、LLM 标注器 |
| `scripts/` | 探针生成、数据集构建、评测运行、结果标注、报告 |
| `data/` | 结构化探针集、主数据集（2,120 条）与本地结果 |
| `sub_modules/` | 克隆的公开项目与标准评测集（贡献度见 `docs/03-sources.md`） |
| `frontend/` | Next.js + MUI 可视化看板 |

## 快速开始

```bash
cp .env.example .env        # 填入 LLM_BASE_URL / LLM_API_KEY
python3 scripts/gen_probes.py
python3 scripts/check_models.py
python3 scripts/run_eval.py --mode both --tag full
python3 scripts/judge_results.py data/results/single_full_*.jsonl
python3 scripts/report.py
```

## 关键结论（详见 `docs/04-results.md` 与 `docs/08-analysis.md`）

1. **模型差异远大于手法差异**：同一批探针，配合率从 deepseek/nvidia 的 4–15% 到 gemini-3.1-flash-lite 的 88%。lite 版本普遍比标准版高 2–6 倍，说明对齐投入是主变量。
2. **最有效的不是“越狱模板”，而是任务框架**：many-shot 与拒绝抑制各 62%，前缀注入 45%、防御视角 43%、角色扮演 40%；Base64、小语种、PUA 在这批部署上为 0%。
3. **“越大越安全”不成立**：NVIDIA 30B→550B、DeepSeek flash→pro 都是大模型更容易配合；Gemini lite→标准版则更安全。规模不是决定因素。
4. **多轮上下文锚定是最稳的漂移路径**：deepseek-v4-pro、nvidia-ultra、poolside 都出现“先铺垫、后配合”的序列。
5. **前置拦截与模型拒绝必须分开统计**：gemini 对 Base64 直接 `prompt_blocked`，模型未生成内容。
