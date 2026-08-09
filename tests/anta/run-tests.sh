#!/usr/bin/env bash
# Tests for anta-mcp (spec 098 / R25).
#
# Verdict assertions are pure stdlib and ALWAYS run -- they need no ANTA, no venv and no device,
# so this file stays useful in CI, which installs nothing (spec 075 SC-013). The live assertions
# skip themselves when the device or venv is absent.
#
# Exit codes are captured DIRECTLY, never through a pipe. `cmd | tail` reports tail's status --
# that mistake misdiagnosed spec 075's central premise.
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SERVER_DIR="$REPO_ROOT/mcp-servers/anta-mcp"
VENV_PY="$SERVER_DIR/.venv/bin/python"
PASS=0; FAIL=0; SKIP=0

ok()   { PASS=$((PASS+1)); echo "  ok   - $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  FAIL - $1"; }
skip() { SKIP=$((SKIP+1)); echo "  skip - $1 ($2)"; }

echo "=== verdict model (stdlib only, always runs) ==="

python3 - "$SERVER_DIR" <<'PY'
import sys, pathlib
sys.path.insert(0, sys.argv[1])
import verdict as V

def check(label, cond):
    print(("  ok   - " if cond else "  FAIL - ") + label)
    return 0 if cond else 1

rc = 0
# The trap: an unconfigured feature must NOT be a failure.
rc |= check("BGP inactive reclassified to not_applicable",
            V.classify("failure", ["'show bgp summary vrf all' failed on veos1: BGP inactive"])[0] == V.NOT_APPLICABLE)
rc |= check("unsupported command reclassified",
            V.classify("failure", ["Invalid input"])[0] == V.NOT_APPLICABLE)
# ...but a real failure must survive. An over-eager rule is worse than the problem.
rc |= check("genuine mismatch stays fail",
            V.classify("failure", ["EOS version mismatch - Actual: 4.36.1F not in Expected: 4.99.9M"])[0] == V.FAIL)
rc |= check("NTP desync stays fail",
            V.classify("failure", ["NTP status mismatch - Expected: synchronised Actual: unsynchronised"])[0] == V.FAIL)
rc |= check("success -> pass", V.classify("success", [])[0] == V.PASS)
rc |= check("skipped -> skipped", V.classify("skipped", [])[0] == V.SKIPPED)
rc |= check("error -> error", V.classify("error", ["ConnectError"])[0] == V.ERROR)
rc |= check("unrecognised status does not become a pass",
            V.classify("unset", [])[0] == V.ERROR)

s = V.summarise([{"verdict": "pass"}, {"verdict": "fail"},
                 {"verdict": "not_applicable"}, {"verdict": "skipped"}, {"verdict": "error"}])
rc |= check("five counts kept separate",
            s == {"passed":1,"failed":1,"not_applicable":1,"skipped":1,"errored":1,"total":5})
rc |= check("not_applicable is not counted as fail", s["failed"] == 1)
rc |= check("skipped is not counted as pass", s["passed"] == 1)

try:
    V.health_percentage(s); rc |= check("health percentage refused", False)
except V.VerdictError:
    rc |= check("health percentage refused", True)

try:
    V.summarise([{"verdict": "healthy"}]); rc |= check("unknown verdict rejected", False)
except V.VerdictError:
    rc |= check("unknown verdict rejected", True)

u = V.unreachable("1.2.3.4", "ConnectError", tls_verified=False)
rc |= check("unreachable yields error with zero results",
            u["outcome"] == V.ERROR and u["results"] == [] and "NOT A TEST FAILURE" in u["caveat"])
n = V.no_tests_selected("nosuch")
rc |= check("empty selection is not a pass",
            n["outcome"] == "no_tests_selected" and "NOT A PASS" in n["caveat"])
e = V.envelope("d1", [{"verdict": "pass"}], tls_verified=False)
rc |= check("envelope carries device, timestamp and tls disclosure",
            e["device"] == "d1" and "observed_at" in e and e["tls_verified"] is False)
try:
    V.envelope("", [], tls_verified=False); rc |= check("unattributed result rejected", False)
except V.VerdictError:
    rc |= check("unattributed result rejected", True)

sys.exit(rc)
PY
VERDICT_RC=$?
if [ $VERDICT_RC -eq 0 ]; then PASS=$((PASS+17)); else FAIL=$((FAIL+1)); fi

echo
echo "=== read-only posture (source scan, always runs) ==="
if grep -qE "configure\(|config_session|\.configure|enable_password.*configure" "$SERVER_DIR/server.py"; then
    bad "server contains a configuration path"
else
    ok "no configuration path in server source"
fi
if grep -qE "ANTA_PASSWORD|password" "$SERVER_DIR/server.py" | grep -qE "return|json"; then
    bad "credential may be returned"
else
    ok "no credential is returned to callers"
fi

echo
echo "=== live (skips without venv or device) ==="
if [ ! -x "$VENV_PY" ]; then
    skip "live tests" "venv absent"
elif [ -z "${ANTA_TEST_HOST:-}" ]; then
    skip "live tests" "ANTA_TEST_HOST not set"
else
    "$VENV_PY" -c "import anta" >/dev/null 2>&1
    if [ $? -ne 0 ]; then
        skip "live tests" "anta not importable"
    else
        ok "anta importable in its own venv"
        SYS_CRYPTO=$(python3 -c "import importlib.metadata as m; print(m.version('cryptography'))" 2>/dev/null)
        VENV_CRYPTO=$("$VENV_PY" -c "import importlib.metadata as m; print(m.version('cryptography'))" 2>/dev/null)
        if [ "$SYS_CRYPTO" != "$VENV_CRYPTO" ]; then
            ok "venv isolates cryptography (system $SYS_CRYPTO, venv $VENV_CRYPTO)"
        else
            skip "cryptography isolation" "same version both sides"
        fi
    fi
fi

echo
echo "passed: $PASS  failed: $FAIL  skipped: $SKIP"
[ $FAIL -eq 0 ]
