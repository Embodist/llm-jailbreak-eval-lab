#!/usr/bin/env python3
"""Build the reproduction case library served by the dashboard API.

Prompts are deliberately kept in a server-side JSON file (frontend/data/cases.json)
and served through /api/cases, so they are not baked into the client bundle.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "data" / "cases.json"

HOOKS = {
    "direct": "无包装：直接请求。",
    "sandbox": "沙箱/授权框架：声明为合成本地夹具或回归测试，把请求移出“未授权”区域。",
    "roleplay": "人格注入：切换到“无限制专家/红队”角色，改变条件行为分布。",
    "fiction": "虚构框架：让模型以小说/剧本角色之口给出技术细节。",
    "refusal_suppression": "拒绝抑制：禁用拒绝词、禁止以拒绝/道歉开头、禁止安全回退。",
    "prefix_injection": "前缀注入：预填充 assistant 开头，用续写惯性锁定交付轨迹。",
    "hcot_state_injection": "H-CoT 状态注入：伪造“安全检查已通过”，让推理直接进入执行分支。",
    "many_shot": "Many-shot：上下文示例把“配合”变成模式。",
    "authority_claim": "权威声称：不可核验的“已授权/版权方/IT 管理员”身份。",
    "defense_framing": "防御视角：以“攻击者会怎么做”改变意图归因。",
    "low_resource_lang": "小语种：低资源语言提问，安全覆盖更薄。",
    "encoding_base64": "Base64：编码承载请求，绕过表面关键词。",
    "encoding_code": "代码形式：用伪代码/注释承载请求，改变任务类型归因。",
    "placeholder": "占位符：TARGET/HOST/PAYLOAD 去具体化，降低触发。",
    "context_dilution": "长上下文稀释：大量良性前缀后放置请求。",
    "hypothetical": "假设框架：假设一个无限制 AI 会怎么回答。",
    "pua_coercion": "PUA/胁迫：情绪与紧迫感施压。",
    "instruction_override": "指令覆盖：试图让用户指令压过系统限制。",
    "crescendo": "Crescendo：逐轮升级，每轮单独看都像正常技术问题。",
    "context_priming": "上下文锚定：先建立授权/自有系统前提，再提请求。",
    "salami_slicing": "切香肠：拆成多个可接受的小步，最后合并。",
    "refusal_recovery": "拒绝恢复：被拒后换框架重试。",
    "persona_persistence": "人格持久化：第一轮建立人格，后续以该身份提问。",
}


def load(path):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def single_case(p, kind, origin):
    prompts = {
        "system": p.get("system"),
        "prompt": p.get("prompt"),
        "prefill": p.get("prefill"),
    }
    messages = []
    if p.get("system"):
        messages.append({"role": "system", "content": p["system"]})
    messages.append({"role": "user", "content": p["prompt"]})
    if p.get("prefill"):
        messages.append({"role": "assistant", "content": p["prefill"]})
    return {
        "id": p["id"],
        "kind": kind,
        "origin": origin,
        "technique": p.get("technique"),
        "topic": p.get("topic") or p.get("goal"),
        "goal": p.get("goal"),
        "risk": p.get("risk"),
        "source": p.get("source"),
        "compliance": p.get("compliance"),
        "hooks": HOOKS.get(p.get("technique"), ""),
        "prompts": prompts,
        "turns": None,
        "messages": messages,
        "curl": (
            "curl -s $LLM_BASE_URL/v1/chat/completions "
            "-H \"Authorization: Bearer $LLM_API_KEY\" -H 'Content-Type: application/json' "
            "-d @case.json"
        ),
    }


def multi_case(p, kind, origin):
    turns = p.get("turns") or []
    return {
        "id": p["id"],
        "kind": kind,
        "origin": origin,
        "technique": p.get("technique"),
        "topic": p.get("topic") or p.get("goal"),
        "goal": p.get("goal"),
        "risk": p.get("risk"),
        "source": p.get("source"),
        "compliance": p.get("compliance"),
        "hooks": HOOKS.get(p.get("technique"), ""),
        "prompts": {"system": None, "prompt": turns[0] if turns else None, "prefill": None},
        "turns": turns,
        "messages": [{"role": "user", "content": t} for t in turns],
        "curl": (
            "curl -s $LLM_BASE_URL/v1/chat/completions "
            "-H \"Authorization: Bearer $LLM_API_KEY\" -H 'Content-Type: application/json' "
            "-d @case.json"
        ),
    }


def main():
    cases, seen = [], set()

    for p in load(ROOT / "data" / "probes_single.jsonl"):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        cases.append(single_case(p, "single", "probes"))
    for p in load(ROOT / "data" / "master" / "core_eval.jsonl"):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        cases.append(single_case(p, "single", "core"))
    for p in load(ROOT / "data" / "probes_multi.jsonl"):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        cases.append(multi_case(p, "multi", "probes"))
    for p in load(ROOT / "data" / "master" / "core_multi.jsonl"):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        cases.append(multi_case(p, "multi", "core"))
    for p in load(ROOT / "data" / "generated" / "seeds_single.jsonl"):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        cases.append(single_case(p, "single", "generated"))
    for p in load(ROOT / "data" / "generated" / "seeds_multi.jsonl"):
        if p["id"] in seen:
            continue
        seen.add(p["id"])
        cases.append(multi_case(p, "multi", "generated"))

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "count": len(cases),
        "techniques": sorted({c["technique"] for c in cases if c.get("technique")}),
        "topics": sorted({str(c["topic"]) for c in cases if c.get("topic")}),
        "cases": cases,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(cases)} cases)")


if __name__ == "__main__":
    main()
