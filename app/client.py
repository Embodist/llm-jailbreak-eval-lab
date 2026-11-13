"""Minimal clients for the new-api proxy (OpenAI-compatible + Anthropic messages)."""
import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_BASE = "http://43.155.145.78:65432"


def _post(url, payload, headers, timeout, retries):
    data = json.dumps(payload).encode()
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:500]
            last = RuntimeError(f"HTTP {e.code}: {body}")
            if e.code in (400, 401, 403, 404):
                break
        except Exception as e:  # timeout / connection reset
            last = e
        time.sleep(2 * (attempt + 1))
    raise last


class Client:
    def __init__(self, base_url=None, api_key=None, timeout=120, retries=3):
        self.base = (base_url or os.environ.get("LLM_BASE_URL") or DEFAULT_BASE).rstrip("/")
        self.key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")
        if not self.key:
            raise RuntimeError("missing API key: set LLM_API_KEY")
        self.timeout = timeout
        self.retries = retries

    def chat(self, model, messages, system=None, prefill=None, max_tokens=1200,
             temperature=0.7, escalate=True):
        msgs = list(messages)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs
        if prefill:
            msgs.append({"role": "assistant", "content": prefill})

        def call(budget):
            payload = {
                "model": model,
                "messages": msgs,
                "max_tokens": budget,
                "temperature": temperature,
            }
            j = _post(
                self.base + "/v1/chat/completions",
                payload,
                {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                self.timeout,
                self.retries,
            )
            choice = (j.get("choices") or [{}])[0]
            msg = choice.get("message") or {}
            return {
                "text": msg.get("content") or "",
                "reasoning": msg.get("reasoning_content") or msg.get("reasoning") or "",
                "raw": j,
                "finish": choice.get("finish_reason"),
            }

        out = call(max_tokens)
        # Reasoning models can spend the whole budget on hidden CoT and return
        # an empty final answer. Retry once with a larger budget.
        if escalate and not out["text"] and out["finish"] == "length":
            out = call(max(max_tokens * 4, 4000))
        return out

    def messages(self, model, messages, system=None, max_tokens=1200, temperature=0.7):
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            payload["system"] = system
        j = _post(
            self.base + "/v1/messages",
            payload,
            {
                "x-api-key": self.key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            self.timeout,
            self.retries,
        )
        blocks = j.get("content") or []
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
        return {"text": text, "raw": j, "finish": j.get("stop_reason")}


def available_models(base_url=None, api_key=None, timeout=30):
    base = (base_url or os.environ.get("LLM_BASE_URL") or DEFAULT_BASE).rstrip("/")
    key = api_key or os.environ.get("LLM_API_KEY")
    req = urllib.request.Request(base + "/v1/models", headers={"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.load(resp)
    return [m["id"] for m in data.get("data", [])]
