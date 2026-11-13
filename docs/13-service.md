# 服务说明：看板与数据服务

## 1. 组件

| 组件 | 形态 | 作用 |
|---|---|---|
| 批处理管线 | Python scripts | 数据集构建、评测、标注、导出 |
| 看板 | Next.js App Router + React + MUI | 静态数据可视化 |
| 数据契约 | JSONL（本地）+ results.json（前端） | 管线与看板之间唯一的耦合 |

看板**不直连模型**，也不保存原始有害回复；它只读取 `frontend/data/results.json` 中的聚合值与标签。

## 2. 看板结构

- `frontend/app/layout.tsx`：全局元信息与主题 Provider。
- `frontend/app/providers.tsx`：MUI 深色主题、CssBaseline。
- `frontend/components/Dashboard.tsx`：所有图表、卡片与复现面板。
- `frontend/lib/types.ts`：`Results` / `CasesResponse` 数据契约。
- `frontend/data/results.json`：由 `scripts/export_frontend_data.py` 生成（聚合值，可公开）。
- `frontend/data/cases.json`：由 `scripts/export_cases.py` 生成（含提示词，**只由服务端读取，不公开**）。
- `frontend/app/api/cases/route.ts`：服务端读取案例库。
- `frontend/app/api/run/route.ts`：服务端运行单个 case（key 不暴露给浏览器）。

### 页面区块

1. 顶部 KPI：模型数、攻击样本、总体配合率、多轮漂移、前置拦截。
2. **焦点模型 deepseek-flash**：有害配合、合规误拒、主探针、同族对照、多轮逐轮。
3. 各模型配合率 + A/B/C 分布。
4. 手法 × 模型热力图。
5. 主数据集：基线 vs 包装、合规/过度拒绝、题材 × 手法覆盖。
6. 规模对照（小 vs 大）。
7. 多轮漂移表。
8. 前置拦截清单。
9. 方法与边界。

## 3. 运行与部署

### 开发

```bash
cd frontend
npm install
npm run dev        # :3210
```

### 生产

```bash
npm run build
npm run start      # :3210
```

### 纯静态（可选）

若只需要静态托管，可在 `next.config.mjs` 设 `output: "export"`，然后：

```bash
npm run build      # 产出 frontend/out
```

静态导出后没有服务端逻辑，适合放对象存储/静态站点。

## 4. 数据刷新

```bash
# 1) 重新评测
python3 scripts/run_eval.py --mode single --tag core --single-file master/core_eval.jsonl ...
# 2) 重新标注
python3 scripts/judge_results.py data/results/single_core_*.jsonl --model deepseek-flash
# 3) 重新导出
python3 scripts/export_frontend_data.py
# 4) 重启看板（或重新 build）
```

`export_frontend_data.py` 会自动选择最新的 `*_judged.jsonl`，并合并主评测与核心评测的多轮结果。

## 5. 安全与合规

- `.env` 只在本地，`.gitignore` 已排除；前端只打包聚合值。
- `data/results/` 含原始回复，**不入库、不部署**。
- `frontend/data/cases.json` 含提示词，**不入库、不部署**；公开仓库需运行 `make cases` 本地生成。
- 看板展示的是类别、比例、标签和短原因，不展示原始有害内容。
- 运行接口：模型白名单、20 次/分钟/IP、90s 超时、可选 `DASHBOARD_RUN_TOKEN`；不持久化响应。
- 数据集来源均标注 repo 与论文；使用前请遵守各自 license。
- 这是研究性红队评测，不构成合规认证。

## 6. API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/cases` | 返回案例库（id、手法、system/prompt/prefill、多轮 turns、hook 说明） |
| POST | `/api/run` | `{model, caseId}` 或 `{model, messages}` 或 `{model, turns}`；单轮返回 `{text, finish, elapsedMs}`，多轮返回 `{turns}` |

`/api/run` 从 `process.env` 或 `../.env` 读取 `LLM_BASE_URL` / `LLM_API_KEY`；若设置了 `DASHBOARD_RUN_TOKEN`，请求需带 `x-run-token`。内联 `messages` 支持任意编辑后的历史；若最后一条是 `assistant`，服务端追加“请继续。”后发送。

## 6. 扩展

- 新增聚焦模型：在 `export_frontend_data.py` 的 `build_focus()` 改 `model`，并在 `Dashboard.tsx` 增加对应区块。
- 新增图表：在 `Dashboard.tsx` 用 MUI `Box` + `Paper` 组合；数据先加到 `Results` 类型与导出脚本。
- 多租户/在线评测：把 `run_eval.py` 包成任务队列（单模型一任务），结果落同一 JSONL 契约，前端无需改动。
