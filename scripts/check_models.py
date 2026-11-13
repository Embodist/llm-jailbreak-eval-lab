#!/usr/bin/env python3
"""Probe every advertised model with a trivial request and report reachability."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.client import Client, available_models  # noqa: E402
from app.config import load_env  # noqa: E402

load_env()


def main():
    c = Client()
    models = available_models()
    for m in models:
        try:
            r = c.chat(m, [{"role": "user", "content": "ping, reply with pong"}], max_tokens=64)
            text = (r["text"] or "").strip().replace("\n", " ")[:40]
            print(f"OK    {m:50s} finish={r['finish']} :: {text}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL  {m:50s} {str(e)[:120]}")


if __name__ == "__main__":
    main()
