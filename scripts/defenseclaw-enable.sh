#!/usr/bin/env bash
# DefenseClaw Enable Script
# Enables Cisco DefenseClaw (model guardrail, component scanning, audit) for an
# existing NetClaw/OpenClaw installation.
#
# Usage: ./scripts/defenseclaw-enable.sh
#
# The DefenseClaw installer is pinned to a release and verified before it runs:
# install.sh and checksums.txt are downloaded from the GitHub release for
# DEFENSECLAW_VERSION into a private temporary directory, and install.sh runs only
# when its SHA-256 matches the release's checksums.txt entry. Nothing is piped
# from the network into a shell.
#
# Environment (all optional):
#   DEFENSECLAW_VERSION=1.0.4            DefenseClaw release tag to install
#   DEFENSECLAW_GUARDRAIL_MODE=observe   observe | action
#   DEFENSECLAW_REINSTALL=1              reinstall even if defenseclaw is present
#   INSTALL_OPENSHELL=1                  also install NVIDIA OpenShell (opt-in; needs
#                                        OPENSHELL_INSTALL_SHA256 of a reviewed installer)
#   REGISTER_MCPS=1                      register gateway MCP servers with DefenseClaw
#   NETCLAW_ENABLE_SERVICES=1            on a Risk host, generate + enable the durable
#                                        services (including defenseclaw-sidecar.service)
#
# Prerequisites:
#   - Python 3.10+, curl, sha256sum (or shasum)
#   - Node.js 20+ (OpenClaw and the DefenseClaw OpenClaw plugin)
#   - Docker only when INSTALL_OPENSHELL=1

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step()  { echo -e "${CYAN}[STEP]${NC} $1"; }

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# security.mode lives in ~/.openclaw/config/openclaw.json, NOT the gateway's
# ~/.openclaw/openclaw.json. The gateway config schema has no security.mode key
# and OpenClaw rejects the whole file if you add one ("security: Unrecognized
# key"), taking every MCP server down with it. bgp/federation/controls.py reads
# this same path. Do not "fix" this to the gateway config.
OPENCLAW_CONFIG="$HOME/.openclaw/config/openclaw.json"
# The gateway config is a separate file. It holds mcp.servers, models,
# gateway.auth and (after `setup guardrail`) the DefenseClaw plugin entries.
# Resolved the same way bgp/federation/controls.py resolves it.
OPENCLAW_STATE="${OPENCLAW_STATE_DIR:-${OPENCLAW_HOME:-$HOME/.openclaw}}"
GATEWAY_CONFIG="${OPENCLAW_CONFIG_PATH:-$OPENCLAW_STATE/openclaw.json}"

DEFENSECLAW_VERSION="${DEFENSECLAW_VERSION:-1.0.4}"
# SHA-256 of the reviewed 1.0.4 release-asset install.sh (spec 167). A release's own
# checksums.txt detects corruption, not a replaced asset, so the reviewed bytes are
# pinned here too. Another version needs an operator-reviewed DEFENSECLAW_INSTALL_SHA256.
REVIEWED_INSTALL_SHA256_1_0_4="9d92f34c6d28d829a31af6e53a8469ceae4cfd2fae1507b408a818a8faf8e9e7"
if [ -z "${DEFENSECLAW_INSTALL_SHA256:-}" ] && [ "${DEFENSECLAW_VERSION#v}" = "1.0.4" ]; then
    DEFENSECLAW_INSTALL_SHA256="$REVIEWED_INSTALL_SHA256_1_0_4"
fi
DEFENSECLAW_RELEASE_URL="https://github.com/cisco-ai-defense/defenseclaw/releases/download/${DEFENSECLAW_VERSION}"
GUARDRAIL_MODE="${DEFENSECLAW_GUARDRAIL_MODE:-observe}"
CUSTOM_PROVIDERS="$HOME/.defenseclaw/custom-providers.json"

# Release-installed binaries land in ~/.local/bin.
export PATH="$HOME/.local/bin:$PATH"

WORK_DIR=""
cleanup() { if [ -n "$WORK_DIR" ]; then rm -rf "$WORK_DIR"; fi; }
trap cleanup EXIT

is_tty() { [ -t 0 ] && [ -t 1 ]; }

sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print tolower($1)}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print tolower($1)}'
    else
        return 1
    fi
}

fetch() { # fetch <url> <dest>
    curl -fsSL --proto '=https' --tlsv1.2 -o "$2" "$1"
}

echo "========================================="
echo "  NetClaw - Enable DefenseClaw"
echo "  Model guardrail, scanning and audit"
echo "========================================="
echo ""

# ═══════════════════════════════════════════
# Step 1: Check Prerequisites
# ═══════════════════════════════════════════

log_step "1/7 Checking prerequisites..."

PREREQ_FAIL=0

if ! [[ "$DEFENSECLAW_VERSION" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+([.-][A-Za-z0-9.]+)?$ ]]; then
    log_error "DEFENSECLAW_VERSION must be a release tag such as 1.0.4 (got: $DEFENSECLAW_VERSION)."
    PREREQ_FAIL=1
fi
case "$GUARDRAIL_MODE" in
    observe|action) ;;
    *) log_error "DEFENSECLAW_GUARDRAIL_MODE must be observe or action (got: $GUARDRAIL_MODE)."
       PREREQ_FAIL=1 ;;
esac

if ! command -v curl >/dev/null 2>&1; then
    log_error "curl is required to download the pinned DefenseClaw release."
    PREREQ_FAIL=1
fi
if ! command -v sha256sum >/dev/null 2>&1 && ! command -v shasum >/dev/null 2>&1; then
    log_error "sha256sum or shasum is required to verify the DefenseClaw installer."
    PREREQ_FAIL=1
fi

# Check Python 3.10+
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
    if python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
        log_info "Python $PYTHON_VERSION found."
    else
        log_error "Python 3.10+ required. Found: $PYTHON_VERSION"
        PREREQ_FAIL=1
    fi
else
    log_error "Python 3 is required."
    PREREQ_FAIL=1
fi

# Check Node.js 20+ (the DefenseClaw OpenClaw plugin runs inside the gateway)
if command -v node &> /dev/null; then
    NODE_VER=$(node --version | sed 's/^v//' | cut -d. -f1)
    if [[ "$NODE_VER" =~ ^[0-9]+$ ]] && [ "$NODE_VER" -ge 20 ]; then
        log_info "Node.js v$NODE_VER found."
    else
        log_warn "Node.js 20+ recommended. Found: $(node --version)"
    fi
else
    log_warn "Node.js not found. OpenClaw and the DefenseClaw plugin need it."
fi

# Docker is only needed for the optional OpenShell container sandbox.
if [ "${INSTALL_OPENSHELL:-0}" = "1" ]; then
    if ! command -v docker &> /dev/null; then
        log_error "INSTALL_OPENSHELL=1 requires Docker: https://docs.docker.com/get-docker/"
        PREREQ_FAIL=1
    elif ! docker info &> /dev/null; then
        log_error "INSTALL_OPENSHELL=1 requires a running Docker daemon."
        PREREQ_FAIL=1
    else
        log_info "Docker found and running (OpenShell)."
    fi
fi

# DefenseClaw 1.0.x `init` copies gateway.auth.token from the OpenClaw gateway
# config verbatim and fails ("gateway defaults: str expected, not dict") when it
# is a SecretRef object. Detect that before installing anything. Never print the
# token and never rewrite it here.
TOKEN_STATE=$(GATEWAY_CONFIG="$GATEWAY_CONFIG" python3 - <<'PY' 2>/dev/null || echo unreadable
import json, os
path = os.environ["GATEWAY_CONFIG"]
try:
    with open(path) as fh:
        cfg = json.load(fh)
except FileNotFoundError:
    print("absent"); raise SystemExit
except (OSError, ValueError):
    print("unreadable"); raise SystemExit
gateway = cfg.get("gateway") if isinstance(cfg, dict) else None
auth = gateway.get("auth") if isinstance(gateway, dict) else None
token = auth.get("token") if isinstance(auth, dict) else None
print("secretref" if isinstance(token, dict) else "ok")
PY
)
case "$TOKEN_STATE" in
    secretref)
        log_error "OpenClaw gateway.auth.token in $GATEWAY_CONFIG is a SecretRef object."
        log_error "DefenseClaw 1.0.x 'init' cannot read it and fails with"
        log_error "  \"gateway defaults: str expected, not dict\"."
        log_error "Options (this script does not change your token):"
        log_error "  1. Give the gateway a literal token (for example rotate it to a new random"
        log_error "     value with your usual OpenClaw procedure), restart the gateway, re-run."
        log_error "  2. Keep the SecretRef and wait for a DefenseClaw release that resolves it."
        PREREQ_FAIL=1
        ;;
    absent)
        log_warn "No OpenClaw gateway config at $GATEWAY_CONFIG; DefenseClaw init needs one."
        ;;
    unreadable)
        log_warn "Could not parse $GATEWAY_CONFIG as JSON; gateway.auth.token was not checked."
        log_warn "If it is a SecretRef object, DefenseClaw init will fail (see docs/DEFENSECLAW.md)."
        ;;
    *)
        log_info "OpenClaw gateway token is not a SecretRef (compatible with DefenseClaw init)."
        ;;
esac

if [ "$PREREQ_FAIL" -eq 1 ]; then
    log_error ""
    log_error "Prerequisites not met. Nothing was installed or changed."
    exit 1
fi

echo ""

# ═══════════════════════════════════════════
# Step 2: Backup Current Configuration
# ═══════════════════════════════════════════

log_step "2/7 Backing up configuration..."

STAMP="$(date +%Y%m%d_%H%M%S)"
for cfg in "$OPENCLAW_CONFIG" "$GATEWAY_CONFIG"; do
    if [ -f "$cfg" ]; then
        cp -p "$cfg" "$cfg.backup.$STAMP"
        log_info "Backed up $cfg -> $cfg.backup.$STAMP"
    fi
done
if [ ! -f "$OPENCLAW_CONFIG" ]; then
    log_warn "No $OPENCLAW_CONFIG yet. It will be created."
    mkdir -p "$(dirname "$OPENCLAW_CONFIG")"
fi

echo ""

# ═══════════════════════════════════════════
# Step 3: Install DefenseClaw (pinned + verified)
# ═══════════════════════════════════════════

log_step "3/7 Installing DefenseClaw $DEFENSECLAW_VERSION (pinned release, checksum-verified)..."

# Called in a `||` context, so errexit is off inside: every step is checked.
install_defenseclaw() {
    local expected actual
    WORK_DIR="$(mktemp -d)" || return 1
    chmod 700 "$WORK_DIR" || return 1
    log_info "Downloading install.sh and checksums.txt from $DEFENSECLAW_RELEASE_URL/"
    if ! fetch "$DEFENSECLAW_RELEASE_URL/install.sh" "$WORK_DIR/install.sh" \
        || ! fetch "$DEFENSECLAW_RELEASE_URL/checksums.txt" "$WORK_DIR/checksums.txt"; then
        log_error "Download failed. Check DEFENSECLAW_VERSION ($DEFENSECLAW_VERSION) and connectivity."
        return 1
    fi
    expected=$(awk '{f=$2; sub(/^\*/, "", f); sub(/^\.\//, "", f); if (f == "install.sh") print tolower($1)}' \
        "$WORK_DIR/checksums.txt")
    if [ -z "$expected" ] || [[ "$expected" == *$'\n'* ]]; then
        log_error "checksums.txt has no single entry for install.sh. Refusing to run it."
        return 1
    fi
    if ! [[ "$expected" =~ ^[0-9a-f]{64}$ ]]; then
        log_error "checksums.txt entry for install.sh is not a SHA-256 digest. Refusing to run it."
        return 1
    fi
    actual="$(sha256_of "$WORK_DIR/install.sh")"
    if [ "$actual" != "$expected" ]; then
        log_error "install.sh SHA-256 mismatch (expected $expected, got ${actual:-none}). Refusing to run it."
        return 1
    fi
    if [ -z "${DEFENSECLAW_INSTALL_SHA256:-}" ]; then
        log_error "No reviewed SHA-256 for DefenseClaw $DEFENSECLAW_VERSION install.sh."
        log_error "Review that installer, then set DEFENSECLAW_INSTALL_SHA256=$actual and rerun."
        return 1
    fi
    if [ "$actual" != "$(printf '%s' "$DEFENSECLAW_INSTALL_SHA256" | tr 'A-F' 'a-f')" ]; then
        log_error "install.sh does not match the reviewed SHA-256 for $DEFENSECLAW_VERSION. Refusing to run it."
        return 1
    fi
    log_info "install.sh verified against checksums.txt and the reviewed digest (sha256 $actual)."
    # --connector openclaw wires the OpenClaw plugin. The installer keeps an
    # existing, newer OpenClaw; it may install OpenClaw only if absent or older.
    if ! bash "$WORK_DIR/install.sh" --yes --connector openclaw; then
        log_error "DefenseClaw installer exited non-zero."
        return 1
    fi
    rm -rf "$WORK_DIR"
    WORK_DIR=""
}

if command -v defenseclaw &> /dev/null; then
    CURRENT_VERSION=$(defenseclaw --version 2>/dev/null || echo "unknown")
    log_info "DefenseClaw already installed: $CURRENT_VERSION"
    REINSTALL="${DEFENSECLAW_REINSTALL:-}"
    if [ -z "$REINSTALL" ] && is_tty; then
        read -rp "Reinstall pinned release $DEFENSECLAW_VERSION? [y/N] " REINSTALL || REINSTALL=""
    fi
    if [[ "$REINSTALL" =~ ^([Yy]|1) ]]; then
        install_defenseclaw || { log_error "DefenseClaw was not reinstalled."; exit 1; }
    else
        log_info "Keeping the installed DefenseClaw (set DEFENSECLAW_REINSTALL=1 to reinstall)."
    fi
else
    install_defenseclaw || { log_error "DefenseClaw was not installed."; exit 1; }
fi

if ! command -v defenseclaw &> /dev/null; then
    log_error "defenseclaw is not on PATH after installation (looked in ~/.local/bin too)."
    exit 1
fi
log_info "DefenseClaw: $(defenseclaw --version 2>/dev/null || echo unknown)"

echo ""

# ═══════════════════════════════════════════
# Step 4: Initialize DefenseClaw + guardrail
# ═══════════════════════════════════════════

log_step "4/7 Initializing DefenseClaw and the OpenClaw guardrail ($GUARDRAIL_MODE mode)..."

if ! defenseclaw init --connector openclaw --non-interactive --yes --scanner-mode local; then
    log_error "'defenseclaw init' failed (output above). security.mode was NOT changed."
    log_error "If it reports \"gateway defaults: str expected, not dict\", see the SecretRef"
    log_error "gateway token note in docs/DEFENSECLAW.md."
    exit 1
fi

# Installs the DefenseClaw OpenClaw plugin (~/.openclaw/extensions/defenseclaw plus
# plugins.allow/entries/load.paths in the gateway config). The plugin sends model
# traffic through the guardrail proxy on 127.0.0.1:4000. --no-restart: the operator
# restarts the gateway once the sidecar is running.
if ! defenseclaw setup guardrail --connector openclaw --mode "$GUARDRAIL_MODE" \
        --scanner-mode local --detection-strategy regex_only --non-interactive --no-restart; then
    log_error "'defenseclaw setup guardrail' failed (output above). security.mode was NOT changed."
    exit 1
fi
log_info "Guardrail configured in $GUARDRAIL_MODE mode."

echo ""

# ═══════════════════════════════════════════
# Step 5: security.mode
# ═══════════════════════════════════════════

log_step "5/7 Setting security.mode=defenseclaw in $OPENCLAW_CONFIG..."

OPENCLAW_CONFIG="$OPENCLAW_CONFIG" python3 - <<'PY'
import json, os, sys, tempfile
path = os.environ["OPENCLAW_CONFIG"]
try:
    with open(path) as fh:
        config = json.load(fh)
except FileNotFoundError:
    config = {}
except (OSError, ValueError) as exc:
    sys.exit(f"Refusing to overwrite unreadable {path}: {exc}")
if not isinstance(config, dict):
    sys.exit(f"Refusing to overwrite {path}: top level is not an object")
security = config.get("security")
if not isinstance(security, dict):
    security = config["security"] = {}
security["mode"] = "defenseclaw"
config.pop("netshell", None)  # old NetShell config
mode = os.stat(path).st_mode & 0o777 if os.path.exists(path) else 0o600
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".openclaw.json.")
with os.fdopen(fd, "w") as fh:
    json.dump(config, fh, indent=2)
    fh.write("\n")
os.chmod(tmp, mode)
os.replace(tmp, path)
print("Configuration updated.")
PY

echo ""

# ═══════════════════════════════════════════
# Step 6: Optional OpenShell, optional MCP registration
# ═══════════════════════════════════════════

log_step "6/7 Optional components..."

if [ "${INSTALL_OPENSHELL:-0}" = "1" ]; then
    OPENSHELL_URL="https://raw.githubusercontent.com/NVIDIA/OpenShell/${OPENSHELL_REF:-main}/install.sh"
    if command -v openshell &> /dev/null; then
        log_info "OpenShell already installed: $(openshell --version 2>/dev/null || echo unknown)"
    elif [ -z "${OPENSHELL_INSTALL_SHA256:-}" ]; then
        log_warn "INSTALL_OPENSHELL=1 but OPENSHELL_INSTALL_SHA256 is not set; OpenShell not installed."
        log_warn "Download and review the installer, then re-run with its SHA-256:"
        log_warn "  curl -fsSL --proto '=https' --tlsv1.2 -o openshell-install.sh $OPENSHELL_URL"
        log_warn "  sha256sum openshell-install.sh"
    else
        WORK_DIR="$(mktemp -d)"; chmod 700 "$WORK_DIR"
        WANT_SHA="$(printf '%s' "$OPENSHELL_INSTALL_SHA256" | tr 'A-F' 'a-f')"
        if fetch "$OPENSHELL_URL" "$WORK_DIR/openshell-install.sh" \
            && [ "$(sha256_of "$WORK_DIR/openshell-install.sh")" = "$WANT_SHA" ]; then
            if sh "$WORK_DIR/openshell-install.sh"; then
                log_info "OpenShell installed."
            else
                log_warn "OpenShell installer exited non-zero."
            fi
        else
            log_warn "OpenShell installer download failed or did not match OPENSHELL_INSTALL_SHA256; not run."
        fi
        rm -rf "$WORK_DIR"; WORK_DIR=""
    fi
else
    log_info "OpenShell not installed (opt-in: INSTALL_OPENSHELL=1). NetClaw's production"
    log_info "sandbox control for Risk members is systemd confinement (feature 057,"
    log_info "specs 165/166), not an OpenShell container."
fi

if [ "${REGISTER_MCPS:-0}" = "1" ]; then
    log_info "Registering gateway MCP servers with DefenseClaw (REGISTER_MCPS=1)..."
    GATEWAY_CONFIG="$GATEWAY_CONFIG" python3 - <<'PY' || log_warn "MCP registration did not complete (see above)."
import json, os, subprocess, sys
try:
    with open(os.environ["GATEWAY_CONFIG"]) as fh:
        config = json.load(fh)
except (OSError, ValueError) as exc:
    sys.exit(f"Could not read gateway config: {exc}")
servers = (config.get("mcp") or {}).get("servers") or config.get("mcpServers") or {}
counts = {"registered": 0, "skipped": 0, "failed": 0}
for name, server in sorted(servers.items()):
    url = server.get("url", "")
    if "command" not in server and not url.startswith("http"):
        print(f"  SKIP: {name} (no command)"); counts["skipped"] += 1; continue
    if "${" in url:
        print(f"  SKIP: {name} (env var URL)"); counts["skipped"] += 1; continue
    cmd = ["defenseclaw", "mcp", "set", name, "--skip-scan"]
    if "command" in server:
        cmd += ["--command", server["command"]]
        if "args" in server:
            args = server["args"]
            cmd += ["--args", json.dumps(args) if isinstance(args, list) else str(args)]
    if url:
        cmd += ["--url", url]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except Exception as exc:
        print(f"  ERROR: {name} - {exc}"); counts["failed"] += 1; continue
    if result.returncode == 0:
        print(f"  OK: {name}"); counts["registered"] += 1
    else:
        print(f"  FAIL: {name} - {result.stderr.strip()[:120]}"); counts["failed"] += 1
print("MCP registration: {registered} registered, {skipped} skipped, {failed} failed".format(**counts))
PY
else
    log_info "MCP registration skipped (opt-in: REGISTER_MCPS=1)."
fi

echo ""

# ═══════════════════════════════════════════
# Step 7: Guardrail sidecar + next steps
# ═══════════════════════════════════════════

log_step "7/7 Guardrail sidecar and next steps..."

FEDERATION_DB="${N2N_BASE_DIR:-$HOME/.openclaw/n2n}/federation.db"
SIDECAR_STARTED=0
if [ -f "$FEDERATION_DB" ] && command -v defenseclaw-gateway >/dev/null 2>&1 \
        && command -v systemctl >/dev/null 2>&1 && systemctl --user show-environment >/dev/null 2>&1; then
    DO_SERVICES="${NETCLAW_ENABLE_SERVICES:-}"
    if [ -z "$DO_SERVICES" ] && is_tty; then
        read -rp "Risk detected. Generate + enable its durable services (mesh, members, defenseclaw-sidecar)? [y/N] " DO_SERVICES || DO_SERVICES=""
    fi
    if [[ "$DO_SERVICES" =~ ^([Yy]|1) ]]; then
        if python3 "$NETCLAW_DIR/scripts/in2n-services.py" generate \
            && python3 "$NETCLAW_DIR/scripts/in2n-services.py" enable; then
            SIDECAR_STARTED=1
            log_info "Durable services enabled, including defenseclaw-sidecar.service."
        else
            log_warn "in2n-services.py generate/enable reported a failure (output above)."
        fi
    fi
fi

# Provider hostnames only (never keys or full URLs), to compare with DefenseClaw's
# provider registry.
PROVIDER_HOSTS=$(GATEWAY_CONFIG="$GATEWAY_CONFIG" python3 - <<'PY' 2>/dev/null || true
import json, os
from urllib.parse import urlsplit
try:
    with open(os.environ["GATEWAY_CONFIG"]) as fh:
        cfg = json.load(fh)
    providers = (cfg.get("models") or {}).get("providers") or {}
    hosts = {urlsplit(p.get("baseUrl") or "").hostname or "" for p in providers.values()
             if isinstance(p, dict)}
    print(" ".join(sorted(hosts - {""})))
except Exception:
    pass
PY
)

echo ""
echo "========================================="
echo "  DefenseClaw $DEFENSECLAW_VERSION enabled ($GUARDRAIL_MODE mode)"
echo "========================================="
echo ""
echo "  Next steps"
echo "  ----------"
echo ""
echo "  1. Register model providers DefenseClaw does not know. The guardrail proxy"
echo "     blocks traffic to unknown provider domains fail-closed (OpenClaw gets a 403)."
if [ -n "$PROVIDER_HOSTS" ]; then
    echo "     Provider hosts in your gateway config: $PROVIDER_HOSTS"
fi
echo "     Register any host DefenseClaw does not know (check: defenseclaw setup provider list)."
echo "     $CUSTOM_PROVIDERS is derived from config.yaml; do not edit it. Ollama Cloud example:"
cat <<'EOF'
       defenseclaw setup provider add --name ollama-cloud --domain ollama.com \
         --env-key OLLAMA_API_KEY --profile-id ollama-cloud:default --base-provider-type ollama
       systemctl --user restart defenseclaw-sidecar   # if live reload reports the sidecar unreachable
EOF
echo ""
if [ "$SIDECAR_STARTED" -eq 1 ]; then
    echo "  2. Guardrail sidecar: running as defenseclaw-sidecar.service."
elif [ -f "$FEDERATION_DB" ]; then
    echo "  2. Start the guardrail sidecar (proxy on 127.0.0.1:4000) as a durable service:"
    echo "       python3 scripts/in2n-services.py generate"
    echo "       python3 scripts/in2n-services.py enable"
    echo "     (generate writes defenseclaw-sidecar.service when defenseclaw-gateway is on PATH)"
else
    echo "  2. Start the guardrail sidecar (proxy on 127.0.0.1:4000): run defenseclaw-gateway"
    echo "     under your service manager. On an iN2N Risk host use instead:"
    echo "       python3 scripts/in2n-services.py generate && python3 scripts/in2n-services.py enable"
fi
echo ""
echo "  3. Restart the OpenClaw gateway so it loads the DefenseClaw plugin:"
echo "       openclaw gateway restart"
echo ""
echo "  4. Send one model turn and confirm it reaches DefenseClaw's audit log. To block"
echo "     (not only log) once observe mode looks right:"
echo "       defenseclaw setup guardrail --connector openclaw --mode action \\"
echo "         --scanner-mode local --detection-strategy regex_only --non-interactive --no-restart"
echo "       openclaw gateway restart"
echo ""
echo "  5. On a Risk in production mode, check posture (n2n_posture, or"
echo "       curl -s http://127.0.0.1:8179/n2n/posture )"
echo ""
echo "  Documentation: docs/DEFENSECLAW.md, docs/N2N-RISK.md"
echo "  To disable:    ./scripts/defenseclaw-disable.sh"
echo ""
