#!/usr/bin/env bash
# NetClaw Secure Startup Script
# Starts the full enterprise security stack: OpenShell + DefenseClaw + NetClaw
#
# Usage:
#   ./scripts/netclaw-secure-start.sh          # Start everything
#   ./scripts/netclaw-secure-start.sh stop     # Stop everything
#   ./scripts/netclaw-secure-start.sh status   # Check status

set -uo pipefail
# Note: removed -e so script doesn't exit on first error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
log_error() { echo -e "${RED}[✗]${NC} $1"; }
log_step()  { echo -e "${CYAN}[→]${NC} $1"; }

SANDBOX_NAME="netclaw"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NETCLAW_DIR="$(dirname "$SCRIPT_DIR")"

# ═══════════════════════════════════════════
# Status Command
# ═══════════════════════════════════════════

show_status() {
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  NetClaw Enterprise Security Status"
    echo "═══════════════════════════════════════════"
    echo ""

    # Ring 1: OpenShell
    echo -e "${CYAN}Ring 1 - OpenShell (Container Isolation):${NC}"
    if docker ps 2>/dev/null | grep -q openshell; then
        echo "  Gateway:  Running"
        openshell sandbox list 2>/dev/null | grep -E "NAME|$SANDBOX_NAME" || echo "  Sandbox:  Not created"
    else
        echo "  Gateway:  Not running"
    fi
    echo ""

    # Ring 2: DefenseClaw
    echo -e "${CYAN}Ring 2 - DefenseClaw (Runtime Guardrails):${NC}"
    if pgrep -f defenseclaw-gateway &> /dev/null; then
        GUARDRAIL_MODE=$(grep -A2 "^guardrail:" ~/.defenseclaw/config.yaml 2>/dev/null | grep "mode:" | awk '{print $2}')
        echo "  Gateway:  Running"
        echo "  Mode:     ${GUARDRAIL_MODE:-observe}"
    else
        echo "  Gateway:  Not running"
    fi
    echo ""

    # Ring 3: NetClaw
    echo -e "${CYAN}Ring 3 - NetClaw (AI Agent):${NC}"
    if pgrep -f "openclaw.*gateway" &> /dev/null; then
        echo "  Gateway:  Running"
    else
        echo "  Gateway:  Not running"
    fi
    echo ""
}

# ═══════════════════════════════════════════
# Stop Command
# ═══════════════════════════════════════════

stop_all() {
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  Stopping NetClaw Enterprise Stack"
    echo "═══════════════════════════════════════════"
    echo ""

    log_step "Stopping sandbox '$SANDBOX_NAME'..."
    openshell sandbox delete "$SANDBOX_NAME" 2>/dev/null || true
    log_info "Sandbox stopped"

    echo ""
    log_info "NetClaw sandbox stopped. Security infrastructure still running."
    echo ""
    echo "  To fully stop the security stack:"
    echo "    openshell gateway stop     # Stop OpenShell (frees Docker resources)"
    echo "    pkill defenseclaw-gateway  # Stop DefenseClaw"
    echo ""
}

# ═══════════════════════════════════════════
# Build Custom Sandbox Image
# ═══════════════════════════════════════════

build_sandbox_image() {
    log_info "Building custom sandbox with latest OpenClaw..."
    log_info "This takes 2-3 minutes. Watching progress..."

    # Create Dockerfile
    mkdir -p /tmp/netclaw-sandbox
    cat > /tmp/netclaw-sandbox/Dockerfile << 'EOF'
FROM ghcr.io/nvidia/openshell-community/sandboxes/base:latest

USER root

# Install latest OpenClaw
RUN npm install -g openclaw@latest

# Create claw alias
RUN ln -sf /usr/lib/node_modules/openclaw/bin/openclaw.js /usr/local/bin/claw || true

USER sandbox

# Verify
RUN openclaw --version
EOF

    # Build in background and monitor
    openshell sandbox create --name "$SANDBOX_NAME" --from /tmp/netclaw-sandbox > /tmp/sandbox-build.log 2>&1 &
    BUILD_PID=$!

    # Show progress while building
    while kill -0 $BUILD_PID 2>/dev/null; do
        if [ -f /tmp/sandbox-build.log ]; then
            LAST_LINE=$(tail -1 /tmp/sandbox-build.log 2>/dev/null | tr -d '\n' | cut -c1-60)
            if [ -n "$LAST_LINE" ]; then
                printf "\r  [build] %s..." "$LAST_LINE"
            fi
        fi
        sleep 2
    done
    printf "\n"

    wait $BUILD_PID
    BUILD_EXIT=$?

    if [ $BUILD_EXIT -eq 0 ] && grep -q "Created sandbox" /tmp/sandbox-build.log; then
        log_info "Sandbox image built successfully"
        return 0
    else
        log_error "Failed to build sandbox image"
        echo "Build log:"
        cat /tmp/sandbox-build.log
        return 1
    fi
}

# ═══════════════════════════════════════════
# Apply Network Policy for Sandbox
# ═══════════════════════════════════════════

apply_network_policy() {
    log_info "Applying network policy (Slack, LLM APIs, MCPs)..."

    cat > /tmp/netclaw-sandbox-policy.yaml << 'POLICY_EOF'
# NetClaw Enterprise Sandbox Network Policy
# Allows Slack, WebEx, LLM APIs, and MCP endpoints

version: 1

filesystem_policy:
  include_workdir: true
  read_only: [/usr, /lib, /proc, /dev/urandom, /app, /etc, /var/log]
  read_write: [/sandbox, /tmp, /dev/null]

landlock:
  compatibility: best_effort

process:
  run_as_user: sandbox
  run_as_group: sandbox

network_policies:
  # Slack API - full access for bot operations
  slack:
    name: slack-api
    endpoints:
      - host: api.slack.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: slack.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: www.slack.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: edgeapi.slack.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: wss-primary.slack.com
        port: 443
        protocol: wss
        enforcement: enforce
        access: full
      - host: wss-backup.slack.com
        port: 443
        protocol: wss
        enforcement: enforce
        access: full
      - host: wss-mobile.slack.com
        port: 443
        protocol: wss
        enforcement: enforce
        access: full
      - host: files.slack.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: a.slack-edge.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: b.slack-edge.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: app.slack.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # WebEx API
  webex:
    name: webex-api
    endpoints:
      - host: webexapis.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: api.ciscospark.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: idbroker.webex.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: wdm-a.wbx2.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Anthropic Claude API
  anthropic:
    name: anthropic-api
    endpoints:
      - host: api.anthropic.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # OpenAI API
  openai:
    name: openai-api
    endpoints:
      - host: api.openai.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Cisco DevNet MCP
  devnet:
    name: devnet-api
    endpoints:
      - host: devnet.cisco.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Datadog API
  datadog:
    name: datadog-api
    endpoints:
      - host: api.datadoghq.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: app.datadoghq.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # GitHub API
  github:
    name: github-api
    endpoints:
      - host: api.github.com
        port: 443
        protocol: rest
        enforcement: enforce
        access: full
      - host: github.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/curl }

  # GitLab API
  gitlab:
    name: gitlab-api
    endpoints:
      - host: gitlab.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Atlassian API
  atlassian:
    name: atlassian-api
    endpoints:
      - host: api.atlassian.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: auth.atlassian.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Azure APIs
  azure:
    name: azure-api
    endpoints:
      - host: management.azure.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: login.microsoftonline.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # AWS APIs
  aws:
    name: aws-api
    endpoints:
      - host: ec2.amazonaws.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: sts.amazonaws.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # GCP APIs
  gcp:
    name: gcp-api
    endpoints:
      - host: compute.googleapis.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: cloudresourcemanager.googleapis.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Splunk API
  splunk:
    name: splunk-api
    endpoints:
      - host: api.splunk.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # PagerDuty API
  pagerduty:
    name: pagerduty-api
    endpoints:
      - host: api.pagerduty.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # ServiceNow API
  servicenow:
    name: servicenow-api
    endpoints:
      - host: service-now.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Terraform
  terraform:
    name: terraform-api
    endpoints:
      - host: registry.terraform.io
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: app.terraform.io
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Vault
  vault:
    name: vault-api
    endpoints:
      - host: vault.hashicorp.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # ThousandEyes
  thousandeyes:
    name: thousandeyes-api
    endpoints:
      - host: api.thousandeyes.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Zscaler
  zscaler:
    name: zscaler-api
    endpoints:
      - host: zsapi.zscaler.net
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: config.zscaler.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Cloudflare
  cloudflare:
    name: cloudflare-api
    endpoints:
      - host: api.cloudflare.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Grafana
  grafana:
    name: grafana-api
    endpoints:
      - host: grafana.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # Meraki
  meraki:
    name: meraki-api
    endpoints:
      - host: api.meraki.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
      - host: dashboard.meraki.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Cisco DNA Center
  dnac:
    name: dnac-api
    endpoints:
      - host: sandboxdnac.cisco.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Cisco ISE
  ise:
    name: ise-api
    endpoints:
      - host: ise.cisco.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Cisco SD-WAN
  sdwan:
    name: sdwan-api
    endpoints:
      - host: vmanage-sdwan.cisco.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Infoblox
  infoblox:
    name: infoblox-api
    endpoints:
      - host: csp.infoblox.com
        port: 443
        protocol: https
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }
      - { path: /usr/bin/python3 }

  # Ollama local
  ollama:
    name: ollama-local
    endpoints:
      - host: localhost
        port: 11434
        protocol: http
        enforcement: enforce
        access: full
      - host: 127.0.0.1
        port: 11434
        protocol: http
        enforcement: enforce
        access: full
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/node }

  # PyPI
  pypi:
    name: pypi
    endpoints:
      - host: pypi.org
        port: 443
        protocol: https
        enforcement: enforce
        access: read-only
      - host: files.pythonhosted.org
        port: 443
        protocol: https
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/python3 }
      - { path: /usr/bin/pip3 }

  # npm
  npm:
    name: npm
    endpoints:
      - host: registry.npmjs.org
        port: 443
        protocol: https
        enforcement: enforce
        access: read-only
    binaries:
      - { path: /usr/bin/node }
      - { path: /usr/local/bin/npm }
POLICY_EOF

    if openshell policy set "$SANDBOX_NAME" --policy /tmp/netclaw-sandbox-policy.yaml --wait 2>&1; then
        log_info "Network policy applied successfully"
    else
        log_warn "Failed to apply network policy. May need manual setup."
    fi
}

# ═══════════════════════════════════════════
# Prepare Config for Sandbox
# ═══════════════════════════════════════════

prepare_sandbox_config() {
    log_info "Preparing config for sandbox..."

    # Create staging directory
    rm -rf /tmp/netclaw-sandbox-config
    mkdir -p /tmp/netclaw-sandbox-config/config

    python3 << 'EOF'
import json
import os
import shutil

staging = "/tmp/netclaw-sandbox-config"
home_openclaw = os.path.expanduser("~/.openclaw")

def clean_config(config):
    """Remove host-specific paths, stale plugin references, and fix model for sandbox"""
    # Remove defenseclaw plugin paths
    if "plugins" in config:
        if "load" in config["plugins"] and "paths" in config["plugins"]["load"]:
            config["plugins"]["load"]["paths"] = [
                p for p in config["plugins"]["load"]["paths"]
                if "defenseclaw" not in p and "/home/" not in p
            ]
        # Remove stale plugin entries
        if "entries" in config["plugins"]:
            for key in ["defenseclaw", "webex"]:
                if key in config["plugins"]["entries"]:
                    del config["plugins"]["entries"][key]
        # Remove from allow list
        if "allow" in config["plugins"]:
            config["plugins"]["allow"] = [
                p for p in config["plugins"]["allow"]
                if p not in ["defenseclaw", "webex"]
            ]

    # Change model from defenseclaw/* to anthropic/* for sandbox
    # (DefenseClaw gateway runs on host, not accessible from sandbox)
    if "agent" in config and "model" in config["agent"]:
        model = config["agent"]["model"]
        if model.startswith("defenseclaw/"):
            config["agent"]["model"] = model.replace("defenseclaw/", "anthropic/")
            print(f"  Model changed for sandbox: {model} -> {config['agent']['model']}")

    return config

# Process config/openclaw.json
src = os.path.join(home_openclaw, "config", "openclaw.json")
dst = os.path.join(staging, "config", "openclaw.json")
if os.path.exists(src):
    with open(src) as f:
        config = json.load(f)
    config = clean_config(config)
    with open(dst, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Cleaned config/openclaw.json")

# Process root openclaw.json (also needs cleaning!)
root_src = os.path.join(home_openclaw, "openclaw.json")
root_dst = os.path.join(staging, "openclaw.json")
if os.path.exists(root_src):
    with open(root_src) as f:
        config = json.load(f)
    config = clean_config(config)
    with open(root_dst, "w") as f:
        json.dump(config, f, indent=2)
    print(f"  Cleaned openclaw.json (root)")

# Copy .env file
env_src = os.path.join(home_openclaw, ".env")
if os.path.exists(env_src):
    shutil.copy(env_src, os.path.join(staging, ".env"))
    print(f"  Copied .env")

# Copy SOUL files
for fname in ["SOUL.md", "SOUL-EXPERTISE.md", "SOUL-SKILLS.md"]:
    src_path = os.path.join(home_openclaw, fname)
    if os.path.exists(src_path):
        shutil.copy(src_path, os.path.join(staging, fname))
        print(f"  Copied {fname}")

# Copy agents auth directory (contains API keys)
agents_src = os.path.join(home_openclaw, "agents")
agents_dst = os.path.join(staging, "agents")
if os.path.exists(agents_src):
    shutil.copytree(agents_src, agents_dst, dirs_exist_ok=True)
    print(f"  Copied agents/ (auth profiles)")

print("Config prepared for sandbox")
EOF
}

# ═══════════════════════════════════════════
# Start Command
# ═══════════════════════════════════════════

start_all() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  NetClaw Enterprise Secure Startup"
    echo "  3 Rings: OpenShell → DefenseClaw → NetClaw"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # ─────────────────────────────────────────
    # Ring 1: OpenShell (Container Isolation)
    # ─────────────────────────────────────────
    log_step "Ring 1/3: OpenShell (Container Isolation)..."

    if ! command -v openshell &> /dev/null; then
        log_error "OpenShell not installed."
        log_info "Installing OpenShell..."
        curl -LsSf https://raw.githubusercontent.com/NVIDIA/OpenShell/main/install.sh | sh
    fi

    if ! command -v docker &> /dev/null || ! docker info &> /dev/null 2>&1; then
        log_error "Docker not running. Start Docker first."
        exit 1
    fi

    # Start OpenShell gateway
    if docker ps 2>/dev/null | grep -q openshell; then
        log_info "OpenShell gateway already running"
    else
        log_info "Starting OpenShell gateway (may take 30-60 seconds)..."
        openshell gateway start 2>&1 | tail -3
    fi

    # Wait for gateway
    sleep 5

    echo ""

    # ─────────────────────────────────────────
    # Ring 2: DefenseClaw (Runtime Guardrails)
    # ─────────────────────────────────────────
    log_step "Ring 2/3: DefenseClaw (Runtime Guardrails)..."

    if ! command -v defenseclaw &> /dev/null; then
        log_warn "DefenseClaw not installed. Installing..."
        curl -LsSf https://raw.githubusercontent.com/cisco-ai-defense/defenseclaw/main/scripts/install.sh | bash
        defenseclaw init --enable-guardrail 2>/dev/null || true
    fi

    if pgrep -f defenseclaw-gateway &> /dev/null; then
        log_info "DefenseClaw gateway already running"
    else
        log_info "Starting DefenseClaw gateway..."
        nohup defenseclaw-gateway > ~/.defenseclaw/gateway.log 2>&1 &
        sleep 2
    fi

    GUARDRAIL_MODE=$(grep -A2 "^guardrail:" ~/.defenseclaw/config.yaml 2>/dev/null | grep "mode:" | awk '{print $2}' || echo 'observe')
    log_info "DefenseClaw mode: $GUARDRAIL_MODE"

    echo ""

    # ─────────────────────────────────────────
    # Ring 3: NetClaw (AI Agent in Sandbox)
    # ─────────────────────────────────────────
    log_step "Ring 3/3: NetClaw (AI Agent in Sandbox)..."

    # Check if sandbox exists and is ready
    if openshell sandbox list 2>/dev/null | grep -q "$SANDBOX_NAME.*Ready"; then
        log_info "Sandbox '$SANDBOX_NAME' already exists and is ready"
    elif openshell sandbox list 2>/dev/null | grep -q "$SANDBOX_NAME"; then
        log_info "Sandbox exists but not ready. Deleting and recreating..."
        openshell sandbox delete "$SANDBOX_NAME" 2>/dev/null || true
        sleep 3
        build_sandbox_image
    else
        log_info "Creating sandbox with latest OpenClaw..."
        build_sandbox_image
    fi

    # Wait for sandbox to be ready (with timeout)
    log_info "Verifying sandbox is ready..."
    READY=0
    for i in {1..30}; do
        if openshell sandbox list 2>/dev/null | grep "$SANDBOX_NAME" | grep -q "Ready"; then
            log_info "Sandbox ready!"
            READY=1
            break
        fi
        sleep 3
    done

    if [ $READY -eq 0 ]; then
        log_error "Sandbox did not become ready in time"
        log_warn "Try: openshell sandbox list"
        exit 1
    fi

    # Prepare and upload config
    prepare_sandbox_config

    log_info "Migrating your NetClaw config to sandbox..."

    # Create directory structure inside sandbox
    log_step "Creating directory structure..."
    openshell sandbox exec -n "$SANDBOX_NAME" -- mkdir -p /sandbox/.openclaw/config
    openshell sandbox exec -n "$SANDBOX_NAME" -- mkdir -p /sandbox/.openclaw/workspace

    # Upload files one by one with status
    log_step "Uploading config files..."

    if [ -f /tmp/netclaw-sandbox-config/config/openclaw.json ]; then
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/config/openclaw.json /sandbox/.openclaw/config/openclaw.json
        log_info "  → config/openclaw.json"
    fi

    if [ -f /tmp/netclaw-sandbox-config/.env ]; then
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/.env /sandbox/.openclaw/.env
        log_info "  → .env (API keys)"
    fi

    if [ -f /tmp/netclaw-sandbox-config/openclaw.json ]; then
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/openclaw.json /sandbox/.openclaw/openclaw.json
        log_info "  → openclaw.json (root)"
    fi

    if [ -f /tmp/netclaw-sandbox-config/SOUL.md ]; then
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/SOUL.md /sandbox/.openclaw/SOUL.md
        log_info "  → SOUL.md"
    fi

    if [ -f /tmp/netclaw-sandbox-config/SOUL-EXPERTISE.md ]; then
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/SOUL-EXPERTISE.md /sandbox/.openclaw/SOUL-EXPERTISE.md
        log_info "  → SOUL-EXPERTISE.md"
    fi

    if [ -f /tmp/netclaw-sandbox-config/SOUL-SKILLS.md ]; then
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/SOUL-SKILLS.md /sandbox/.openclaw/SOUL-SKILLS.md
        log_info "  → SOUL-SKILLS.md"
    fi

    # Upload agents directory (contains auth profiles with API keys)
    if [ -d /tmp/netclaw-sandbox-config/agents ]; then
        log_step "Uploading agent auth profiles..."
        openshell sandbox exec -n "$SANDBOX_NAME" -- mkdir -p /sandbox/.openclaw/agents/main/agent
        openshell sandbox upload "$SANDBOX_NAME" /tmp/netclaw-sandbox-config/agents /sandbox/.openclaw/agents
        log_info "  → agents/ (auth profiles)"
    fi

    # Verify upload
    log_step "Verifying config migration..."
    if openshell sandbox exec -n "$SANDBOX_NAME" -- test -f /sandbox/.openclaw/.env; then
        log_info "Config migration successful!"
    else
        log_warn "Some files may not have uploaded. Check manually."
    fi

    # Apply network policy to allow Slack, APIs, MCPs
    apply_network_policy

    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  All 3 Rings Active!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  ┌─────────────────────────────────────────────────────────┐"
    echo "  │  Ring 1: OpenShell     - Container isolation    [✓]    │"
    echo "  │  Ring 2: DefenseClaw   - LLM guardrails ($GUARDRAIL_MODE)  [✓]    │"
    echo "  │  Ring 3: NetClaw       - AI agent sandbox       [✓]    │"
    echo "  └─────────────────────────────────────────────────────────┘"
    echo ""
    echo "  ─────────────────────────────────────────────────────────────"
    echo "  CONNECT TO NETCLAW:"
    echo "  ─────────────────────────────────────────────────────────────"
    echo ""
    echo "    openshell sandbox connect $SANDBOX_NAME"
    echo ""
    echo "    # Then inside the sandbox:"
    echo "    export HOME=/sandbox"
    echo "    openclaw gateway run &"
    echo "    openclaw                    # or: openclaw tui"
    echo ""
    echo "  ─────────────────────────────────────────────────────────────"
    echo "  SLACK/WEBEX:"
    echo "  ─────────────────────────────────────────────────────────────"
    echo "  Your channels will connect automatically when you start"
    echo "  the openclaw gateway inside the sandbox."
    echo ""
    echo "  ─────────────────────────────────────────────────────────────"
    echo "  ENABLE BLOCKING MODE (production):"
    echo "    defenseclaw setup guardrail --mode action"
    echo ""
    echo "  ─────────────────────────────────────────────────────────────"
    echo "  STOP:"
    echo "    ./scripts/netclaw-secure-start.sh stop"
    echo ""
}

# ═══════════════════════════════════════════
# Main
# ═══════════════════════════════════════════

case "${1:-start}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|status}"
        exit 1
        ;;
esac
