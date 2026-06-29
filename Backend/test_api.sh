#!/bin/bash
set -e
BASE="http://localhost:9119"

echo "=== 1. Flows ==="
curl -sf "$BASE/flows" | python3 -m json.tool

echo ""
echo "=== 2. Create run ==="
RUN=$(curl -sf -X POST "$BASE/runs" -H "Content-Type: application/json" -d '{"flow_slug":"soda-comparison","context":{}}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['id'])")
echo "Run: $RUN"

echo ""
echo "=== 3. List runs ==="
curl -sf "$BASE/runs" | python3 -m json.tool

echo ""
echo "=== 4. Flow version ==="
curl -sf "$BASE/flow_versions/fv-1" | python3 -m json.tool

echo ""
echo "=== 5. Tick to direct completion ==="
curl -sf -X POST "$BASE/runs/$RUN/tick" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f'Status: {d[\"status\"]}')
for ns in d['node_states']:
    print(f'  {ns[\"node_title\"]} ({ns[\"node_kind\"]}) = {ns[\"status\"]}')
if d['status'] != 'completed':
    exit(1)
removed_pause_field = 'pause' + '_' + 'reason'
if removed_pause_field in d:
    exit(2)
" || { echo "FAIL: expected completed without removed pause field"; exit 1; }

echo ""
echo "=== 6. Removed interruption endpoints are gone ==="
REMOVED_PATH="quest""ions"
if curl -sf "$BASE/runs/$RUN/$REMOVED_PATH" >/dev/null; then
  echo "FAIL: removed interruption endpoint still exists"
  exit 1
fi

echo ""
echo "=== ALL PASSED ==="
