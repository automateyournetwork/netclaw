---
name: desktop-gui-inspect
description: "Full-desktop automation for targets that have no browser and no API at all — a legacy Java-based NMS client, a vendor's Windows-only configuration utility, a terminal emulator with no scriptable interface. Drives OpenClaw's ClawHub computer-use skill (Xvfb+XFCE virtual desktop, xdotool input automation) to read, confirm, or search state in a desktop-only application. Includes a VNC/noVNC Watch Mode so an operator can watch or take over live, the direct desktop analogue of the Chrome DevTools Watch Mode. Never used to submit, apply, or commit a configuration change — that remains the job of the relevant API-based skill."
version: 1.0.0
license: Apache-2.0
tags: [computer-use, desktop-automation, virtual-desktop, gui-gap-fill, xfce, vnc]
metadata:
  { "openclaw": { "requires": { "skills": ["computer-use"], "env": [] } } }
---

# Desktop GUI Inspect Skill

## Purpose

`browser-gui-inspect` (spec 048) fills gaps in web-based controller dashboards NetClaw's API-based skills can't reach. But some legacy network/security tooling has no web GUI *or* API at all — only a native desktop application. Browser automation cannot reach those; this skill can. It drives OpenClaw's own ClawHub `computer-use` skill — a real virtual X11 desktop (Xvfb + XFCE) on this NetClaw host, controlled via `xdotool`-based mouse/keyboard/screenshot scripts — to read, navigate, and confirm state in a desktop-only application.

This skill deliberately contains **no per-application knowledge**. Every invocation is directed by the operator's own `target_application`/`intent` at request time — nothing about any specific legacy tool's UI layout is hardcoded here (Constitution VI — Multi-Vendor Neutrality), the same design principle `browser-gui-inspect` follows. See `specs/050-computer-use-desktop/` for the full spec, research, and design behind this skill.

## Golden Rule — Read/Confirm/Search Only, Never a Config-Change Mechanism

**The underlying desktop actions (click, type, drag, key combinations, scrolling) are for reading, navigating, and confirming state on the virtual desktop — never for submitting, applying, or committing a configuration change to network infrastructure.** If a request would require clicking something like "Apply," "Commit," "Save," or "Deploy" in a legacy tool's configuration workflow, stop and tell the operator that this must go through the relevant API-based skill instead, which implements the proper observe→baseline→modify→verify workflow and ServiceNow CR gating (Constitution I, II, III, VIII). Using this skill to bypass that workflow would create an unaudited, unverified side door around NetClaw's safety model — the same reasoning `browser-gui-inspect` documents for its own interactive tools (see that skill's own Golden Rule, and `specs/048-chrome-devtools-browser-inspection/research.md` R8).

## Underlying Skill

This skill orchestrates OpenClaw's ClawHub `computer-use` skill directly — it is **not** an MCP server. Its actions are individual bash scripts, invoked against a virtual display, documented in `~/.openclaw/skills/computer-use/SKILL.md`:

| Action | Script | Example |
|--------|--------|---------|
| Screenshot | `screenshot.sh` | `./scripts/screenshot.sh` |
| Click (left/right/middle/double/triple) | `click.sh` | `./scripts/click.sh 512 384 left` |
| Type text | `type_text.sh` | `./scripts/type_text.sh "hello"` |
| Key / key combo | `key.sh` | `./scripts/key.sh "ctrl+s"` |
| Scroll | `scroll.sh` | `./scripts/scroll.sh down 5` |
| Drag | `drag.sh` | `./scripts/drag.sh 100 100 400 400` |
| Cropped screenshot | `zoom.sh` | `./scripts/zoom.sh 0 0 512 384` |
| Wait (then screenshot) | `wait.sh` | `./scripts/wait.sh 2` |
| Cursor position | `cursor_position.sh` | `./scripts/cursor_position.sh` |

All actions run against `DISPLAY=:99` (the virtual desktop's display, per the `computer-use` skill's own default). Most action scripts automatically chain a confirmation screenshot onto their own output (e.g. `click.sh`'s last line execs `screenshot.sh`) — a single call to `click.sh`/`type_text.sh`/`key.sh`/etc. returns both a status line and a base64 PNG, so Step 4 of Workflow 1 below is often already satisfied by the action call itself. This skill never installs or modifies the underlying `computer-use` skill's own scripts — it only calls them, per the "no forked upstream code" pattern already used for `chrome-devtools-mcp`.

**Known install quirk**: `openclaw skills install` writes these scripts as non-executable (confirmed live, spec 050 research.md R2) — NetClaw's installer runs `chmod +x` on them automatically. If a manual/out-of-band skill install ever produces "Permission denied" errors, run `chmod +x ~/.openclaw/skills/computer-use/scripts/*.sh` once.

## Configuration

No environment variables — the `computer-use` skill needs no credentials (research.md R6). The virtual desktop and its live-viewing service (VNC on port 5900, noVNC on port 6080) are provisioned once, at install time, via `./scripts/install.sh --components computer-use` (or the equivalent at the time you're reading this) — see `mcp-servers/` is not applicable here; there is no vendored server, only the installer catalog entry in `scripts/lib/catalog.sh` / `scripts/lib/install-steps.sh`.

---

## Workflow 1: Operate a Legacy Desktop-Only Tool (P2)

Use this when an operator needs information from, or a read/confirm interaction with, a desktop-only application that has no browser or API path.

**Input**:
- `intent` (required) — plain-language description of what to read or confirm (e.g., "open the legacy NMS client and tell me the current alarm count")
- `target_application` (optional) — the application name/identifier, if already known

### Step 1: Confirm the virtual desktop is available

Take a screenshot first, always — this is the `computer-use` skill's own documented workflow pattern (Screenshot → Analyze → Act → Screenshot → Repeat):

```
./scripts/screenshot.sh
```

If this fails (virtual desktop not running), stop and return:

```
status: "virtual_desktop_unavailable"
```

### Step 2: Locate or open the target application

Analyze the screenshot for the target application. If it's not already open and needs to be launched, do so via the desktop (e.g., a terminal command through `xfce4-terminal`, or an existing desktop icon/menu). If the application appears to need first-time interactive setup (a license dialog, an initial login) that cannot be completed programmatically, **stop** and return:

```
status: "manual_setup_required"
```

Do not guess or fabricate a result — ask the operator to complete setup via Watch Mode (Workflow 2) instead.

### Step 3: Perform the read/confirm/search actions needed to satisfy `intent`

Using `click`, `type`, `scroll`, `key`, etc. as needed to navigate to the information described in `intent` — e.g., opening a menu, switching a tab, searching a list. Reiterate: these actions are for navigating *to* the information, never for submitting a change (Golden Rule above).

### Step 4: Capture the result

```
./scripts/screenshot.sh
```

Read the relevant value(s) from the screenshot content, using `zoom.sh` on a specific region if the full screenshot is too coarse to read reliably.

### Step 5: Return the result

```
{
  "result": "<the extracted value/text/confirmation answering intent>",
  "screenshot_path": "<path to the captured screenshot>",
  "status": "ok" | "manual_setup_required" | "virtual_desktop_unavailable" | "conflict"
}
```

### Worked Example

> "Open the legacy NMS client and tell me the current alarm count."

1. `screenshot.sh` — confirm the virtual desktop is up.
2. Locate the NMS client icon/window; if not running, launch it via `xfce4-terminal` or the desktop's own launcher.
3. `wait.sh 3` — give the legacy app time to render (many older Java/Swing apps are slow to start).
4. `screenshot.sh` again — read the alarm count directly from the rendered UI, or `zoom.sh` on the specific panel if needed.
5. Report the alarm count back, with the screenshot as supporting evidence.

---

## Workflow 2: Watch Mode via Live Viewer (P3)

Use this when the operator wants to watch NetClaw operate the virtual desktop live, or wants to take over manually (e.g. to complete a `manual_setup_required` step from Workflow 1) — the desktop analogue of `browser-gui-inspect`'s Chrome DevTools Watch Mode.

Unlike the browser skill, there is no headless/headed *choice* to make here — Xvfb is inherently a virtual display with no physical monitor, so NetClaw always "operates headless" in that sense. Watching is purely a matter of whether a viewer is connected to the same virtual desktop while actions run; it never changes how the actions themselves execute.

### Local viewing (NetClaw and the operator are on the same machine)

Point a VNC client, or a browser via noVNC, at the loopback-bound live-viewing service:

```
VNC:   localhost:5900
noVNC: http://localhost:6080
```

Both are confirmed loopback-only by the installer (`scripts/lib/install-steps.sh`'s `component_install_computer_use()` verifies this with `ss -tlnp` after every install — see FR-004, research.md R5). If either is reachable from a non-loopback address, treat that as a real, unresolved security exposure — stop and fix it (re-run the installer's computer-use step, or manually reapply the `-localhost` / `--listen 127.0.0.1:6080` patches documented in research.md R5) before continuing, rather than proceeding anyway.

### Remote viewing (operator is on a different machine than NetClaw)

The live-viewing service being loopback-only is deliberate, not a bug to route around — never expose port 5900 or 6080 directly. Instead, tunnel:

```bash
ssh -L 6080:localhost:6080 <netclaw-host>
```

Then open `http://localhost:6080` in a local browser. This is the same secure-remote-access pattern documented for `chrome-devtools-mcp`'s Watch Mode in spec 048.

### During a Watch Mode session

Continue running Workflow 1's actions normally — screenshot, click, type, etc. There is no special "watch flag" to pass to the action scripts; a connected viewer simply sees the same virtual display those scripts are already driving in real time. If the operator wants to take over and complete a step manually (e.g. an interactive login `manual_setup_required` stopped on), they can click and type directly into the viewer — the virtual desktop has no concept of whose input is "real," so operator and NetClaw actions on the same display are equivalent.

## Error Handling

| Status | Meaning | What to tell the operator |
|--------|---------|----------------------------|
| `ok` | Requested information/interaction succeeded | Return the result and the screenshot |
| `manual_setup_required` | The target application needs interactive first-time setup | Ask the operator to complete it via Watch Mode (Workflow 2), then retry |
| `virtual_desktop_unavailable` | The `computer-use` component isn't installed, or its virtual desktop failed to start | Point at `./scripts/install.sh --components computer-use` (or the equivalent at the time) |
| `conflict` | Another task is already using the single shared virtual desktop | Retry once the other task completes — only one virtual display exists (data-model.md) |
