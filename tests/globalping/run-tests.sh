#!/usr/bin/env bash
# Offline test harness for the Globalping integration (spec 079 / roadmap R8).
#
# TWO RULES
#
# 1. **No network, no measurements.** The budget is 500/hour shared across everything
#    using the token. A suite that spent any of it would make running the tests
#    compete with using the product. Live checks live in `live-api.sh`, opt-in.
#
# 2. **Exit codes are captured DIRECTLY, never through a pipe.** `cmd | tail` reports
#    tail's status, not cmd's — that mistake misdiagnosed spec 075's central premise.
#
# There is no server to test here: this is a remote MCP, so the assertions cover the
# registration and the SKILL.md content. That is not a weaker test than usual — for a
# remote MCP the skill *is* the implementation, because prose is the only mechanism
# available for the safety semantics (research R1).

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PY="${NETCLAW_PY:-/usr/bin/python3}"
SKILL="$REPO_ROOT/workspace/skills/globalping-external-checks/SKILL.md"
CONFIG="$REPO_ROOT/config/openclaw.json"
PASS=0
FAIL=0

check() {  # check <label> <rc>
    if [ "$2" -eq 0 ]; then
        echo "  ok   $1"; PASS=$((PASS + 1))
    else
        echo "  FAIL $1"; FAIL=$((FAIL + 1))
    fi
}

echo "### Registration (FR-001, FR-002) ###"

"$PY" -c "
import json, sys
d = json.load(open('$CONFIG'))
e = d['mcpServers']['globalping-mcp']
assert e['url'] == 'https://mcp.globalping.dev/mcp', e['url']
" >/dev/null 2>&1
check "registered at the official endpoint" $?

"$PY" -c "
import json
e = json.load(open('$CONFIG'))['mcpServers']['globalping-mcp']
auth = e['headers']['Authorization']
assert auth == 'Bearer \${GLOBALPING_TOKEN}', auth
" >/dev/null 2>&1
check "bearer auth by variable reference" $?

# FR-003 / SC-009: the config must reference the token by NAME. A literal token in a
# tracked file is the failure this asserts against.
! grep -qE '"Authorization"[^,]*Bearer [A-Za-z0-9]{16,}' "$CONFIG"
check "no literal token in config (FR-003, SC-009)" $?

# FR-001: no server directory. The absence is the design decision, so assert it —
# otherwise a later well-meaning change could quietly vendor a client.
[ ! -d "$REPO_ROOT/mcp-servers/globalping-mcp" ]
check "no vendored server directory (FR-001, research R1)" $?

"$PY" -c "
import json
e = json.load(open('$CONFIG'))['mcpServers']['globalping-mcp']
assert 'command' not in e and 'args' not in e, e
" >/dev/null 2>&1
check "remote entry has no local command/args" $?
echo

echo "### The skill exists and documents the capability (FR-004, FR-005) ###"
[ -f "$SKILL" ]
check "SKILL.md present" $?

for tool in ping traceroute dns mtr http; do
    grep -qE "\`$tool\`" "$SKILL"
    check "documents the '$tool' measurement tool" $?
done
for tool in limits locations; do
    grep -qE "\`$tool\`" "$SKILL"
    check "documents the '$tool' meta tool" $?
done
echo

echo "### The three-way distinction — the point of the feature (FR-006, FR-007) ###"
grep -q "no_probes_found" "$SKILL"
check "names no_probes_found explicitly" $?
grep -qi "measurement never ran\|measurement did not run\|Nothing was tested" "$SKILL"
check "says no_probes_found means the measurement did not run (FR-006)" $?
grep -qi "NOT an outage" "$SKILL"
check "forbids reporting no_probes_found as an outage (FR-006)" $?
grep -qi "broader\|widen the location" "$SKILL"
check "suggests a broader filter (FR-006a)" $?
grep -qi "0 of N successful\|0 of 10\|IS a finding\|real finding" "$SKILL"
check "treats 0-of-N successful as a positive finding (FR-007)" $?
echo

echo "### Outside-in boundary, refused locally (FR-009, FR-010) ###"
for cidr in "10.0.0.0/8" "172.16.0.0/12" "192.168.0.0/16" "localhost" "fe80::/10"; do
    grep -qF "$cidr" "$SKILL"
    check "names $cidr as refused" $?
done
grep -qi "before.*sent to a third party\|already been sent to a third party\|disclosure control" "$SKILL"
check "explains WHY refusal is local, not just that it is (FR-009)" $?
grep -qi "pyATS" "$SKILL" && grep -qi "multivendor-cli" "$SKILL" && grep -qi "gtrace" "$SKILL"
check "names the internal tools to use instead (FR-009a)" $?
echo

echo "### Location syntax, including the vendor's broken example (FR-011, FR-011a) ###"
grep -qF 'London+UK' "$SKILL"
check "documents '+' as AND" $?
grep -qi "comma inside a single string fails\|does not work" "$SKILL"
check "warns that a comma-string fails (FR-011)" $?
grep -qF "AS13335" "$SKILL"
check "names AS13335 (FR-011a)" $?
grep -qi "never returns probes\|hosts no probes" "$SKILL"
check "explains AS13335 has no probes rather than bad syntax (FR-011a)" $?
grep -qi "own tool documentation\|own schema\|vendor" "$SKILL"
check "notes it is the vendor's own example (FR-011a)" $?
echo

echo "### Budget model — charged PER PROBE (FR-013, FR-013a) ###"
grep -qi "500 probe-measurements" "$SKILL"
check "documents the 500/hour authenticated budget" $?
grep -qi "250" "$SKILL"
check "documents the 250/hour unauthenticated budget" $?
grep -qi "cost of a call equals its probe count\|equals its probe count" "$SKILL"
check "states cost equals probe count (FR-013a)" $?
grep -qi "limits\` to check the budget is free\|costs nothing" "$SKILL"
check "notes meta calls are free (FR-013a)" $?
# The wrong version of this skill told the agent breadth was free. Assert the claim is
# gone, not merely that the right one is present — a stale sentence left beside a
# correct one is worse than either alone.
! grep -qi "one call costs one measurement\|breadth is free\|no matter how many probes" "$SKILL"
check "the corrected 'breadth is free' claim is absent (R4 correction)" $?
grep -qi "conscious decision\|deliberate choice" "$SKILL"
check "directs right-sizing limit rather than maximising it (FR-013a)" $?
echo

echo "### Attribution and composition (FR-008, FR-015, FR-016) ###"
grep -qi "attribut" "$SKILL"
check "requires location attribution (FR-008)" $?
grep -qi "never generalise\|not \"Europe\"" "$SKILL"
check "forbids generalising one probe to a region (FR-008a)" $?
grep -qi "ThousandEyes" "$SKILL"
check "states the ThousandEyes boundary (FR-015, SC-010)" $?
grep -qi "gtrace" "$SKILL"
check "states the gtrace boundary (FR-016, SC-010)" $?
grep -qi "split" "$SKILL"
check "requires DNS disagreement reported as a split (SC-005)" $?
echo

echo "### The analytics field and credential hygiene (FR-012, XIII) ###"
grep -qi "context" "$SKILL"
check "documents the context field (FR-012)" $?
grep -qi "leaves NetClaw and reaches a third party\|reaches a third party" "$SKILL"
check "discloses that context leaves NetClaw (FR-012a)" $?
grep -qi "Never include" "$SKILL"
check "lists what must never go in context (FR-012)" $?
grep -qi "accepts calls with .context. omitted\|omitted despite marking it required" "$SKILL"
check "records that omission is accepted but not relied on (FR-012b)" $?
grep -qi "fragment of the token\|token fragment" "$SKILL"
check "warns that limits output echoes a token fragment (XIII)" $?
grep -qi "not scanning\|do not sweep\|Do not sweep" "$SKILL"
check "states measurement-not-scanning (FR-018)" $?
echo

echo "### No literal token anywhere in tracked files (SC-009) ###"
if [ -n "${GLOBALPING_TOKEN:-}" ]; then
    ! git -C "$REPO_ROOT" grep -qF "$GLOBALPING_TOKEN" -- . 2>/dev/null
    check "the real token appears in no tracked file" $?
else
    echo "  ok   GLOBALPING_TOKEN unset — nothing to leak in this shell"
    PASS=$((PASS + 1))
fi
echo

echo "======================================"
echo " PASS: $PASS   FAIL: $FAIL"
echo "======================================"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
