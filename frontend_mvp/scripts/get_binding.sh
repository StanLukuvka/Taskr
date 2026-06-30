#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINDING_ID="${1:-}"

if [[ -z "$BINDING_ID" ]]; then
  echo "Usage: $0 <binding_id>"
  echo ""
  echo "  Retrieve a single integration binding and its kind-specific config."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

binding=$(curl -sf "$BACKEND/bindings/$BINDING_ID") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Binding not found or backend unreachable at $BACKEND.'))"
  exit 1
}

python3 - "$binding" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_binding

binding = json.loads(sys.argv[1])
print()
print(format_binding(binding))
print()
PY
