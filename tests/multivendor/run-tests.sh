#!/usr/bin/env bash
# Test harness for the multivendor CLI driver (spec 076).
#
# Follows spec 075's tests/reconcile/run-tests.sh convention: bash + the server's
# own venv, no test framework, so this runs in a bare CI container.
#
# Exit codes are captured DIRECTLY, never through a pipe. `cmd | tail` reports
# tail's status, not cmd's — that mistake misdiagnosed spec 075's central premise
# and is the reason this comment exists.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_PY="$REPO_ROOT/mcp-servers/multivendor-cli-mcp/.venv/bin/python"
PASS=0
FAIL=0

if [ ! -x "$VENV_PY" ]; then
    echo "ERROR: server venv missing at $VENV_PY" >&2
    echo "  create it with: virtualenv -p /usr/bin/python3 mcp-servers/multivendor-cli-mcp/.venv" >&2
    echo "  (ensurepip is unavailable for Python 3.14 on this host, so 'python3 -m venv' fails)" >&2
    exit 2
fi

run_suite() {
    local label="$1" script="$2"
    echo "=== $label ==="
    "$VENV_PY" "$script"
    local rc=$?          # captured directly — no pipe
    if [ "$rc" -eq 0 ]; then
        echo "  SUITE PASS ($label)"
        PASS=$((PASS + 1))
    else
        echo "  SUITE FAIL ($label, exit $rc)"
        FAIL=$((FAIL + 1))
    fi
    echo
}

echo "### Dependency isolation (FR-030a/c) ###"
# The venv must have the packages; the SYSTEM interpreter must not. If these ever
# converge, isolation has silently broken and the NCFED cryptography version is
# at risk (research R7, T005 found the venv resolves cryptography 49 vs system 46).
for mod in nornir napalm netmiko jdiff; do
    if "$VENV_PY" -c "import $mod" >/dev/null 2>&1; then
        echo "  ok   venv imports $mod"; PASS=$((PASS + 1))
    else
        echo "  FAIL venv cannot import $mod"; FAIL=$((FAIL + 1))
    fi
    if /usr/bin/python3 -c "import $mod" >/dev/null 2>&1; then
        echo "  FAIL $mod LEAKED into the system interpreter"; FAIL=$((FAIL + 1))
    else
        echo "  ok   $mod absent from system interpreter"; PASS=$((PASS + 1))
    fi
done
echo

run_suite "Command filter contract (FR-022/023/029)" "$REPO_ROOT/tests/multivendor/test_filter.py"

if [ -f "$REPO_ROOT/tests/multivendor/test_inventory.py" ]; then
    run_suite "Inventory sources contract (FR-017*)" "$REPO_ROOT/tests/multivendor/test_inventory.py"
fi

echo "### Summary ###"
printf '  suites/checks passed: %d\n  failed: %d\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
echo "  all multivendor tests passed"
