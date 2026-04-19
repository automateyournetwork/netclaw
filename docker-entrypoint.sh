#!/bin/bash
set -e

# Ensure venv is on PATH inside the container
export PATH="/opt/venv/bin:$PATH"

NETCLAW_DIR="/opt/netclaw"
OPENCLAW_HOME="${OPENCLAW_HOME:-/data/openclaw}"
OPENCLAW_CONFIG_DIR="$HOME/.openclaw"
WORKSPACE="$OPENCLAW_CONFIG_DIR/workspace"
FIRST_BOOT_MARKER="$OPENCLAW_CONFIG_DIR/.initialized"

mkdir -p "$WORKSPACE/skills" "$WORKSPACE/testbed" "$OPENCLAW_CONFIG_DIR/agents/main/sessions" \
         "$OPENCLAW_CONFIG_DIR/logs" "$OPENCLAW_CONFIG_DIR/memory"

# --- Deploy skills (baked into image, always fresh) ---
cp -r "$NETCLAW_DIR/workspace/skills/"* "$WORKSPACE/skills/"

# --- Deploy workspace files ---
# User overrides (from ./workspace-override/) take priority.
# Fall back to the defaults baked into the image.
for md in SOUL.md SOUL-SKILLS.md SOUL-EXPERTISE.md AGENTS.md IDENTITY.md USER.md TOOLS.md CLAUDE.md; do
    if [ -f "/workspace-override/$md" ]; then
        cp "/workspace-override/$md" "$WORKSPACE/$md"
    elif [ -f "$NETCLAW_DIR/workspace-override.example/$md" ]; then
        cp "$NETCLAW_DIR/workspace-override.example/$md" "$WORKSPACE/$md"
    fi
done

# --- Symlink testbed ---
if [ -f "/workspace-override/testbed.yaml" ]; then
    ln -sf "/workspace-override/testbed.yaml" "$WORKSPACE/testbed/testbed.yaml"
else
    ln -sf "$NETCLAW_DIR/testbed/testbed.yaml" "$WORKSPACE/testbed/testbed.yaml"
fi

# --- Build openclaw.json ---
# This is the core fix: always merge mcpServers from netclaw's config into
# whatever openclaw.json exists (whether from onboard or from scratch).
# On first boot with no prior onboard, we build a working config from .env.
python3 - <<'PYMERGE'
import json, os

openclaw_home = os.path.expanduser("~/.openclaw")
netclaw_dir = os.environ.get("NETCLAW_DIR", "/opt/netclaw")
runtime_path = os.path.join(openclaw_home, "openclaw.json")
netclaw_path = os.path.join(netclaw_dir, "config", "openclaw.json")
os.makedirs(openclaw_home, exist_ok=True)

# Start with runtime config if it exists (preserves onboard choices)
runtime = {}
if os.path.exists(runtime_path):
    with open(runtime_path) as f:
        runtime = json.load(f)

# Load netclaw config (has mcpServers + tokenOptimization + commands)
with open(netclaw_path) as f:
    netclaw = json.load(f)

# Always overwrite MCP servers from netclaw config (authoritative source)
# OpenClaw uses mcp.servers, not mcpServers
# 1. Strip servers with unresolved ${VAR} in url fields
# 2. Resolve ${VAR} and ${VAR:-default} in env blocks against real environment
import re
raw_servers = netclaw.get("mcpServers", {})
clean_servers = {}
for name, cfg in raw_servers.items():
    url = cfg.get("url", "")
    if "${" in str(url):
        continue  # skip unconfigured remote MCP servers
    if url and not url.startswith(("http://", "https://")):
        continue  # skip mcp:// and other non-http URLs this version doesn't support
    # Resolve env var references in the env block
    env = cfg.get("env", {})
    resolved_env = {}
    for key, val in env.items():
        if isinstance(val, str) and "${" in val:
            # ${VAR:-default} pattern
            m = re.match(r'^\$\{([^:}]+):-([^}]*)\}$', val)
            if m:
                resolved_env[key] = os.environ.get(m.group(1), m.group(2))
                continue
            # ${VAR} pattern
            m = re.match(r'^\$\{([^}]+)\}$', val)
            if m:
                env_val = os.environ.get(m.group(1), "")
                if env_val:
                    resolved_env[key] = env_val
                continue
        else:
            resolved_env[key] = val
    if resolved_env:
        cfg["env"] = resolved_env
    elif "env" in cfg:
        del cfg["env"]
    clean_servers[name] = cfg
runtime["mcp"] = {"servers": clean_servers}
skipped = len(raw_servers) - len(clean_servers)
if skipped:
    print(f"[entrypoint] Skipped {skipped} MCP servers with unconfigured URLs")

# Merge commands if netclaw defines them
if "commands" in netclaw:
    runtime["commands"] = netclaw["commands"]

# -- Auto-configure model from env if no onboard has run --
if "models" not in runtime or "auth" not in runtime:
    # Check for common AI provider env vars and configure accordingly
    provider = None
    defaults = runtime.setdefault("agents", {}).setdefault("defaults", {})

    if os.environ.get("OLLAMA_API_KEY"):
        provider = "ollama"
        model_id = os.environ.get("NETCLAW_MODEL", "qwen3.5:397b-cloud")
        base_url = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")
        defaults["model"] = {
            "primary": f"ollama/{model_id}",
        }
        # Ollama Cloud provides a model catalog - define known cloud models
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
            "ollama": {
                "baseUrl": base_url, "api": "ollama",
                "apiKey": os.environ["OLLAMA_API_KEY"],
                "models": cloud_models,
            }
        }}
        runtime["auth"] = {"profiles": {"ollama:default": {"provider": "ollama", "mode": "api_key"}}}
        runtime["plugins"] = {"entries": {"ollama": {"enabled": True}, "openai": {"enabled": True}}}

    elif os.environ.get("ANTHROPIC_API_KEY"):
        provider = "anthropic"
        model_id = os.environ.get("NETCLAW_MODEL", "claude-sonnet-4-20250514")
        defaults["model"] = {"primary": f"anthropic/{model_id}"}
        runtime["models"] = {"mode": "merge", "providers": {
            "anthropic": {"api": "anthropic", "apiKey": os.environ["ANTHROPIC_API_KEY"]}
        }}
        runtime["auth"] = {"profiles": {"anthropic:default": {"provider": "anthropic", "mode": "api_key"}}}

    elif os.environ.get("OPENAI_API_KEY"):
        provider = "openai"
        model_id = os.environ.get("NETCLAW_MODEL", "gpt-4o")
        defaults["model"] = {"primary": f"openai/{model_id}"}
        runtime["models"] = {"mode": "merge", "providers": {
            "openai": {"api": "openai", "apiKey": os.environ["OPENAI_API_KEY"]}
        }}
        runtime["auth"] = {"profiles": {"openai:default": {"provider": "openai", "mode": "api_key"}}}

    elif os.environ.get("AWS_ACCESS_KEY_ID") and os.environ.get("BEDROCK_MODEL_ID"):
        provider = "bedrock"
        model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-sonnet-4-20250514-v1:0")
        defaults["model"] = {"primary": f"bedrock/{model_id}"}

    if provider:
        print(f"[entrypoint] Auto-configured AI provider: {provider}")
    else:
        print("[entrypoint] WARNING: No AI provider API key found in environment")
        print("[entrypoint]   Set OLLAMA_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, or run:")
        print("[entrypoint]   docker compose exec netclaw openclaw onboard")

# -- Gateway defaults --
runtime.setdefault("gateway", {})
runtime["gateway"].setdefault("mode", "local")
runtime["gateway"].setdefault("port", 18789)
runtime["gateway"]["bind"] = "lan"  # listen on all interfaces inside container

# Auth is required even in local mode - generate a token if none exists
if "auth" not in runtime.get("gateway", {}):
    import secrets
    runtime["gateway"]["auth"] = {
        "mode": "token",
        "token": secrets.token_hex(24)
    }
    print(f"[entrypoint] Generated gateway auth token")

# -- Workspace path --
runtime.setdefault("agents", {}).setdefault("defaults", {})
runtime["agents"]["defaults"]["workspace"] = os.path.join(openclaw_home, "workspace")

# -- Channel auto-config from env --
channels = runtime.get("channels", {})

# Discord
discord_token = os.environ.get("DISCORD_BOT_TOKEN")
if discord_token and "discord" not in channels:
    channels["discord"] = {"enabled": True, "token": discord_token, "groupPolicy": "open"}

# Slack
slack_token = os.environ.get("SLACK_BOT_TOKEN")
slack_app_token = os.environ.get("SLACK_APP_TOKEN")
if slack_token and slack_app_token and "slack" not in channels:
    channels["slack"] = {"enabled": True, "botToken": slack_token, "appToken": slack_app_token}

if channels:
    runtime["channels"] = channels

with open(runtime_path, "w") as f:
    json.dump(runtime, f, indent=2)

mcp_count = len(runtime.get("mcpServers", {}))
print(f"[entrypoint] openclaw.json ready - {mcp_count} MCP servers configured at {runtime_path}")
PYMERGE

# --- Write env vars for MCP script paths ---
ENV_FILE="$OPENCLAW_CONFIG_DIR/.env"
[ -f "$ENV_FILE" ] || touch "$ENV_FILE"

set_env() {
    local key="$1" val="$2"
    if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
        sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
        echo "${key}=${val}" >> "$ENV_FILE"
    fi
}

set_env "PYATS_TESTBED_PATH"      "$WORKSPACE/testbed/testbed.yaml"
set_env "PYATS_MCP_SCRIPT"        "$NETCLAW_DIR/mcp-servers/pyATS_MCP/pyats_mcp_server.py"
set_env "MCP_CALL"                 "$NETCLAW_DIR/scripts/mcp-call.py"
set_env "MARKMAP_MCP_SCRIPT"       "$NETCLAW_DIR/mcp-servers/markmap_mcp/markmap-mcp/dist/index.js"
set_env "GAIT_MCP_SCRIPT"          "$NETCLAW_DIR/scripts/gait-stdio.py"
set_env "NETBOX_MCP_SCRIPT"        "$NETCLAW_DIR/mcp-servers/netbox-mcp-server/src/netbox_mcp_server/server.py"
set_env "SERVICENOW_MCP_SCRIPT"    "$NETCLAW_DIR/mcp-servers/servicenow-mcp/src/servicenow_mcp/cli.py"
set_env "ACI_MCP_SCRIPT"           "$NETCLAW_DIR/mcp-servers/ACI_MCP/aci_mcp/main.py"
set_env "ISE_MCP_SCRIPT"           "$NETCLAW_DIR/mcp-servers/ISE_MCP/src/ise_mcp_server/server.py"
set_env "WIKIPEDIA_MCP_SCRIPT"     "$NETCLAW_DIR/mcp-servers/Wikipedia_MCP/main.py"
set_env "NVD_MCP_SCRIPT"           "$NETCLAW_DIR/mcp-servers/mcp-nvd/mcp_nvd/main.py"
set_env "SUBNET_MCP_SCRIPT"        "$NETCLAW_DIR/mcp-servers/subnet-calculator-mcp/servers/subnetcalculator_mcp.py"
set_env "F5_MCP_SCRIPT"            "$NETCLAW_DIR/mcp-servers/f5-mcp-server/F5MCPserver.py"
set_env "CATC_MCP_SCRIPT"          "$NETCLAW_DIR/mcp-servers/catalyst-center-mcp/catalyst-center-mcp.py"
set_env "PACKET_BUDDY_MCP_SCRIPT"  "$NETCLAW_DIR/mcp-servers/packet-buddy-mcp/server.py"
set_env "NMAP_MCP_SCRIPT"          "$NETCLAW_DIR/mcp-servers/nmap-mcp/server.py"
set_env "PROTOCOL_MCP_SCRIPT"      "$NETCLAW_DIR/mcp-servers/protocol-mcp/server.py"
set_env "CLAB_MCP_SCRIPT"          "$NETCLAW_DIR/mcp-servers/clab-mcp-server/clab_mcp_server.py"
set_env "SDWAN_MCP_SCRIPT"         "$NETCLAW_DIR/mcp-servers/cisco-sdwan-mcp/sdwan_mcp_server.py"
set_env "TTS_MCP_SCRIPT"           "$NETCLAW_DIR/mcp-servers/tts-mcp/server.py"
set_env "MEMPALACE_MCP_SCRIPT"     "$NETCLAW_DIR/mcp-servers/mempalace/mempalace/mcp_server.py"
set_env "FWRULE_MCP_DIR"           "$NETCLAW_DIR/mcp-servers/fwrule-mcp"
set_env "AAP_MCP_DIR"              "$NETCLAW_DIR/mcp-servers/AAP-Enterprise-MCP-Server"
set_env "AAP_MCP_ANSIBLE_SCRIPT"   "$NETCLAW_DIR/mcp-servers/AAP-Enterprise-MCP-Server/ansible.py"
set_env "AAP_MCP_EDA_SCRIPT"       "$NETCLAW_DIR/mcp-servers/AAP-Enterprise-MCP-Server/eda.py"
set_env "AAP_MCP_LINT_SCRIPT"      "$NETCLAW_DIR/mcp-servers/AAP-Enterprise-MCP-Server/ansible-lint.py"
set_env "AAP_MCP_DOCS_SCRIPT"      "$NETCLAW_DIR/mcp-servers/AAP-Enterprise-MCP-Server/redhat_docs.py"

[ -f /usr/local/bin/gtrace ] && set_env "GTRACE_MCP_BIN" "/usr/local/bin/gtrace"

# --- Merge user .env (credentials) into OpenClaw .env ---
if [ -f "/workspace-override/.env" ]; then
    while IFS= read -r line; do
        [[ "$line" =~ ^#.*$ || -z "$line" ]] && continue
        key="${line%%=*}"
        if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
            sed -i "s|^${key}=.*|${line}|" "$ENV_FILE"
        else
            echo "$line" >> "$ENV_FILE"
        fi
    done < "/workspace-override/.env"
    echo "[entrypoint] Merged credentials from /workspace-override/.env"
fi

# --- First boot message ---
if [ ! -f "$FIRST_BOOT_MARKER" ]; then
    echo ""
    echo "========================================="
    echo "  NetClaw - First Boot"
    echo "========================================="
    echo ""
    echo "  The container is ready. Here's how to configure it:"
    echo ""
    echo "  OPTION A: Env-based (headless, recommended for Docker)"
    echo "    1. Set ANTHROPIC_API_KEY (or OPENAI_API_KEY) in .env"
    echo "    2. Set platform credentials in workspace-override/.env"
    echo "    3. Restart: docker compose restart"
    echo ""
    echo "  OPTION B: Interactive wizards"
    echo "    docker compose exec -it netclaw openclaw onboard    # AI provider + channels"
    echo "    docker compose exec -it netclaw /opt/netclaw/scripts/setup.sh  # Platform creds"
    echo ""
    echo "  OPTION C: Chat directly (if API key is already set)"
    echo "    docker compose exec -it netclaw openclaw chat --new"
    echo ""
    touch "$FIRST_BOOT_MARKER"
fi

echo "[entrypoint] OpenClaw home: $OPENCLAW_HOME"
echo "[entrypoint] Workspace: $WORKSPACE"
echo "[entrypoint] Skills: $(ls -d "$WORKSPACE/skills/"*/ 2>/dev/null | wc -l)"

# --- Run command ---
case "${1:-gateway}" in
    gateway)
        echo "[entrypoint] Starting NetClaw Visual HUD on port 3000..."
        cd "$NETCLAW_DIR/ui/netclaw-visual"
        HUD_PORT=3000 node server.js &
        cd "$NETCLAW_DIR"

        # Pre-warm MCP servers in background after gateway starts
        (
            sleep 30  # wait for gateway to be ready
            echo "[entrypoint] Pre-warming MCP servers..."
            python3 - <<'WARMUP'
import json, subprocess, os, sys

config_path = os.path.expanduser("~/.openclaw/openclaw.json")
try:
    with open(config_path) as f:
        cfg = json.load(f)
except:
    sys.exit(0)

servers = cfg.get("mcp", {}).get("servers", {})
init_msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2024-11-05", "capabilities": {},
    "clientInfo": {"name": "warmup", "version": "1.0"}
}}) + "\n"

for name, srv in servers.items():
    cmd = srv.get("command", "")
    args = srv.get("args", [])
    if not cmd or srv.get("url"):
        continue
    try:
        env = dict(os.environ)
        env.update(srv.get("env", {}))
        p = subprocess.Popen(
            [cmd] + args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, env=env, cwd="/opt/netclaw"
        )
        p.stdin.write(init_msg.encode())
        p.stdin.flush()
        p.stdout.readline()  # read response
        p.terminate()
        print(f"  [warmup] {name}: OK")
    except Exception as e:
        print(f"  [warmup] {name}: FAILED ({e})")
print("[entrypoint] MCP warmup complete")
WARMUP
        ) &

        echo "[entrypoint] Starting OpenClaw gateway on port 18789..."
        exec openclaw gateway
        ;;
    tui)
        exec openclaw tui
        ;;
    chat)
        exec openclaw chat --new
        ;;
    setup)
        exec bash "$NETCLAW_DIR/scripts/setup.sh"
        ;;
    onboard)
        exec openclaw onboard --install-daemon
        ;;
    bash|sh)
        exec /bin/bash
        ;;
    *)
        exec "$@"
        ;;
esac
