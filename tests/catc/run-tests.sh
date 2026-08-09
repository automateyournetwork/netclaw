#!/usr/bin/env bash
# Contract tests for catc-mcp — spec 087.
#
# STATIC — the catalogue is read-only, correctly grouped, dispatchable, and the manifest
#          stays under the ceiling. This is what stops a 1,821-token surface drifting back
#          toward the 64,420 it would cost to inline every upstream tool.
# LIVE   — needs CATC_TEST_HOST + credentials. Proves dispatch works, and (with
#          CATC_TEST_EMPTY_HOST) proves the central distinction: two appliances, same
#          credentials, one empty, two different answers.
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"; cd "$REPO_ROOT" || exit 1
export PYTHONPATH="$REPO_ROOT/tests/catc:${PYTHONPATH:-}"
FAILED=0
run(){ echo; echo "=============================================================="; echo "  $1"; \
       echo "=============================================================="; python3 "$2" || FAILED=$((FAILED+1)); }
run "catalogue — 514 read-only ops, 8 groups, manifest <= 5,000 (FR-001..006)" tests/catc/test_catalogue.py
if [ -n "${CATC_TEST_HOST:-}" ]; then
  run "LIVE — dispatch, and empty-vs-populated appliances (SC-001..SC-008)" tests/catc/test_live_catc.py
else
  echo; echo "=============================================================="
  echo "  LIVE — SKIPPED (set CATC_TEST_HOST, CATC_TEST_USER, CATC_TEST_PASS)"
  echo "  Static tests prove the catalogue is right."
  echo "  Only the live suite proves an empty appliance reads differently"
  echo "  from an empty network — which is why this feature exists."
  echo "=============================================================="
fi
echo; echo "=============================================================="
[ "$FAILED" -eq 0 ] && { echo "  ALL SUITES PASSED"; exit 0; }; echo "  $FAILED SUITE(S) FAILED"; exit 1
