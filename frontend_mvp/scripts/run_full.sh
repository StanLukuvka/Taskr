#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND="${BACKEND:-http://localhost:9120}"

usage() {
  echo "Usage: $0 [--auto-answer <answer>] [--interval <seconds>]"
  echo ""
  echo "  Full demo: list flows, create a run, tick, and poll to completion."
  echo "  This is the easiest way to see Taskr in action."
  echo ""
  echo "Options:"
  echo "  --auto-answer <answer>  Automatically answer every open question with <answer>"
  echo "  --interval <seconds>    Polling interval (default: 2)"
  echo ""
  echo "Environment:"
  echo "  BACKEND                 Base URL for the Taskr API (default: http://localhost:9120)"
  exit 1
}

AUTO_ANSWER=""
INTERVAL=2

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --auto-answer)
      AUTO_ANSWER="${2:-}"
      shift 2
      ;;
    --interval)
      INTERVAL="${2:-2}"
      shift 2
      ;;
    -h|--help)
      usage
      ;;
    *)
      echo "Unknown option: $1"
      usage
      ;;
  esac
done

export INTERVAL

echo ""
echo "  ╔══════════════════════════════════════════╗"
echo "  ║          Taskr — Full Run Runner         ║"
echo "  ╚══════════════════════════════════════════╝"
echo ""

echo "  Step 1: List available flows"
bash "$SCRIPT_DIR/list_flows.sh"
echo ""

echo "  Step 2: Create run"
run_json=$(curl -sf -X POST "$BACKEND/runs" -H 'Content-Type: application/json' -d '{}') || {
  python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not create run. Is the backend running at $BACKEND?'))"
  exit 1
}
run_id=$(python3 -c "import json,sys; print(json.loads(sys.argv[1])['id'])" "$run_json")

if [[ -z "$run_id" ]]; then
  echo "  ✗ Failed to create run"
  exit 1
fi

python3 - "$run_json" "$SCRIPT_DIR" <<'PY'
import json, sys
sys.path.insert(0, sys.argv[2])
from _format import format_run, success
run = json.loads(sys.argv[1])
print()
print(format_run(run))
print()
print(success("Run created."))
PY

echo ""
echo "  Step 3: Initial tick"
bash "$SCRIPT_DIR/tick.sh" "$run_id" >/dev/null
echo "  ✓ Tick sent"
echo ""

if [[ -n "$AUTO_ANSWER" ]]; then
  echo "  Step 4: Poll to completion (auto-answer: $AUTO_ANSWER)"
else
  echo "  Step 4: Poll run (stop at first question)"
fi
echo ""
bash "$SCRIPT_DIR/poll_run.sh" "$run_id" ${AUTO_ANSWER:+"$AUTO_ANSWER"}
