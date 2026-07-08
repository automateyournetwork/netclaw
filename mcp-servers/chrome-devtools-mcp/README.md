# Chrome DevTools MCP Server

Official Chrome DevTools team MCP server integration for NetClaw, providing controlled browser automation and inspection — navigation, screenshots, console/network capture, and performance auditing — over a real Chrome instance. NetClaw uses this to verify its own generated visualization outputs, fill gaps in controller skills whose REST APIs don't expose a GUI-only report, discover undocumented vendor APIs, and automate one-off web-GUI interactions. See `workspace/skills/browser-viz-verify/SKILL.md` and `workspace/skills/browser-gui-inspect/SKILL.md` for the operational skills built on top of this server, and `specs/048-chrome-devtools-browser-inspection/` for the full spec, research, and design.

## Server Details

| Property | Value |
|----------|-------|
| Package | [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp) |
| Language | Node.js |
| Publisher | Chrome DevTools team (Google) |
| Transport | stdio (spawned via `npx -y chrome-devtools-mcp@latest`) — registered **twice**, once headless and once headed (see Two Registrations below) |
| Tools | ~50+ upstream; ~20 used by NetClaw's two skills (see contracts) |
| Auth | None — target-site authentication happens via a one-time manual sign-in into a persistent Chrome profile, never via NetClaw |
| Platforms | Any host with Node.js 18+. Headless mode works everywhere, including headless/no-display hosts. Headed/"Watch Mode" works anywhere a display is reachable — a Mac or Linux desktop, a Linux box with WSLg, or any host with an X11/Wayland session — with no OS-specific code; on a genuinely display-less host it will fail to launch and Pattern B (below) is the fallback. |

## Least Privilege (Constitution IX)

This integration's only privilege is the ability to spawn/control a local Chrome process and read/write one designated profile directory on disk. There is no API key, no network credential, and no elevated host permission involved. Access scoping (which sites this can reach) is governed by NetClaw's existing permission-prompt model and DefenseClaw's `tool block` / `tool allow` controls — not a bespoke mechanism in this integration.

## Scope: Read/Observation-Oriented, Not a Config-Change Mechanism

This integration is explicitly scoped to reading, screenshotting, and inspecting pages — never to submitting, applying, or committing configuration changes to network infrastructure via a vendor's web GUI. Doing so would bypass NetClaw's baseline→apply→verify and ServiceNow CR gating that API-based skills already implement correctly (Constitution I/II/III/VIII). Any real configuration change belongs to the relevant API-based skill, not this one. See `specs/048-chrome-devtools-browser-inspection/research.md` R8.

## Configuration

`chrome-devtools-mcp` takes all of its configuration as CLI flags, not environment variables — it does not read `CHROME_DEVTOOLS_*` (or any other) env var for `--headless`/`--userDataDir`/`--channel` (verified directly against its source). There is nothing to set in `.env`. NetClaw's registration pins `--headless=true` for the default server, so it runs headless without asking; everything else uses the tool's own sensible defaults — in particular its built-in persistent profile directory:

```
~/.cache/chrome-devtools-mcp/chrome-profile
```

Two ways to install: `./scripts/install.sh --components chrome-devtools` (the modular installer — this is also part of the `recommended` profile), or the standalone `./scripts/chrome-devtools-enable.sh` (same underlying logic, useful for a repair/re-run outside the full installer flow). Either checks prerequisites, resolves a Chrome binary, and — on a live OpenClaw instance — registers both servers automatically.

### The `--channel` default-path gotcha (and why NetClaw pins `--executablePath` instead)

`--channel=stable` (the tool's default when no channel is given) looks for Chrome at an OS-standard install path — on Linux, `/opt/google/chrome/chrome`. A real host can easily have Node.js/npx without a system Chrome installed at that exact path (confirmed on this project's own dev box: Node was present, but nothing lived at `/opt/google/chrome`). Relying on `--channel` alone is therefore not reliably "universal" the way this feature needs to be.

`scripts/chrome-devtools-enable.sh` resolves this deterministically instead of guessing at OS-standard paths:

1. Look for a system `google-chrome` / `chromium` binary on `PATH` (Linux) or the macOS app bundle.
2. If none is found, provision one via `npx @puppeteer/browsers install chrome@stable --path ~/.cache/chrome-devtools-mcp/browsers` — the same cross-platform, Node-based installer Puppeteer itself uses. No OS package manager, no sudo, identical invocation on Linux, macOS, and WSL2.
3. Register (or re-register) both `chrome-devtools-mcp` and `chrome-devtools-mcp-visible` with an explicit `--executablePath` pointing at whichever binary was found or provisioned — so neither registration ever depends on `--channel`'s path guess.

This runs automatically as part of `scripts/install.sh`, and can be re-run any time (idempotent) via `./scripts/chrome-devtools-enable.sh`.

## Sign-In Patterns

NetClaw never stores, requests, or transmits credentials for any target site (spec 048, FR-005). Instead, sign in once per site, directly in Chrome, using whichever pattern fits your host:

**Pattern A — this host has a display** (desktop Linux, or WSL2 with WSLg):

```bash
npx chrome-devtools-mcp@latest --headless=false
```

Sign in in the visible window (complete MFA/SSO as needed), then close it — the same default profile directory (`~/.cache/chrome-devtools-mcp/chrome-profile`) is what the headless automated registration uses too, so the session carries forward automatically.

**Pattern B — this host is headless / has no display** (remote server, or WSL2 without WSLg):

```bash
# On your own workstation (which has a display):
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-devtools-signin-profile

# Tunnel that port to this host:
ssh -R 9222:localhost:9222 <this-host>

# Sign in in that local, visible Chrome window, then attach this host's
# chrome-devtools-mcp to it for that session instead of launching its own:
npx chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222
```

(Chrome 144+ also supports `--autoConnect` as a simpler alternative to `--browserUrl`.) Pattern B uses whatever profile the workstation's Chrome was launched with — it doesn't automatically merge into this host's default profile — so it's suited to per-session interactive use; for a persistent shared profile on a headless host, run Pattern A's command once with `--executablePath` pointed at a locally installed Chrome/Chromium binary instead.

## Two Registrations: Headless (default) and Watch Mode (headed)

`--headless` is fixed at process-launch time for a given `chrome-devtools-mcp` instance — it can't be flipped mid-session on one running daemon. To give operators a genuine choice per request (rather than one fixed mode for the whole integration), NetClaw registers **two independent MCP servers** from the same package:

| Server ID | Flag | Use |
|-----------|------|-----|
| `chrome-devtools-mcp` | `--headless=true` | Default for `browser-viz-verify` and routine `browser-gui-inspect` calls — no visible window, runs anywhere |
| `chrome-devtools-mcp-visible` | `--headless=false` | "Watch Mode" — a real Chrome window opens wherever NetClaw is running, and you watch it navigate/click/read live |

Both use the tool's own default profile directory (`~/.cache/chrome-devtools-mcp/chrome-profile`) unless told otherwise, so a session signed in via one is usable from the other — with one caveat: Chrome refuses to open the same profile directory from two processes at once. If both registrations are used at the same moment, the second one to start reports a profile-conflict error (see Error Handling) rather than corrupting anything. In practice this is rare — Watch Mode is normally a deliberate, one-off "show me" request, not something run concurrently with background QA checks.

This is not WSL-specific or platform-specific: `--headless=false` just asks Chrome to open a normal window, the same flag, on any OS. Whether that window is actually visible to you depends on where NetClaw's host process runs relative to you — on a Mac or Linux desktop it's simply on your screen; on WSL2 with WSLg it renders as a native Windows window; on a genuinely headless remote server with no display at all, launching headed will fail, and Pattern B below (remote-debugging + SSH tunnel to a display you do have) is the way to get an interactive session instead.

## Registration (openclaw.json)

This is the generic reference shape. `scripts/chrome-devtools-enable.sh` appends a resolved `--executablePath=<path>` to both `args` arrays on your actual host (see the `--channel` gotcha above) — so what lands in your live config will have three args, not two:

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

On a live OpenClaw instance, register (or re-register) with the resolved path baked in:

```bash
openclaw mcp set chrome-devtools-mcp '{"command":"npx","args":["-y","chrome-devtools-mcp@latest","--headless=true","--executablePath=/path/to/chrome"]}'
openclaw mcp set chrome-devtools-mcp-visible '{"command":"npx","args":["-y","chrome-devtools-mcp@latest","--headless=false","--executablePath=/path/to/chrome"]}'
openclaw mcp reload && openclaw gateway restart
```

(`scripts/chrome-devtools-enable.sh` does exactly this for you, automatically.)

## Tool Categories Used by NetClaw

See `specs/048-chrome-devtools-browser-inspection/contracts/mcp-tools.md` for the full breakdown. Summary:

### Navigation & Session
`navigate_page`, `new_page`, `list_pages`, `select_page`, `close_page`, `wait_for`

### Reading & Interacting (read/confirm/search use only — see Scope above)
`take_snapshot`, `take_screenshot`, `click`, `hover`, `fill`, `fill_form`, `drag`, `press_key`, `type_text`, `handle_dialog`, `upload_file`

### Network Inspection
`list_network_requests`, `get_network_request`

### Debugging, Performance & Emulation
`list_console_messages`, `get_console_message`, `evaluate_script` (read-only use), `resize_page`, `emulate`, `performance_start_trace`, `performance_stop_trace`, `performance_analyze_insight`, `lighthouse_audit`

The upstream server also exposes memory/heap-snapshot and extension-management tool categories — these are out of scope for NetClaw's current skills.

## Audit & Access Control

No bespoke audit trail or domain allowlist is built into this integration. It relies entirely on DefenseClaw's existing, tool-agnostic "Tool Call Inspection" and audit logging (documented in `docs/DEFENSECLAW.md`) and its `tool block <tool>` / `tool allow <tool>` controls — the same governance every other MCP server in NetClaw operates under. See `specs/048-chrome-devtools-browser-inspection/research.md` R4/R5.

## Usage Examples

Once registered with an MCP client (OpenClaw, Claude Desktop, etc.):

- "Verify the topology visualization you just generated actually rendered." (`browser-viz-verify`)
- "Pull the bridge domain list from the ACI tenant page in APIC — the API doesn't expose it the way I need." (`browser-gui-inspect`)
- "Load the Meraki dashboard's client list page and tell me what API calls it makes when I filter by SSID." (`browser-gui-inspect`)
- "Open the ONOS GUI topology view and tell me how many devices it shows." (`browser-gui-inspect`)
- "Watch it log into the NetBox demo at https://demo.netbox.dev/ and create a new site." (`browser-gui-inspect`, Watch Mode — uses `chrome-devtools-mcp-visible`, opens a real window you can watch)

## Error Handling

Surfaced (via the skill layer) for:
- **Browser runtime unavailable**: Node.js or a Chrome/Chromium binary missing on the host
- **Sign-in required**: the target page's cached session has expired or was never established
- **Profile conflict**: a concurrent session attempted to use the same persistent profile
- **Navigation timeout**: the page did not finish loading within the bounded wait
- **Blocked**: the target site detected and blocked automated access
- **File not found**: a local file target does not exist at the given path

## Prerequisites

- Node.js 18+ (for `npx`)
- A Chrome/Chromium binary discoverable on the host (or let `chrome-devtools-mcp` auto-download one on first run)
- Run `./scripts/chrome-devtools-enable.sh` for guided first-time setup
