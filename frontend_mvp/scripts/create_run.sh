#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

FLOW_SLUG=""
FLOW_VERSION_ID=""
CONTEXT_JSON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version)
      FLOW_VERSION_ID="${2:-}"
      if [[ -z "$FLOW_VERSION_ID" ]]; then
        python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Usage: create_run.sh [--version <flow_version_id>] [--context <json>] [<flow_slug>]'))"
        exit 1
      fi
      shift 2
      ;;
    --context)
      CONTEXT_JSON="${2:-}"
      if [[ -z "$CONTEXT_JSON" ]]; then
        python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Usage: create_run.sh [--version <flow_version_id>] [--context <json>] [<flow_slug>]'))"
        exit 1
      fi
      shift 2
      ;;
    --help|-h)
      echo "Usage: create_run.sh [--version <flow_version_id>] [--context <json>] [<flow_slug>]"
      exit 0
      ;;
    -*)
      python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Unknown option: $1'))"
      exit 1
      ;;
    *)
      FLOW_SLUG="$1"
      shift
      ;;
  esac
done

BODY='{}'
if [[ -n "$FLOW_VERSION_ID" ]]; then
  BODY="{\"flow_version_id\":\"$FLOW_VERSION_ID\"}"
  if [[ -n "$CONTEXT_JSON" ]]; then
    BODY="{\"flow_version_id\":\"$FLOW_VERSION_ID\",\"context\":$CONTEXT_JSON}"
  fi
elif [[ -n "$FLOW_SLUG" ]]; then
  BODY="{\"flow_slug\":\"$FLOW_SLUG\"}"
  if [[ -n "$CONTEXT_JSON" ]]; then
    BODY="{\"flow_slug\":\"$FLOW_SLUG\",\"context\":$CONTEXT_JSON}"
  fi
elif [[ -n "$CONTEXT_JSON" ]]; then
  BODY="{\"context\":$CONTEXT_JSON}"
fi

echo "Starting a new run..."
run=$(curl -sf -X POST "$BACKEND/runs" -H 'Content-Type: application/json' -d "$BODY") || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not reach backend at $BACKEND. Is the server running?'))"
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
print(success("Run created. Run tick.sh to advance it."))
PY
