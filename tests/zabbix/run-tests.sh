#!/usr/bin/env bash
# Contract tests for zabbix-mcp — spec 083 (roadmap R11).
#
# Bash + stdlib only, following tests/bgp-intel/run-tests.sh (spec 075 lineage).
#
# TWO KINDS OF TEST, and the split matters. This feature ADOPTS a third-party server
# unmodified, so NetClaw authors no server code and there is no chokepoint to test:
#
#   STATIC  — runs anywhere. Does NetClaw force read-only? Is the deny-list real and
#             non-vacuous? Does the venv isolate? Does the skill contain a FOLLOWABLE
#             PROCEDURE rather than a warning?
#   LIVE    — needs ZABBIX_URL + ZABBIX_TOKEN. Does following that procedure produce the
#             right answer from a real NMS? Skipped without a lab.
#
# Asserting on skill text alone would prove nothing about the answer a user receives.
# That is the cost of adopt-as-is, and this suite is built to face it rather than
# generate green ticks around it.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT" || exit 1
export PYTHONPATH="$REPO_ROOT/tests/zabbix:${PYTHONPATH:-}"

FAILED=0
run() {
    local name="$1" path="$2"
    echo
    echo "=============================================================="
    echo "  $name"
    echo "=============================================================="
    python3 "$path" || { FAILED=$((FAILED + 1)); return 1; }
}

run "read-only  — forced by NetClaw, deny-list non-vacuous (FR-021a/b, SC-018a/b)" tests/zabbix/test_readonly_forced.py
run "venv       — fastmcp 3.x isolated from five <3 pins (FR-037a/b/c, SC-026/027)"  tests/zabbix/test_venv_isolation.py
run "skills     — a followable PROCEDURE, not a warning (FR-006a, FR-045..049)"      tests/zabbix/test_skill_procedure.py
run "manifest   — <= 5,000 tokens, 3-tool surface stable (FR-044, SC-021/030)"       tests/zabbix/test_manifest_size.py

if [ -n "${ZABBIX_URL:-}" ] && [ -n "${ZABBIX_TOKEN:-}" ]; then
    run "LIVE traps — both reproduce against a real NMS (FR-001..006b, SC-002..005/016)" tests/zabbix/test_live_traps.py
else
    echo
    echo "=============================================================="
    echo "  LIVE traps — SKIPPED (set ZABBIX_URL and ZABBIX_TOKEN)"
    echo "  Static tests prove the skill SAYS the right thing."
    echo "  Only the live suite proves following it gives the right ANSWER."
    echo "=============================================================="
fi

echo
echo "=============================================================="
if [ "$FAILED" -eq 0 ]; then
    echo "  ALL SUITES PASSED"
    exit 0
fi
echo "  $FAILED SUITE(S) FAILED"
exit 1
