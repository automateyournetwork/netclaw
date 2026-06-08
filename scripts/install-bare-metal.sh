#!/usr/bin/env bash
# NetClaw Bare-Metal Installation (Non-Interactive)
#
# Reads all configuration from .env — no interactive prompts.
# Installs prerequisites, MCP servers, deploys workspace, configures OpenClaw.
#
# Usage:
#   cp .env.example .env && nano .env   # set your API keys
#   ./scripts/install-bare-metal.sh
#
# After install:
#   openclaw gateway    # terminal 1
#   openclaw tui        # terminal 2

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${CYAN}[STEP]${NC} $1"; }

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$NETCLAW_DIR/.env"

echo "========================================="
echo "  NetClaw - Bare-Metal Install"
echo "  Non-Interactive (reads from .env)"
echo "========================================="
echo ""
echo "  Project: $NETCLAW_DIR"
echo ""

# ═══════════════════════════════════════════
# Load .env
# ═══════════════════════════════════════════

if [ ! -f "$ENV_FILE" ]; then
    log_error ".env file not found at $ENV_FILE"
    log_error "Copy .env.example to .env and configure it first:"
    echo "  cp $NETCLAW_DIR/.env.example $NETCLAW_DIR/.env"
    echo "  nano $NETCLAW_DIR/.env"
    exit 1
fi

set -a
source "$ENV_FILE"
set +a
log_info "Loaded .env from $ENV_FILE"

# Detect AI provider from env
AI_PROVIDER=""
if [ -n "${OLLAMA_API_KEY:-}" ]; then
    AI_PROVIDER="ollama"
elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then
    AI_PROVIDER="anthropic"
elif [ -n "${OPENAI_API_KEY:-}" ]; then
    AI_PROVIDER="openai"
fi

if [ -z "$AI_PROVIDER" ]; then
    log_error "No AI provider API key found in .env"
    log_error "Set one of: OLLAMA_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY"
    exit 1
fi
log_info "AI provider: $AI_PROVIDER"

# ═══════════════════════════════════════════
# Step 1: System Prerequisites
# ═══════════════════════════════════════════

log_step "1/8 Installing system prerequisites..."

if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3 python3-pip python3-venv python3-dev \
        git curl ca-certificates tshark nmap graphviz \
        openssh-client sshpass build-essential \
        2>&1 | tail -5
    # Docker — install only if not already present
    if ! command -v docker &> /dev/null; then
        sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io 2>&1 | tail -5
    else
        log_info "Docker already installed: $(docker --version)"
    fi
    log_info "System packages installed"
else
    log_warn "Not a Debian/Ubuntu system — install prerequisites manually"
fi

# Node.js via nvm
if ! command -v node &> /dev/null; then
    log_info "Installing Node.js via nvm..."
    export NVM_DIR="$HOME/.nvm"
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash
    . "$NVM_DIR/nvm.sh"
    nvm install 24
    nvm alias default 24
    log_info "Node.js $(node --version) installed"
else
    log_info "Node.js $(node --version) already installed"
fi

# uv/uvx
if ! command -v uvx &> /dev/null; then
    log_info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo ""

# ═══════════════════════════════════════════
# Step 2: Python Virtual Environment
# ═══════════════════════════════════════════

log_step "2/8 Setting up Python virtual environment..."

VENV_DIR="$NETCLAW_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    log_info "Created venv at $VENV_DIR"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q

# Install core Python dependencies
pip install -r "$NETCLAW_DIR/requirements.txt" -q 2>/dev/null || {
    log_warn "Some pip dependencies failed — continuing"
}

# Install MCP servers that need pip install
cd "$NETCLAW_DIR"
for pkg_dir in mcp-servers/mcp-nvd mcp-servers/junos-mcp-server mcp-servers/fwrule-mcp \
               mcp-servers/mempalace mcp-servers/AAP-Enterprise-MCP-Server; do
    if [ -d "$pkg_dir" ]; then
        pip install -e "$pkg_dir" -q 2>/dev/null || log_warn "Failed: $pkg_dir"
    fi
done
pip install gait-ai -q 2>/dev/null || log_warn "gait-ai install failed"
pip install -r mcp-servers/nautobot-mcp-v2/requirements.txt -q 2>/dev/null || true

log_info "Python dependencies installed"
echo ""

# ═══════════════════════════════════════════
# Step 3: Node.js MCP Servers
# ═══════════════════════════════════════════

log_step "3/8 Building Node.js MCP servers..."

# Markmap
if [ -d "mcp-servers/markmap_mcp/markmap-mcp" ]; then
    cd mcp-servers/markmap_mcp/markmap-mcp && npm install -q && npm run build -q && cd "$NETCLAW_DIR"
    log_info "Markmap MCP built"
fi

# Pre-cache npx packages
npm cache add @drawio/mcp @mjpitz/mcp-rfc @anthropic-ai/microsoft-graph-mcp 2>/dev/null || true

# Proxmox MCP
if [ -d "mcp-servers/mcp-proxmox" ]; then
    cd mcp-servers/mcp-proxmox && npm install -q && cd "$NETCLAW_DIR"
    log_info "Proxmox MCP built"
fi

# Pull GitHub MCP Docker image and start the persistent keeper container
# (single named container + docker exec for stdio; avoids dozens of random containers)
if command -v docker &> /dev/null; then
    docker pull ghcr.io/github/github-mcp-server 2>/dev/null || log_warn "GitHub MCP image pull failed"
    if [ -x "./scripts/ensure-github-mcp.sh" ]; then
        ./scripts/ensure-github-mcp.sh || log_warn "ensure-github-mcp failed (PAT may be missing from env or config)"
    fi
fi

echo ""

# ═══════════════════════════════════════════
# Step 4: Install OpenClaw
# ═══════════════════════════════════════════

log_step "4/8 Installing OpenClaw..."

if command -v openclaw &> /dev/null; then
    log_info "OpenClaw already installed: $(openclaw --version 2>/dev/null || echo 'unknown')"
else
    npm install -g openclaw@latest
    log_info "OpenClaw installed"
fi

echo ""

# ═══════════════════════════════════════════
# Step 5: Configure OpenClaw (non-interactive)
# ═══════════════════════════════════════════

log_step "5/8 Configuring OpenClaw from .env..."

OPENCLAW_DIR="$HOME/.openclaw"
mkdir -p "$OPENCLAW_DIR/workspace/skills" "$OPENCLAW_DIR/workspace/testbed" \
         "$OPENCLAW_DIR/agents/main/sessions" "$OPENCLAW_DIR/logs" "$OPENCLAW_DIR/memory"

# Generate openclaw.json from netclaw config + .env auto-detection
python3 - <<'PYCONFIG'
import json, os, re, secrets

netclaw_dir = os.environ.get("NETCLAW_DIR", os.getcwd())
openclaw_home = os.path.expanduser("~/.openclaw")
runtime_path = os.path.join(openclaw_home, "openclaw.json")
netclaw_path = os.path.join(netclaw_dir, "config", "openclaw.json")

# Load netclaw config
with open(netclaw_path) as f:
    netclaw = json.load(f)

runtime = {}

# MCP servers — resolve env vars, skip unconfigured remote servers
raw_servers = netclaw.get("mcpServers", {})
clean_servers = {}
venv_python = os.path.join(netclaw_dir, ".venv", "bin", "python3")

for name, cfg in raw_servers.items():
    url = cfg.get("url", "")
    if "${" in str(url):
        continue
    if url and not url.startswith(("http://", "https://")):
        continue

    # Rewrite /opt/venv/bin/python3 to local venv
    if cfg.get("command") == "/opt/venv/bin/python3":
        cfg["command"] = venv_python

    # Rewrite /opt/netclaw/ paths to local paths
    if "args" in cfg:
        cfg["args"] = [a.replace("/opt/netclaw/", netclaw_dir + "/") for a in cfg["args"]]

    # Rewrite /root/.openclaw/ paths to local home
    home_dir = os.path.expanduser("~")
    if "args" in cfg:
        cfg["args"] = [a.replace("/root/.openclaw/", home_dir + "/.openclaw/") for a in cfg["args"]]

    # Resolve env vars
    env = cfg.get("env", {})
    resolved_env = {}
    for key, val in env.items():
        if isinstance(val, str) and "${" in val:
            m = re.match(r'^\$\{([^:}]+):-([^}]*)\}$', val)
            if m:
                resolved_env[key] = os.environ.get(m.group(1), m.group(2))
                continue
            m = re.match(r'^\$\{([^}]+)\}$', val)
            if m:
                env_val = os.environ.get(m.group(1), "")
                if env_val:
                    resolved_env[key] = env_val
                continue
        else:
            resolved_env[key] = val
    # Rewrite Docker paths in resolved env values
    for key, val in resolved_env.items():
        if isinstance(val, str):
            val = val.replace("/opt/netclaw/", netclaw_dir + "/")
            val = val.replace("/root/.openclaw/", home_dir + "/.openclaw/")
            resolved_env[key] = val
    if resolved_env:
        cfg["env"] = resolved_env
    elif "env" in cfg:
        del cfg["env"]
    clean_servers[name] = cfg

runtime["mcp"] = {"servers": clean_servers}

# Commands
if "commands" in netclaw:
    runtime["commands"] = netclaw["commands"]

# AI provider auto-config
defaults = runtime.setdefault("agents", {}).setdefault("defaults", {})

if os.environ.get("OLLAMA_API_KEY"):
    model_id = os.environ.get("NETCLAW_MODEL", "qwen3.5:397b-cloud")
    base_url = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")
    defaults["model"] = {"primary": f"ollama/{model_id}"}
    cloud_models = []
    for mid in ["kimi-k2.5:cloud", "qwen3.5:cloud", "qwen3.5:397b-cloud",
                 "minimax-m2.7:cloud", "glm-5.1:cloud"]:
        cloud_models.append({
            "id": mid, "name": mid, "reasoning": False,
            "input": ["text", "image"] if "kimi" in mid else ["text"],
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
            "contextWindow": 128000, "maxTokens": 8192,
        })
    runtime["models"] = {"mode": "merge", "providers": {
        "ollama": {"baseUrl": base_url, "api": "ollama",
                   "apiKey": os.environ["OLLAMA_API_KEY"], "models": cloud_models}
    }}
    runtime["auth"] = {"profiles": {"ollama:default": {"provider": "ollama", "mode": "api_key"}}}
    runtime["plugins"] = {"entries": {"ollama": {"enabled": True}, "openai": {"enabled": True}}}
    print(f"[config] AI provider: ollama (model: {model_id})")

elif os.environ.get("ANTHROPIC_API_KEY"):
    model_id = os.environ.get("NETCLAW_MODEL", "claude-sonnet-4-6")
    defaults["model"] = {"primary": f"anthropic/{model_id}"}
    defaults["params"] = {"cacheRetention": "long"}
    runtime["models"] = {"mode": "merge", "providers": {
        "anthropic": {"api": "anthropic-messages", "baseUrl": "https://api.anthropic.com",
                      "apiKey": os.environ["ANTHROPIC_API_KEY"], "models": [
            {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "reasoning": False,
             "input": ["text", "image"],
             "cost": {"input": 3.0, "output": 15.0, "cacheRead": 0.30, "cacheWrite": 3.75},
             "contextWindow": 200000, "maxTokens": 16384}
        ]}
    }}
    runtime["auth"] = {"profiles": {"anthropic:default": {"provider": "anthropic", "mode": "api_key"}}}
    print(f"[config] AI provider: anthropic (model: {model_id}, cacheRetention: long)")

elif os.environ.get("OPENAI_API_KEY"):
    model_id = os.environ.get("NETCLAW_MODEL", "gpt-4o")
    defaults["model"] = {"primary": f"openai/{model_id}"}
    runtime["models"] = {"mode": "merge", "providers": {
        "openai": {"api": "openai-responses", "baseUrl": "https://api.openai.com/v1",
                   "apiKey": os.environ["OPENAI_API_KEY"], "models": []}
    }}
    runtime["auth"] = {"profiles": {"openai:default": {"provider": "openai", "mode": "api_key"}}}
    print(f"[config] AI provider: openai (model: {model_id})")

# Gateway
runtime.setdefault("gateway", {})
runtime["gateway"]["mode"] = "local"
runtime["gateway"]["port"] = 18789
if "auth" not in runtime.get("gateway", {}):
    runtime["gateway"]["auth"] = {"mode": "token", "token": secrets.token_hex(24)}

# Workspace
defaults["workspace"] = os.path.join(openclaw_home, "workspace")

# Discord channel from env
channels = {}
discord_token = os.environ.get("DISCORD_BOT_TOKEN")
if discord_token:
    channels["discord"] = {"enabled": True, "token": discord_token, "groupPolicy": "open"}
    print("[config] Discord channel enabled")

slack_token = os.environ.get("SLACK_BOT_TOKEN")
slack_app_token = os.environ.get("SLACK_APP_TOKEN")
if slack_token and slack_app_token:
    channels["slack"] = {"enabled": True, "botToken": slack_token, "appToken": slack_app_token}
    print("[config] Slack channel enabled")

if channels:
    runtime["channels"] = channels

with open(runtime_path, "w") as f:
    json.dump(runtime, f, indent=2)

mcp_count = len(clean_servers)
print(f"[config] openclaw.json written — {mcp_count} MCP servers")
PYCONFIG

echo ""

# ═══════════════════════════════════════════
# Step 6: Deploy Workspace
# ═══════════════════════════════════════════

log_step "6/8 Deploying workspace files..."

WORKSPACE="$OPENCLAW_DIR/workspace"

# Deploy skills
cp -r "$NETCLAW_DIR/workspace/skills/"* "$WORKSPACE/skills/"
SKILL_COUNT=$(ls -d "$WORKSPACE/skills/"*/ 2>/dev/null | wc -l)
log_info "Deployed $SKILL_COUNT skills"

# Deploy workspace markdown files from workspace/personality/ and workspace/user/
for md in SOUL.md SOUL-SKILLS.md SOUL-EXPERTISE.md AGENTS.md IDENTITY.md HEARTBEAT.md CLAUDE.md; do
    if [ -f "$NETCLAW_DIR/workspace/personality/$md" ]; then
        cp "$NETCLAW_DIR/workspace/personality/$md" "$WORKSPACE/$md"
    fi
done
for md in USER.md TOOLS.md; do
    if [ -f "$NETCLAW_DIR/workspace/user/$md" ]; then
        cp "$NETCLAW_DIR/workspace/user/$md" "$WORKSPACE/$md"
    fi
done
log_info "Deployed workspace files"

# Symlink testbed
mkdir -p "$WORKSPACE/testbed"
ln -sf "$NETCLAW_DIR/testbed/testbed.yaml" "$WORKSPACE/testbed/testbed.yaml"

# Write env vars for MCP script paths
OPENCLAW_ENV="$OPENCLAW_DIR/.env"
[ -f "$OPENCLAW_ENV" ] || touch "$OPENCLAW_ENV"

_set_env() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$OPENCLAW_ENV"
    else
        echo "${key}=${val}" >> "$OPENCLAW_ENV"
    fi
}

_set_env "PYATS_TESTBED_PATH" "$WORKSPACE/testbed/testbed.yaml"
_set_env "PYATS_MCP_SCRIPT" "$NETCLAW_DIR/mcp-servers/pyATS_MCP/pyats_mcp_server.py"
_set_env "MCP_CALL" "$NETCLAW_DIR/scripts/mcp-call.py"

# Merge credentials from project .env into OpenClaw .env
while IFS= read -r line; do
    [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
    key="${line%%=*}"
    if grep -q "^${key}=" "$OPENCLAW_ENV" 2>/dev/null; then
        sed -i "s|^${key}=.*|${line}|" "$OPENCLAW_ENV"
    else
        echo "$line" >> "$OPENCLAW_ENV"
    fi
done < "$ENV_FILE"
log_info "Merged .env credentials into OpenClaw"

echo ""

# ═══════════════════════════════════════════
# Step 7: Visual HUD (optional)
# ═══════════════════════════════════════════

log_step "7/8 Building Visual HUD..."

if [ -d "$NETCLAW_DIR/ui/netclaw-visual" ]; then
    cd "$NETCLAW_DIR/ui/netclaw-visual"
    npm install -q 2>/dev/null
    npm run build -q 2>/dev/null || log_warn "HUD build failed — run manually: cd ui/netclaw-visual && npm run dev"
    cd "$NETCLAW_DIR"
    log_info "Visual HUD built"
else
    log_warn "Visual HUD not found"
fi

echo ""

# ═══════════════════════════════════════════
# Step 8: Verify
# ═══════════════════════════════════════════

log_step "8/8 Verifying installation..."

CHECKS_OK=0
CHECKS_FAIL=0

_check() {
    local name="$1" cmd="$2"
    if eval "$cmd" &>/dev/null; then
        log_info "$name: OK"
        CHECKS_OK=$((CHECKS_OK + 1))
    else
        log_warn "$name: FAILED"
        CHECKS_FAIL=$((CHECKS_FAIL + 1))
    fi
}

_check "OpenClaw" "command -v openclaw"
_check "Python venv" "[ -f $VENV_DIR/bin/python3 ]"
_check "Node.js" "command -v node"
_check "openclaw.json" "[ -f $OPENCLAW_DIR/openclaw.json ]"
_check "Skills deployed" "[ -d $WORKSPACE/skills/golden-config-bootstrap ]"
_check "SOUL.md" "[ -f $WORKSPACE/SOUL.md ]"
_check "pyATS MCP" "[ -f $NETCLAW_DIR/mcp-servers/pyATS_MCP/pyats_mcp_server.py ]"
_check "Nautobot MCP v2" "[ -f $NETCLAW_DIR/mcp-servers/nautobot-mcp-v2/server.py ]"
_check "Docker" "command -v docker"

echo ""
log_info "Verification: $CHECKS_OK OK, $CHECKS_FAIL FAILED"

echo ""
echo "========================================="
echo "  NetClaw Bare-Metal Install Complete"
echo "========================================="
echo ""
echo "  AI Provider: $AI_PROVIDER"
echo "  Workspace:   $WORKSPACE"
echo "  Skills:      $SKILL_COUNT"
echo "  Config:      $OPENCLAW_DIR/openclaw.json"
echo ""
echo "  To start:"
echo "    source $VENV_DIR/bin/activate"
echo "    openclaw gateway          # terminal 1"
echo "    openclaw tui              # terminal 2"
echo ""
echo "  Visual HUD (optional):"
echo "    cd $NETCLAW_DIR/ui/netclaw-visual && npm run dev"
echo ""
echo "  Reconfigure:"
echo "    nano $NETCLAW_DIR/.env && ./scripts/install-bare-metal.sh"
echo ""
