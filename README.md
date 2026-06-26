# Taskr

A persistent state machine for task coordination. State machine first, web app second.

## What it does

Taskr runs directed flows made of nodes. A node can:

- call a generic HTTP API (`api` kind)
- dispatch a task to Hermes and block until it answers a question (`hermes` kind)
- iterate over a list and run child nodes for each item (`foreach` kind)

Runs are durable SQLite records. Each run is one row in `runs`; each node execution is one row in `node_states`. Questions are attached to the exact node-state instance that asked them.

## Quick start

```bash
# install deps
uv sync

# run tests
uv run pytest tests/ -v

# start server
uv run uvicorn app.main:app --host 0.0.0.0 --port 9119

# create and drive a run via curl
bash test_api.sh
```

## API overview

| Endpoint | What it does |
|---|---|---|
| `POST /runs` | Create a new run from the seeded goal |
| `POST /runs/{id}/tick` | Advance the state machine by one step |
| `GET /runs/{id}` | Inspect run and all node states |
| `GET /runs/{id}/node-states` | List node states for a run |
| `GET /runs/{id}/node-states/{ns_id}` | Inspect one node state |
| `GET /runs/{id}/node-states/{ns_id}/questions` | List questions on that node state |
| `POST /runs/{id}/node-states/{ns_id}/answer` | Answer the open question |
| `POST /flow_versions/{fv_id}/flow_nodes` | Add a node to a draft flow version |

## Project layout

```
app/
  main.py              # FastAPI routes and response builders
  repository.py        # SQLite access, schema application, CRUD
  runner.py            # State machine: tick, advance_run, advance_foreach, advance_action
  mapping.py           # $path resolution for node inputs and outputs
  integrations/fake.py # Deterministic test-only API and Hermes stubs
schema.sql             # Canonical SQLite DDL
tests/
  test_vertical_slice.py  # End-to-end pause/resume scenario
```

## Design notes

- **Raw SQL via `sqlite3`**. No ORM. The schema uses triggers, partial indexes, and foreign keys.
- **Explicit ticks**. The `POST /runs/{id}/tick` endpoint advances state one step at a time. This makes tests and debugging deterministic.
- **Ordering is implicit**. Siblings run in `flow_nodes.ord` order. There is no dependency graph yet.
- **Questions are nested**. Questions live under a `node_state`, not as a global resource.

## Frontend readiness

The backend is a working vertical slice, but a frontend workbench still needs:

1. **CRUD for goals and flow versions** — currently only one hard-coded demo goal exists.
2. **Binding management API** — integrations are hard-coded in `seed_data()`.
3. **Run list / search / cancel / retry** — only create and inspect are exposed.
4. **CORS / auth scaffolding** — required for a browser-based frontend and multi-user use.
5. **OpenAPI metadata** — tags and examples will improve the generated docs.
6. **Real integrations** — `app/integrations/fake.py` is test-only.

## License

MIT
