# Implementation Plan: Computer Use — Full-Desktop Automation via OpenClaw's Native Skill

**Branch**: `050-computer-use-desktop` | **Date**: 2026-07-08 | **Spec**: `specs/050-computer-use-desktop/spec.md`
**Input**: Feature specification from `/specs/050-computer-use-desktop/spec.md`

## Summary

Integrate OpenClaw's own ClawHub-hosted `computer-use` skill (Xvfb + XFCE virtual desktop, xdotool input automation, x11vnc/noVNC live viewing — verified available via `openclaw skills search computer-use` on this exact host) as NetClaw's full-desktop automation capability, extending spec 048's browser-automation model to targets no browser can reach: legacy desktop-only network/security tooling with no web GUI and no API. Add one new NetClaw skill (`desktop-gui-inspect`) wrapping the upstream skill's 17 actions with the same read/confirm/search-only Golden Rule as `browser-gui-inspect`, plus documentation of the built-in VNC/noVNC live-viewing path as the Watch Mode analogue. Add a `computer-use` catalog entry + install function to the modular installer (spec 049's architecture) — a new *shape* of install function, since this component is installed via `openclaw skills install computer-use` (OpenClaw's own skill marketplace) plus a handful of apt packages, not a vendored `mcp-servers/<name>` clone + `config/openclaw.json` entry like every prior catalog entry. Full artifact coherence per Constitution XI.

## Technical Context

**Language/Version**: Bash (install function, matching every existing `scripts/lib/install-steps.sh` entry), Markdown (skill documentation)
**Primary Dependencies**: OpenClaw's ClawHub `computer-use` skill (consumed as-is, no fork); apt packages `xvfb`, `xfce4`, `xfce4-terminal`, `xdotool`, `scrot`, `imagemagick`, `dbus-x11`, `x11vnc`, `novnc`, `websockify` (all confirmed present in this host's apt repositories; `dbus-x11`, `imagemagick`, `scrot`, `xvfb` already installed)
**Storage**: N/A — the virtual desktop's state is ephemeral (X11 session state), nothing NetClaw-managed persists across a restart
**Testing**: `bash -n` on the new install function (matching spec 049's own bar); a live install-and-connect test during implementation (installing a full XFCE desktop environment is a real, several-hundred-MB system change — flagged explicitly to the operator before it runs, not assumed)
**Target Platform**: Linux hosts running NetClaw (the upstream skill's own target — "headless Linux servers"); explicitly not macOS (that's the separate, out-of-scope `codex-computer-use` plugin path)
**Project Type**: Skill + installer catalog entry (configuration/documentation integration, consistent with the "no forked server code" pattern used for `chrome-devtools-mcp`)
**Performance Goals**: N/A — desktop-automation tasks are interactive/on-demand, no throughput target
**Constraints**: No NetClaw-managed credentials (FR-007); live-viewing service loopback-only by default (FR-004); single shared virtual desktop, concurrent-use conflicts must be detected and reported, not silently interleaved (FR-008); `codex-computer-use` explicitly not implemented (FR-011)
**Scale/Scope**: One new skill (`desktop-gui-inspect`), one new catalog entry + install function, full artifact-coherence touchpoints (README, SOUL, TOOLS, `.env.example` if applicable, HUD, coverage-check recognition)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS (scoped) | Same scoping approach as spec 048's `browser-gui-inspect`: `desktop-gui-inspect` is read/confirm/search-only by charter (FR-002). Any real configuration change stays with the appropriate API-based skill's baseline→apply→verify + ITSM-gated workflow. |
| II. Read-Before-Write | N/A | This feature performs no device configuration writes. |
| III. ITSM-Gated Changes | N/A | Reinforced by I — no config changes are performed via this capability. |
| IV. Immutable Audit Trail | PASS | Same basis as spec 048 (research R5 there): DefenseClaw's existing, tool-agnostic "Tool Call Inspection... on all tool executions" covers this skill's tool calls like every other MCP tool in NetClaw — no bespoke audit trail needed. |
| V. MCP-Native Integration | PASS | The upstream `computer-use` skill exposes its 17 actions as MCP tool calls (standard MCP, per OpenClaw's skill architecture) — no bespoke protocol introduced. |
| VI. Multi-Vendor Neutrality | PASS | `desktop-gui-inspect` contains no pre-programmed knowledge of any specific legacy application's UI — every invocation is directed by the operator's own target/intent at request time, mirroring `browser-gui-inspect`'s design exactly. |
| VII. Skill Modularity | PASS | One focused skill (`desktop-gui-inspect`) for this capability's charter — driving desktop-only targets — kept separate from the existing browser-focused skills rather than merged into them. |
| VIII. Verify After Every Change | N/A | No changes are applied by this feature (see I). |
| IX. Security by Default | PASS (design requirement) | Least privilege = ability to control one local virtual desktop session, nothing else. FR-004's loopback-only default for the live-viewing service is a direct Security-by-Default requirement — an open, unauthenticated VNC port reachable from the network would be a real exposure, and the spec treats it as a hard requirement, not an afterthought. |
| X. Observability as First-Class | PASS | `ui/netclaw-visual/` (Three.js HUD) gets a new node for this integration, consistent with every other capability addition. |
| XI. Full-Stack Artifact Coherence | PASS (this feature's explicit scope) | README.md, SOUL.md, TOOLS.md, `.env.example` (if applicable), `ui/netclaw-visual/`, `workspace/skills/desktop-gui-inspect/SKILL.md`, `scripts/lib/catalog.sh` + `scripts/lib/install-steps.sh` (per spec 049's amended checklist), and `scripts/verify-catalog-coverage.py` recognition — all tracked explicitly in tasks.md. |
| XII. Documentation-as-Code | PASS | Skill documentation and MCP/tool reference written in the same effort as the integration, not a follow-up. |
| XIII. Credential Safety | PASS | FR-007 — no NetClaw-managed credentials for this capability at all; any target-application login happens manually via the live viewer, mirroring spec 048's manual-sign-in precedent. |
| XIV. Human-in-the-Loop | PASS | Installing a full desktop environment (several hundred MB of system packages) is flagged explicitly to the operator before the live validation step runs, not silently assumed — same spirit as spec 048's careful handling of first-run browser provisioning, one level more consequential here since it's OS package installation, not a cached binary download. |
| XV. Backwards Compatibility | PASS | Purely additive: one new skill, one new catalog entry, no changes to `browser-viz-verify` or `browser-gui-inspect`'s behavior (FR out-of-scope note). |
| XVI. Spec-Driven Development | PASS | Following the full SDD workflow, per the operator's own request. |
| XVII. Milestone Documentation | DEFERRED | Applies post-implementation; the operator has already indicated this and spec 048/049's work will be combined into one milestone post. |

## Project Structure

### Documentation (this feature)

```text
specs/050-computer-use-desktop/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
workspace/skills/desktop-gui-inspect/
└── SKILL.md                         # New skill: drive the virtual desktop for API-less/browser-less targets

scripts/lib/catalog.sh               # + "computer-use" catalog entry (Analysis & Diagrams or a new category)
scripts/lib/install-steps.sh         # + component_install_computer_use() — apt packages + `openclaw skills install computer-use`
scripts/verify-catalog-coverage.py   # Updated GROUPED_* mapping if this entry needs one (see research.md)

README.md, SOUL.md, TOOLS.md         # + capability descriptions (Artifact Coherence)
.env.example                         # + note only if any configuration surface is found (research indicates none)
ui/netclaw-visual/                   # + HUD node for this integration
```

**Structure Decision**: No server code is authored by NetClaw — the upstream `computer-use` ClawHub skill is consumed as-is, matching the "no forked server code" pattern already used for `chrome-devtools-mcp`. The one genuinely new piece is `desktop-gui-inspect/SKILL.md` (NetClaw's operational workflow layer on top of the upstream skill's raw actions), plus the installer catalog entry/install function. This install function has a materially different shape from every prior one (OS package installation + OpenClaw's own skill-marketplace command, not a vendored git clone + `config/openclaw.json` registration) — documented explicitly in research.md so it doesn't read as an inconsistency in the catalog's style.

## Complexity Tracking

> No constitution violations requiring justification. Two things worth flagging explicitly rather than glossing over: (1) FR-004's loopback-only default for VNC/noVNC is a real security requirement, not a nice-to-have — an open, unauthenticated port exposing full desktop control would be a genuine exposure, so this is treated as a hard gate in the design, verified during implementation. (2) The live installation step in Phase 6 installs a full desktop environment (XFCE) plus several other packages — a heavier, more consequential system change than any prior spec's live-testing step (which only ever downloaded cached binaries into user-space directories) — flagged explicitly to the operator before it runs, per Constitution XIV's spirit even though that principle is framed around external communications specifically.
