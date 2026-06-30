#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id>"
  echo ""
  echo "  Inspect a run and its step states."
  echo ""
  echo "  Shows the run's current status, all node states, and which"
  echo "  steps are active, completed, or waiting."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

run=$(curl -sf "$BACKEND/runs/$RUN_ID") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Run not found or backend unreachable at $BACKEND.'))"
  exit 1
}

python3 - "$run" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_run, failure

try:
    run = json.loads(sys.argv[1])
except json.JSONDecodeError:
    print(failure("Could not parse response from backend."))
    sys.exit(1)

print()
print(format_run(run))
print()
PY
