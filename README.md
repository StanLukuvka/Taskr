# Taskr

A persistent state machine for task coordination. State machine first, web app second.

## What it does

Taskr runs directed flows made of nodes. A node can:

- call a generic HTTP API (`api` kind)
- dispatch a task to Hermes and block until it answers a question (`hermes` kind)
- iterate over a list and run child nodes for each item (`foreach` kind)

Runs are durable SQLite records. Each run is one row in `runs`; each node execution is one row in `node_states`. Questions are attached to the exact node-state instance that asked them.

## Quick start

The backend lives in `Backend/` and uses its own virtual environment.

```bash
cd Backend

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
| `GET /flows` | List all flows |
| `GET /runs` | List all runs with summary status |
| `POST /runs` | Create a new run from a flow (`flow_slug`, optional `context` JSON) |
| `GET /runs/{id}` | Inspect run and all node states |
| `GET /runs/{id}/questions` | List all open questions across the run's node states |
| `POST /runs/{id}/tick` | Advance the state machine by one step |
| `GET /runs/{id}/node-states` | List node states for a run |
| `GET /runs/{id}/node-states/{ns_id}` | Inspect one node state |
| `GET /runs/{id}/node-states/{ns_id}/questions` | List questions on that node state |
| `POST /runs/{id}/node-states/{ns_id}/answer` | Answer the open question |
| `GET /flow_versions/{id}` | Inspect a flow version and its nodes |
| `POST /flow_versions/{fv_id}/flow_nodes` | Add a node to a draft flow version |

## Frontend readiness

The backend is now browser-ready for a workbench UI:

1. **CORS is enabled** — `CORSMiddleware` is configured in `Backend/app/main.py` for development (all origins, all methods, all headers). Restrict this for production.
2. **Flow listing** — `GET /flows` returns every flow and its latest flow version.
3. **Run creation with context** — `POST /runs` accepts `flow_slug` and optional `context` (e.g. `{"prompt": "..."}`) so the frontend can start flow-driven runs.
4. **Run listing** — `GET /runs` returns a summary list with status and IDs for the workbench index view.
5. **Run-level questions** — `GET /runs/{id}/questions` collects open questions across all node states so a single view can show what needs answering.
6. **Flow version inspection** — `GET /flow_versions/{id}` returns the version and its nodes for the flow editor.

## OpenAPI documentation

When the server is running, FastAPI serves interactive API documentation automatically:

- **Swagger UI** — `http://localhost:9119/docs`
- **Raw OpenAPI spec** — `http://localhost:9119/openapi.json`

A static export of the spec is also committed to the repository at `Backend/openapi.json` so the API surface can be reviewed without starting the server.

Remaining workbench gaps:

- **Create / update flows and flow versions** — only node addition and reading are exposed.
- **Binding management API** — integrations are still hard-coded in `seed_data()`.
- **Cancel / retry / delete runs** — only create, inspect, and tick are available.
- **Auth / multi-user scoping** — required for shared deployments.
- **OpenAPI metadata** — tags, examples, and operation grouping would improve the generated docs.
- **Real integrations** — `app/integrations/fake.py` is test-only.

## Project layout

```
Backend/
  app/
    main.py              # FastAPI routes and response builders
    repository.py        # SQLite access, schema application, CRUD
    runner.py            # State machine: tick, advance_run, advance_foreach, advance_action
    mapping.py           # $path resolution for node inputs and outputs
    integrations/fake.py # Deterministic test-only API and Hermes stubs
  schema.sql             # Canonical SQLite DDL
  tests/
    test_vertical_slice.py  # End-to-end pause/resume scenario
  pyproject.toml         # Backend dependencies
  uv.lock                # Locked dependency graph
  test_api.sh            # Curl-based API walkthrough
```

## Design notes

- **Raw SQL via `sqlite3`**. No ORM. The schema uses triggers, partial indexes, and foreign keys.
- **Explicit ticks**. The `POST /runs/{id}/tick` endpoint advances state one step at a time. This makes tests and debugging deterministic.
- **Ordering is implicit**. Siblings run in `flow_nodes.ord` order. There is no dependency graph yet.
- **Questions are nested**. Questions live under a `node_state`, not as a global resource.

## License

MIT
