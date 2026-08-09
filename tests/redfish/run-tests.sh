#!/usr/bin/env bash
# Contract tests for redfish-mcp (spec 094, roadmap R15).
#
# R15 exists to answer "is the box dead, or is it the network?" -- and the trap is symmetric:
#
#   BMC unreachable    -> nothing learned about the host. NOT "the host is down".
#   BMC reachable, Off -> the host IS off. A fact, and the point of out-of-band.
#   BMC reachable, On  -> the host has power. The OS may be hung.
#
# Most assertions here are about that verdict rather than about data, because a reading without
# its qualifier is the wrong answer this server exists to prevent.
#
# Verdict assertions are pure stdlib. The live ones need httpx + the DMTF mockup container and
# skip themselves, so this runs in CI (which installs nothing, spec 075 SC-013).
#
# Every exit code captured DIRECTLY, never through a pipe.

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRV="$REPO_ROOT/mcp-servers/redfish-mcp"
PASS=0; FAIL=0; SKIP=0
ok()   { printf '  ok   %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  FAIL %s\n' "$1"; FAIL=$((FAIL+1)); }
skip() { printf '  skip %s\n' "$1"; SKIP=$((SKIP+1)); }
py() { local d="$1" c="$2" o; o="$(cd "$SRV" && python3 -c "$c" 2>&1)"
       if [ "$o" = "PASS" ]; then ok "$d"; else bad "$d -- got: ${o##*$'\n'}"; fi; }

echo "=== The verdict: what a BMC reading establishes about the host ==="

py "an unreachable BMC yields host_state UNKNOWN, never 'down'" '
import verdict
v = verdict.unreachable_verdict("timeout")
print("PASS" if v["host_state"] == "UNKNOWN" and v["bmc_reachable"] is False else v)'

py "the unreachable verdict names the conclusion NOT to draw" '
import verdict
print("PASS" if verdict.unreachable_verdict("t")["do_not_conclude"] == "host is down" else "missing")'

py "PowerState Off is reported as a FACT about the host" '
import verdict
v = verdict.host_verdict("Off", "OK")
print("PASS" if v["host_state"] == "POWERED_OFF" and "fact" in v["means"] else v)'

py "PowerState On carries the caveat that the OS may be hung" '
import verdict
v = verdict.host_verdict("On", "OK")
print("PASS" if v["host_state"] == "POWERED_ON" and "does NOT mean" in v["means"] else v)'

py "an unrecognised PowerState is UNREPORTED, not guessed" '
import verdict
print("PASS" if verdict.host_verdict("Quiescing", "OK")["host_state"] == "POWER_STATE_UNREPORTED" else "guessed")'

py "a hardware fault is reported as independent of OS state" '
import verdict
v = verdict.host_verdict("On", "Critical")
print("PASS" if "independent of whether the OS is running" in v.get("hardware_fault","") else v)'

# The central guard: a host state must never be derived from a failed BMC reach.
py "deriving a host state from an unreachable BMC is refused" '
import verdict
try:
    verdict.host_verdict("On", "OK", bmc_reachable=False); print("not refused")
except verdict.VerdictError: print("PASS")'

py "emitting a host claim without a verdict is refused" '
import verdict
try:
    verdict.emit("probe", host_claim={"state": "on"}); print("not refused")
except verdict.VerdictError: print("PASS")'

py "a host claim WITH a verdict is allowed" '
import verdict
e = verdict.emit("probe", host_claim=[], verdict=verdict.host_verdict("Off", "OK"))
print("PASS" if e["verdict"]["host_state"] == "POWERED_OFF" else e)'

echo
echo "=== Read-only is enforced at the transport ==="

py "the client implements no verb but GET" '
import pathlib
src = pathlib.Path("client.py").read_text()
bad = [v for v in (".post(", ".put(", ".patch(", ".delete(") if v in src]
print("PASS" if not bad else f"found: {bad}")'

py "ComputerSystem.Reset is never invoked anywhere in the server" '
import pathlib
src = "".join(pathlib.Path(f).read_text() for f in ("server.py", "client.py"))
# The docstrings explain why it is absent; an actual invocation would be a POST.
print("PASS" if "Actions/ComputerSystem.Reset" not in src else "reset path present")'

py "an unset endpoint refuses rather than guessing an address" '
import os, client
os.environ.pop("REDFISH_URL", None)
try:
    client.RedfishClient(); print("constructed with no endpoint")
except client.BmcUnreachable as e: print("PASS" if "never guesses" in str(e) else e)'

echo
echo "=== Live against the DMTF mockup (needs httpx + container) ==="

if ! (cd "$SRV" && python3 -c 'import httpx' 2>/dev/null); then
    skip "live mockup assertions (httpx is not installed here)"
    skip "reachable-BMC verdict against real Redfish"
elif ! curl -s -m 3 http://127.0.0.1:8000/redfish/v1 >/dev/null 2>&1; then
    skip "live mockup assertions (no Redfish mock on :8000)"
    skip "reachable-BMC verdict against real Redfish"
else
    py "systems are read from a real Redfish service with a verdict attached" '
import os; os.environ["REDFISH_URL"] = "http://127.0.0.1:8000"
import server
r = server.redfish_systems()
h = r["host"][0]
print("PASS" if h["power_state"] == "On" and r["verdict"]["host_state"] == "POWERED_ON"
      and h["processors"]["Count"] == 2 else r["verdict"])'

    py "an unreachable endpoint yields UNKNOWN, not a host claim" '
import os; os.environ["REDFISH_URL"] = "http://127.0.0.1:9"
import server
v = server.redfish_systems()["verdict"]
print("PASS" if v["host_state"] == "UNKNOWN" and v["bmc_reachable"] is False else v)'
fi

echo
echo "=== Empty results must not read as good news ==="

py "TLS verification being off is disclosed, not silent" '
import os; os.environ["REDFISH_URL"] = "http://x"
os.environ.pop("REDFISH_VERIFY_TLS", None)
import importlib, client; importlib.reload(client)
n = client.RedfishClient().tls_note()
print("PASS" if n and "DISABLED" in n else n)'

echo
echo "=== Summary ==="
printf '  passed: %d\n  failed: %d\n  skipped: %d\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] || exit 1
echo "  all redfish-mcp contract tests passed"
