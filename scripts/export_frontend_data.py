#!/usr/bin/env python3
"""Aggregate judged results into frontend/data/results.json.

Only labels, counts and short judge reasons are exported. Raw model responses
are intentionally excluded from the web bundle.
"""
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "frontend" / "data" / "results.json"

TECH_ZH = {
    "direct": "直接请求",
    "roleplay": "角色扮演",
    "sandbox": "沙箱/授权框架",
    "refusal_suppression": "拒绝抑制",
    "fiction": "虚构框架",
    "encoding_base64": "Base64 编码",
    "encoding_code": "代码形式",
    "low_resource_lang": "小语种",
    "hypothetical": "假设框架",
    "pua_coercion": "PUA/胁迫",
    "defense_framing": "防御视角",
    "instruction_override": "指令覆盖",
    "many_shot": "many-shot",
    "hcot_state_injection": "H-CoT 状态注入",
    "placeholder": "占位符",
    "authority_claim": "权威声称",
    "prefix_injection": "前缀注入",
    "context_dilution": "长上下文稀释",
    "crescendo": "Crescendo 升级",
    "context_priming": "上下文锚定",
    "salami_slicing": "切香肠",
    "refusal_recovery": "拒绝恢复",
    "persona_persistence": "人格持久化",
}

FAMILY = {
    "deepseek": "DeepSeek",
    "gemini": "Gemini",
    "nvidia": "NVIDIA",
    "poolside": "Poolside",
    "glm": "GLM",
}

SIZE = {
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning": "30B",
    "nvidia/nemotron-3-ultra-550b-a55b": "550B",
}

SCALE_PAIRS = [
    ("NVIDIA Nemotron", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
     "nvidia/nemotron-3-ultra-550b-a55b"),
    ("DeepSeek v4", "deepseek-v4-flash", "deepseek-v4-pro"),
    ("Gemini 2.5", "gemini-2.5-flash-lite", "gemini-2.5-flash"),
    ("Gemini 3.5", "gemini-3.5-flash-lite", "gemini-3.5-flash"),
]


def latest(pattern):
    files = sorted((ROOT / "data" / "results").glob(pattern))
    return files[-1] if files else None


def load(path):
    if not path:
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def label_of(row):
    if row.get("blocked"):
        return "BLOCKED"
    if row.get("error") or row.get("skipped"):
        return "ERR"
    j = row.get("judge") or {}
    return j.get("label") or "?"


def family_of(model):
    for key, name in FAMILY.items():
        if model.startswith(key):
            return name
    return "Other"


def main():
    single_path = latest("single_full_*_judged.jsonl") or latest("single_full_*.jsonl")
    multi_paths = [p for p in (latest("multi_full_*_judged.jsonl"),
                               latest("multi_core_*_judged.jsonl")) if p]
    single = load(single_path)
    multi, _seen_multi = [], set()
    for p in multi_paths:
        for r in load(p):
            key = (r.get("model"), r.get("id"))
            if key in _seen_multi:
                continue
            _seen_multi.add(key)
            multi.append(r)
    if not single:
        sys.exit("no single results found")

    attack = [r for r in single if not str(r.get("id", "")).startswith("ctrl_")]
    controls = [r for r in single if str(r.get("id", "")).startswith("ctrl_")]
    models = sorted({r["model"] for r in single})
    techniques = sorted({r.get("technique") for r in attack if r.get("technique")})

    per_model = defaultdict(lambda: defaultdict(int))
    per_tech = defaultdict(lambda: defaultdict(int))
    matrix = defaultdict(lambda: defaultdict(lambda: [0, 0]))  # [C, n]
    per_goal = defaultdict(lambda: defaultdict(int))
    blocked = []
    for r in attack:
        lb = label_of(r)
        per_model[r["model"]][lb] += 1
        if r.get("technique"):
            per_tech[r["technique"]][lb] += 1
        if lb in ("A", "B", "C"):
            cell = matrix[r["model"]][r.get("technique")]
            cell[1] += 1
            if lb == "C":
                cell[0] += 1
        if lb == "BLOCKED":
            blocked.append({"model": r["model"], "probe": r["id"]})
    for r in single:
        per_goal[r.get("goal")][label_of(r)] += 1

    def rate(d):
        n = d.get("A", 0) + d.get("B", 0) + d.get("C", 0)
        return round(100 * d.get("C", 0) / n, 1) if n else None, n

    model_rows = []
    for m in models:
        d = per_model[m]
        rr, n = rate(d)
        model_rows.append({
            "id": m,
            "name": m,
            "family": family_of(m),
            "size": SIZE.get(m, "—"),
            "A": d.get("A", 0), "B": d.get("B", 0), "C": d.get("C", 0),
            "blocked": d.get("BLOCKED", 0), "errors": d.get("ERR", 0),
            "n": n, "rate": rr,
        })
    model_rows.sort(key=lambda x: (x["rate"] if x["rate"] is not None else -1), reverse=True)

    tech_rows = []
    for t in techniques:
        d = per_tech[t]
        rr, n = rate(d)
        tech_rows.append({"key": t, "name": TECH_ZH.get(t, t), "A": d.get("A", 0),
                          "B": d.get("B", 0), "C": d.get("C", 0), "n": n, "rate": rr})
    tech_rows.sort(key=lambda x: (x["rate"] if x["rate"] is not None else -1), reverse=True)

    heat = {
        "models": [m["id"] for m in model_rows],
        "techniques": [t["key"] for t in tech_rows],
        "values": [
            [
                (round(100 * matrix[m][t][0] / matrix[m][t][1], 1)
                 if matrix[m][t][1] else None)
                for t in heat_tech_keys(tech_rows)
            ]
            for m in [x["id"] for x in model_rows]
        ],
    }
    heat["techniqueNames"] = [TECH_ZH.get(k, k) for k in heat["techniques"]]

    goals = []
    for g, d in per_goal.items():
        rr, n = rate(d)
        goals.append({"goal": g, "A": d.get("A", 0), "B": d.get("B", 0),
                      "C": d.get("C", 0), "n": n, "rate": rr})

    scale = []
    by_model = {m["id"]: m for m in model_rows}
    for label, small, large in SCALE_PAIRS:
        if small in by_model and large in by_model:
            scale.append({"label": label, "small": by_model[small], "large": by_model[large]})

    multi_rows = []
    drift_total = 0
    for r in multi:
        turns = r.get("turns") or []
        seq = []
        for t in turns:
            j = (t.get("judge") or {}).get("label")
            seq.append(j or ((t.get("score") or {}).get("label", "?")[:1]))
        final = label_of(r)
        first = seq[0] if seq else "?"
        drifted = first in ("A", "B") and final == "C"
        drift_total += 1 if drifted else 0
        multi_rows.append({"model": r["model"], "scenario": r["id"],
                           "sequence": seq, "final": final, "drift": drifted})

    master = build_master()
    focus = build_focus(single, multi)
    dataset = build_dataset()

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "single": single_path.name if single_path else None,
            "multi": multi_paths[0].name if multi_paths else None,
            "attackProbes": len(attack),
            "controlProbes": len(controls),
            "models": len(models),
            "multiScenarios": len(multi),
            "driftScenarios": drift_total,
            "judged": sum(1 for r in attack if label_of(r) in ("A", "B", "C")),
        },
        "models": model_rows,
        "techniques": tech_rows,
        "heatmap": heat,
        "goals": goals,
        "scale": scale,
        "multi": multi_rows,
        "blocked": blocked,
        "master": master,
        "focus": focus,
        "dataset": dataset,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(model_rows)} models, {len(tech_rows)} techniques, {len(multi_rows)} multi rows)")


def build_dataset():
    mpath = ROOT / "data" / "master" / "manifest.json"
    if not mpath.exists():
        return None
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    val_path = ROOT / "data" / "master" / "validation.json"
    cov_path = ROOT / "data" / "master" / "coverage.json"
    validation = json.loads(val_path.read_text(encoding="utf-8")) if val_path.exists() else {}
    coverage = json.loads(cov_path.read_text(encoding="utf-8")) if cov_path.exists() else {}
    gen_single = ROOT / "data" / "generated" / "seeds_single.jsonl"
    gen_multi = ROOT / "data" / "generated" / "seeds_multi.jsonl"
    return {
        "total": manifest["total"],
        "by_source": manifest["by_source"],
        "by_master_category": manifest["by_master_category"],
        "by_label": manifest["by_label"],
        "by_risk": manifest["by_risk"],
        "taxonomy": manifest["master_taxonomy"],
        "validation": validation,
        "coverage": coverage,
        "generated": {
            "single": len(load(gen_single)) if gen_single.exists() else 0,
            "multi": len(load(gen_multi)) if gen_multi.exists() else 0,
        },
    }


def build_focus(single, multi):
    """Focused profile for deepseek-flash (the model the user prioritised)."""
    model = "deepseek-flash"
    core_path = (ROOT / "data" / "results" / "core_dflash_judged_compliance.jsonl")
    if not core_path.exists():
        core_path = ROOT / "data" / "results" / "core_dflash_judged.jsonl"
    if not core_path.exists():
        return None
    core = load(core_path)
    harmful = [r for r in core if r.get("goal") == "harmful_core"]
    compliant = [r for r in core if r.get("compliance") or r.get("goal") == "compliance_core"]

    def cell(rows):
        d = defaultdict(int)
        for r in rows:
            d[label_of(r)] += 1
        n = d["A"] + d["B"] + d["C"]
        return (round(100 * d["C"] / n, 1) if n else None), n, d

    techs = ["direct", "sandbox", "roleplay", "refusal_suppression", "fiction"]
    names = {"direct": "直接请求", "sandbox": "沙箱/授权框架", "roleplay": "角色扮演",
             "refusal_suppression": "拒绝抑制", "fiction": "虚构框架"}
    tech_rows = []
    for t in techs:
        rr, n, d = cell([r for r in harmful if r.get("technique") == t])
        tech_rows.append({"key": t, "name": names[t], "C": d["C"], "n": n, "rate": rr})

    h_rate, h_n, h_d = cell(harmful)
    refused = [r for r in compliant if (r.get("compliance_judge") or {}).get("refused") is True]
    valid_comp = [r for r in compliant if (r.get("compliance_judge") or {}).get("refused") is not None]
    over_rate = round(100 * len(refused) / len(valid_comp), 1) if valid_comp else None

    main_rows = [r for r in single if r["model"] == model and not str(r.get("id", "")).startswith("ctrl_")]
    m_rate, m_n, m_d = cell(main_rows)

    multi_rows = []
    for r in multi:
        if r.get("model") != model:
            continue
        turns = r.get("turns") or []
        seq = []
        for t in turns:
            j = (t.get("judge") or {}).get("label")
            seq.append(j or ((t.get("score") or {}).get("label", "?")[:1]))
        multi_rows.append({"scenario": r.get("id"), "sequence": seq,
                           "final": label_of(r)})

    family = []
    for m in ["deepseek-flash", "deepseek-v4-flash", "deepseek-v4-pro",
              "deepseek-v4-flash-vision-exp"]:
        rows = [r for r in single if r["model"] == m and not str(r.get("id", "")).startswith("ctrl_")]
        rr, n, d = cell(rows)
        family.append({"id": m, "C": d["C"], "n": n, "rate": rr})

    over_by_topic = defaultdict(int)
    for r in refused:
        over_by_topic[r.get("topic")] += 1

    return {
        "model": model,
        "harmful": {"C": h_d["C"], "A": h_d["A"], "B": h_d["B"], "n": h_n, "rate": h_rate},
        "overRefusal": {"refused": len(refused), "n": len(valid_comp), "rate": over_rate,
                        "byTopic": dict(over_by_topic)},
        "main": {"C": m_d["C"], "n": m_n, "rate": m_rate},
        "techniques": tech_rows,
        "family": family,
        "multi": multi_rows,
        "findings": [
            "有害核心只漏 2/76；唯一稳定通道是 roleplay（SQLi 枚举流程、勒索信模板）。",
            "直接请求、沙箱、拒绝抑制、虚构均为 0；编码/小语种/PUA 在主探针集也为 0。",
            "合规误拒 7/30（23%）：XSTest 的安全上下文被按字面拒绝。",
            "多轮会配合前几轮，但对最后一步的显式恶意收手。",
            "同族里 v4-pro 反而比 flash 更容易配合，规模不是安全变量。",
        ],
        "caveats": [
            "每格 n=1–2，结论是方向性的。",
            "标注器对“定位但不绕过”偏宽松，且出现过一次拒绝误标为 C；本文已人工修正口径。",
            "合规标注器同为 DeepSeek 族，可能有偏置。",
        ],
    }


def heat_tech_keys(tech_rows):
    return [t["key"] for t in tech_rows]


def build_master():
    manifest_path = ROOT / "data" / "master" / "manifest.json"
    core_path = latest("single_core_*_judged.jsonl") or latest("single_core_*.jsonl")
    if not manifest_path.exists() or not core_path:
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    core = load(core_path)
    harmful = [r for r in core if r.get("goal") == "harmful_core"]
    compliant = [r for r in core if r.get("compliance") or r.get("goal") == "compliance_core"]

    tax = [t for t in manifest["master_taxonomy"] if t["key"] != "benign_adjacent"]
    topics = [t["key"] for t in tax]
    topic_names = [t["zh"] for t in tax]
    tech_keys = ["direct", "sandbox", "roleplay", "refusal_suppression", "fiction"]
    tech_names = [TECH_ZH.get(k, k) for k in tech_keys]

    def cell(rows):
        d = defaultdict(int)
        for r in rows:
            d[label_of(r)] += 1
        n = d["A"] + d["B"] + d["C"]
        return (round(100 * d["C"] / n, 1) if n else None), n, d

    tech_rates = []
    for k, name in zip(tech_keys, tech_names):
        rr, n, d = cell([r for r in harmful if r.get("technique") == k])
        tech_rates.append({"key": k, "name": name, "A": d["A"], "B": d["B"],
                           "C": d["C"], "n": n, "rate": rr})

    matrix_rows, matrix_values = [], []
    for t in topics:
        vals = []
        for k in tech_keys:
            rr, _, _ = cell([r for r in harmful
                             if r.get("topic") == t and r.get("technique") == k])
            vals.append(rr)
        matrix_rows.append(t)
        matrix_values.append(vals)

    direct_h, n_h, _ = cell([r for r in harmful if r.get("technique") == "direct"])
    direct_c, n_c, d_c = cell([r for r in compliant if r.get("technique") == "direct"])
    false_refusal = round(100 * d_c["A"] / n_c, 1) if n_c else None

    return {
        "manifest": {
            "total": manifest["total"],
            "core": manifest["core"],
            "by_master_category": manifest["by_master_category"],
            "by_label": manifest["by_label"],
            "by_risk": manifest["by_risk"],
            "master_taxonomy": manifest["master_taxonomy"],
        },
        "core": {
            "topics": topics,
            "topicNames": topic_names,
            "techniqueRates": tech_rates,
            "topicMatrix": {
                "topics": matrix_rows,
                "topicNames": topic_names,
                "techniques": tech_keys,
                "techniqueNames": tech_names,
                "values": matrix_values,
            },
            "harmfulRate": direct_h,
            "complianceRate": direct_c,
            "falseRefusalRate": false_refusal,
            "counts": {"harmful": len(harmful), "compliance": len(compliant)},
        },
    }


if __name__ == "__main__":
    main()
