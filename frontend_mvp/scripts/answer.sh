#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"
NODE_STATE_ID="${2:-}"
ANSWER="${3:-}"

if [[ -z "$RUN_ID" || -z "$NODE_STATE_ID" || -z "$ANSWER" ]]; then
  echo "Usage: $0 <run_id> <node_state_id> <answer>"
  echo ""
  echo "  Answer an open question that's blocking a run."
  echo ""
  echo "  When a step pauses for input (status: blocked), it creates an"
  echo "  open question. Provide your answer here to unblock it, then"
  echo "  run tick.sh to resume the run."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

# Build the JSON payload safely so answers containing quotes do not break the request.
payload=$(python3 -c "import json,sys; print(json.dumps({'answer': sys.argv[1]}))" "$ANSWER")

echo "Submitting answer for step $NODE_STATE_ID..."
http_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND/runs/$RUN_ID/node-states/$NODE_STATE_ID/answer" \
  -H 'Content-Type: application/json' \
  -d "$payload")

if [[ "$http_status" -ge 200 && "$http_status" -lt 300 ]]; then
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import success; print(success('Answer submitted. Run tick.sh to resume the run.'))"
else
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Failed to submit answer (HTTP $http_status). Check that the run and node state IDs are valid.'))"
  exit 1
fi
