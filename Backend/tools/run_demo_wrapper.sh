#!/usr/bin/env bash
set -euo pipefail

set -a
source "$(dirname "$0")/../.env"
set +a

export TASKR_ALLOW_PRIVATE_URLS=1

cd /agent/projects/taskr/Backend
exec tools/run_stripe_budget_demo.sh
