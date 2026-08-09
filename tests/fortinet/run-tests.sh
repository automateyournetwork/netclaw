#!/usr/bin/env bash
# Contract tests for fortinet-mcp — spec 080 (roadmap R3).
#
# Bash + stdlib only, following tests/reconcile/run-tests.sh (spec 075). No new
# test framework in the shared environment.
#
# EVERY TEST HERE RUNS WITHOUT AN APPLIANCE. That is a design property, not a
# limitation: the guarantees this feature makes — plane attribution, scope
# validation, credential non-disclosure, distinct write-gate refusals, audit
# emission — are structural, so they are provable with no FortiGate in the room.
# It earned its keep on 2026-08-01, when the lab was unavailable all day.
#
# Live verification against real appliances is separate and lives in the task
# list (T034, T042, T049, T065).
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
    if python3 "$path"; then
        return 0
    fi
    FAILED=$((FAILED + 1))
    return 1
}

run "envelope    — plane/scope attribution (FR-005/009, SC-002a)" tests/fortinet/test_envelope.py
run "audit       — GAIT trail (FR-023, Principle IV, SC-011)"     tests/fortinet/test_audit.py
run "credentials — by-name-only disclosure (FR-029, SC-012)"      tests/fortinet/test_credentials.py
run "device plane — admin vs link, VPN phase 1 vs 2 (FR-015/016)" tests/fortinet/test_device_plane.py

echo
echo "=============================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "  ALL SUITES PASSED"
    exit 0
fi
echo "  $FAILED SUITE(S) FAILED"
exit 1
