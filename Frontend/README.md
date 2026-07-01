# Taskr Frontend

React + Vite + TypeScript workbench for Taskr flows, runs, and integrations.

---

## Quick start

```bash
cd Frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Start the Vite dev server (defaults to port 9112)
npm run dev
```

The dev server proxies API routes to the backend at `http://127.0.0.1:9113`.

---

## Environment variables

Copy `.env.example` to `.env` and adjust as needed.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_PORT` | `9112` | Port for the Vite dev server |
| `VITE_API_BASE` | `http://127.0.0.1:9113` | Base URL for backend API requests |
| `VITE_LOG_LEVEL` | `info` | Client-side log level (optional) |

In development, leave `VITE_API_BASE` empty if you want the dev server proxy to handle API routes.

---

## Scripts

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Vite dev server with HMR |
| `npm run build` | Build the production bundle to `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run typecheck` | Run TypeScript compiler without emitting files |
| `npm run test` | Run the Vitest test suite |
| `npm run lint` | Run ESLint |
| `npm run format` | Format code with Prettier |

---

## Backend dependency

The frontend expects a Taskr backend running on port `9113` by default. Make sure the backend is started:

```bash
cd ../Backend
TASKR_USE_FAKE_INTEGRATIONS=1 uv run python -m app.main
```

The fake integrations flag lets the built-in `soda-comparison` demo flow complete end-to-end without real credentials.

---

## SPA routing in development

Direct navigation to client-side routes such as `/flows` or `/runs/:id` is supported in development. Vite serves `index.html` for HTML-accepting requests, then React Router takes over.

---

## Project layout

```
src/
  api/              # API client and typed fetch helpers
  components/       # React components grouped by domain
    flows/          # Flow list, detail, node tree
    integrations/   # Integration bindings list and detail
    runs/           # Runs list and related UI
    workbench/      # Run workbench (tree, inspector, console)
  hooks/            # React Query hooks
  routes.tsx        # React Router route definitions
  types/            # TypeScript API types
  main.tsx          # Application entry point
  App.tsx           # Root layout with navigation
public/             # Static assets
index.html          # HTML shell
taskr-icon-kit/     # Logo, favicon, icon fonts
vite.config.ts      # Vite configuration + dev proxy
tsconfig*.json      # TypeScript configuration
```

---

## Design system

- **Background:** `#0a0a0a`
- **Surface:** `#141414`
- **Border:** `#2a2a2a`
- **Text:** `#ededed`
- **Muted text:** `#888888`
- **Accent:** `#ffac02`
- **Font:** `JetBrains Mono`
- **Corners:** square (`border-radius: 0`)

---

## Common issues

### Blank page on direct navigation to `/flows` or `/runs/:id`

Make sure the Vite dev server is running. In production, the backend serves `Frontend/dist/index.html` for all unknown routes. If you see this in development, restart `npm run dev`.

### `Failed to load runs` / backend connection error

The backend is not running or is on a different port. Check `VITE_API_BASE` in `Frontend/.env` and `TASKR_PORT` in `Backend/.env`.

### Type errors after pulling latest code

```bash
npm run typecheck
```

Fix any missing dependencies or broken imports before committing.

---

## Production build

```bash
npm run build
```

The backend serves the contents of `dist/` at `/` in production. Make sure `dist/` is built before deploying.
