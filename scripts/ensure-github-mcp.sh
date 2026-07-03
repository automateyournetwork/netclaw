#!/bin/bash
# ensure-github-mcp.sh
#
# Ensures exactly one long-lived container named "github-mcp" exists.
# It runs the GitHub MCP server's HTTP listener as a keeper process
# (so the container stays up). Stdio MCP connections are then obtained
# cheaply via "docker exec -i github-mcp /server/github-mcp-server stdio".
#
# This prevents the "MCP docker explosion" where the OpenClaw/Grok client
# repeatedly does "docker run -i --rm ..." (creating a new random-named
# container every few minutes when it re-initializes MCP stdio transports).
#
# Usage:
#   ./scripts/ensure-github-mcp.sh
#   GITHUB_PERSONAL_ACCESS_TOKEN=xxx ./scripts/ensure-github-mcp.sh
#
# The script will try (in order):
#   1. $GITHUB_PERSONAL_ACCESS_TOKEN from the environment
#   2. The value from config/openclaw.json (github-mcp.env.GITHUB_PERSONAL_ACCESS_TOKEN)
#   3. Fail with instructions

set -euo pipefail

NETCLAW_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG_JSON="$NETCLAW_DIR/config/openclaw.json"
IMAGE="ghcr.io/github/github-mcp-server"
CONTAINER="github-mcp"

log() { echo "[ensure-github-mcp] $*"; }

get_pat() {
    if [ -n "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
        echo "$GITHUB_PERSONAL_ACCESS_TOKEN"
        return 0
    fi

    if [ -f "$CONFIG_JSON" ] && command -v python3 >/dev/null 2>&1; then
        # Use a temp file for the extractor to avoid fragile heredoc+argv passing
        PYTMP=$(mktemp /tmp/extract_pat.XXXXXX.py)
        cat >"$PYTMP" <<'PYCODE'
import json, sys, os
path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CONFIG_JSON", "")
if not path:
    path = "/home/ubuntu/netclaw/config/openclaw.json"
try:
    with open(path) as f:
        cfg = json.load(f)
    pat = (cfg.get("mcp", {})
              .get("servers", {})
              .get("github-mcp", {})
              .get("env", {})
              .get("GITHUB_PERSONAL_ACCESS_TOKEN", ""))
    print(pat)
except Exception:
    pass
PYCODE
        PAT=$(python3 "$PYTMP" "$CONFIG_JSON" 2>/dev/null || true)
        rm -f "$PYTMP" 2>/dev/null || true
        if [ -n "$PAT" ]; then
            echo "$PAT"
            return 0
        fi
    fi

    return 1
}

PAT="$(get_pat || true)"
if [ -z "$PAT" ]; then
    echo "ERROR: No GITHUB_PERSONAL_ACCESS_TOKEN found." >&2
    echo "  Set it in the environment, or ensure it is present in $CONFIG_JSON" >&2
    echo "  under mcp.servers.github-mcp.env.GITHUB_PERSONAL_ACCESS_TOKEN" >&2
    exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker not found in PATH. GitHub MCP requires Docker." >&2
    exit 1
fi

log "Pulling $IMAGE (if needed)..."
docker pull "$IMAGE" >/dev/null 2>&1 || log "pull failed or not needed; continuing"

# Remove any old/stopped instance with our name so we can recreate cleanly
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

# Also reap any leftover random-named containers from the old "docker run -i --rm" pattern.
# These are the ones that were causing "so many MCP dockers".
for cid in $(docker ps -aq --filter "ancestor=$IMAGE" 2>/dev/null); do
    cname=$(docker inspect -f '{{.Name}}' "$cid" 2>/dev/null | sed 's#^/##')
    if [ "$cname" != "$CONTAINER" ]; then
        docker rm -f "$cid" >/dev/null 2>&1 && log "Reaped old orphan container $cname ($cid)" || true
    fi
done

log "Starting persistent keeper container '$CONTAINER' (http listener)..."
# We run the "http" subcommand as the main process so the container stays alive.
# Individual stdio sessions are obtained on-demand via docker exec (see openclaw.json).
docker run -d \
    --name "$CONTAINER" \
    --restart unless-stopped \
    -e GITHUB_PERSONAL_ACCESS_TOKEN="$PAT" \
    "$IMAGE" http >/dev/null

# Brief wait for it to be healthy/listening
for i in 1 2 3 4 5; do
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
        break
    fi
    sleep 0.5
done

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    log "OK: $CONTAINER is running."
    log "MCP clients should now use: docker exec -i $CONTAINER /server/github-mcp-server stdio"
else
    log "WARNING: container did not stay running. Check: docker logs $CONTAINER"
    exit 1
fi
