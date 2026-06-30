#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id>"
  echo ""
  echo "  Advance a run by one execution step (tick)."
  echo ""
  echo "  Each tick moves all pending nodes forward by one step."
  echo "  Runs that are paused (waiting on a question) won't advance"
  echo "  until the question is answered."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

echo "Advancing run $RUN_ID by one step..."
http_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND/runs/$RUN_ID/tick" -H 'Content-Type: application/json' -d '{}')

if [[ "$http_status" -lt 200 || "$http_status" -ge 300 ]]; then
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Tick failed (HTTP $http_status). Check if the run ID is valid.'))"
  exit 1
fi

echo "Fetching updated state..."
run=$(curl -sf "$BACKEND/runs/$RUN_ID") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not fetch run state after tick.'))"
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
print(success("Step complete. Run tick.sh again to advance further."))
PY
