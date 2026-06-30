#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id>"
  echo ""
  echo "  Cancel a running, blocked, or paused run."
  echo ""
  echo "  Cancellation is a local state change — in-flight API calls"
  echo "  are not interrupted. The run stops advancing and all active"
  echo "  steps are marked cancelled."
  echo ""
  echo "Environment:"
  echo "  BACKEND  Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
fi

echo "Cancelling run $RUN_ID..."
http_status=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$BACKEND/runs/$RUN_ID/cancel" -H 'Content-Type: application/json' -d '{}')

if [[ "$http_status" -ge 200 && "$http_status" -lt 300 ]]; then
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import success; print(success('Run cancelled.'))"
else
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Failed to cancel (HTTP $http_status). The run may already be completed or cancelled.'))"
  exit 1
fi
