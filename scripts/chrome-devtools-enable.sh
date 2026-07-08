#!/usr/bin/env bash
# Enable Chrome DevTools MCP integration for existing NetClaw installations.
#
# This script does NOT install or fork chrome-devtools-mcp itself — it is
# fetched on demand via `npx` (see config/openclaw.json). What it DOES do:
#   1. Check Node.js 18+ is present.
#   2. Find a usable Chrome/Chromium binary, or provision one deterministically
#      via `@puppeteer/browsers` (the same cross-platform Node-based installer
#      Puppeteer itself uses — works identically on Linux, macOS, and WSL2,
#      no OS package manager, no sudo, no platform-specific branching).
#   3. If a live OpenClaw instance is present, register/patch both
#      chrome-devtools-mcp registrations (headless + Watch Mode) with an
#      explicit --executablePath, then reload the MCP runtime.
#
# Why --executablePath instead of --channel: chrome-devtools-mcp's --channel
# flag looks for Chrome at OS-standard install paths (e.g. /opt/google/chrome
# on Linux). A real-world install can easily have Node/npm but no system
# Chrome at that path (confirmed live on this project — see spec 048's
# post-implementation notes). Pinning --executablePath to a NetClaw-managed,
# deterministically-provisioned binary avoids ever depending on that lookup.
#
# No credentials are ever read, stored, or requested (spec 048, FR-005) —
# target-site authentication happens via a one-time manual sign-in into
# chrome-devtools-mcp's own persistent Chrome profile, not via this script.

set -euo pipefail

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
BROWSER_CACHE_DIR="$HOME/.cache/chrome-devtools-mcp/browsers"
# chrome-devtools-mcp's own default profile path for the stable channel
# (see: npx chrome-devtools-mcp@latest --help). NetClaw does not override
# this — it's already a sensible, cross-platform, zero-config default.
DEFAULT_PROFILE_DIR="$HOME/.cache/chrome-devtools-mcp/chrome-profile"

echo "========================================="
echo "  Chrome DevTools MCP Integration"
echo "  for NetClaw"
echo "========================================="
echo ""
echo "  Source: https://github.com/ChromeDevTools/chrome-devtools-mcp"
echo "  Spawned on demand via: npx -y chrome-devtools-mcp@latest"
echo ""

log_step "1/3 Checking Node.js..."

missing=0

if ! command -v node >/dev/null 2>&1; then
    log_error "Node.js is required (18+)."
    missing=1
else
    node_major="$(node --version | sed -E 's/^v([0-9]+).*/\1/')"
    if [ "$node_major" -lt 18 ]; then
        log_error "Node.js 18+ is required. Found: $(node --version)"
        missing=1
    else
        log_info "Node.js version: $(node --version)"
    fi
fi

if ! command -v npx >/dev/null 2>&1; then
    log_error "npx is required (ships with Node.js 18+)."
    missing=1
fi

if [ "$missing" -eq 1 ]; then
    log_error "Install missing prerequisites and re-run."
    exit 1
fi

log_step "2/3 Finding or provisioning a Chrome/Chromium binary..."

EXECUTABLE_PATH=""

# 1. Prefer a system binary already on PATH (Linux package managers, most
#    common case on a pre-existing dev box).
for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
    if command -v "$candidate" >/dev/null 2>&1; then
        EXECUTABLE_PATH="$(command -v "$candidate")"
        log_info "Found system browser: $EXECUTABLE_PATH"
        break
    fi
done

# 2. macOS app bundle (not on PATH by default).
if [ -z "$EXECUTABLE_PATH" ] && [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ]; then
    EXECUTABLE_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    log_info "Found system browser: $EXECUTABLE_PATH"
fi

# 3. Nothing found — provision one deterministically. This is the same
#    installer Puppeteer itself uses, so it works identically on Linux and
#    macOS (Intel or Apple Silicon) with no OS-specific branching and no sudo.
if [ -z "$EXECUTABLE_PATH" ]; then
    log_warn "No system Chrome/Chromium found. Provisioning a pinned build via @puppeteer/browsers..."
    mkdir -p "$BROWSER_CACHE_DIR"
    install_output="$(npx -y @puppeteer/browsers install chrome@stable --path "$BROWSER_CACHE_DIR" 2>&1 | tail -1)"
    EXECUTABLE_PATH="$(echo "$install_output" | awk '{print $2}')"
    if [ -n "$EXECUTABLE_PATH" ] && [ -x "$EXECUTABLE_PATH" ]; then
        log_info "Provisioned: $EXECUTABLE_PATH"
    else
        log_warn "Automatic provisioning did not return a usable path (output: $install_output)"
        log_warn "chrome-devtools-mcp may still auto-download its own copy on first use, but this is unverified — pass --executablePath manually if it fails."
        EXECUTABLE_PATH=""
    fi
fi

log_step "3/3 Registering with OpenClaw (if a live instance is present)..."

if command -v openclaw >/dev/null 2>&1; then
    if [ -n "$EXECUTABLE_PATH" ]; then
        HEADLESS_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=true\",\"--executablePath=$EXECUTABLE_PATH\"]"
        VISIBLE_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=false\",\"--executablePath=$EXECUTABLE_PATH\"]"
    else
        HEADLESS_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=true\"]"
        VISIBLE_ARGS="[\"-y\",\"chrome-devtools-mcp@latest\",\"--headless=false\"]"
    fi

    if openclaw mcp set chrome-devtools-mcp "{\"command\":\"npx\",\"args\":${HEADLESS_ARGS}}" >/dev/null 2>&1; then
        log_info "Registered chrome-devtools-mcp (headless) with OpenClaw"
    else
        log_warn "Could not register chrome-devtools-mcp via 'openclaw mcp set' — register it manually (see mcp-servers/chrome-devtools-mcp/README.md)"
    fi

    if openclaw mcp set chrome-devtools-mcp-visible "{\"command\":\"npx\",\"args\":${VISIBLE_ARGS}}" >/dev/null 2>&1; then
        log_info "Registered chrome-devtools-mcp-visible (Watch Mode) with OpenClaw"
    else
        log_warn "Could not register chrome-devtools-mcp-visible via 'openclaw mcp set' — register it manually"
    fi

    openclaw mcp reload >/dev/null 2>&1 || true
    log_info "Reloaded MCP runtime cache. Run 'openclaw gateway restart' to pick this up fully."
else
    log_warn "openclaw CLI not found on PATH — skipping live registration."
    log_info "Once OpenClaw is installed, register manually or re-run this script."
    if [ -n "$EXECUTABLE_PATH" ]; then
        log_info "Use this --executablePath: $EXECUTABLE_PATH"
    fi
fi

echo ""
echo "Chrome DevTools MCP integration is ready."
echo ""
echo "No credentials are stored or required by this integration, and there is no"
echo ".env to configure. The persistent Chrome profile lives at:"
echo ""
echo "  $DEFAULT_PROFILE_DIR"
echo ""
echo "Complete a one-time manual sign-in per target site using ONE of these patterns"
echo "(both use the same default profile path above, so the automated headless"
echo "registration picks up the signed-in session automatically):"
echo ""
echo "  Pattern A — this host has a display (desktop Linux, macOS, or WSL2 with WSLg):"
echo "    npx chrome-devtools-mcp@latest --headless=false${EXECUTABLE_PATH:+ --executablePath=\"$EXECUTABLE_PATH\"}"
echo "    (sign in in the visible window, then close it — normal headless use resumes automatically)"
echo "    Or, once registered, just ask NetClaw to \"watch\" a task — see Watch Mode in"
echo "    workspace/skills/browser-gui-inspect/SKILL.md."
echo ""
echo "  Pattern B — this host is headless/has no display (remote server, WSL2 without WSLg):"
echo "    1. On your own workstation:"
echo "       google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-devtools-signin-profile"
echo "    2. Tunnel that port to this host:"
echo "       ssh -R 9222:localhost:9222 <this-host>"
echo "    3. Sign in in that local, visible Chrome window."
echo "    4. Point this host's chrome-devtools-mcp at the tunnel for that session:"
echo "       npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222"
echo "    (Pattern B uses its own temporary profile, not the shared default — see"
echo "    mcp-servers/chrome-devtools-mcp/README.md if you need it to persist too.)"
echo ""
echo "Next steps:"
echo "  1. If registration above didn't run automatically, restart the OpenClaw gateway."
echo "  2. Verify with: openclaw mcp status"
echo "  3. Try: browser-viz-verify against any generated visualization HTML file"
echo "     (no sign-in needed — it never touches an external site)."
echo ""
