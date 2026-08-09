#!/usr/bin/env bash
# Exit-code contract tests for NetClaw's MCP reconciliation checks.
#
# Contract: specs/075-mcp-config-reconciliation/contracts/reconcile-cli.md
# Requirements: FR-008 (non-zero exit on failure), FR-012 (unlocatable claim is
#               a failure), SC-002 (verified by introducing one defect per
#               surface), SC-013 (runs with no agent installed).
#
# These tests exist because the entire premise of spec 075 was once misdiagnosed
# by reading an exit code through a `| tail` pipe -- which reports the pipe's
# status, not the command's. Every assertion here captures the exit code
# directly. Never pipe a command whose exit code you are about to check.
#
# No test framework: bash + Python stdlib only, so this runs in a bare CI
# container. Fixtures are built in a temp dir; the repository is never modified.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PASS=0
FAIL=0
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# assert_exit <expected> <description> -- command supplied via "$@"
assert_exit() {
    local expected="$1" desc="$2"; shift 2
    "$@" >"$TMP/out" 2>&1
    local actual=$?
    if [ "$actual" -eq "$expected" ]; then
        printf '  ok   %s (exit %d)\n' "$desc" "$actual"
        PASS=$((PASS + 1))
    else
        printf '  FAIL %s (expected exit %d, got %d)\n' "$desc" "$expected" "$actual"
        sed 's/^/         /' "$TMP/out" | head -6
        FAIL=$((FAIL + 1))
    fi
}

# assert_mentions <substring> <description> -- command supplied via "$@"
assert_mentions() {
    local needle="$1" desc="$2"; shift 2
    "$@" >"$TMP/out" 2>&1
    if grep -qF "$needle" "$TMP/out"; then
        printf '  ok   %s\n' "$desc"
        PASS=$((PASS + 1))
    else
        printf '  FAIL %s (output never mentioned %s)\n' "$desc" "$needle"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== Clean repository: every surface reconciled ==="
# Scoped to the DECLARATION surfaces, which compare repository artifacts against each other
# and are therefore true of the tree regardless of what is installed. The `startup` surface
# (spec 088/090) launches real servers, so on a fresh checkout with no vendored clones it
# cannot pass and would make this assertion a statement about the machine rather than the
# repository. Its own gate behaviour is asserted separately below, against fixtures.
assert_exit 0 "reconcile-mcp.py exits 0 on a reconciled tree (declaration surfaces)" \
    python3 "$REPO_ROOT/scripts/reconcile-mcp.py" \
        --surface catalog --surface dependencies --surface docs \
        --surface meraki-ids --surface portability
assert_exit 0 "verify-catalog-coverage.py exits 0" \
    python3 "$REPO_ROOT/scripts/verify-catalog-coverage.py"
assert_exit 0 "verify-inventory-counts.py exits 0" \
    python3 "$REPO_ROOT/scripts/verify-inventory-counts.py"
assert_exit 0 "check-mcp-portability.py exits 0" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py"

echo
echo "=== Portability surface: a machine-specific path must fail ==="
cat >"$TMP/machine-specific.json" <<'JSON'
{"mcpServers": {
  "broken-mcp": {"command": "/home/ubuntu/netclaw/.venv/bin/python3",
                 "args": ["-u", "/home/ubuntu/netclaw/mcp-servers/x/server.py"]}
}}
JSON
assert_exit 1 "a /home/ path fails the portability check" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/machine-specific.json"
assert_mentions "broken-mcp" "the failure names the offending entry" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/machine-specific.json"
assert_mentions "machine-specific" "the failure states what is wrong" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/machine-specific.json"

echo
echo "=== Portability surface: legitimate system paths must NOT fail (FR-004) ==="
cat >"$TMP/system-paths.json" <<'JSON'
{"mcpServers": {
  "sys-mcp": {"command": "/usr/bin/python3", "args": ["-m", "foo"]},
  "pkg-mcp": {"command": "npx", "args": ["-y", "@scope/pkg"]}
}}
JSON
assert_exit 0 "/usr/bin/python3 and npx package specs pass" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/system-paths.json"

echo
echo "=== Portability surface: --warn-only suppresses the failure exit ==="
assert_exit 0 "--warn-only exits 0 despite findings" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/machine-specific.json" --warn-only

echo
echo "=== Cannot-run is distinguishable from inconsistent (exit 2) ==="
assert_exit 2 "a missing config yields exit 2, not 1" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/does-not-exist.json"
printf 'not json at all' >"$TMP/broken.json"
assert_exit 2 "an unparseable config yields exit 2, not 1" \
    python3 "$REPO_ROOT/scripts/check-mcp-portability.py" --config "$TMP/broken.json"

echo
echo "=== Orchestrator aggregates a surface failure (FR-008) ==="
# Drive the real portability script through the orchestrator by pointing the
# orchestrator at a repo copy whose config is defective. Only the config is
# swapped; scripts are symlinked so this stays cheap.
FAKE="$TMP/repo"
mkdir -p "$FAKE/scripts" "$FAKE/config" "$FAKE/mcp-servers" "$FAKE/workspace/skills"
for f in reconcile-mcp.py check-mcp-portability.py; do
    cp "$REPO_ROOT/scripts/$f" "$FAKE/scripts/$f"
done
cp "$TMP/machine-specific.json" "$FAKE/config/openclaw.json"
assert_exit 1 "orchestrator exits 1 when the portability surface fails" \
    python3 "$FAKE/scripts/reconcile-mcp.py" --surface portability
assert_exit 0 "orchestrator --warn-only exits 0 despite a failing surface" \
    python3 "$FAKE/scripts/reconcile-mcp.py" --surface portability --warn-only

echo
echo "=== Orchestrator reports exit 2 when a check script is missing ==="
rm "$FAKE/scripts/check-mcp-portability.py"
assert_exit 2 "a missing check script yields exit 2" \
    python3 "$FAKE/scripts/reconcile-mcp.py" --surface portability

echo
echo "=== Dependency-pin surface (spec 077 / R0a) ==="
# These three classes broke FRESH installs only, which is why nothing caught them.
assert_exit 0 "check-dependency-pins.py passes on a clean tree" \
    python3 "$REPO_ROOT/scripts/check-dependency-pins.py"

# An unbounded pin on a package whose SUBMODULE is imported must fail.
DEPFIX="$TMP/depsrv/mcp-servers/probe-mcp"
mkdir -p "$DEPFIX"
printf 'mcp>=1.0.0\n' >"$DEPFIX/requirements.txt"
printf 'from mcp.server.fastmcp import FastMCP\n' >"$DEPFIX/server.py"
mkdir -p "$TMP/depsrv/scripts/lib"
cp "$REPO_ROOT/scripts/check-dependency-pins.py" "$TMP/depsrv/scripts/"
: >"$TMP/depsrv/scripts/lib/install-steps.sh"
assert_exit 1 "unbounded pin + submodule import fails" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"
assert_mentions "probe-mcp" "the failure names the offending server" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"
assert_mentions "SUBMODULE" "the failure explains why it matters" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"

# Bounding it must clear the finding.
printf 'mcp>=1.0.0,<2\n' >"$DEPFIX/requirements.txt"
assert_exit 0 "bounding the pin clears it" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"

# A bare pip invocation in install steps must fail, naming the line.
printf 'pip3 install something\n' >"$TMP/depsrv/scripts/lib/install-steps.sh"
assert_exit 1 "bare pip3 install fails" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"
assert_mentions "netclaw_pip_install" "the failure names the remedy" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"

# A comment or log message mentioning pip must NOT fail — false positives here
# would train maintainers to ignore the check.
printf '# pip3 install is what we used to do\nlog_info "pip install failed"\n' \
    >"$TMP/depsrv/scripts/lib/install-steps.sh"
assert_exit 0 "pip in a comment or log string is not a finding" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py"

# --warn-only must report but not fail.
printf 'pip3 install something\n' >"$TMP/depsrv/scripts/lib/install-steps.sh"
assert_exit 0 "--warn-only exits 0 despite findings" \
    python3 "$TMP/depsrv/scripts/check-dependency-pins.py" --warn-only

# ── Startup surface (spec 088) ────────────────────────────────────────────────
# This surface exists because the four checks above validate DECLARATIONS and none
# of them ran anything: seven registered servers could not start while
# reconcile-mcp.py exited 0. These tests build fixture servers whose startup
# behaviour is known, since the real failure was found only by launching.
echo
echo "--- startup surface ---"
SUP="$TMP/startup"
mkdir -p "$SUP/scripts" "$SUP/mcp-servers/good-mcp" "$SUP/mcp-servers/broken-mcp"
cp "$REPO_ROOT/scripts/check-server-startup.py" "$SUP/scripts/"

# A server that imports cleanly and then blocks reading stdio is CORRECT MCP
# behaviour -- a timeout must never be reported as a failure. Getting this
# backwards would flag all 75 working servers.
cat >"$SUP/mcp-servers/good-mcp/server.py" <<'EOF'
import sys, json
sys.stdin.read()
EOF
cat >"$SUP/mcp-servers/broken-mcp/server.py" <<'EOF'
import nonexistent_module_xyz
EOF
write_cfg() { printf '%s
' "$1" >"$SUP/config.json"; }
mkdir -p "$SUP/config"
run_startup() { python3 "$SUP/scripts/check-server-startup.py" --config "$SUP/config/openclaw.json" "$@"; }

python3 - "$SUP" <<'EOF'
import json, sys, os
root = sys.argv[1]
cfg = {"mcpServers": {"good-mcp": {"command": "python3",
        "args": [os.path.join(root, "mcp-servers/good-mcp/server.py")]}}}
os.makedirs(os.path.join(root, "config"), exist_ok=True)
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 0 "a server that blocks on stdio is not a failure (timeout != broken)" \
    run_startup

# Missing module must fail, and must name both the server and the module -- a
# finding that says only "failed" sends the reader back to the shell.
python3 - "$SUP" <<'EOF'
import json, sys, os
root = sys.argv[1]
cfg = {"mcpServers": {"broken-mcp": {"command": "python3",
        "args": [os.path.join(root, "mcp-servers/broken-mcp/server.py")]}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 1 "a server with a missing module fails" run_startup
assert_mentions "broken-mcp" "the finding names the server" run_startup
assert_mentions "nonexistent_module_xyz" "the finding names the missing module" run_startup

# A registered server whose file is absent -- the aruba-cx-mcp case, which no
# amount of installing packages would have fixed.
python3 - "$SUP" <<'EOF'
import json, sys, os
root = sys.argv[1]
cfg = {"mcpServers": {"absent-mcp": {"command": "python3",
        "args": [os.path.join(root, "mcp-servers/absent-mcp/server.py")]}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 1 "a registered server with no entry point fails" run_startup
assert_mentions "does not exist" "the finding distinguishes absent file from missing module" \
    run_startup

# --warn-only reports without failing, matching every other surface.
python3 - "$SUP" <<'EOF'
import json, sys, os
root = sys.argv[1]
cfg = {"mcpServers": {"broken-mcp": {"command": "python3",
        "args": [os.path.join(root, "mcp-servers/broken-mcp/server.py")]}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 0 "--warn-only exits 0 despite startup findings" run_startup --warn-only

# STARTUP_EXCEPTIONS is the documented escape hatch, so it must actually work --
# an untested suppression list is how a check quietly stops checking.
# Inject an entry after the opening brace rather than replacing an empty literal: the
# dict now has a real entry (RADKit), and matching `= {}` silently stopped applying --
# the test passed for the wrong reason until spec 090 populated it.
sed 's/^STARTUP_EXCEPTIONS: dict\[str, str\] = {$/&\n    "broken-mcp": "test",/' \
    "$REPO_ROOT/scripts/check-server-startup.py" >"$SUP/scripts/excepted.py"
grep -q '"broken-mcp": "test"' "$SUP/scripts/excepted.py" || \
    { printf '  FAIL could not inject a STARTUP_EXCEPTIONS entry\n'; FAIL=$((FAIL + 1)); }
assert_exit 0 "a server in STARTUP_EXCEPTIONS is suppressed" \
    python3 "$SUP/scripts/excepted.py" --config "$SUP/config/openclaw.json"

# A remote/HTTP server has no local process to launch and must be skipped, not
# reported as broken.
python3 - "$SUP" <<'EOF'
import json, sys, os
root = sys.argv[1]
cfg = {"mcpServers": {"remote-mcp": {"type": "http",
        "url": "https://example.invalid/mcp"}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 0 "a remote server is skipped, not failed" run_startup

# ── Meraki capability-ID surface (spec 089) ───────────────────────────────────
# The five Meraki skills cited 80 method names and 54 DID NOT EXIST in the Meraki
# API. The docs surface passed throughout, because it compares counts and never
# asks whether a documented call is real. These tests pin that down.
echo
echo "--- meraki capability-id surface ---"
MER="$TMP/meraki"
mkdir -p "$MER/scripts" "$MER/workspace/skills/meraki-probe" \
         "$MER/specs/089-meraki-official/contracts"
cp "$REPO_ROOT/scripts/check-meraki-capability-ids.py" "$MER/scripts/"
cp "$REPO_ROOT/specs/089-meraki-official/contracts/meraki-capability-ids.json" \
   "$MER/specs/089-meraki-official/contracts/"
run_meraki() { python3 "$MER/scripts/check-meraki-capability-ids.py" "$@"; }

# A real reachable GET must pass.
printf 'Call `getNetworkWirelessSsids` for the SSID list.\n' \
    >"$MER/workspace/skills/meraki-probe/SKILL.md"
assert_exit 0 "a real reachable capability ID passes" run_meraki

# An invented ID must fail -- this is the 54-name failure mode.
printf 'Call `getWirelessSSIDs` for the SSID list.\n' \
    >"$MER/workspace/skills/meraki-probe/SKILL.md"
assert_exit 1 "an invented capability ID fails" run_meraki
assert_mentions "DOES NOT EXIST" "the finding says the ID cannot succeed anywhere" run_meraki
assert_mentions "getWirelessSSIDs" "the finding names the invented ID" run_meraki

# A mutating verb cited WITHOUT marking it unreachable must fail.
printf 'Use `updateNetwork` to rename the network.\n' \
    >"$MER/workspace/skills/meraki-probe/SKILL.md"
assert_exit 1 "an unmarked mutating ID fails" run_meraki

# The same verb cited AS A NEGATIVE EXAMPLE must pass -- otherwise the check pushes
# authors toward vaguer docs, which is worse than the problem it solves.
printf '`updateNetwork` returns Capability not found: writes are absent upstream.\n' \
    >"$MER/workspace/skills/meraki-probe/SKILL.md"
assert_exit 0 "a mutating ID marked unreachable is allowed" run_meraki

# Deprecated GETs are filtered upstream, so citing one unmarked is also a finding.
printf 'Call `getOrganizationDevicesStatuses` for device status.\n' \
    >"$MER/workspace/skills/meraki-probe/SKILL.md"
assert_exit 1 "an unmarked deprecated ID fails" run_meraki
assert_mentions "deprecated" "the finding distinguishes deprecated from nonexistent" run_meraki

# --warn-only reports without failing, matching every other surface.
printf 'Call `getWirelessSSIDs` now.\n' >"$MER/workspace/skills/meraki-probe/SKILL.md"
assert_exit 0 "--warn-only exits 0 despite meraki-id findings" run_meraki --warn-only

# The real repository skills must be clean.
assert_exit 0 "the shipped Meraki skills cite only real capability IDs" \
    python3 "$REPO_ROOT/scripts/check-meraki-capability-ids.py"

# ── pip helper: PEP 668 and legibility (spec 090) ─────────────────────────────
# netclaw_pip_install had no PEP 668 handling, so on an externally-managed host the
# ONE install path spec 077 mandates could not install any new package -- while 56
# call sites papered over it with `--break-system-packages 2>/dev/null || log_warn`,
# turning total failure into one warning line and exit 0. Three servers were dead.
echo
echo "--- pip helper (PEP 668 + legibility) ---"
PH="$TMP/piphelper"; mkdir -p "$PH"

# A fake interpreter that refuses like a PEP 668 host unless --break-system-packages
# is present. Exercises the retry without touching the real environment.
cat >"$PH/fakepy668" <<'EOF'
#!/usr/bin/env bash
[ "$1" = "-m" ] && [ "$2" = "pip" ] || exit 9
case " $* " in
    *" --version "*) echo "pip 99.0"; exit 0 ;;
    *" --break-system-packages "*) echo "Successfully installed thing-1.0"; exit 0 ;;
esac
echo "error: externally-managed-environment" >&2
echo "hint: See PEP 668 for the detailed specification." >&2
exit 1
EOF
chmod +x "$PH/fakepy668"

assert_exit 0 "PEP 668 refusal is retried with --break-system-packages" \
    env NETCLAW_PY="$PH/fakepy668" bash -c \
        'source "$0"/scripts/lib/pip-helper.sh; netclaw_pip_install thing' "$REPO_ROOT"
assert_mentions "externally managed" "the retry is announced, not silent" \
    env NETCLAW_PY="$PH/fakepy668" bash -c \
        'source "$0"/scripts/lib/pip-helper.sh; netclaw_pip_install thing' "$REPO_ROOT"

# A failure for any OTHER reason must surface its actual output, not be swallowed.
cat >"$PH/fakepyfail" <<'EOF'
#!/usr/bin/env bash
[ "$1" = "-m" ] && [ "$2" = "pip" ] || exit 9
case " $* " in *" --version "*) echo "pip 99.0"; exit 0 ;; esac
echo "ERROR: No matching distribution found for nonexistent-xyz" >&2
exit 1
EOF
chmod +x "$PH/fakepyfail"

assert_exit 1 "a genuine install failure returns non-zero" \
    env NETCLAW_PY="$PH/fakepyfail" bash -c \
        'source "$0"/scripts/lib/pip-helper.sh; netclaw_pip_install nonexistent-xyz' "$REPO_ROOT"
assert_mentions "No matching distribution" "the real pip error is not swallowed" \
    env NETCLAW_PY="$PH/fakepyfail" bash -c \
        'source "$0"/scripts/lib/pip-helper.sh; netclaw_pip_install nonexistent-xyz' "$REPO_ROOT"
assert_mentions "FAILED installing" "the failure names what it was installing" \
    env NETCLAW_PY="$PH/fakepyfail" bash -c \
        'source "$0"/scripts/lib/pip-helper.sh; netclaw_pip_install nonexistent-xyz' "$REPO_ROOT"

# The installer must no longer contain the redundant swallowing retry pattern: the
# helper handles PEP 668 itself, and a second discarded call can only hide things.
assert_exit 1 "install-steps.sh has no --break-system-packages call sites left" \
    grep -q 'netclaw_pip_install --break-system-packages' "$REPO_ROOT/scripts/lib/install-steps.sh"

# NOT INSTALLED is not BROKEN. CI is a fresh checkout where every vendored clone is
# absent, so without this distinction the hard gate fails on a healthy tree -- which is
# exactly what happened on the first push of spec 090.
NI="$TMP/notinstalled"; mkdir -p "$NI/config" "$NI/mcp-servers/present-mcp"
python3 - "$NI" <<'EOF'
import json, os, sys
root = sys.argv[1]
cfg = {"mcpServers": {"absent-component": {"command": "python3",
        "args": ["-u", "mcp-servers/never-cloned-mcp/server.py"]}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 0 "a component whose vendored directory was never cloned is skipped" \
    python3 "$REPO_ROOT/scripts/check-server-startup.py" --config "$NI/config/openclaw.json"

# But a wrong path INSIDE a directory that DOES exist is still the aruba-cx-mcp bug.
python3 - "$NI" "$REPO_ROOT" <<'EOF'
import json, os, sys
root, repo = sys.argv[1], sys.argv[2]
present = next((d for d in os.listdir(os.path.join(repo, "mcp-servers"))
                if os.path.isdir(os.path.join(repo, "mcp-servers", d))), None)
cfg = {"mcpServers": {"bad-path": {"command": "python3",
        "args": ["-u", f"mcp-servers/{present}/DEFINITELY-NOT-HERE.py"]}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 1 "a wrong path inside an EXISTING vendored directory still fails" \
    python3 "$REPO_ROOT/scripts/check-server-startup.py" --config "$NI/config/openclaw.json"

# ── startup surface is a HARD GATE now (spec 090) ─────────────────────────────
# Spec 088 shipped it warn-only because seven servers were dead. Six are fixed and the
# seventh is excepted with a reason, so a dead server must now break the build. If this
# test fails, someone re-added "startup" to ALWAYS_WARN.
GATE="$TMP/gate"; mkdir -p "$GATE/scripts" "$GATE/config"
for f in reconcile-mcp.py check-server-startup.py; do
    cp "$REPO_ROOT/scripts/$f" "$GATE/scripts/$f"
done
python3 - "$GATE" <<'EOF'
import json, os, sys
root = sys.argv[1]
cfg = {"mcpServers": {"broken-mcp": {"command": "python3",
        "args": [os.path.join(root, "absent", "server.py")]}}}
json.dump(cfg, open(os.path.join(root, "config/openclaw.json"), "w"))
EOF
assert_exit 1 "a dead server FAILS reconciliation (startup is not warn-only)" \
    python3 "$GATE/scripts/reconcile-mcp.py" --surface startup

# A config/inventory file the server loads is NOT a missing entry point -- spec 088's
# generic pattern reported junos-mcp's absent devices.json as an entry-point problem.
# Uses the real junos-mcp entry point (which exists) pointed at a device-mapping file
# that does not -- the exact shape of the original misdiagnosis.
if [ -f "$REPO_ROOT/mcp-servers/junos-mcp-server/jmcp.py" ]; then
    python3 - "$TMP" "$REPO_ROOT" <<'EOF'
import json, os, sys
tmp, root = sys.argv[1], sys.argv[2]
cfg = {"mcpServers": {"junos-probe": {"command": "python3", "args": [
    "-u", os.path.join(root, "mcp-servers/junos-mcp-server/jmcp.py"),
    "-f", "/nonexistent/devices.json", "-t", "stdio"]}}}
json.dump(cfg, open(os.path.join(tmp, "junoscfg.json"), "w"))
EOF
    assert_mentions "a file the server loads at startup is missing" \
        "a missing runtime data file is distinguished from a missing entry point" \
        python3 "$REPO_ROOT/scripts/check-server-startup.py" --config "$TMP/junoscfg.json"
else
    printf '  skip junos data-file assertion (junos-mcp-server not cloned)\n'
fi

# ── Package-reference surface (spec 093) ──────────────────────────────────────
# Three skills invoked `npx -y @anthropic-ai/microsoft-graph-mcp`, which 404s on npm, and
# documented 14 tool names against it. Neither the docs surface (counts) nor the startup
# surface (registered servers) can see an on-demand npx reference, so nothing caught it.
echo
echo "--- package-reference surface ---"
PKG="$TMP/pkg"
mkdir -p "$PKG/scripts" "$PKG/workspace/skills/probe-skill" \
         "$PKG/specs/093-package-reference-check/contracts"
cp "$REPO_ROOT/scripts/check-package-references.py" "$PKG/scripts/"
run_pkg() { python3 "$PKG/scripts/check-package-references.py" "$@"; }
MAN="$PKG/specs/093-package-reference-check/contracts/verified-packages.json"
cat >"$MAN" <<'JSON'
{"packages": {
  "npm:real-mcp-thing": {"registry":"npm","name":"real-mcp-thing","exists":true,"http_status":200},
  "npm:@ghost/not-real-mcp": {"registry":"npm","name":"@ghost/not-real-mcp","exists":false,"http_status":404}
}}
JSON

# A verified-existing package passes.
printf 'Run `npx -y real-mcp-thing` to start it.\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 0 "a verified existing package passes" run_pkg

# A package the registry said does not exist must fail, naming skill and package.
printf 'Run `npx -y @ghost/not-real-mcp` to start it.\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 1 "a package that does not exist fails" run_pkg
assert_mentions "DOES NOT EXIST" "the finding says the package cannot work" run_pkg
assert_mentions "probe-skill" "the finding names the skill that invokes it" run_pkg

# An unverified reference is a finding, not a pass: unverified is indistinguishable from
# fictional, and defaulting to "probably fine" is how the msgraph 404 survived.
printf 'Run `npx -y some-unknown-mcp-pkg` to start it.\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 1 "an unverified package reference fails rather than passing silently" run_pkg
assert_mentions "never been verified" "the finding distinguishes unverified from nonexistent" run_pkg

# A version/tag suffix must be stripped -- missing this dropped chrome-devtools-mcp@latest
# out of the manifest entirely, the exact quiet failure this check exists to prevent.
printf 'Run `npx -y real-mcp-thing@latest` now.\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 0 "a pinned @version suffix resolves to the same package" run_pkg

# Prose must not be mistaken for a package. Skills contain "npx with Azure AD credentials:".
printf 'Use npx with Azure AD credentials:\nAlso npx skills add opsmill/infrahub-skills\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 0 "prose after npx is not treated as a package" run_pkg

# A reference marked as broken is history, not an invocation -- otherwise the check punishes
# a skill for recording why it changed. Same allowance as the meraki-ids surface.
printf 'Until spec 093 this invoked `npx -y @ghost/not-real-mcp`, which 404s on npm.\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 0 "a reference marked as nonexistent is allowed as history" run_pkg

# --warn-only reports without failing, matching every other surface.
printf 'Run `npx -y @ghost/not-real-mcp` now.\n' \
    >"$PKG/workspace/skills/probe-skill/SKILL.md"
assert_exit 0 "--warn-only exits 0 despite package findings" run_pkg --warn-only

# A missing manifest is cannot-run (exit 2), not a silent pass.
rm "$MAN"
assert_exit 2 "a missing manifest yields exit 2, not a false pass" run_pkg

# The real repository must be clean.
assert_exit 0 "every package the shipped skills invoke is verified to exist" \
    python3 "$REPO_ROOT/scripts/check-package-references.py"

echo
echo "=== Summary ==="
printf '  passed: %d\n  failed: %d\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
echo "  all reconciliation contract tests passed"
