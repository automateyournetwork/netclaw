# Quickstart: Computer Use — Full-Desktop Automation via OpenClaw's Native Skill

**Feature**: 050-computer-use-desktop
**Date**: 2026-07-08

## Prerequisites

1. A Linux host running NetClaw (the upstream `computer-use` skill targets headless Linux servers — not macOS; see research.md R1 on why `codex-computer-use` doesn't apply here)
2. apt (or equivalent package manager) access to install `xvfb`, `xfce4`, `xfce4-terminal`, `xdotool`, `scrot`, `imagemagick`, `dbus-x11`, `x11vnc`, `novnc`, `websockify` — all confirmed available on this project's own dev host
3. `openclaw` CLI available (already true on any NetClaw install)

## Setup

### 1. Install the component

Via the modular installer (spec 049):

```bash
./scripts/install.sh --components computer-use
```

This installs the required system packages, then runs `openclaw skills install --global computer-use` to pull the skill itself from ClawHub.

### 2. Verify the virtual desktop and live-viewing service

```bash
openclaw skills list | grep computer-use
```

Confirm the live-viewing service is loopback-only (FR-004) — do not skip this:

```bash
ss -tlnp | grep -E "5900|6080"   # typical VNC / noVNC ports; confirm bound to 127.0.0.1, not 0.0.0.0
```

If it's listening on `0.0.0.0`, do not expose that port to the network — use an SSH tunnel for remote viewing instead (see step 4).

### 3. Try it

- "Open the legacy NMS client on the virtual desktop and tell me the current alarm count." → `desktop-gui-inspect`
- "Watch it interact with the terminal emulator while it checks something." → `desktop-gui-inspect` with `watch: true`

### 4. Watch or take over live (remote viewing)

Locally, connect a VNC client or open the noVNC URL directly. From another machine:

```bash
ssh -L 6080:localhost:6080 <netclaw-host>
```

Then open `http://localhost:6080` in your own browser — the same secure-tunnel pattern spec 048 uses for headless-host Chrome sign-in.

## Verification

1. `./scripts/install.sh --components computer-use` completes with no sudo prompt beyond what the installer's own package-install confirmation already handles, and no credential requested.
2. `desktop-gui-inspect` against a simple desktop application (e.g., the bundled `xfce4-terminal`) successfully reads back a value.
3. A live viewer connection shows the virtual desktop's real-time state while a task runs.
4. The live-viewing service is confirmed loopback-only via `ss -tlnp` (or equivalent) — not just documented as such.
5. `scripts/verify-catalog-coverage.py` continues to report zero unexplained gaps after this component is added.
