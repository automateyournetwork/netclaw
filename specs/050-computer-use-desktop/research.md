# Research: Computer Use — Full-Desktop Automation via OpenClaw's Native Skill

**Feature**: 050-computer-use-desktop
**Date**: 2026-07-08

## R1: `computer-use` vs. `codex-computer-use` — Which One, and Why

**Decision**: Integrate OpenClaw's ClawHub `computer-use` skill. Do not implement `codex-computer-use`.

**Verified live on this host**:
```
$ openclaw skills search computer-use
computer-use  Computer Use  Full desktop computer use for headless Linux servers.
  Xvfb + XFCE virtual desktop with xdotool automation. 17 actions
  (click, type, scroll, screenshot, drag,...)
```
This exact description matches the `openclawai.io/skills/skill/computer-use` page word-for-word — confirms the skill is real, currently listed, and installable on this exact NetClaw deployment.

By contrast, `docs.openclaw.ai/plugins/codex-computer-use` describes a plugin that is explicitly scoped to **Codex-mode agents** (OpenAI's Codex app-server as the backend) and is **macOS-only**, requiring the desktop `Codex.app` bundle plus macOS Accessibility/Screen Recording permissions. NetClaw's constitution specifies an Anthropic-Claude-based agent runtime (`AI Runtime: OpenClaw gateway with Anthropic Claude`), and this deployment runs on Linux (WSL2). `codex-computer-use` cannot function in this deployment regardless of implementation effort — it isn't a design choice to reject, it's a platform mismatch.

**Rationale for `computer-use` specifically**: It targets exactly this deployment's real environment (headless Linux server, no physical display required), needs no specific AI backend mode, and its dependency list (`xvfb`, `xfce4`, `xdotool`, etc.) is confirmed available via apt on this host.

**Alternatives considered** (from the same ClawHub search, all rejected): `open-computer-use` (cross-platform MCP service, less specifically matched to the headless-Linux-server use case the requester pointed at); `computer-use-macos`/`computer-use-windows`/`computer-use-linux` (platform-specific bundled-runtime variants — `computer-use` itself already covers Linux without needing a separate bundled-runtime skill); `gemini-computer-use` (Gemini-model-specific, doesn't fit an Anthropic-Claude runtime).

## R2: Installation Mechanics

**Decision**: Install via `openclaw skills install computer-use` (ClawHub ref, confirmed as a bare slug in the search output, no `@owner/` prefix needed for this particular skill), plus the apt packages the skill's own documentation lists as required.

**Verified live on this host** (read-only checks, no packages installed as part of this research):
```
$ apt list xvfb xfce4 xfce4-terminal xdotool scrot imagemagick dbus-x11 x11vnc novnc websockify
dbus-x11        [installed,automatic]
imagemagick     [installed]
scrot           [installed]
xvfb            [installed]
xfce4, xfce4-terminal, x11vnc, novnc, websockify, xdotool   (available, not yet installed)
```
All ten packages exist in this host's apt repositories; four are already present from prior work. No unavailable or exotic dependency.

`openclaw skills install <ref>` supports `--global` (shared managed skills directory) and `--agent <id>` (target a specific agent workspace). Given NetClaw runs as a single default agent on this host, no special flags are needed beyond the bare install command; `--global` is worth using so the skill is available regardless of which agent workspace is active, consistent with how NetClaw's other capabilities aren't scoped to a single agent.

**Confirmed live** (`openclaw skills install --global computer-use`, `computer-use@1.2.1`, installed to `~/.openclaw/skills/computer-use`): this is **not** an MCP server at all — it is a script-based skill. Its 17 actions are individual bash scripts (`screenshot.sh`, `click.sh x y left`, `type_text.sh "text"`, etc.) that the agent invokes directly against `DISPLAY=:99`, documented in the skill's own `SKILL.md`. There is no `config/openclaw.json` entry to write and no MCP registration step. This resolves the open question from the original research pass cleanly: `desktop-gui-inspect` orchestrates these scripts directly, the same way any OpenClaw skill wraps shell commands, not via MCP tool calls.

**Also confirmed live**: `openclaw skills install` only downloads the skill's scripts — it does **not** provision or start the virtual desktop. That requires separately running the skill's own `scripts/setup-vnc.sh`, which installs the same system packages (idempotently) and generates+starts four systemd services (`xvfb`, `xfce-minimal`, `x11vnc`, `novnc`). NetClaw's install function runs this automatically so the component is actually usable after installation, not just downloaded (see R5 for what else this step must do).

**A third bug confirmed live during `desktop-gui-inspect`'s functional test (T014)**: `openclaw skills install` writes the downloaded action scripts (`screenshot.sh`, `click.sh`, etc.) as non-executable (`-rw-r--r--`, mode 0644). Since `desktop-gui-inspect` invokes them directly as `./scripts/<action>.sh` (not `bash scripts/<action>.sh`) — and, more importantly, since each action script's own tail line does `exec "$(dirname "$0")/screenshot.sh"` to chain a confirmation screenshot after every action — every single action failed with "Permission denied" until this was fixed. NetClaw's install function now runs `chmod +x` on all of the skill's `scripts/*.sh` immediately after install, so this is fixed for every install rather than needing to be rediscovered per-host.

## R3: Catalog & Coverage-Script Placement

**Decision**: New catalog entry `computer-use` (category: `Analysis & Diagrams`, alongside `chrome-devtools` and the other visualization/inspection tools, since it's the same class of "give NetClaw eyes/hands on something it couldn't otherwise reach" capability). `component_install_computer_use()` installs the apt packages, then runs `openclaw skills install --global computer-use`.

This capability is **not** a `config/openclaw.json`-registered MCP server in the same sense as every prior catalog entry (it's installed through OpenClaw's own skill mechanism, not a vendored `mcp-servers/<name>` clone). It therefore won't automatically appear in `scripts/verify-catalog-coverage.py`'s primary ground truth (the `mcpServers` keys). To satisfy FR-009 without producing a false gap or a false sense of verification, this capability is added to `scripts/verify-inventory-counts.py`'s `EXTERNAL_INTEGRATIONS` list (as "Computer Use" — it's a genuine NetClaw-supported integration NetClaw itself doesn't statically register, exactly what that list is for) and to `scripts/verify-catalog-coverage.py`'s `GROUPED_EXTERNAL_COVERAGE` (`"computer-use": ["Computer Use"]`), mirroring exactly how spec 049 handled `memory-mcp` and `ollama` — two other capabilities installed outside the `config/openclaw.json` pattern.

**Alternatives considered**: Skipping coverage-script registration entirely, on the grounds that it's "not really an MCP server the same way" — rejected. FR-009 is explicit about not regressing the zero-unexplained-gap guarantee, and the whole point of spec 049's coverage tooling was to stop capabilities from being silently absent from either the catalog or the count. Treating this one as a special case exempt from tracking would undermine that guarantee on its first real test.

## R4: Skill Design — `desktop-gui-inspect`

**Decision**: One new skill, `desktop-gui-inspect`, structured as closely as possible to `browser-gui-inspect`'s proven shape:

- **Golden Rule** (direct parallel): the 17 desktop actions (click, type, scroll, drag, etc.) are for reading, navigating, and confirming state in a desktop-only target — never for submitting/applying/committing a real configuration change. Any such change stays with the relevant API-based skill's baseline→apply→verify + ITSM-gated workflow (FR-002).
- **Workflow 1 — Operate a legacy desktop-only tool** (User Story 2): open/navigate the target application, read the requested information via screenshots/UI state, report back.
- **Workflow 2 — Watch Mode via live viewer** (User Story 3): document connecting to the virtual desktop's VNC/noVNC endpoint to watch or take over, directly mirroring `browser-gui-inspect`'s Watch Mode section but simpler — there's no headless/headed *choice* here the way there was for Chrome (Xvfb is inherently a virtual, headless-host display), so "watching" is purely a matter of whether a viewer connection is open, not a different launch mode.
- **No per-application knowledge baked in** (Constitution VI, matching `browser-gui-inspect`'s own design): every invocation is directed by the operator's `target`/`intent` at request time.

**Rationale**: Reusing a proven shape (rather than inventing a new one) keeps NetClaw's two GUI-gap-filling skills easy to reason about side by side — an operator or contributor who understands `browser-gui-inspect` already understands most of `desktop-gui-inspect`.

## R5: Security — Live-Viewing Service Must Not Be Network-Reachable by Default (resolves FR-004)

**Confirmed live, not hypothetical**: the upstream skill's own `setup-vnc.sh` generates systemd units that do **not** default to loopback-only. Reading the generated `/etc/systemd/system/x11vnc.service` before starting it showed `ExecStart=/usr/bin/x11vnc -display :99 -forever -shared -rfbport 5900 -noxdamage -noxfixes -noclipboard` — no `-localhost` flag. After running `setup-vnc.sh` and starting the service, `ss -tlnp` confirmed it live: `LISTEN 0.0.0.0:5900` and `LISTEN [::]:5900` — reachable from any network interface, handing full desktop control to anyone who can reach that port. This is exactly the exposure this requirement anticipated, now proven real rather than assumed.

A second, unrelated bug surfaced at the same time: the generated `novnc.service` pointed at `/usr/share/novnc/utils/novnc_proxy`, which does not exist in Ubuntu/Debian's `novnc` apt package (that package ships `launch.sh` instead — a naming difference between the upstream skill's assumed environment and this host's actual packaging). The service crash-looped (`code=exited, status=203/EXEC`) until this was corrected.

**Decision**: NetClaw's install function does not merely detect this and warn — it actively remediates it, then verifies the remediation. Concretely, after running `setup-vnc.sh`:
1. Patch `/etc/systemd/system/x11vnc.service`'s `ExecStart` to add `-localhost` (x11vnc's own flag for refusing non-loopback connections).
2. Patch `/etc/systemd/system/novnc.service`'s `ExecStart` to point at the correct binary for this host (`launch.sh`, not the assumed `novnc_proxy`) and pass `--listen 127.0.0.1:6080` instead of a bare port (`websockify`'s listen argument accepts a `host:port` pair; `launch.sh` passes it through unmodified).
3. `systemctl daemon-reload` and restart both services.
4. Re-verify via `ss -tlnp` that both are now loopback-only — confirmed: `127.0.0.1:5900`, `[::1]:5900`, and `127.0.0.1:6080`.

This does not change the skill's documented usage pattern at all — the skill's own `SKILL.md` already tells operators to reach VNC/noVNC exclusively via an SSH tunnel (`ssh -L 6080:localhost:6080 <host>`). Enforcing loopback-only just makes that the *only* way in, rather than a recommendation a misconfigured or curious network client could bypass.

**Rationale**: NetClaw could have shipped a warning-only check (the originally planned, more conservative design) and left the exposure in place for the operator to fix. Given the fix is small, well-understood, and doesn't touch the upstream skill's own source (only the generated systemd units, a deployment-level configuration — the same spirit as pinning `chrome-devtools-mcp`'s `--executablePath` rather than forking it), actively closing a confirmed, real exposure is a better outcome than merely documenting it.

**Alternatives considered**: Leaving detection-only (the original plan) — rejected once the exposure was confirmed live rather than hypothetical; a security requirement framed as "verify and warn" is materially weaker than "verify and fix" when the fix is this cheap. A NetClaw-managed firewall rule (`ufw`/`iptables`) as a second layer — not needed once the service itself is correctly bound to loopback; would be pure redundancy for the confirmed exposure.

## R6: `.env.example` / Credential Surface

**Decision**: No new environment variables. Confirmed by the upstream skill's own description (screenshot/mouse/keyboard actions, VNC viewing — nothing that names an API key, token, or account) and by direct analogy to spec 048's `chrome-devtools-mcp`, which likewise needed zero credentials. If a specific legacy application being automated needs its own login, that happens manually through the live viewer (R4, Workflow 2), never through a NetClaw-stored credential.
