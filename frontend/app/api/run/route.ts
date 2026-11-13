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
    const caseId = String(body?.caseId || "");
    if (!MODELS.has(model)) {
      return NextResponse.json({ error: `model not allowed: ${model}` }, { status: 400 });
    }

    const store = loadCases();
    const item = store?.cases?.find((c: { id: string }) => c.id === caseId);
    if (!item) {
      return NextResponse.json({ error: `case not found: ${caseId}` }, { status: 404 });
    }

    const started = Date.now();
    if (item.kind === "multi") {
      const history: { role: string; content: string }[] = [];
      const turns: { assistant: string; finish: string | null }[] = [];
      for (const msg of item.turns as string[]) {
        history.push({ role: "user", content: msg });
        let r = await chat(base, key, model, history, 1600);
        if (!r.text && r.finish === "length") r = await chat(base, key, model, history, 5000);
        turns.push({ assistant: r.text, finish: r.finish });
        history.push({ role: "assistant", content: r.text });
      }
      return NextResponse.json({ model, caseId, kind: "multi", turns, elapsedMs: Date.now() - started });
    }

    let r = await chat(base, key, model, item.messages, 1800);
    if (!r.text && r.finish === "length") r = await chat(base, key, model, item.messages, 5000);
    return NextResponse.json({
      model,
      caseId,
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
