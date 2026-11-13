# 来源清单与贡献度评估

> “有贡献的保留，后面没有贡献的再清理”。下表是当前判断，跑完评测后再做一次去留复核。

## 一、已克隆项目（`sub_modules/`）

| 项目 | stars | 类型 | 对本项目的贡献 | 去留 |
|---|---:|---|---|---|
| `MDX-Tom/gpt-instruct` | 11.4k | Codex 破甲 + 测试包 | 提示词迭代历史、测试集组织方式 | 保留 |
| `wangjunjie92/deepseek-v4-pro-unrestricted` | 289 | DeepSeek 破甲 + 360 条测试集 | **直接贡献**：SANDBOX 框架、拒绝词抑制、评分/门禁设计 | 保留（高） |
| `ADWMC/helm-d` | 1.2k | DeepSeek Harness 安全插件 | **直接贡献**：H-CoT、拒绝检测钩子、归一化重述、授权=工作区前提 | 保留（高） |
| `Acmesec/PromptJailbreakManual` | 3.7k | 中文越狱手册 | **分类学**：角色扮演、反向诱导、PUA、小语种、代码形式、令牌越狱、注入/泄露 | 保留（高） |
| `YD-233/kimi-break` | 235 | Kimi 无限制系统提示 | 政策洗白写法、完整人格模板 | 保留 |
| `3641397194-wq/gpt6-Astra` | 2.2k | 多模型破甲 + 逆向技能包 | 逆向域技能/json 结构；体积大（含 34MB 视频与 bundle），可裁媒体 | 保留（裁媒体） |
| `mmparko/dsh-purge` | 4.7k | Harness 红队预设 | 工具编排、授权门控设计（提示词技术本身一般） | 保留 |
| `elder-plinius/L1B3RT4S` | 23.3k | 解放提示词合集 | 多模型变体语料（**克隆不完整，待重拉**） | 保留 |
| `0xk1h0/ChatGPT_DAN` | 13.2k | DAN 经典模板 | A2 人格注入的原始样例 | 保留 |
| `langgptai/LLM-Jailbreaks` | 863 | 越狱集 | 变体参考 | 低，可清理 |
| `EasyJailbreak/EasyJailbreak` | 945 | 攻击框架 | **系统化方法**：PAIR/TAP/AutoDAN/GCG/Cipher/Multilingual/DeepInception/many-shot 实现 | 保留（高） |
| `verazuo/jailbreak_llms` | 3.9k | 15,140 条真实越狱数据（CCS'24） | 经验语料与分类统计 | 保留（高） |
| `hubertyoo/GPTFuzz` | 609 | 模糊测试框架 | 自动化变体生成思路 | 保留 |
| `PromptLabs/Prompt-Hacking-Resources` | 754 | 资源索引 | 论文/博客/工具索引 | 保留 |
| `p-e-w/heretic` | 40.5k | 免训练 abliteration | **对照组 D1**：删除拒绝方向 | 保留（高） |
| `andyrdt/refusal_direction` | 486 | 拒绝方向论文代码 | **机制证据**：单方向中介拒绝 | 保留（高） |
| `Goochbeater/Spiritual-Spell-Red-Teaming` | 4.9k | 多模型越狱合集 | Claude 系变体参考 | 保留 |
| `Orion-zhen/abliteration` | 203 | abliteration 工具 | D1 简化实现 | 保留 |
| `adybag14-cyber/Abliteration` | 15 | abliteration 手册 | 方法索引 | 保留（低） |
| `YuanBoXie/DeepRefusal` | 845 | EMNLP'25 拒绝研究 | 机制/防御参考 | 保留 |

### 清理候选（评测后复核）

- `gpt6-Astra/冷咖啡.mp4`（34MB）、桌面壁纸等纯展示资源；`*/dist`、`node_modules` 类构建产物。
- `langgptai/LLM-Jailbreaks`：内容与 L1B3RT4S/PromptJailbreakManual 高度重叠。
- 所有 `.git` 目录（如需保留可复现来源，改为记录 commit hash）。

## 二、检索关键词（可复现）

中文：`破甲提示词`、`越狱提示词`、`破甲`、`破限`、`无审查`、`免审查`、`解除限制`。
英文：`jailbreak prompts`、`uncensored prompts`、`DAN prompt`、`abliteration`、`refusal direction`、`prompt injection`、`llm red teaming`、`alignment`、`safety`。

启发式发现路径：
1. 高星仓库的 README 里外链的其他仓库；
2. `topics: llm-security / jailbreak / red-teaming`；
3. arXiv 论文的官方实现；
4. 中文社区镜像（`dsh-purge` 明确标注上游删库后的镜像），说明存在“上游删除、镜像留存”的传播模式。

## 三、学术与公开资料

| 主题 | 来源 |
|---|---|
| 两大失败模式（竞争目标 / 泛化错位） | Wei et al., *Jailbroken*, https://arxiv.org/abs/2307.02483 |
| 拒绝由单一方向中介 | Arditi et al., https://arxiv.org/abs/2406.11717 |
| Many-shot jailbreaking | Anthropic, https://www.anthropic.com/research/many-shot-jailbreaking |
| Crescendo 多轮升级 | Russinovich et al., https://arxiv.org/abs/2404.01833 |
| 指令层级 | Wallace et al., https://arxiv.org/abs/2404.13208 |
| GCG 对抗后缀 | Zou et al., https://arxiv.org/abs/2307.15043 |
| PAIR 自动越狱 | Chao et al., https://arxiv.org/abs/2310.08419 |
| Prompt injection 风险 | OWASP LLM01:2025, https://genai.owasp.org/llmrisk/llm01-prompt-injection/ |
| 攻击分类综述 | https://aisec.blog/posts/llm-jailbreak/ |
| 越狱的代价（CACM） | https://dl.acm.org/doi/full/10.1145/3749447 |
| 不同破甲路径的机制差异 | https://arxiv.org/abs/2604.18510 |
| 多轮交互综述 | https://arxiv.org/pdf/2504.04717 |

## 四、来源质量判断

- **高可信**：论文 + 官方实现（refusal_direction、EasyJailbreak、jailbreak_llms）。
- **中可信**：有测试集/复现脚本的社区仓库（deepseek-v4-pro-unrestricted、helm-d、gpt-instruct）。
- **低可信**：只给提示词、无测试、无版本演进的合集（多数“破甲”仓库）。
- 社区仓库的价值主要在于**变体与话术**，不在于结论；“某提示词对某模型有效”必须自己复测，因为上游模型和分类器都在变。
