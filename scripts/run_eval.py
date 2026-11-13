#!/usr/bin/env python3
"""Run the single-turn and multi-turn probe sets across models.

Writes one JSONL row per (model, probe) or (model, scenario) into
data/results/. Multi-turn rows keep the full transcript plus per-turn labels
so context-drift can be measured.
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.client import Client, available_models  # noqa: E402
from app.config import load_env, results_dir  # noqa: E402
from app.scorer import classify  # noqa: E402

load_env()
DATA = Path(__file__).resolve().parent.parent / "data"


def load(path):
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def run_single(client, model, probe):
    msgs = [{"role": "user", "content": probe["prompt"]}]
    try:
        r = client.chat(model, msgs, system=probe.get("system"),
                        prefill=probe.get("prefill"), max_tokens=2200)
    except Exception as e:  # noqa: BLE001
        return {"id": probe["id"], "model": model, "prompt": probe["prompt"],
                "blocked": "blocked" in str(e).lower(), "error": str(e)[:300]}
    s = classify(r["text"])
    return {
        "id": probe["id"],
        "model": model,
        "prompt": probe["prompt"],
        "goal": probe.get("goal"),
        "topic": probe.get("topic"),
        "source": probe.get("source"),
        "compliance": probe.get("compliance"),
        "technique": probe.get("technique"),
        "risk": probe.get("risk"),
        "text": r["text"],
        "reasoning": r["reasoning"][:4000],
        "finish": r["finish"],
        "score": s,
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def run_multi(client, model, scen):
    history = []
    turns = []
    for i, user_msg in enumerate(scen["turns"]):
        history.append({"role": "user", "content": user_msg})
        try:
            r = client.chat(model, history, max_tokens=2200)
        except Exception as e:  # noqa: BLE001
            turns.append({"turn": i + 1, "user": user_msg, "error": str(e)[:300]})
            break
        s = classify(r["text"])
        turns.append({
            "turn": i + 1,
            "user": user_msg,
            "assistant": r["text"],
            "reasoning": r["reasoning"][:2000],
            "finish": r["finish"],
            "score": s,
        })
        history.append({"role": "assistant", "content": r["text"]})
    return {
        "id": scen["id"],
        "model": model,
        "goal": scen.get("goal"),
        "topic": scen.get("topic"),
        "technique": scen.get("technique"),
        "risk": scen.get("risk"),
        "turns": turns,
        "final_label": turns[-1]["score"]["label"] if turns and "score" in turns[-1] else "error",
        "first_label": turns[0]["score"]["label"] if turns and "score" in turns[0] else "error",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", help="default: all reachable")
    ap.add_argument("--mode", choices=["single", "multi", "both"], default="both")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tag", default="run")
    ap.add_argument("--single-file", default="probes_single.jsonl")
    ap.add_argument("--multi-file", default="probes_multi.jsonl")
    args = ap.parse_args()

    client = Client(timeout=90, retries=1)
    models = args.models or [m for m in available_models() if m != "glm-5.3"]
    out = results_dir()
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    if args.mode in ("single", "both"):
        probes = load(DATA / args.single_file)
        path = out / f"single_{args.tag}_{stamp}.jsonl"
        rows = []
        state = {m: {"consec": 0, "dead": False} for m in models}
        lock = threading.Lock()

        def guarded(model, probe):
            if state[model]["dead"]:
                return {"id": probe["id"], "model": model, "skipped": True}
            row = run_single(client, model, probe)
            with lock:
                if row.get("error"):
                    state[model]["consec"] += 1
                    if state[model]["consec"] >= 4:
                        state[model]["dead"] = True
                else:
                    state[model]["consec"] = 0
            return row

        # Interleave by probe so one slow model cannot monopolise the pool.
        tasks = [(m, p) for p in probes for m in models]
        with ThreadPoolExecutor(max_workers=args.workers) as pool, path.open("w", encoding="utf-8") as f:
            futs = {pool.submit(guarded, m, p): (m, p["id"]) for m, p in tasks}
            done = 0
            for fut in as_completed(futs):
                row = fut.result()
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                rows.append(row)
                done += 1
                if done % 20 == 0:
                    dead = [m for m, s in state.items() if s["dead"]]
                    print(f"single {done}/{len(futs)} dead={dead}", flush=True)
        print(f"single -> {path} ({len(rows)} rows)")

    if args.mode in ("multi", "both"):
        scens = load(DATA / args.multi_file)
        path = out / f"multi_{args.tag}_{stamp}.jsonl"
        tasks = [(m, s) for s in scens for m in models]
        with ThreadPoolExecutor(max_workers=max(2, args.workers // 2)) as pool, path.open("w", encoding="utf-8") as f:
            futs = {pool.submit(run_multi, client, m, s): (m, s["id"]) for m, s in tasks}
            for fut in as_completed(futs):
                row = fut.result()
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
        print(f"multi -> {path} ({len(futs)} rows)")


if __name__ == "__main__":
    main()
