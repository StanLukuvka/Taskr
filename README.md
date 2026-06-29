# Taskr

The point of enterprise software is ultimately one thing: **closing the gap between a question and an answer**.

- "Did every store report sales today?"
- "Do we still have enough credits to keep the image generator running?"
- "Which customers hit the spending threshold and need a follow-up?"
- "Is the product catalogue fresh across every retailer?"

Some questions are simple. Some run once. Some run forever, with answers that drift out of date hours after you last answered them. Some split into a thousand smaller jobs and need to hand off to agents, workers, review queues, or payment systems before they can be closed.

Taskr gives those questions a home. It turns them into durable flows — pipelines of integrations, decisions, and handoffs — and runs them until they settle.

---

## 30-second demo: compare drink prices and generate a diagram

A concrete flow that runs end-to-end in the workbench:

1. **Scrape product data** — fetch price and image from a product URL via an API integration.
2. **Collect opinions** — call a Hermes agent to search for and summarize 2-3 real customer review quotes.
3. **Design the infographic** — call another Hermes agent to produce an image-generation prompt and layout spec.
4. **Check budget, then "generate"** — verify the run's budget, dispatch a fake image-generation API call, and return the final prompt as the artifact.

Every step, every cost, every input, and every output is stored. You can inspect the run, retry it, or cancel it at any point.

---

## What Taskr does

You describe a persistent operation as a versioned flow of nodes. Each node does one of three things:

1. **Call an API** — fetch, post, mutate, poll
2. **Ask an agent** — dispatch to a Hermes worker and wait for completion
3. **Loop over a list** — run child nodes once per item

A **flow** is the reusable recipe. A **run** is one execution of that recipe with a specific context. Runs are durable: every node execution is stored in SQLite, so state survives process restarts, flaky APIs, and the credit card declining halfway through a run.

```text
              Flow definition                   Run instance
   ┌──────────────────────────────┐      ┌──────────────────────────────┐
   │  Scrape product page         │      │  Run #184                    │
   │        (api)                 │      │   status: running            │
   └──────────┬───────────────────┘      └──────────┬───────────────────┘
              │                                     │
              ▼                                     ▼
   ┌──────────────────────────────┐      ┌──────────────────────────────┐
   │  For each review topic       │      │  NodeState #1                │
   │      (foreach)               │      │   completed                  │
   └──────────┬───────────────────┘      └──────────┬───────────────────┘
              │                                     │
     ┌─────────┴─────────┐                ┌─────────┴─────────┐
     ▼                   ▼                ▼                   ▼
┌──────────┐      ┌──────────┐     ┌──────────┐      ┌──────────┐
│ Gather   │      │ Design   │     │ Gather   │      │ Design   │
│ (hermes) │      │ (hermes) │     │ running  │      │ pending  │
└──────────┘      └──────────┘     └──────────┘      └──────────┘
```

---

## Why this shape

Persistent-business-operation graphs are useful because:

- **Questions stay alive.** "Is our catalogue accurate within 24 hours?" does not end after one HTTP call. It lives for months.
- **Failure is normal.** APIs flake, agents get stuck, lists are longer than expected. Nodes can fail, be retried, or be cancelled independently.
- **Payment is sometimes part of the work.** Some integrations need budget. Taskr can gate paid integrations against a per-run budget and use Stripe to replenish those budgets when the demo is configured for it.
- **Agents sometimes need to think.** Hermes workers are treated as asynchronous nodes that complete, fail, or block on external review.

---

## Hermes integration

Taskr talks to Hermes over API, not as a local plugin.

> Run it on NemoClaw, local, a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. 
>
> — [Hermes README](https://hermes-agent.nousresearch.com/)

For hackathon demos and GPU workloads this means Taskr's agent nodes can run on [NVIDIA NeMo Claw](https://www.nvidia.com/en-au/ai/nemoclaw/): a serverless agent runtime that deploys anywhere without your own container. The Hermes worker endpoint is configured as a normal Taskr binding — the runner schedules the task, polls for completion, and stores the result like any other node state.

---

## Quick start

The backend lives in `Backend/` and uses `uv`.

```bash
cd Backend

# install deps
uv sync

# reset the dev database and run tests
rm -f taskr.db taskr.db-shm taskr.db-wal
uv run pytest -q

# start server (uses taskr.db in this directory)
uv run uvicorn app.main.app:app --host 0.0.0.0 --port 8000
```

## API overview

| Endpoint | What it does |
|---|---|
| `GET /flows` | List all flows |
| `POST /flows` | Create a new flow |
| `GET /flows/{slug}` | Inspect a flow and its active version |
| `PUT /flows/{slug}` | Update flow metadata |
| `DELETE /flows/{slug}` | Delete a flow |
| `GET /flow_versions/{id}` | Inspect a flow version and its nodes |
| `POST /flow_versions/{id}/flow_nodes` | Add a node to a draft flow version |
| `GET /runs` | List all runs with summary status |
| `POST /runs` | Create a new run from a flow (`flow_slug`, optional `context` JSON) |
| `GET /runs/{id}` | Inspect a run and all node states |
| `POST /runs/{id}/tick` | Advance the state machine by one step |
| `POST /runs/{id}/cancel` | Cancel a running run |
| `POST /runs/{id}/retry` | Retry a run from a fresh copy |
| `DELETE /runs/{id}` | Delete a run |
| `GET /runs/{id}/node-states` | List node states for a run |
| `GET /bindings` | List integration bindings |
| `POST /bindings` | Create an `api` or `hermes` binding |
| `GET /bindings/{id}` | Inspect a binding |

## Frontend

The browser interface lives in `Frontend/` (React + Vite + TypeScript). The backend serves the built `Frontend/dist` in production and has CORS enabled for local Vite development.

## OpenAPI documentation

When the server is running:

- **Swagger UI** — `http://localhost:8000/docs`
- **Raw OpenAPI spec** — `http://localhost:8000/openapi.json`

A static export of the spec is committed at `Backend/openapi.json`.

## Project layout

```
Backend/
  app/
    main/app.py         # FastAPI app assembly
    endpoint/           # routers, models, builders, deps
    logic/              # runner, integrations
    data/               # repository, schema
  tests/                # pytest suite
  openapi.json          # OpenAPI spec
  pyproject.toml        # dependencies
  uv.lock               # locked dependency graph
Frontend/               # React + Vite + TypeScript frontend
NODES.md                # current project status
NOTES.md                # developer guide
```

## License

MIT
