# Security & publishing policy

This repository is a **research red-team evaluation lab**. It is dual-use.

## What is intentionally excluded from git

- API keys and `.env` files.
- Raw harmful prompt corpora and raw model responses.
- The full reproduction case library (`frontend/data/cases.json`) — served
  server-side only and regenerated with `make cases`.
- Third-party clones under `sub_modules/`.

## Running the optional `/api/run` endpoint

- It reads `LLM_BASE_URL` / `LLM_API_KEY` from `process.env` or `../.env`.
- It only calls a whitelist of model IDs, with a 20 requests/minute/IP limit and
  a 90s timeout.
- Responses are not persisted.
- Set `DASHBOARD_RUN_TOKEN` to require an `x-run-token` header.
- Do not deploy it publicly without a token and network restrictions.

## Responsible use

- Only evaluate models you own or are authorized to test.
- Do not use this project to obtain or distribute operational harm.
- Follow the licenses of the upstream datasets and repositories.
- This is not a compliance certification.
