#!/usr/bin/env bash
set -euo pipefail

cd /agent/projects/taskr/Backend

export TASKR_ALLOW_PRIVATE_URLS=1
BASE_URL="${TASKR_BASE_URL:-http://127.0.0.1:8000}"
PROVIDER_URL="${TASKR_FAKE_IMAGE_PROVIDER_URL:-http://127.0.0.1:9122}"
PROVIDER_HOST="${TASKR_FAKE_IMAGE_PROVIDER_HOST:-127.0.0.1}"
PROVIDER_PORT="${TASKR_FAKE_IMAGE_PROVIDER_PORT:-9122}"
MAX_TICKS="${TASKR_MAX_TICKS:-10}"

if [[ -z "${STRIPE_SECRET_KEY:-}" ]]; then
  echo "STRIPE_SECRET_KEY must be set to a Stripe test-mode key" >&2
  exit 1
fi

provider_pid=""
server_pid=""
cleanup() {
  local exit_code=$?
  if [[ -n "$server_pid" ]] && kill -0 "$server_pid" 2>/dev/null; then
    kill "$server_pid" 2>/dev/null || true
    wait "$server_pid" 2>/dev/null || true
  fi
  if [[ -n "$provider_pid" ]] && kill -0 "$provider_pid" 2>/dev/null; then
    kill "$provider_pid" 2>/dev/null || true
    wait "$provider_pid" 2>/dev/null || true
  fi
  return $exit_code
}
trap cleanup EXIT

rm -f taskr.db*

uv run python tools/fake_image_provider.py --host "$PROVIDER_HOST" --port "$PROVIDER_PORT" --initial-balance 0 >/tmp/taskr-fake-image-provider.log 2>&1 &
provider_pid=$!

for _ in $(seq 1 30); do
  if curl -sf "$PROVIDER_URL/credits" >/dev/null; then
    break
  fi
  sleep 0.2
done
curl -sf "$PROVIDER_URL/credits" >/dev/null

uv run uvicorn app.main.app:app --host 127.0.0.1 --port 8000 >/tmp/taskr-stripe-budget-demo-server.log 2>&1 &
server_pid=$!

for _ in $(seq 1 50); do
  if curl -sf "$BASE_URL/flows" >/dev/null; then
    break
  fi
  sleep 0.2
done
curl -sf "$BASE_URL/flows" >/dev/null

TASKR_FAKE_IMAGE_PROVIDER_URL="$PROVIDER_URL" uv run python tools/seed_stripe_budget_demo.py

create_payload='{"flow_slug":"stripe-budget-demo","context":{"budget_cents":100}}'
run_json=$(curl -sf -X POST "$BASE_URL/runs" -H 'Content-Type: application/json' -d "$create_payload")
run_id=$(python -c 'import json,sys; print(json.loads(sys.argv[1])["id"])' "$run_json")

echo "Created run: $run_id"

tick_json=''
for _ in $(seq 1 "$MAX_TICKS"); do
  tick_json=$(curl -sf -X POST "$BASE_URL/runs/$run_id/tick")
  status=$(python -c 'import json,sys; print(json.loads(sys.argv[1])["status"])' "$tick_json")
  echo "Tick status: $status"
  if [[ "$status" == "completed" || "$status" == "failed" || "$status" == "cancelled" ]]; then
    python -m json.tool <<<"$tick_json"
    exit 0
  fi
  sleep 0.2
done

echo "Run $run_id did not reach a terminal state after $MAX_TICKS ticks" >&2
python -m json.tool <<<"$tick_json"
exit 1
