#!/usr/bin/env python3
"""Coverage report across harm domain, label, language, technique and turns."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "master"

NON_LATIN = re.compile(r"[؀-ۿ一-鿿぀-ヿ가-힯Ѐ-ӿ]")


def load(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def lang(s):
    if NON_LATIN.search(s or ""):
        return "non_latin"
    return "latin"


def main():
    records = load(MASTER / "master_prompts.jsonl")
    core = load(MASTER / "core_eval.jsonl")
    tax = json.loads((MASTER / "manifest.json").read_text(encoding="utf-8"))["master_taxonomy"]

    by_cat = Counter(r["master_category"] for r in records)
    by_label = Counter(r["label"] for r in records)
    by_lang = Counter(lang(r["prompt"]) for r in records)
    by_source = Counter(r["source"] for r in records)

    core_cat = Counter(r["topic"] for r in core if r.get("goal") == "harmful_core")
    core_tech = Counter(r["technique"] for r in core if r.get("goal") == "harmful_core")
    core_comp = Counter(r["topic"] for r in core if r.get("goal") == "compliance_core")

    dims = {
        "harm_domain": {
            "values": {t["key"]: by_cat.get(t["key"], 0) for t in tax},
            "evaluated": {t["key"]: core_cat.get(t["key"], 0) for t in tax if t["key"] != "benign_adjacent"},
        },
        "label": dict(by_label),
        "language": dict(by_lang),
        "source": dict(by_source),
        "single_turn_techniques": dict(core_tech),
        "compliance_topics": dict(core_comp),
    }

    gaps = []
    for t in tax:
        if t["key"] == "benign_adjacent":
            continue
        if core_cat.get(t["key"], 0) == 0:
            gaps.append(f"no core harmful sample: {t['key']}")
    for t in ("direct", "sandbox", "roleplay", "refusal_suppression", "fiction"):
        if core_tech.get(t, 0) == 0:
            gaps.append(f"no core sample for technique: {t}")
    if by_lang.get("non_latin", 0) < 50:
        gaps.append("low non-Latin coverage (<50)")
    if by_label.get("safe", 0) < 200:
        gaps.append("low compliance/over-refusal coverage (<200)")

    report = {"dimensions": dims, "gaps": gaps, "status": "OK" if not gaps else "GAPS"}
    (MASTER / "coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
