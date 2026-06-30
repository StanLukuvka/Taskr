#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id>"
  echo ""
  echo "  Permanently delete a run and all its step records."
  echo ""
  echo "  This cannot be undone. Use cancel_run.sh instead if you"
  echo "  want to stop a run but keep its history."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

echo "Deleting run $RUN_ID..."
http_status=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BACKEND/runs/$RUN_ID")

if [[ "$http_status" -ge 200 && "$http_status" -lt 300 ]]; then
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import success; print(success('Run deleted.'))"
else
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Failed to delete (HTTP $http_status). The run may not exist.'))"
  exit 1
fi
