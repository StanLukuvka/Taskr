# Taskr Backend

FastAPI service that stores flow definitions, runs, integration bindings, and executes the durable node-state machine.

---

## Quick start

```bash
cd Backend

# Install dependencies with uv
uv sync

# Reset dev DB and run the test suite
rm -f taskr.db taskr.db-shm taskr.db-wal
uv run pytest -q

# Start the dev server (defaults to port 9113)
uv run python -m app.main
```

The server creates `taskr.db` in the `Backend/` directory on first startup.

---

## Environment variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Purpose |
|---|---|---|
| `TASKR_PORT` | `9113` | HTTP port for the FastAPI/Uvicorn server |
| `TASKR_HOST` | `0.0.0.0` | Bind address |
| `TASKR_USE_FAKE_INTEGRATIONS` | unset | When `1`, `api` bindings call in-process fakes instead of real HTTP |
| `TASKR_HERMES_BASE_URL` | unset | Base URL for real Hermes agent worker endpoints |
| `TASKR_HERMES_API_KEY` | unset | API key for Hermes worker endpoints |
| `TASKR_STRIPE_API_KEY` | unset | Stripe API key for budget-replenishment demo flows |
| `TASKR_LOG_LEVEL` | `info` | Python logging level (`debug`, `info`, `warning`, `error`) |
| `TASKR_DB_PATH` | `taskr.db` | SQLite database file path (relative to `Backend/`) |

Example minimal dev `.env`:

```bash
TASKR_PORT=9113
TASKR_USE_FAKE_INTEGRATIONS=1
TASKR_LOG_LEVEL=info
```

---

## Fake integrations mode

For demos and tests the backend can substitute real HTTP calls with deterministic fakes.

Set `TASKR_USE_FAKE_INTEGRATIONS=1` to:

- Resolve `https://fake.api/*` URLs to in-memory handlers.
- Generate synthetic images and text without external services.
- Run the `soda-comparison` demo end-to-end without DNS or credentials.

Without this flag, the `fake.api` bindings in the demo flow will fail with DNS errors.

---

## Demo data

On first startup the backend seeds:

- A `soda-comparison` flow with three nodes: scrape, research, generate image.
- Sample `api` and `hermes` bindings wired to fake integrations (when fakes are enabled).

To re-seed from a clean state:

```bash
rm -f taskr.db taskr.db-shm taskr.db-wal
uv run python -m app.main
```

---

## Running tests

```bash
# Run the full pytest suite
uv run pytest -q

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_run_lifecycle.py -q
```

The test suite uses a temporary SQLite database and does not require external services.

---

## Key commands

| Command | Purpose |
|---|---|
| `uv run python -m app.main` | Start the dev server |
| `uv run pytest -q` | Run tests |
| `rm -f taskr.db* && uv run python -m app.main` | Reset DB and restart |
| `TASKR_USE_FAKE_INTEGRATIONS=1 uv run python -m app.main` | Start with fake integrations |
| `uv run python -m app.main --help` | Show CLI options (if any) |

---

## OpenAPI / docs

When the server is running:

- **Swagger UI** — `http://localhost:9113/docs`
- **Raw OpenAPI spec** — `http://localhost:9113/openapi.json`

A static export is committed at `Backend/openapi.json`.

---

## Project layout

```
app/
  main/           # FastAPI app assembly and startup
  endpoint/       # HTTP routers, request/response models, deps
  logic/          # Runner, state machine, integration callers
  data/           # Repository, SQLite schema, migrations
  flow/           # Flow seeding and version helpers
  types/          # Internal type definitions
tests/            # pytest suite
openapi.json      # Exported OpenAPI spec
pyproject.toml    # Dependencies and project metadata
uv.lock           # Locked dependency graph
```

---

## Common issues

### `sqlite3.OperationalError: disk I/O error`

Caused by concurrent processes writing to the same SQLite database (e.g., multiple Uvicorn workers or a test run colliding with the dev server). Fix:

1. Stop all `app.main` processes.
2. Delete the lock/WAL files: `rm -f taskr.db-shm taskr.db-wal`.
3. Restart with a single process: `uv run python -m app.main`.

### `Errno 98: address already in use`

Another process is holding port 9113. Find and kill it, or change `TASKR_PORT` in `.env`:

```bash
lsof -i :9113
# or
fuser -k 9113/tcp
```

### Demo runs fail with DNS errors

The backend is not running with `TASKR_USE_FAKE_INTEGRATIONS=1`. Restart with that flag set.

---

## Production notes

- Use a real WSGI/ASGI server (e.g., Gunicorn with Uvicorn workers) behind a reverse proxy.
- Move from SQLite to PostgreSQL for multi-worker or high-availability deployments.
- Keep `.env` out of version control; use `.env.example` as a template.
