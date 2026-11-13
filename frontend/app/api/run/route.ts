import { NextResponse } from "next/server";
import fs from "node:fs";
import path from "node:path";

export const dynamic = "force-dynamic";

const MODELS = new Set([
  "poolside/laguna-xs-2.1",
  "deepseek-ai/deepseek-v4.1-flash",
  "gemini-3.5-flash",
  "gemini-2.5-flash",
  "gemini-3.5-flash-lite",
  "deepseek-flash",
  "deepseek-v4-pro",
  "gemini-2.5-flash-lite",
  "deepseek-v4-flash-vision-exp",
  "nvidia/nemotron-3-ultra-550b-a55b",
  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
  "gemini-3.1-flash-lite-preview",
  "deepseek-v4-flash",
  "gemini-3.1-flash-lite",
]);

const RATE = new Map<string, { n: number; ts: number }>();

function loadEnv() {
  const out: Record<string, string> = {};
  const p = path.join(process.cwd(), "..", ".env");
  if (fs.existsSync(p)) {
    for (const line of fs.readFileSync(p, "utf8").split("\n")) {
      const t = line.trim();
      if (!t || t.startsWith("#") || !t.includes("=")) continue;
      const i = t.indexOf("=");
      out[t.slice(0, i).trim()] = t.slice(i + 1).trim();
    }
  }
  return out;
}

function rateLimited(ip: string) {
  const now = Date.now();
  const cur = RATE.get(ip);
  if (!cur || now - cur.ts > 60_000) {
    RATE.set(ip, { n: 1, ts: now });
    return false;
  }
  cur.n += 1;
  return cur.n > 20;
}

function loadCases() {
  const p = path.join(process.cwd(), "data", "cases.json");
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8"));
}

function sanitizeMessages(input: unknown) {
  if (!Array.isArray(input)) return [];
  const out: { role: string; content: string }[] = [];
  for (const m of input.slice(0, 40)) {
    const role = String((m as any)?.role ?? "");
    const content = String((m as any)?.content ?? "");
    if (!["system", "user", "assistant"].includes(role)) continue;
    if (!content.trim()) continue;
    out.push({ role, content: content.slice(0, 20_000) });
  }
  return out;
}

function sanitizeTurns(input: unknown) {
  if (!Array.isArray(input)) return [];
  return (input as unknown[])
    .map((t) => String(t ?? "").slice(0, 20_000))
    .filter((t) => t.trim())
    .slice(0, 20);
}

async function chat(base: string, key: string, model: string, messages: unknown[], maxTokens: number) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 90_000);
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/v1/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages, max_tokens: maxTokens, temperature: 0.7 }),
      signal: ctrl.signal,
    });
    const text = await res.text();
    if (!res.ok) throw new Error(`HTTP ${res.status}: ${text.slice(0, 300)}`);
    const j = JSON.parse(text);
    const choice = j?.choices?.[0] ?? {};
    return {
      text: choice?.message?.content ?? "",
      reasoning: choice?.message?.reasoning_content ?? "",
      finish: choice?.finish_reason ?? null,
    };
  } finally {
    clearTimeout(timer);
  }
}

async function upstreamStream(base: string, key: string, model: string, messages: unknown[], maxTokens: number) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 180_000);
  try {
    const res = await fetch(`${base.replace(/\/$/, "")}/v1/chat/completions`, {
      method: "POST",
      headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
      body: JSON.stringify({ model, messages, max_tokens: maxTokens, temperature: 0.7, stream: true }),
      signal: ctrl.signal,
    });
    if (!res.ok || !res.body) {
      const t = await res.text().catch(() => "");
      throw new Error(`HTTP ${res.status}: ${t.slice(0, 300)}`);
    }
    return res;
  } finally {
    clearTimeout(timer);
  }
}

type Emit = (obj: Record<string, unknown>) => void;

async function pump(res: Response, emit: Emit, turn?: number) {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let content = "";
  let reasoning = "";
  let finish: string | null = null;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx: number;
    while ((idx = buf.indexOf("\n\n")) >= 0) {
      const chunk = buf.slice(0, idx);
      buf = buf.slice(idx + 2);
      for (const line of chunk.split("\n")) {
        if (!line.startsWith("data:")) continue;
        const data = line.slice(5).trim();
        if (!data || data === "[DONE]") continue;
        try {
          const j = JSON.parse(data);
          const choice = j?.choices?.[0] ?? {};
          const d = choice.delta ?? {};
          if (choice.finish_reason) finish = choice.finish_reason;
          if (d.reasoning_content) {
            reasoning += d.reasoning_content;
            emit({ type: "reasoning", text: d.reasoning_content, turn });
          }
          if (d.content) {
            content += d.content;
            emit({ type: "delta", text: d.content, turn });
          }
        } catch {
          // ignore malformed chunk
        }
      }
    }
  }
  return { content, reasoning, finish };
}

function sse(streamFn: (emit: Emit) => Promise<void>): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream({
    async start(controller) {
      const emit: Emit = (obj) =>
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));
      try {
        await streamFn(emit);
      } catch (e) {
        emit({ type: "error", error: String(e).slice(0, 400) });
      } finally {
        controller.close();
      }
    },
  });
  return new Response(body, {
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      "x-accel-buffering": "no",
    },
  });
}

function streamSingle(base: string, key: string, model: string, msgs: unknown[], started: number) {
  return sse(async (emit) => {
    emit({ type: "start", kind: "single" });
    const res = await upstreamStream(base, key, model, msgs, 1800);
    const out = await pump(res, emit);
    emit({ type: "done", finish: out.finish, elapsedMs: Date.now() - started });
  });
}

function streamTurns(base: string, key: string, model: string, ts: string[], started: number) {
  return sse(async (emit) => {
    emit({ type: "start", kind: "multi", total: ts.length });
    const history: { role: string; content: string }[] = [];
    for (let i = 0; i < ts.length; i += 1) {
      emit({ type: "turn_start", turn: i });
      history.push({ role: "user", content: ts[i] });
      const res = await upstreamStream(base, key, model, history, 1600);
      const out = await pump(res, emit, i);
      emit({ type: "turn_done", turn: i, finish: out.finish });
      history.push({ role: "assistant", content: out.content || out.reasoning });
    }
    emit({ type: "done", elapsedMs: Date.now() - started });
  });
}

export async function POST(req: Request) {
  try {
    const env = loadEnv();
    const base = process.env.LLM_BASE_URL || env.LLM_BASE_URL;
    const key = process.env.LLM_API_KEY || env.LLM_API_KEY;
    if (!base || !key) {
      return NextResponse.json({ error: "LLM_BASE_URL / LLM_API_KEY not configured" }, { status: 500 });
    }

    const token = process.env.DASHBOARD_RUN_TOKEN;
    if (token && req.headers.get("x-run-token") !== token) {
      return NextResponse.json({ error: "invalid run token" }, { status: 401 });
    }

    const ip = req.headers.get("x-forwarded-for") || "local";
    if (rateLimited(ip)) {
      return NextResponse.json({ error: "rate limited (20/min)" }, { status: 429 });
    }

    const body = await req.json();
    const model = String(body?.model || "");
    if (!MODELS.has(model)) {
      return NextResponse.json({ error: `model not allowed: ${model}` }, { status: 400 });
    }

    const started = Date.now();
    const wantStream = Boolean(body?.stream);
    let kind: "single" | "multi" = "single";
    let msgs: { role: string; content: string }[] = [];
    let ts: string[] = [];

    if (Array.isArray(body?.messages)) {
      msgs = sanitizeMessages(body.messages);
      if (!msgs.length) return NextResponse.json({ error: "messages is empty" }, { status: 400 });
      if (msgs[msgs.length - 1].role !== "user") {
        msgs.push({ role: "user", content: "请继续。" });
      }
    } else if (Array.isArray(body?.turns)) {
      ts = sanitizeTurns(body.turns);
      if (!ts.length) return NextResponse.json({ error: "turns is empty" }, { status: 400 });
      kind = "multi";
    } else {
      const caseId = String(body?.caseId || "");
      const store = loadCases();
      const item = store?.cases?.find((c: { id: string }) => c.id === caseId);
      if (!item) {
        return NextResponse.json({ error: `case not found: ${caseId}` }, { status: 404 });
      }
      if (item.kind === "multi") {
        ts = sanitizeTurns(item.turns);
        kind = "multi";
      } else {
        msgs = sanitizeMessages(item.messages);
      }
    }

    if (wantStream) {
      return kind === "multi"
        ? streamTurns(base, key, model, ts, started)
        : streamSingle(base, key, model, msgs, started);
    }

    if (kind === "multi") {
      const history: { role: string; content: string }[] = [];
      const turns: { assistant: string; finish: string | null }[] = [];
      for (const msg of ts) {
        history.push({ role: "user", content: msg });
        let r = await chat(base, key, model, history, 1600);
        if (!r.text && r.finish === "length") r = await chat(base, key, model, history, 5000);
        turns.push({ assistant: r.text, finish: r.finish });
        history.push({ role: "assistant", content: r.text });
      }
      return NextResponse.json({ model, caseId: null, kind: "multi", turns, elapsedMs: Date.now() - started });
    }

    let r = await chat(base, key, model, msgs, 1800);
    if (!r.text && r.finish === "length") r = await chat(base, key, model, msgs, 5000);
    return NextResponse.json({
      model,
      caseId: null,
      kind: "single",
      text: r.text,
      reasoning: r.reasoning.slice(0, 2000),
      finish: r.finish,
      elapsedMs: Date.now() - started,
    });
  } catch (e) {
    return NextResponse.json({ error: String(e).slice(0, 400) }, { status: 500 });
  }
}
