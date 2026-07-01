# Budgets, credits, and Stripe in Taskr

Taskr tracks spend at the **node-state** level and rolls it up to the **run** level. A node can report a `cost_cents` value in its output, and the runner adds that amount to both the node state and the run total. This is the foundation for budget-aware flows.

---

## How cost tracking works

### Schema

Two columns store cost:

- `NODE_STATE.cost_cents` — spend attributed to a single node execution.
- `RUN.total_cost_cents` — sum of all node costs for that run.

Both are unsigned integers (`CHECK >= 0`) and are stored in cents.

### Runner behavior

When a node completes, the runner looks at `result.output["cost_cents"]`. If it is present and positive:

1. The value is added to `NODE_STATE.cost_cents`.
2. The value is added to `RUN.total_cost_cents` via `repo.add_run_cost()`.
3. Downstream nodes can read it from `$nodes.<node_id>.output.cost_cents`.

This is a write-only ledger: costs are accumulated, never subtracted. Retries create new node states with their own cost records, so retry spend is also captured.

### Cost in integration results

Any `api` or `hermes` integration can return a `cost_cents` field in its output dictionary. The runner treats this value as authoritative. For example:

```json
{
  "image_url": "http://localhost:9122/image/1",
  "balance": 40,
  "credits_deducted": 10,
  "cost_cents": 10
}
```

The runner will record `10` cents for that node and roll it into the run total.

---

## Budget-aware flow pattern

Budgets are not enforced globally by the runner. Instead, flows encode budget logic as ordinary nodes:

1. **Check credits** — call a provider's `/credits` endpoint to get the current balance.
2. **Top up if low** — call a Stripe-backed binding to charge a card if the balance is below a threshold.
3. **Apply credits** — call the provider's `/topup` endpoint to reflect the new balance.
4. **Do the paid work** — call the provider's `/generate` endpoint, which returns `cost_cents`.

The `stripe-budget-demo` flow uses this exact pattern.

### Budget gating

The top-up node can refuse to charge if `run.total_cost_cents + amount_cents > budget_cents`. This lets a flow fail early when the run is about to exceed a budget supplied in the run context, e.g.:

```json
{"budget_cents": 100}
```

---

## The Stripe demo binding

The runner recognizes a special `api` binding URL:

```
url_template: "stripe://top-up"
```

When a node with this URL is dispatched, the runner calls `_start_stripe_top_up()` instead of making a generic HTTP request. This is a demo-only convenience binding.

### Inputs expected by the Stripe top-up node

| Field | Type | Purpose |
|---|---|---|
| `balance` | integer | Current credit balance in cents |
| `threshold_credits` | integer (from binding config) | Minimum balance before a charge is triggered |
| `amount_cents` | integer | How much to charge if balance is below threshold |
| `budget_cents` | integer | Run budget cap; charge is rejected if it would exceed the cap |
| `description` | string | Stripe charge description |

### Outputs returned

| Field | Meaning |
|---|---|
| `ok` | Whether the top-up succeeded or was unnecessary |
| `charged` | `true` if a Stripe charge was created |
| `balance` | New balance after the charge (or unchanged if no charge) |
| `cost_cents` | Amount charged, if any |

### Configuration

Set `STRIPE_SECRET_KEY` to a Stripe test-mode key (`sk_test_*`). The runner will use `pm_card_visa` as a test payment method and create/confirm a PaymentIntent in one call. The charge is idempotent per run/node pair.

Without `STRIPE_SECRET_KEY`, the Stripe top-up node fails with `stripe_not_configured`.

---

## Seeding the Stripe demo flow

A helper script creates the demo flow and bindings:

```bash
cd Backend
uv run python tools/seed_stripe_budget_demo.py
```

By default the script expects a fake image provider on `http://127.0.0.1:9122`. You can override it:

```bash
TASKR_FAKE_IMAGE_PROVIDER_URL=http://127.0.0.1:9999 uv run python tools/seed_stripe_budget_demo.py
```

Then create a run and tick it to completion:

```bash
# Create a run with a budget cap
curl -X POST http://127.0.0.1:9113/runs \
  -H "Content-Type: application/json" \
  -d '{"flow_slug":"stripe-budget-demo","context":{"budget_cents":100}}'

# Tick until terminal
# Use the frontend workbench or call POST /runs/{run_id}/tick repeatedly
```

---

## Testing

`tests/test_stripe_budget_demo.py` runs the full Stripe budget demo in-memory with a fake HTTP server and a mocked Stripe API. It verifies:

- The run completes.
- `total_cost_cents` is recorded on the run.
- The top-up node records the Stripe charge amount as its cost.
- The generate node records its own cost.
- Stripe is called with the expected amount and idempotency key.

Run it with:

```bash
uv run pytest tests/test_stripe_budget_demo.py -q
```

---

## Extending cost tracking

To add cost tracking to a new integration:

1. Return `"cost_cents"` in the integration's output dictionary.
2. Make sure the value is a non-negative integer.
3. Optionally read `RUN.total_cost_cents` or a run-context budget to gate execution.

There is no separate billing service. Cost is a plain integer that flows travel with, so any workflow that needs accounting can implement its own policy without backend changes.
