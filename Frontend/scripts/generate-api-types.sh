#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_OPENAPI="$PROJECT_ROOT/../Backend/openapi.json"
OUT="$PROJECT_ROOT/src/api/api-types.ts"

mkdir -p "$(dirname "$OUT")"
npx openapi-typescript "$BACKEND_OPENAPI" -o "$OUT"
