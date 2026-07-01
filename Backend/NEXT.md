# Taskr Backend — Current State

Last updated: 2026-06-29

## Test Status

```bash
cd /agent/projects/taskr/Backend
rm -f taskr.db* && uv run pytest -q
```

Latest result: **136 passed, 49 skipped, 1 warning** (FastAPI/Starlette httpx deprecation).

## What is Implemented

- Full run lifecycle (create, tick, cancel, retry, delete)
- Flow / flow-version / flow-node CRUD
- Node state read endpoints
- Binding CRUD for `api` and `hermes` kinds
- Real HTTP API integration (`ApiIntegration`) with SSRF-hardened URL validation
- Hermes Runs API client (`HermesIntegration`) for async job execution
- Stripe test-mode integration (`StripeIntegration`) for PaymentIntent top-ups
- Fake image provider (`tools/fake_image_provider.py`) for demo credit flow
- Cost tracking (`total_cost_cents` on runs, `cost_cents` on node states)
- Stripe budget demo flow + script

## Architecture

```
Frontend (built separately, served from ../Frontend/dist in production)
    │
FastAPI app (app/main/app.py)
    ├── routers: flows, runs, node_states, bindings
    ├── error handler: app/errors/handlers.py
    └── dependencies: app/endpoint/deps.py
              │
              ├─ TaskrRunner ── TaskrRepository
              │       │
              │       ├─ ApiIntegration (real HTTP)
              │       ├─ HermesIntegration (Hermes gateway /v1/runs)
              │       └─ StripeIntegration (Stripe PaymentIntents)
              │
              └─ raw sqlite3 + schema.sql
```

## Key Files

- `app/main/app.py` — FastAPI bootstrap, CORS, frontend mount
- `app/endpoint/deps.py` — shared dependencies and integration singletons
- `app/endpoint/runs.py` — run lifecycle endpoints
- `app/endpoint/flows.py` — flow/version/node endpoints
- `app/endpoint/bindings.py` — binding endpoints
- `app/endpoint/node_states.py` — node state endpoints
- `app/endpoint/models.py` — Pydantic request/response models
- `app/endpoint/builders.py` — DB row → API response mappers
- `app/logic/runner.py` — state machine
- `app/logic/integrations/api.py` — real HTTP client
- `app/logic/integrations/hermes.py` — Hermes Runs client
- `app/logic/integrations/stripe.py` — Stripe client
- `app/logic/integrations/fake.py` — fakes for tests
- `app/data/repository.py` — SQLite data access
- `app/data/schema.sql` — schema
- `openapi.json` — generated OpenAPI spec

## Remaining Non-Code Debt

These are documentation/process items only; code is not being touched right now.

1. Some backend plans in `/root/.hermes/plans/archive/` are historical. Current source of truth is this file and `/agent/projects/taskr/NODES.md`.
2. Backend/notes.md contains older handoff content and is kept for reference; use this file for the latest state.

## Known Code Debt (Intentionally Deferred)

1. **Stripe budget model is flow-run-cost based.** The current demo flow hardcodes a `stripe://top-up` URL template that the runner intercepts. The budget check happens inside a flow node using resolved `input_data`, not against a per-tool credit balance. This is enough for the hackathon demo but is architecturally the wrong layer: payments should be tied to a Tool/Connection entity with its own budget, not inferred from a flow node's input mapping. Revisit after demo.

## Demo flow idea: "Compare drink prices and generate diagram"

A fun end-to-end frontend demo flow once the React UI is ready.

**Title:** Compare drink prices and generate diagram

**Steps:**

1. **Scrape product page** (`api` node)
   - URL: `https://www.coles.com.au/product/pepsi-max-no-sugar-cola-soft-drink-bottle-1.25l-5441863`
   - Output: price, product name, image URL

2. **Gather review quotes** (`hermes` node)
   - Agent searches the internet for 2-3 real user review quotes about Pepsi Max
   - Output: list of quotes + sources

3. **Create diagram spec** (`hermes` node)
   - Takes the scraped image + review quotes
   - Produces a detailed image-generation prompt and a structured diagram/layout spec

4. **Generate fake image** (`api` node)
   - Pretends to call ChatGPT/DALL-E image API
   - For the demo, just writes the final prompt to a text file / output instead of actually calling the API
   - Output: `image_prompt.txt`, mock image URL

This is intentionally a toy flow. It wires together scraping, agent research, prompt engineering, and a fake external image API into one visible run that the workbench can show end-to-end.

## Conventions

- Never auto-commit git changes.
- Single-concern commits, dependency order documented.
- "connections" is the universal term for external API callers.
- Use `TaskrError` subclasses; do not raise bare `ValueError` or `HTTPException`.
- Do not write secrets programmatically; use `[REDACTED]` in notes.
