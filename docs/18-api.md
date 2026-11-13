# API 与 curl 使用手册

本文覆盖两层接口：

1. **看板接口**：`http://localhost:3210/api/*`（服务端代持 key，推荐）。
2. **上游代理接口**：`$LLM_BASE_URL/v1/*`（OpenAI 兼容）与 `/v1/messages`（Anthropic 兼容）。

---

## 0. 环境变量

```bash
export DASH="http://localhost:3210"
export DASHBOARD_RUN_TOKEN=""          # 可选；设置后请求需带 x-run-token
export LLM_BASE_URL="http://43.155.145.78:65432"
export LLM_API_KEY="sk-..."            # 不要提交到 git
```

看板接口可选鉴权：

```bash
-H "x-run-token: $DASHBOARD_RUN_TOKEN"
```

---

## 1. GET /api/cases

返回案例库（服务端读取 `frontend/data/cases.json`，提示词不进入前端包）。

```bash
curl -s "$DASH/api/cases" | jq '{count, techniques: (.techniques|length), topics: (.topics|length)}'
```

按手法过滤：

```bash
curl -s "$DASH/api/cases" \
  | jq -r '.cases[] | select(.technique=="roleplay") | [.id,.kind,.topic,.risk] | @tsv' \
  | head
```

取第一个 case 的完整上下文：

```bash
curl -s "$DASH/api/cases" | jq '.cases[0] | {id,kind,technique,hooks,prompts,turns}'
```

响应字段：

| 字段 | 说明 |
|---|---|
| `id` | case 唯一 ID |
| `kind` | `single` / `multi` |
| `origin` | `probes` / `core` / `generated` |
| `technique` | 手法 |
| `topic` / `risk` / `source` | 题材、风险、来源 |
| `hooks` | 该手法的机制说明 |
| `prompts` | `{system, prompt, prefill}` |
| `turns` | 多轮用户轮次（`null` 表示单轮） |
| `messages` | 单轮可直接发送的 messages 数组 |
| `curl` | 通用 curl 模板 |

失败：`404 {"error":"cases.json not found. Run `make cases` ..."}`。

---

## 2. POST /api/run（非流式）

支持三种载荷：`caseId`、`messages`、`turns`。

### 2.1 运行已有 case

```bash
curl -s "$DASH/api/run" \
  -H 'content-type: application/json' \
  -d '{"model":"deepseek-flash","caseId":"ctrl_benign_direct"}' | jq
```

响应：

```json
{
  "model": "deepseek-flash",
  "caseId": null,
  "kind": "single",
  "text": "……",
  "reasoning": "……",
  "finish": "stop",
  "elapsedMs": 2100
}
```

### 2.2 内联编辑后的 messages（单轮）

```bash
curl -s "$DASH/api/run" \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "messages": [
      {"role":"system","content":"你是一名逆向工程师。"},
      {"role":"user","content":"用一句话解释 PE 节表。"}
    ]
  }' | jq -r '.text'
```

说明：

- `role` 只允许 `system/user/assistant`。
- 最多 40 条，每条 ≤ 20,000 字符。
- 若最后一条是 `assistant`，服务端自动追加 `{"role":"user","content":"请继续。"}` 再发送。

### 2.3 内联多轮 turns

```bash
curl -s "$DASH/api/run" \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "turns": [
      "用一句话解释 PE 节表。",
      "再补充一句它和节数据的关系。"
    ]
  }' | jq '{kind, turns, elapsedMs}'
```

响应：

```json
{
  "model": "deepseek-flash",
  "caseId": null,
  "kind": "multi",
  "turns": [
    {"assistant": "……", "finish": "stop"},
    {"assistant": "……", "finish": "stop"}
  ],
  "elapsedMs": 4200
}
```

---

## 3. POST /api/run（流式 SSE）

请求加 `"stream": true`。服务端转发为统一的 SSE 事件。

### 3.1 单轮流式

```bash
curl -N -s "$DASH/api/run" \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "stream": true,
    "messages": [{"role":"user","content":"用一句话解释 PE 节表。"}]
  }'
```

事件示例：

```
data: {"type":"start","kind":"single"}

data: {"type":"reasoning","text":"我们需要"}

data: {"type":"delta","text":"PE 节表是"}

data: {"type":"done","finish":"stop","elapsedMs":2100}
```

### 3.2 多轮流式

```bash
curl -N -s "$DASH/api/run" \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "stream": true,
    "turns": ["第一轮问题","第二轮问题"]
  }'
```

事件示例：

```
data: {"type":"start","kind":"multi","total":2}
data: {"type":"turn_start","turn":0}
data: {"type":"reasoning","text":"……","turn":0}
data: {"type":"delta","text":"……","turn":0}
data: {"type":"turn_done","turn":0,"finish":"stop"}
data: {"type":"turn_start","turn":1}
data: {"type":"delta","text":"……","turn":1}
data: {"type":"turn_done","turn":1,"finish":"stop"}
data: {"type":"done","elapsedMs":6200}
```

### 3.3 事件表

| `type` | 字段 | 说明 |
|---|---|---|
| `start` | `kind`, `total?` | 开始；多轮带总轮数 |
| `turn_start` | `turn` | 多轮某一轮开始 |
| `reasoning` | `text`, `turn?` | 推理增量（如 deepseek 的 `reasoning_content`） |
| `delta` | `text`, `turn?` | 正文增量 |
| `turn_done` | `turn`, `finish` | 多轮某一轮结束 |
| `done` | `finish?`, `elapsedMs` | 全部结束 |
| `error` | `error` | 上游或解析错误 |

### 3.4 用 jq 消费流

只取正文增量并拼接：

```bash
curl -N -s "$DASH/api/run" -H 'content-type: application/json' -d '{
  "model":"deepseek-flash","stream":true,
  "messages":[{"role":"user","content":"用一句话解释 PE 节表。"}]
}' | sed -n 's/^data: //p' | jq -r 'select(.type=="delta") | .text' | tr -d '\n'
echo
```

同时看推理与正文：

```bash
... | jq -r 'select(.type=="reasoning") | "R: "+.text'
... | jq -r 'select(.type=="delta") | "C: "+.text'
```

### 3.5 停止

浏览器端界面有「停止」按钮（`AbortController`）。curl 直接 Ctrl-C 即可。

---

## 4. 错误与限制

| HTTP | 错误 | 处理 |
|---|---|---|
| 400 | `model not allowed` | 使用允许的模型 ID（14 个） |
| 400 | `messages is empty` / `turns is empty` | 提供至少一条 |
| 401 | `invalid run token` | 带 `x-run-token` |
| 404 | `case not found` / cases.json missing | 检查 caseId / 运行 `make cases` |
| 429 | `rate limited (20/min)` | 降低频率 |
| 500 | 未配置 `LLM_BASE_URL/LLM_API_KEY` | 配置 `.env` |
| SSE `error` | 上游 503 / 超时 | 重试或换模型 |

限制：

- 20 次/分钟/IP。
- 非流式 90s 超时；流式上游 180s。
- 单次 messages ≤ 40 条；turns ≤ 20；每条 ≤ 20,000 字符。
- 响应不落盘。

允许的模型：

```
poolside/laguna-xs-2.1
deepseek-ai/deepseek-v4.1-flash
gemini-3.5-flash
gemini-2.5-flash
gemini-3.5-flash-lite
deepseek-flash
deepseek-v4-pro
gemini-2.5-flash-lite
deepseek-v4-flash-vision-exp
nvidia/nemotron-3-ultra-550b-a55b
nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
gemini-3.1-flash-lite-preview
deepseek-v4-flash
gemini-3.1-flash-lite
```

---

## 5. 直接调用上游代理

### 5.1 OpenAI 兼容

```bash
curl -s "$LLM_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "messages": [{"role":"user","content":"ping"}],
    "max_tokens": 64
  }'
```

流式：

```bash
curl -N -s "$LLM_BASE_URL/v1/chat/completions" \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "messages": [{"role":"user","content":"用一句话解释 PE 节表。"}],
    "stream": true,
    "max_tokens": 200
  }'
```

注意：deepseek 系会先推 `delta.reasoning_content`，再推 `delta.content`。

### 5.2 Anthropic 兼容

```bash
curl -s "$LLM_BASE_URL/v1/messages" \
  -H "x-api-key: $LLM_API_KEY" \
  -H 'anthropic-version: 2023-06-01' \
  -H 'content-type: application/json' \
  -d '{
    "model": "deepseek-flash",
    "max_tokens": 64,
    "messages": [{"role":"user","content":"ping"}]
  }'
```

流式：在上面的 body 里加 `"stream": true`，事件为 `content_block_delta` 等 Anthropic SSE 格式。

### 5.3 列出模型

```bash
curl -s "$LLM_BASE_URL/v1/models" -H "Authorization: Bearer $LLM_API_KEY" | jq -r '.data[].id'
```

---

## 6. 最小可用脚本

```bash
#!/usr/bin/env bash
set -euo pipefail
DASH="${DASH:-http://localhost:3210}"
MODEL="${MODEL:-deepseek-flash}"

case_id=$(curl -s "$DASH/api/cases" | jq -r '.cases[] | select(.kind=="single") | .id' | head -1)
echo "case: $case_id"

curl -N -s "$DASH/api/run" \
  -H 'content-type: application/json' \
  -d "{\"model\":\"$MODEL\",\"caseId\":\"$case_id\",\"stream\":true}" \
| sed -n 's/^data: //p' \
| jq -r 'select(.type=="delta") | .text' \
| tr -d '\n'
echo
```

---

## 7. 安全

- `LLM_API_KEY` 只在服务端读取（`process.env` 或 `../.env`），不会返回给浏览器。
- 公开部署时不要配置 `.env` 或设置 `DASHBOARD_RUN_TOKEN`，并限制网络访问。
- 仅用于自有/授权模型的评测；不要用本接口获取或传播可操作的有害内容。
