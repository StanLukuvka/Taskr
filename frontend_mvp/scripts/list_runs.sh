#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

runs=$(curl -sf "$BACKEND/runs") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not reach backend at $BACKEND. Is the server running?'))"
  exit 1
}

python3 - "$runs" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_run_row, header, _c, _C

runs = json.loads(sys.argv[1])
print(header("All Runs"))
if not runs:
    print("    No runs yet. Use create_run.sh to start one.")
    print()
    sys.exit(0)

# Column header (aligns with format_run_row: "  icon label(11)  id(24)  flow(16)  created")
print(f"  {_c(_C.DIM, f\"{'':2}{'Status':<11}  {'ID':<24}  {'Flow':<16}  {'Created'}\")}")
print(f"  {_c(_C.DIM, '─' * 82)}")

for r in runs:
    print(format_run_row(r))
    if r.get('pause_reason'):
        print(f"      {_c(_C.YELLOW, '⏳')} {r['pause_reason']}")

print()
PY
