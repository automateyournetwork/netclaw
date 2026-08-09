#!/usr/bin/env bash
# Contract tests for bgp-intel-mcp — spec 081 (roadmap R9).
#
# Bash + stdlib only, following tests/reconcile/run-tests.sh (spec 075).
#
# EVERY TEST HERE RUNS WITHOUT TOUCHING A PUBLIC API. The rate-limit suite stubs
# the transport so it can assert on the request timeline the limiter produces;
# the rest are pure functions. That matters twice over: these are volunteer-funded
# services that should not be hit by CI, and the guarantees under test are
# structural, so they are provable without the network.
#
# Live verification against the real sources is separate and lives in the task
# list (T048, T049, T056, T057, T067, T068, T073, T083).
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1

FAILED=0
run() {
    local name="$1" path="$2"
    echo
    echo "=============================================================="
    echo "  $name"
    echo "=============================================================="
    python3 "$path" || { FAILED=$((FAILED + 1)); return 1; }
}

run "outcomes    — the four RPKI states (FR-002/003/004, SC-004/005)" tests/bgp-intel/test_outcomes.py
run "envelope    — provenance + GAIT (FR-019/021/022, SC-012/013/014)" tests/bgp-intel/test_envelope.py
run "validate    — local refusal as disclosure control (FR-028, SC-015)" tests/bgp-intel/test_validate.py
run "rate limit  — sliding window + TTL cache (FR-023/026, SC-016a/017)" tests/bgp-intel/test_rate_limit.py
run "surface     — read-only + <= 5,000 token ceiling (FR-034/027a)"           tests/bgp-intel/test_manifest_size.py

echo
echo "=============================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "  ALL SUITES PASSED"
    exit 0
fi
echo "  $FAILED SUITE(S) FAILED"
exit 1
