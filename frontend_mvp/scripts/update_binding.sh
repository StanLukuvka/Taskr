#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINDING_ID="${1:-}"
PAYLOAD="${2:-}"

if [[ -z "$BINDING_ID" || -z "$PAYLOAD" ]]; then
  echo "Usage: $0 <binding_id> <json_file_or_inline_json>"
  echo ""
  echo "  Update an existing integration binding."
  echo ""
  echo "  The payload must match the binding's existing kind (api or hermes)."
  echo "  You may pass either a path to a JSON file or a raw JSON string."
  echo ""
  echo "Examples:"
  echo "  $0 b-abc123 binding.json"
  echo "  $0 b-abc123 '{\"kind\":\"api\",\"display_title\":\"Updated title\"}'"
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

if [[ -f "$PAYLOAD" ]]; then
  DATA_OPT="@$PAYLOAD"
else
  DATA_OPT="$PAYLOAD"
fi

binding=$(curl -sf -X PUT "$BACKEND/bindings/$BINDING_ID" -H 'Content-Type: application/json' --data-binary "$DATA_OPT") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not update binding. Binding may not exist, kind may mismatch, or payload invalid.'))"
  exit 1
}

python3 - "$binding" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_binding, success

binding = json.loads(sys.argv[1])
print()
print(format_binding(binding))
print()
print(success("Binding updated."))
PY
