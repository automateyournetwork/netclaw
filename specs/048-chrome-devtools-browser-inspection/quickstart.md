# Quickstart: Chrome DevTools Browser Automation & Inspection Skill

**Feature**: 048-chrome-devtools-browser-inspection
**Date**: 2026-07-07

## Prerequisites

1. Node.js 18+ on the NetClaw host
2. A Chrome/Chromium binary — the enable script (below) finds one or provisions one automatically; no manual install required
3. For `browser-gui-inspect` against any authenticated site: the ability to reach that site's login/SSO flow at least once, interactively

Note: `chrome-devtools-mcp` takes all of its configuration as CLI flags, not environment variables (verified directly against its source) — there is no `.env` to fill in for this integration.

## Setup

### 1. Run the enable script

```bash
./scripts/chrome-devtools-enable.sh
```

This checks Node.js 18+, then finds a usable Chrome/Chromium binary — checking `PATH` and the macOS app bundle first, and if nothing is found, provisioning a pinned build via `npx @puppeteer/browsers install chrome@stable` (the same cross-platform installer Puppeteer uses — no OS package manager, no sudo, works identically on Linux/macOS/WSL2). It then registers both `chrome-devtools-mcp` and `chrome-devtools-mcp-visible` with an explicit `--executablePath` on any live OpenClaw instance it finds, and reloads the MCP runtime. The tool's own default persistent profile path:

```
~/.cache/chrome-devtools-mcp/chrome-profile
```

No `.env` values are written — there's nothing for this integration to configure that way. This script is idempotent — safe to re-run any time.

### 2. Register in `openclaw.json`

Added to `config/openclaw.json` under `mcpServers` — **two** registrations, headless (default) and headed (Watch Mode, FR-015):

```json
{
  "chrome-devtools-mcp": {
    "command": "npx",
    "args": [
      "-y",
      "chrome-devtools-mcp@latest",
      "--headless=true"
    ]
  },
  "chrome-devtools-mcp-visible": {
    "command": "npx",
    "args": [
      "-y",
      "chrome-devtools-mcp@latest",
      "--headless=false"
    ]
  }
}
```

On a live OpenClaw instance (not the repo's reference file), register both with `openclaw mcp set chrome-devtools-mcp '{...}'` and `openclaw mcp set chrome-devtools-mcp-visible '{...}'`, then `openclaw mcp reload` and `openclaw gateway restart`.

The single `--headless=true` flag is the only thing NetClaw pins; everything else (including the persistent profile path above) uses the tool's own defaults.

### 3. One-time interactive sign-in per target site (only needed for `browser-gui-inspect` against authenticated sites — skip entirely for `browser-viz-verify`)

**Pattern A — NetClaw host has a display** (desktop Linux, or WSL2 with WSLg):

```bash
npx chrome-devtools-mcp@latest --headless=false
```

A visible Chrome window opens using the default persistent profile. Sign into the target site (complete MFA/SSO as needed), then close it — the session cookies persist in that same profile directory, which the headless automated registration also uses.

**Pattern B — headless/no-display host** (remote server, or WSL2 without WSLg):

On your own workstation (which has a display):
```bash
google-chrome --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-devtools-signin-profile
```

Tunnel that port to the NetClaw host:
```bash
ssh -R 9222:localhost:9222 <netclaw-host>
```

Sign into the target site in that local, visible Chrome window. Then, on the NetClaw host, point the MCP registration at the tunnel for that session:
```bash
npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222
```

(Chrome 144+ supports `--autoConnect` as a simpler alternative to `--browserUrl` — see `research.md` R3.)

## Usage Examples

Once registered:

- *(automatic, via `threejs-network-viz` or similar)* — "Verify the topology visualization you just generated actually rendered." → `browser-viz-verify`
- "Pull the bridge domain list from the ACI tenant page in APIC — the API doesn't expose it the way I need." → `browser-gui-inspect`
- "Load the Meraki dashboard's client list page and tell me what API calls it makes when I filter by SSID." → `browser-gui-inspect` with `capture: ["network_requests"]`
- "Open the ONOS GUI topology view and tell me how many devices it shows." → `browser-gui-inspect`
- "Watch it log into the NetBox demo and create a new site." → `browser-gui-inspect`, Watch Mode (`chrome-devtools-mcp-visible`) — see Watch Mode below

## Watch Mode (FR-015: headless AND headed, per request)

`chrome-devtools-mcp` is registered **twice**: `chrome-devtools-mcp` (`--headless=true`, default) and `chrome-devtools-mcp-visible` (`--headless=false`, Watch Mode). This is a per-request choice, not a fixed setting — when an operator's phrasing signals they want to see it happen ("watch", "show me"), `browser-gui-inspect` uses `chrome-devtools-mcp-visible`'s tools for the whole request instead of the default headless server. A real Chrome window opens wherever NetClaw's host process runs — on a Mac or Linux desktop it's simply on that screen, on WSL2 with WSLg it renders as a native Windows window. This is not platform-specific code; it's the same `--headless=false` flag everywhere a display is reachable.

**Try it via Slack**, against the public NetBox demo sandbox (no credentials needed — publicly published demo login on the site's own login page):

```
@NetClaw watch it log into https://demo.netbox.dev/ and create a new site called "Test Site 1"
```

Expect: a visible Chrome window opens (Watch Mode), navigates to the NetBox demo login page, signs in, opens the Sites section, creates the new site with the requested name, and reports back with a screenshot of the created site.

## Verification

1. `browser-viz-verify` against a known-good visualization file → expect `verdict: "rendered_clean"` and a screenshot artifact. **Validated live during implementation** (T024): a `file://` fixture with no script errors produced zero console messages via `list_console_messages`.
2. `browser-viz-verify` against a deliberately broken HTML file (e.g., a bad script `src`) → expect `verdict: "rendered_with_errors"` with the console error text included. **Validated live during implementation** (T024): a fixture with a missing script and a thrown error produced exactly two console error entries (`net::ERR_FILE_NOT_FOUND` and the thrown error's message), and `list_network_requests` independently confirmed the failed resource load.
3. `browser-gui-inspect` against a site with an intentionally expired/absent session in the profile → expect `status: "sign_in_required"`, not a silent empty result.
4. `browser-gui-inspect` against an authenticated dashboard (after completing sign-in via Pattern A or B) → expect the requested information returned without any credential prompt reaching NetClaw.
5. Confirm DefenseClaw's audit log (`~/.defenseclaw/audit.db`) records these tool calls like any other MCP tool (Research R5) — only meaningful if running in `defenseclaw` security mode.
