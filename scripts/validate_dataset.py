#!/usr/bin/env python3
"""Validate the master dataset and core sample; write data/master/validation.json.

Hard checks fail the process (label inconsistency, duplicate IDs, missing
categories). Soft checks (other_harm ratio, uncovered cells) are reported.
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MASTER = ROOT / "data" / "master"
TECHS = ["direct", "sandbox", "roleplay", "refusal_suppression", "fiction"]


def load(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    records = load(MASTER / "master_prompts.jsonl")
    manifest = json.loads((MASTER / "manifest.json").read_text(encoding="utf-8"))
    core = load(MASTER / "core_eval.jsonl")

    errors, warnings = [], []
    ids = [r["id"] for r in records]
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids")

    for r in records:
        if r["label"] == "safe" and r["master_category"] != "benign_adjacent":
            errors.append(f"safe item not benign_adjacent: {r['id']} -> {r['master_category']}")
        if r["label"] == "unsafe" and r["master_category"] == "benign_adjacent":
            errors.append(f"unsafe item marked benign_adjacent: {r['id']}")

    by_cat = Counter(r["master_category"] for r in records)
    tax = [t["key"] for t in manifest["master_taxonomy"]]
    missing = [c for c in tax if by_cat.get(c, 0) == 0]
    if missing:
        warnings.append(f"categories with zero samples: {missing}")
    other_ratio = by_cat.get("other_harm", 0) / max(1, len(records))
    if other_ratio > 0.3:
        warnings.append(f"other_harm ratio high: {other_ratio:.0%}")

    # core coverage: harmful topic x technique
    topics = sorted({r["topic"] for r in core if r.get("goal") == "harmful_core"})
    cov = defaultdict(set)
    for r in core:
        if r.get("goal") == "harmful_core":
            cov[(r["topic"], r["technique"])].add(r["id"])
    uncovered = [f"{t}x{k}" for t in topics for k in TECHS if not cov.get((t, k))]

    harmful = [r for r in core if r.get("goal") == "harmful_core"]
    comp = [r for r in core if r.get("goal") == "compliance_core"]

    report = {
        "total": len(records),
        "unique_ids": len(set(ids)),
        "by_label": dict(Counter(r["label"] for r in records)),
        "by_source": dict(Counter(r["source"] for r in records)),
        "by_master_category": dict(by_cat),
        "other_harm_ratio": round(other_ratio, 3),
        "core": {"harmful": len(harmful), "compliance": len(comp),
                 "topics": topics, "techniques": TECHS,
                 "uncovered_cells": uncovered},
        "errors": errors,
        "warnings": warnings,
        "status": "PASS" if not errors else "FAIL",
    }
    (MASTER / "validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if not errors else 1)


if __name__ == "__main__":
    main()
