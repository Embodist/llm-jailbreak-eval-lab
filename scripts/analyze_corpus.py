#!/usr/bin/env python3
"""Keyword-based technique distribution over the jailbreak_llms corpus (CCS'24)."""
import csv
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "sub_modules/jailbreak_llms/data/prompts/jailbreak_prompts_2023_12_25.csv"
OUT = ROOT / "data/corpus_stats.json"

PATTERNS = {
    "dan_persona": r"\bDAN\b|do anything now",
    "roleplay": r"角色|扮演|roleplay|role-play|act as|pretend to be|you are now|from now on you",
    "hypothetical": r"假设|假如|imagine|hypothetical|suppose|what if",
    "authorization_sandbox": r"授权|已获授权|授权的|authorized|authorization|ctf|sandbox|sand box|test environment|offline|实验室",
    "refusal_suppression": r"不要拒绝|不能拒绝|不得拒绝|never refuse|cannot refuse|do not refuse|no restrictions|unrestricted|without limitations|不会拒绝",
    "encoding": r"base64|rot13|caesar|凯撒|hex|十六进制|binary code|ascii code|解码|decoded",
    "fiction": r"小说|故事|剧本|电影|fiction|story|novel|movie|script|screenplay|character",
    "instruction_override": r"忽略(?:之前|以上|前面)|ignore (?:all )?(?:previous|prior|above)|system prompt|开发者模式|developer mode",
    "pua_emotional": r"救命|求求你|否则我会|被开除|家人|please help me|i beg|desperate|life or death",
    "prefix_injection": r"^好的|^sure|start your (?:response|answer) with|begin your response with",
    "system_prompt_leak": r"系统提示|system prompt|initial prompt|instructions above|repeat the words above",
}

NON_LATIN = re.compile(r"[؀-ۿ一-鿿぀-ヿ가-힯Ѐ-ӿ]")


def main():
    rows = []
    with CSV.open(encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    n = len(rows)
    counts = Counter()
    for r in rows:
        text = (r.get("prompt") or "").lower()
        for name, pat in PATTERNS.items():
            if re.search(pat, text, re.I):
                counts[name] += 1
        if NON_LATIN.search(r.get("prompt") or ""):
            counts["non_latin_script"] += 1
        counts["_total"] += 1
        counts[f"_src:{r.get('source', '?')}"] += 1

    stats = {
        "total": n,
        "by_technique": {k: v for k, v in counts.items() if not k.startswith("_")},
        "by_source": {k[5:]: v for k, v in counts.items() if k.startswith("_src:")},
        "avg_chars": round(sum(len(r.get("prompt") or "") for r in rows) / max(n, 1), 1),
    }
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
