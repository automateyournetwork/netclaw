#!/usr/bin/env bash
# OPT-IN live API test for the Cisco PSIRT MCP server (spec 078 T040).
#
# THIS SPENDS REAL API CALLS. The budget is 5/second and 30/minute, shared across
# every caller of the credential, so this script must never run in CI or as part of
# `run-tests.sh` — a test suite that competes with using the product is worse than no
# suite. Roughly 12 calls per run.
#
# Usage:
#   set -a && . ./.env && set +a
#   ./tests/cisco-psirt/live-api.sh
#
# Exit codes are captured DIRECTLY, never through a pipe (`cmd | tail` reports tail's
# status, not cmd's).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${NETCLAW_PY:-/usr/bin/python3}"
SERVER_DIR="$REPO_ROOT/mcp-servers/cisco-psirt-mcp"

if [ -z "${CISCO_CLIENT_ID:-}" ] || [ -z "${CISCO_CLIENT_SECRET:-}" ]; then
    echo "SKIP: CISCO_CLIENT_ID / CISCO_CLIENT_SECRET not set." >&2
    echo "  This script is opt-in and needs live credentials. Load them with:" >&2
    echo "    set -a && . ./.env && set +a" >&2
    exit 2
fi

echo "This spends ~12 live API calls against a 30/minute budget."
if [ "${PSIRT_LIVE_YES:-}" != "1" ]; then
    printf 'Continue? [y/N] '
    read -r reply
    case "$reply" in [yY]*) ;; *) echo "aborted"; exit 2 ;; esac
fi

# A throwaway cache directory, so a live run never pollutes (or is answered by) the
# operator's real cache — otherwise this tests the cache rather than the API.
LIVE_CACHE="$(mktemp -d -t psirt-live-XXXXXX)"
trap 'rm -rf "$LIVE_CACHE"' EXIT

PSIRT_SERVER_DIR="$SERVER_DIR" CISCO_PSIRT_CACHE_DIR="$LIVE_CACHE" "$PY" - <<'PY'
import os, sys
sys.path.insert(0, os.environ["PSIRT_SERVER_DIR"])
import server

PASS = FAIL = 0
def check(label, cond, detail=""):
    global PASS, FAIL
    if cond:
        print(f"  ok   {label}"); PASS += 1
    else:
        print(f"  FAIL {label}" + (f" — {detail}" if detail else "")); FAIL += 1

print("### Every family answers, with its own format (FR-001, FR-004a) ###")
# (ostype, version, expected advisory count as measured 2026-07-31)
for ostype, version, expected in [
        ("iosxe", "17.3.1", 122), ("ios", "15.2(4)E", 74), ("nxos", "9.3(5)", 33),
        ("asa", "9.16.1", 65), ("ftd", "7.0.1", 90), ("fmc", "7.0.1", 34),
        ("aci", "15.2(3e)", 10)]:
    r = server.check_version(ostype, version)
    check(f"{ostype} {version} -> advisories_found",
          r["outcome"] == "advisories_found", f"{r['outcome']}: {r.get('error')}")
    # Counts drift as Cisco publishes. A large move means something changed upstream
    # rather than here, so this warns instead of failing.
    got = r.get("advisory_count", 0)
    if got != expected:
        print(f"       note: {ostype} {version} now returns {got}, was {expected} "
              f"— expected as Cisco publishes")
    check(f"{ostype} advisories carry severity",
          bool(r["advisories"]) and r["advisories"][0].get("severity") is not None)

print("\n### Normalisation works in BOTH directions, live (FR-009) ###")
# The dotted form of a parenthesised family, and vice versa. Each must reach the same
# advisory set as its canonical form — a cache hit here proves they normalised alike.
for ostype, alt_form, canonical in [("ios", "15.2.4E", "15.2(4)E"),
                                    ("nxos", "9.3.5", "9.3(5)"),
                                    ("asa", "9.16(1)", "9.16.1"),
                                    ("iosxe", "17.3(1)", "17.3.1")]:
    r = server.check_version(ostype, alt_form)
    check(f"{ostype} {alt_form} normalises to {canonical}",
          r["version_normalised"] == canonical, str(r["version_normalised"]))
    check(f"{ostype} {alt_form} was served from cache (same key as canonical)",
          r["cache"] == "hit", r["cache"])

print("\n### A banner from real `show version` output ###")
banner = "Cisco IOS Software [Amsterdam], Version 17.3(1), RELEASE SOFTWARE (fc2)"
r = server.check_version("iosxe", banner)
check("banner yields advisories", r["outcome"] == "advisories_found")
check("banner normalised to 17.3.1", r["version_normalised"] == "17.3.1",
      str(r["version_normalised"]))

print("\n### The refusals cost no API call (FR-004, FR-010) ###")
r = server.check_version("iosxr", "7.5.2")
check("iosxr refused", r["outcome"] == "unsupported_ostype")
r = server.check_version("junos", "21.4R3")
check("non-Cisco refused", r["outcome"] == "unsupported_ostype")

print("\n### FR-009a live: a parse failure never returns an empty advisory list ###")
r = server.check_version("iosxe", "garbage")
check("garbage -> normalisation_failed", r["outcome"] == "normalisation_failed")
check("garbage returns no advisories AND says nothing was checked",
      r["advisories"] == [] and "NOTHING WAS CHECKED" in (r["caveat"] or ""))

print("\n### CVE and severity-range lookups (FR-002) ###")
r = server.list_recent("critical", "2026-01-01", "2026-07-31")
check("critical advisories in 2026 found", r["outcome"] == "advisories_found",
      f"{r['outcome']}: {r.get('error')}")
print(f"       {r.get('advisory_count')} critical advisories in range (15 when measured)")

print("\n### SC-007: the token survives and refreshes ###")
s = server.psirt_status()
check("authenticated", s["authenticated"] is True)
check("token has remaining lifetime", s["token_expires_in_seconds"] > 0,
      str(s["token_expires_in_seconds"]))
check("rate budget reported", s["rate_budget"]["calls_remaining_estimate"] >= 0)
print(f"       {s['rate_budget']['calls_remaining_estimate']} of 30 calls left this minute")

print("\n### FR-007 live: the real credential appears nowhere in output ###")
import json
blob = json.dumps([s, r, server.psirt_status()])
for var in ("CISCO_CLIENT_ID", "CISCO_CLIENT_SECRET"):
    secret = os.environ.get(var, "")
    check(f"{var} value absent from output", bool(secret) and secret not in blob)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
PY
rc=$?          # captured directly — no pipe
echo
if [ "$rc" -eq 0 ]; then
    echo "LIVE API SUITE: PASS"
else
    echo "LIVE API SUITE: FAIL (exit $rc)"
fi
exit "$rc"
