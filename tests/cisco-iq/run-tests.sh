#!/usr/bin/env bash
# Offline contract tests for the Cisco IQ remote MCP integration (spec 191, issue #346).
# No network beyond 127.0.0.1 mocks, no credentials, stdlib only. Live checks are opt-in:
#   scripts/cisco-iq-enable.sh diagnose --live   (needs a real key; never run here)
set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1
FAILED=0
for t in test_enable test_operate test_policy_docs; do
    echo "== $t"
    python3 -I -m unittest discover -s tests/cisco-iq -p "$t.py" -t tests/cisco-iq 2>&1 || FAILED=$((FAILED+1))
done
echo "NEEDS_LIVE_CREDENTIALS: live Cisco IQ connectivity not run (set CISCO_IQ_API_KEY and use diagnose --live)"
[ "$FAILED" -eq 0 ] && { echo "ALL SUITES PASSED"; exit 0; }
echo "$FAILED SUITE(S) FAILED"; exit 1
