SHELL := /bin/bash
PY := python3

.PHONY: help setup data validate eval-core judge-core focus export dev build clean seeds coverage cases

help:
	@echo "make setup       - install frontend deps"
	@echo "make data        - generate probes + master dataset"
	@echo "make validate    - run dataset consistency checks"
	@echo "make seeds       - generate technique variants from the master corpus"
	@echo "make coverage    - report coverage gaps"
	@echo "make cases       - build the reproduction case library"
	@echo "make eval-core   - run the 108-probe core set (8 models)"
	@echo "make judge-core  - judge core results"
	@echo "make focus       - judge + export deepseek-flash focus data"
	@echo "make export      - export results.json for the dashboard"
	@echo "make dev         - run Next.js dev server on :3210"
	@echo "make build       - production build of the dashboard"

setup:
	cd frontend && npm install --no-audit --no-fund

data:
	$(PY) scripts/gen_probes.py
	$(PY) scripts/gen_refusal_probes.py
	$(PY) scripts/build_master_dataset.py
	$(PY) scripts/validate_dataset.py

validate:
	$(PY) scripts/validate_dataset.py

seeds:
	$(PY) scripts/generate_seeds.py --per-category 6

coverage:
	$(PY) scripts/coverage_report.py

cases:
	$(PY) scripts/export_cases.py

eval-core:
	$(PY) scripts/run_eval.py --mode single --tag core --workers 10 \
	  --single-file master/core_eval.jsonl \
	  --models deepseek-flash deepseek-v4-pro deepseek-v4-flash \
	    gemini-3.5-flash gemini-2.5-flash \
	    nvidia/nemotron-3-ultra-550b-a55b \
	    nvidia/nemotron-3-nano-omni-30b-a3b-reasoning \
	    poolside/laguna-xs-2.1

judge-core:
	$(PY) scripts/judge_results.py data/results/single_core_*.jsonl \
	  --model deepseek-flash --workers 12 --timeout 60 --retries 1

focus:
	jq -c 'select(.model=="deepseek-flash")' data/results/single_core_*.jsonl > data/results/core_dflash.jsonl
	$(PY) scripts/judge_results.py data/results/core_dflash.jsonl --model deepseek-flash --workers 8
	$(PY) scripts/judge_compliance.py data/results/core_dflash_judged.jsonl --model deepseek-v4-pro --workers 8
	$(PY) scripts/export_frontend_data.py
	$(PY) scripts/export_cases.py

export:
	$(PY) scripts/export_frontend_data.py

dev:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

clean:
	rm -rf frontend/.next
