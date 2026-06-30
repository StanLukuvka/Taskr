#!/usr/bin/env bash
# Restart a run from a specific flow node.
#
# Usage: ./restart_from.sh <run_id> <node_id>

set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RUN_ID="${1:-}"
NODE_ID="${2:-}"

if [[ -z "$RUN_ID" || -z "$NODE_ID" ]]; then
    echo "Usage: $0 <run_id> <node_id>"
    echo ""
    echo "  Create a new run from the same flow and context as RUN_ID,"
    echo "  starting from NODE_ID. Upstream completed action nodes are"
    echo "  copied; the target node and downstream nodes are pending."
    echo ""
    echo "Environment:"
    echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
    exit 1
fi

if ! curl -sf "$BACKEND/health" >/dev/null 2>&1; then
    python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Backend unreachable at $BACKEND.'))"
    exit 1
fi

run=$(curl -sf -X POST "$BACKEND/runs/$RUN_ID/restart_from" \
    -H 'Content-Type: application/json' \
    -d "{\"node_id\": \"$NODE_ID\"}") || {
    python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not restart run. Check that the run and node IDs are valid.'))"
    exit 1
}

python3 - "$run" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_run, success

run = json.loads(sys.argv[1])
print()
print(format_run(run))
print()
print(success(f"New run created from restart. source_run_id={run.get('source_run_id')}"))
PY
