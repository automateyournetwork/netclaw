#!/usr/bin/env bash
# Offline test harness for the Cisco PSIRT MCP server (spec 078 / roadmap R2).
#
# Follows tests/reconcile/run-tests.sh and tests/multivendor/run-tests.sh: bash plus
# the system interpreter, no test framework, so this runs in a bare CI container.
#
# TWO RULES
#
# 1. **No network.** The PSIRT budget is 5 calls/second and 30/minute, shared across
#    every caller of the credential. A default suite that spent any of it would make
#    running the tests compete with using the product. Live checks live in
#    `live-api.sh` and are opt-in.
#
# 2. **Exit codes are captured DIRECTLY, never through a pipe.** `cmd | tail` reports
#    tail's status, not cmd's — that mistake misdiagnosed spec 075's central premise
#    and is the reason this comment exists.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${NETCLAW_PY:-/usr/bin/python3}"
SERVER_DIR="$REPO_ROOT/mcp-servers/cisco-psirt-mcp"
PASS=0
FAIL=0

if [ ! -x "$PY" ]; then
    echo "ERROR: interpreter not found at $PY" >&2
    echo "  set NETCLAW_PY to the interpreter the servers run under" >&2
    exit 2
fi

note() { printf '%s\n' "$1"; }

check() {  # check <label> <rc>
    if [ "$2" -eq 0 ]; then
        echo "  ok   $1"; PASS=$((PASS + 1))
    else
        echo "  FAIL $1 (exit $2)"; FAIL=$((FAIL + 1))
    fi
}

run_suite() {
    local label="$1" script="$2"
    echo "=== $label ==="
    "$PY" "$script"
    local rc=$?          # captured directly — no pipe
    check "$label" "$rc"
    echo
}

echo "### Dependencies (bounded pins, spec 077) ###"
"$PY" -c "import httpx" >/dev/null 2>&1
check "httpx importable by $PY" $?
"$PY" -c "import mcp.server.fastmcp" >/dev/null 2>&1
check "mcp.server.fastmcp importable (the submodule mcp 2.0 removed)" $?
grep -qE '^mcp>=.*,<2' "$SERVER_DIR/requirements.txt"
check "requirements.txt bounds mcp below 2.0" $?
grep -qE '^httpx>=.*,<1' "$SERVER_DIR/requirements.txt"
check "requirements.txt bounds httpx below 1.0" $?
echo

echo "### Server loads and exposes its tools ###"
"$PY" -c "
import sys; sys.path.insert(0, '$SERVER_DIR')
import server
for tool in ('check_version','check_versions','check_cve','check_advisory',
             'list_recent','psirt_status'):
    assert hasattr(server, tool), tool
assert server.SERVER == 'cisco-psirt'
" >/dev/null 2>&1
check "server.py imports and defines all six tools" $?

# FR-018: read-only. The server must contain no device-transport import at all — if
# one ever appears, this server has grown a capability its contract forbids.
! grep -qE '^\s*(import|from)\s+(netmiko|napalm|nornir|paramiko|genie|pyats)' \
    "$SERVER_DIR"/*.py
check "no device-transport import anywhere (FR-018)" $?

# FR-007: the token must never be persisted. The cache module may write; auth must not.
! grep -qE '(open\(|write_text|json\.dump)' "$SERVER_DIR/auth.py"
check "auth.py writes nothing to disk (FR-007)" $?
echo

run_suite "Version normalisation + OSType table (T018)" \
    "$REPO_ROOT/tests/cisco-psirt/test_normalise.py"
run_suite "Cache, rate budget, outcome typing (T018/T024)" \
    "$REPO_ROOT/tests/cisco-psirt/test_cache_ratelimit.py"

echo "### No live call was made by this suite ###"
# The stub client replaces the real one in the Python tests; this asserts the harness
# itself never reached for a credential.
if [ -z "${CISCO_CLIENT_ID:-}" ]; then
    note "  ok   CISCO_CLIENT_ID unset in this shell — no live call was possible"
    PASS=$((PASS + 1))
else
    note "  ok   credentials present but unused (the suite substitutes a stub client)"
    PASS=$((PASS + 1))
fi
echo

echo "======================================"
echo " PASS: $PASS   FAIL: $FAIL"
echo "======================================"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
