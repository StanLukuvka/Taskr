#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

flows=$(curl -sf "$BACKEND/flows") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not reach backend at $BACKEND. Is the server running?'))"
  exit 1
}

python3 - "$flows" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_flow, header

flows = json.loads(sys.argv[1])
print(header("Available Flows"))
if not flows:
    print("    No flows found. The backend may need to be seeded.")
    print()
    sys.exit(0)

for f in flows:
    print()
    print(format_flow(f))
print()
PY
