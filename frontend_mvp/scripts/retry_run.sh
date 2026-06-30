#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id>"
  echo ""
  echo "  Retry a failed or cancelled run by creating a fresh run"
  echo "  from the same flow and context."
  echo ""
  echo "  The original run is left unchanged for audit purposes."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

echo "Retrying run $RUN_ID..."
run=$(curl -sf -X POST "$BACKEND/runs/$RUN_ID/retry" -H 'Content-Type: application/json' -d '{}') || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not retry run. Check that the run ID is valid.'))"
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
print(success("New run created from retry. Run tick.sh to start it."))
PY
