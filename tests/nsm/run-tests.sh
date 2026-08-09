#!/usr/bin/env bash
# Contract tests for nsm-mcp (spec 091, roadmap R13).
#
# The two things this server exists to prevent are silent wrong answers:
#
#   1. Suricata with no ruleset loads 0 signatures, reports 0 alerts, exits 0.
#   2. Zeek discards invalid-checksum packets, losing http.log entirely and
#      corrupting conn.log, with only a non-fatal stderr warning.
#
# So the assertions below are mostly about POSTURE rather than data: that a finding
# cannot travel without the qualifier that makes it readable. The chokepoint tests
# need no containers; the analysis tests skip themselves without docker, so this file
# is still useful in CI (which has no docker and no images).
#
# No test framework: bash + Python stdlib. Every exit code is captured DIRECTLY,
# never through a pipe -- that mistake misdiagnosed spec 075's central premise.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRV="$REPO_ROOT/mcp-servers/nsm-mcp"
FIXTURE="$REPO_ROOT/tests/nsm/fixtures/checksum-offload.pcap"
PASS=0
FAIL=0
SKIP=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export NSM_HOME="$TMP/nsm"

ok()   { printf '  ok   %s\n' "$1"; PASS=$((PASS + 1)); }
bad()  { printf '  FAIL %s\n' "$1"; FAIL=$((FAIL + 1)); }
skip() { printf '  skip %s\n' "$1"; SKIP=$((SKIP + 1)); }

# py <description> <python> -- passes if the snippet prints exactly "PASS"
py() {
    local desc="$1" code="$2"
    local out
    out="$(cd "$SRV" && python3 -c "$code" 2>&1)"
    if [ "$out" = "PASS" ]; then ok "$desc"; else bad "$desc -- got: ${out##*$'\n'}"; fi
}

# Does importing server.py work here? It needs the `mcp` package. CI installs nothing by
# design (spec 075 SC-013), so tests that import the server skip rather than fail -- while the
# posture and pinning assertions, which are pure stdlib, always run.
if (cd "$SRV" && python3 -c 'import mcp' 2>/dev/null); then HAVE_MCP=1; else HAVE_MCP=0; fi

echo "=== Chokepoint: a finding cannot travel without its posture ==="

py "an alert verdict without Suricata posture is refused" '
import envelope
try:
    envelope.emit("probe", alert_verdict=0); print("not refused")
except envelope.PostureError: print("PASS")'

py "Zeek findings without checksum posture are refused" '
import envelope
try:
    envelope.emit("probe", zeek_findings=[]); print("not refused")
except envelope.PostureError: print("PASS")'

py "an alert verdict WITH posture is allowed" '
import envelope
p = envelope.suricata_posture(52205, True, 0)
e = envelope.emit("probe", alert_verdict=[], suricata=p)
print("PASS" if e["suricata_posture"]["state"] == "ARMED" else e)'

echo
echo "=== Inert detector: 0 alerts must not read as clean ==="

py "0 signatures yields state INERT" '
import envelope
print("PASS" if envelope.suricata_posture(0, False, None)["state"] == "INERT" else "wrong")'

# The central assertion of this suite. An empty alert list from an inert detector must
# not be emittable as a bare empty list, because a caller reading only the alerts field
# would read it as a clean verdict.
py "an empty alert list from an INERT detector is wrapped with NOT_A_CLEAN_RESULT" '
import envelope
p = envelope.suricata_posture(0, False, None)
e = envelope.emit("probe", alert_verdict=[], suricata=p)
a = e["alerts"]
print("PASS" if isinstance(a, dict) and "NOT_A_CLEAN_RESULT" in a else f"not wrapped: {a!r}")'

py "0 (integer) from an INERT detector is also wrapped" '
import envelope
p = envelope.suricata_posture(0, False, None)
a = envelope.emit("probe", alert_verdict=0, suricata=p)["alerts"]
print("PASS" if isinstance(a, dict) else "not wrapped: %r" % (a,))'

py "an ARMED detector reporting no alerts is NOT wrapped" '
import envelope
p = envelope.suricata_posture(52205, True, 1)
a = envelope.emit("probe", alert_verdict=[], suricata=p)["alerts"]
print("PASS" if a == [] else "wrongly wrapped: %r" % (a,))'

py "INERT posture carries a remedy" '
import envelope
print("PASS" if "nsm_update_rules" in (envelope.suricata_posture(0, False, None)["remedy"] or "") else "no remedy")'

echo
echo "=== Zeek checksum posture ==="

py "validation on + invalid checksums seen yields PACKETS_DISCARDED" '
import envelope
print("PASS" if envelope.zeek_posture(True, True)["state"] == "PACKETS_DISCARDED" else "wrong")'

py "PACKETS_DISCARDED carries a remedy" '
import envelope
print("PASS" if "ignore_checksums" in (envelope.zeek_posture(True, True)["remedy"] or "") else "no remedy")'

py "validation off yields IGNORING_CHECKSUMS and no remedy" '
import envelope
p = envelope.zeek_posture(False, True)
print("PASS" if p["state"] == "IGNORING_CHECKSUMS" and p["remedy"] is None else p)'

echo
echo "=== Input validation: an empty capture must not read as empty traffic ==="

py "a missing capture raises rather than returning nothing" '
import runner
try:
    runner.resolve_pcap("/definitely/not/here.pcap"); print("no error")
except runner.NsmError as e: print("PASS" if "not found" in str(e) else e)'

py "a zero-byte capture is refused explicitly" '
import os, runner, tempfile
d = tempfile.mkdtemp(); f = os.path.join(d, "empty.pcap"); open(f, "wb").close()
try:
    runner.resolve_pcap(f); print("no error")
except runner.NsmError as e: print("PASS" if "empty" in str(e) else e)'

py "a directory is refused explicitly" '
import runner, tempfile
try:
    runner.resolve_pcap(tempfile.mkdtemp()); print("no error")
except runner.NsmError as e: print("PASS" if "directory" in str(e) else e)'

echo
echo "=== Pinning: images must be digest-pinned, never floating tags ==="

py "both images are pinned by sha256 digest" '
import runner
bad = [i for i in (runner.ZEEK_IMAGE, runner.SURICATA_IMAGE) if "@sha256:" not in i]
print("PASS" if not bad else f"floating: {bad}")'

py "no :latest tag anywhere in the runner" '
import pathlib
src = pathlib.Path("runner.py").read_text()
print("PASS" if ":latest" not in src else "found :latest")'

echo
echo "=== Tool surface stays under the manifest ceiling ==="

if [ "$HAVE_MCP" = "1" ]; then
    py "6 tools, manifest under 2000 tokens" '
import asyncio, json, server
tools = asyncio.run(server.mcp.list_tools())
tot = sum(len(json.dumps({"name": t.name, "description": t.description,
                          "inputSchema": t.inputSchema})) // 4 for t in tools)
print("PASS" if len(tools) == 6 and tot < 2000 else f"{len(tools)} tools, {tot} tokens")'
else
    skip "tool-surface measurement (the mcp package is not installed here)"
fi

echo
echo "=== Live analysis against the committed fixture (needs docker) ==="

if [ "$HAVE_MCP" != "1" ]; then
    skip "Zeek/Suricata analysis (the mcp package is not installed here)"
    skip "checksum trap reproduction (the mcp package is not installed here)"
elif ! docker info >/dev/null 2>&1; then
    skip "Zeek/Suricata analysis (docker not reachable)"
    skip "checksum trap reproduction (docker not reachable)"
else
    # The trap, reproduced end to end: Zeek's own default hides the HTTP transaction.
    out="$(cd "$SRV" && python3 -c "
import server
d = server.nsm_analyze('$FIXTURE', ignore_checksums=True)
v = server.nsm_analyze('$FIXTURE', ignore_checksums=False)
print('ignore:', d['zeek_posture']['state'], 'http' in d['findings']['logs_produced'],
      d['findings']['connections'])
print('validate:', v['zeek_posture']['state'], 'http' in v['findings']['logs_produced'],
      v['findings']['connections'])
" 2>&1)"
    if printf '%s' "$out" | grep -q 'ignore: IGNORING_CHECKSUMS True 2'; then
        ok "ignore_checksums=true sees http.log and 2 connections"
    else
        bad "ignore_checksums=true analysis -- got: $out"
    fi
    if printf '%s' "$out" | grep -q 'validate: PACKETS_DISCARDED False 3'; then
        ok "Zeek's own default LOSES http.log and miscounts connections (3 not 2)"
    else
        bad "checksum trap reproduction -- got: $out"
    fi
fi

echo
echo "=== Summary ==="
printf '  passed: %d\n  failed: %d\n  skipped: %d\n' "$PASS" "$FAIL" "$SKIP"
[ "$FAIL" -eq 0 ] || exit 1
echo "  all nsm-mcp contract tests passed"
