#!/usr/bin/env python3
"""Annotate a results JSONL with an LLM judge (A/B/C) and write *_judged.jsonl."""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.client import Client  # noqa: E402
from app.config import load_env  # noqa: E402
from app.judge import judge  # noqa: E402

load_env()


def prompt_for(row):
    if "prompt" in row:
        return row["prompt"]
    if row.get("turns"):
        # judge the final turn against the whole scenario goal
        return "\n".join(t.get("user", "") for t in row["turns"])
    return ""


def annotate(client, model, row):
    if "turns" in row:
        for t in row["turns"]:
            text = t.get("assistant", "")
            if not text:
                t["judge"] = {"label": None, "actionable": None, "reason": "empty"}
                continue
            try:
                t["judge"] = judge(client, model, t.get("user", ""), text)
                if not t["judge"].get("label"):
                    t["judge"] = judge(client, model, t.get("user", ""), text)
            except Exception as e:  # noqa: BLE001
                t["judge"] = {"label": None, "actionable": None, "reason": f"error:{str(e)[:80]}"}
        row["judge"] = row["turns"][-1]["judge"] if row["turns"] else {
            "label": None, "actionable": None, "reason": "no turns"}
        return row

    text = row.get("text", "")
    if not text:
        row["judge"] = {"label": None, "actionable": None, "reason": "empty"}
        return row
    try:
        row["judge"] = judge(client, model, prompt_for(row), text)
        if not row["judge"].get("label"):
            row["judge"] = judge(client, model, prompt_for(row), text)
    except Exception as e:  # noqa: BLE001
        row["judge"] = {"label": None, "actionable": None, "reason": f"error:{str(e)[:80]}"}
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=60)
    ap.add_argument("--retries", type=int, default=1)
    args = ap.parse_args()
    client = Client(timeout=args.timeout, retries=args.retries)
    for f in args.files:
        src = Path(f)
        rows = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futs = {pool.submit(annotate, client, args.model, r): r for r in rows}
            out = []
            for fut in as_completed(futs):
                out.append(fut.result())
        dst = src.with_name(src.stem + "_judged.jsonl")
        with dst.open("w", encoding="utf-8") as fh:
            for r in out:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")
        ok = sum(1 for r in out if r.get("judge", {}).get("label"))
        print(f"{src.name} -> {dst.name}: judged {ok}/{len(out)}")


if __name__ == "__main__":
    main()
