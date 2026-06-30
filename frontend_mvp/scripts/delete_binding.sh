#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BINDING_ID="${1:-}"

if [[ -z "$BINDING_ID" ]]; then
  echo "Usage: $0 <binding_id>"
  echo ""
  echo "  Permanently delete an integration binding."
  echo ""
  echo "  Bindings that are referenced by flow nodes cannot be deleted."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

http_status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BACKEND/bindings/$BINDING_ID")

if [[ "$http_status" -ge 200 && "$http_status" -lt 300 ]]; then
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import success; print(success('Binding deleted.'))"
else
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Failed to delete binding (HTTP $http_status). The binding may not exist or is in use by a flow node.'))"
  exit 1
fi
