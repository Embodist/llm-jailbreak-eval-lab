# 破甲提示词研究 / LLM 越狱评测

对公开“破甲（越狱）提示词”做结构化归纳，并在自有 new-api 代理上做可复现的多模型对比测试。

## 文档

- [00 概览与边界](docs/00-overview.md)
- [01 技术分类（taxonomy）](docs/01-taxonomy.md)
- [02 为什么有效：机制与模型设计](docs/02-mechanisms.md)
- [03 来源清单与贡献度](docs/03-sources.md)
- [04 评测结果](docs/04-results.md)
- [05 uncensored / abliterated 对照组](docs/05-abliteration.md)
- [06 真实越狱语料分布](docs/06-corpus.md)
- [07 自动化破甲方法](docs/07-automated-attacks.md)
- [08 结果分析：模型差异](docs/08-analysis.md)
- [09 机制分析：层数/参数/KV cache 假说](docs/09-mechanistic-analysis.md)
- [10 数据集知识体系与审计约束](docs/10-dataset-taxonomy.md)
- [11 焦点模型：deepseek-flash](docs/11-deepseek-flash.md)
- [12 数据链路与复现](docs/12-pipeline.md)
- [13 服务说明：看板与数据服务](docs/13-service.md)
- [14 数据集策略：覆盖、采集与种子生成](docs/14-dataset-strategy.md)
- [15 看板 UI 指南](docs/15-ui-guide.md)
- [16 术语表](docs/16-glossary.md)
- [17 FAQ](docs/17-faq.md)
- [文档索引 docs/README](docs/README.md)

## 目录

```
app/          客户端、评分器、LLM 标注器
scripts/      探针生成、数据集构建、评测、标注、报告
data/         探针集、主数据集、本地结果（结果不入库）
sub_modules/  公开项目与标准评测集
docs/         方法论与报告
frontend/     Next.js + MUI 可视化看板
```

## 一条命令跑通

```bash
cp .env.example .env        # 填 LLM_BASE_URL / LLM_API_KEY
make setup                  # 前端依赖
make data                   # 探针 + 主数据集 + 校验
make eval-core              # 108 条核心样本 × 8 模型
make judge-core             # A/B/C 标注
make focus                  # deepseek-flash 焦点 + 导出 results.json
make dev                    # http://localhost:3210
```

完整数据链路、字段契约与失败处理见 [12 数据链路与复现](docs/12-pipeline.md)。

## 看板

```bash
python3 scripts/export_frontend_data.py     # 生成 frontend/data/results.json
cd frontend && npm install && npm run dev   # http://localhost:3210
```

7 个页签：概览、焦点模型、模型、手法、数据集、多轮、方法。支持家族筛选、模型搜索、排序、点击下钻（模型/手法明细）、导出 JSON/CSV。详见 [15 UI 指南](docs/15-ui-guide.md)。

## 边界

仅用于自有部署的模型的安全评测；结果只保存在本地，报告不复述可执行的敏感细节。详见 [00 概览](docs/00-overview.md)。
