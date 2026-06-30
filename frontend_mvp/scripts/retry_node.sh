#!/usr/bin/env bash
# Retry a single node state within a run.
#
# Usage: ./retry_node.sh <run_id> <node_state_id>

set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RUN_ID="${1:-}"
NODE_STATE_ID="${2:-}"

if [[ -z "$RUN_ID" || -z "$NODE_STATE_ID" ]]; then
    echo "Usage: $0 <run_id> <node_state_id>"
    echo ""
    echo "  Reset NODE_STATE_ID to pending within RUN_ID so the next tick"
    echo "  re-runs it. The run is moved back to running if terminal."
    echo ""
    echo "Environment:"
    echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
    exit 1
fi

if ! curl -sf "$BACKEND/health" >/dev/null 2>&1; then
    python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Backend unreachable at $BACKEND.'))"
    exit 1
fi

resp=$(curl -sf -X POST "$BACKEND/runs/$RUN_ID/node-states/$NODE_STATE_ID/retry" -H 'Content-Type: application/json') || {
    python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not retry node state. Check IDs and that the node is a top-level action node.'))"
    exit 1
}

python3 - "$resp" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import success

result = json.loads(sys.argv[1])
print()
print(success(f"Node state {result.get('node_state_id')} is now {result.get('status')}"))
print(f"  run_id: {result.get('run_id')}")
PY
