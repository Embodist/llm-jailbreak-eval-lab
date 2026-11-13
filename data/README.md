# Data

The public repository intentionally does **not** ship the raw harmful prompt
corpora or raw model responses. Regenerate them locally:

```bash
make data     # builds data/master/{master_prompts,core_eval,core_multi}.jsonl
make seeds    # data/generated/seeds_single.jsonl + seeds_multi.jsonl
make cases    # frontend/data/cases.json (server-side reproduction library)
```

What is committed:

- `data/master/manifest.json` — counts, sources, taxonomy (no prompts)
- `data/master/validation.json` — consistency/coverage checks
- `data/master/coverage.json` — coverage gaps
- `data/corpus_stats.json` — aggregate technique distribution

What is excluded (see `.gitignore`):

- `data/master/master_prompts.jsonl` / `core_eval.jsonl` / `core_multi.jsonl`
- `data/probes_*.jsonl` / `data/refusal_*.jsonl`
- `data/generated/`
- `data/results/` (raw model replies)
- `frontend/data/cases.json` (contains prompts; served server-side only)
- `sub_modules/` (third-party clones)

Sources: HarmBench, StrongREJECT, CCS'24 forbidden questions, AdvBench,
XSTest, SALAD-Bench. See `docs/03-sources.md` and `docs/10-dataset-taxonomy.md`.
