#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

bindings=$(curl -sf "$BACKEND/bindings") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not reach backend at $BACKEND. Is the server running?'))"
  exit 1
}

python3 - "$bindings" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_binding_row, header, _c, _C

bindings = json.loads(sys.argv[1])
print(header("Integration Bindings"))
if not bindings:
    print("    No bindings yet. Use create_binding.sh to add one.")
    print()
    sys.exit(0)

print(f"  {_c(_C.DIM, f"{'Kind':<8}  {'ID':<26}  {'Title':<24}  {'Status'}")}")
print(f"  {_c(_C.DIM, '─' * 76)}")

for b in bindings:
    print(format_binding_row(b))

print()
PY
