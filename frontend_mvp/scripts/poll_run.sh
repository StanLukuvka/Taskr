#!/usr/bin/env bash
set -euo pipefail

BACKEND="${BACKEND:-http://localhost:9120}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_ID="${1:-}"
INTERVAL="${INTERVAL:-2}"
AUTO_ANSWER="${AUTO_ANSWER:-}"

if [[ -z "$RUN_ID" ]]; then
  echo "Usage: $0 <run_id> [auto_answer_value]"
  echo ""
  echo "  Poll a run until it finishes or pauses for a question."
  echo ""
  echo "  The script checks the run every few seconds and displays"
  echo "  its current state. If a step blocks on a question, the"
  echo "  prompt is shown with instructions on how to answer."
  echo ""
  echo "Options:"
  echo "  auto_answer_value   If provided, automatically answer every open"
  echo "                      question with this value and keep polling."
  echo ""
  echo "Environment:"
  echo "  BACKEND      Base URL for the Taskr API (default: http://localhost:9120)"
  echo "  INTERVAL     Seconds between polls (default: 2)"
  echo "  AUTO_ANSWER  If set, automatically answer every open question."
  echo "               The positional argument overrides this environment variable."
  exit 1
fi

if [[ "${2:-}" ]]; then
  AUTO_ANSWER="$2"
fi

echo "Watching run $RUN_ID (checking every ${INTERVAL}s)..."
if [[ -n "$AUTO_ANSWER" ]]; then
  echo "Auto-answer mode: questions will be answered with '$AUTO_ANSWER'"
fi
echo

while true; do
  run_json=$(curl -sf "$BACKEND/runs/$RUN_ID") || {
    python3 -c "import sys; sys.path.insert(0,'$SCRIPT_DIR'); from _format import failure; print(failure('Could not reach backend. Retrying...'))"
    sleep "$INTERVAL"
    continue
  }

  exit_code=0
  python3 - "$BACKEND" "$RUN_ID" "$AUTO_ANSWER" "$run_json" "$SCRIPT_DIR" <<'PY' || exit_code=$?
import json, sys, subprocess
sys.path.insert(0, sys.argv[5])
from _format import format_run, status_text, success, failure, _c, _C

backend, run_id, auto_answer, run_json = sys.argv[1:5]
run = json.loads(run_json)
status = run.get('status', 'unknown')

print(format_run(run))
print()

# Check for open questions on blocked or paused nodes
open_questions = []
for ns in run.get('node_states', []):
    if ns.get('status') in ('blocked', 'paused'):
        try:
            resp = subprocess.run(
                ['curl', '-sf', f"{backend}/runs/{run_id}/node-states/{ns['id']}/questions"],
                capture_output=True, text=True, timeout=10
            )
            data = json.loads(resp.stdout)
            for q in data.get('questions', []):
                if q.get('status') == 'open':
                    title = ns.get('node_title') or ns.get('node_id', '?')
                    open_questions.append((ns['id'], q.get('id'), q.get('prompt', ''), title))
        except Exception:
            pass

if open_questions:
    print()
    print(f"  {_c(_C.BOLD, 'Open Questions')}")
    for node_state_id, question_id, prompt, node_title in open_questions:
        print(f"    {_c(_C.YELLOW, '⏳')} {node_title}")
        print(f"       {prompt}")
        print(f"       {_c(_C.DIM, f'answer with: answer.sh {run_id} {node_state_id} <your-answer>')}")
    print()

    if auto_answer:
        print(f"  Auto-answering with: {auto_answer}")
        for node_state_id, question_id, prompt, node_title in open_questions:
            answer_resp = subprocess.run(
                ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
                 '-X', 'POST', f"{backend}/runs/{run_id}/node-states/{node_state_id}/answer",
                 '-H', 'Content-Type: application/json',
                 '-d', json.dumps({"answer": auto_answer})],
                capture_output=True, text=True, timeout=10
            )
            if answer_resp.stdout.strip() not in ('200', '201', '202'):
                print(failure(f"Failed to answer {node_title}: HTTP {answer_resp.stdout.strip()}"))
                sys.exit(11)
            print(success(f"Answered: {node_title}"))

        # After answering, fire one tick and keep polling.
        tick_resp = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
             '-X', 'POST', f"{backend}/runs/{run_id}/tick",
             '-H', 'Content-Type: application/json', '-d', '{}'],
            capture_output=True, text=True, timeout=10
        )
        if tick_resp.stdout.strip() not in ('200', '201', '202'):
            print(failure(f"Tick failed after answer: HTTP {tick_resp.stdout.strip()}"))
            sys.exit(11)
        sys.exit(1)  # keep polling
    else:
        print(f"  {_c(_C.YELLOW, 'Run is waiting for your answer. Use answer.sh to respond.')}")
        sys.exit(10)

if status in ('completed', 'failed', 'cancelled'):
    print()
    if status == 'completed':
        print(success("Run completed successfully."))
    elif status == 'failed':
        failure_reason = run.get('failure_summary', 'Unknown error')
        print(failure(f"Run failed: {failure_reason}"))
    else:
        print(failure("Run cancelled."))
    sys.exit(0)

sys.exit(1)  # keep polling
PY

  if [[ "$exit_code" -eq 0 ]]; then
    exit 0
  elif [[ "$exit_code" -eq 10 || "$exit_code" -eq 11 ]]; then
    exit "$exit_code"
  fi

  sleep "$INTERVAL"
done
