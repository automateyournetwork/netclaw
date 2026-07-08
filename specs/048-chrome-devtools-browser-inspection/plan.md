# Implementation Plan: Chrome DevTools Browser Automation & Inspection Skill

**Branch**: `048-chrome-devtools-browser-inspection` | **Date**: 2026-07-07 | **Spec**: `specs/048-chrome-devtools-browser-inspection/spec.md`
**Input**: Feature specification from `/specs/048-chrome-devtools-browser-inspection/spec.md`

## Summary

Integrate the official `chrome-devtools-mcp` server (published by the Chrome DevTools team, npm package `chrome-devtools-mcp`) into NetClaw by registering it as a locally-spawned stdio MCP server in `config/openclaw.json`, documenting it under `mcp-servers/chrome-devtools-mcp/`, and building **two** companion skills instead of one monolithic skill (per Constitution VII — Skill Modularity):

1. **`browser-viz-verify`** (P1) — opens a NetClaw-generated visualization file, screenshots it, reads the console, and optionally runs a Lighthouse audit, to close the "did it actually render" QA gap across `threejs-network-viz`, `canvas-network-viz`, `drawio-diagram`, `uml-diagram`, and `markmap-viz`.
2. **`browser-gui-inspect`** (P2–P4) — the controller-agnostic navigate/click/fill/screenshot/network-inspect toolkit for filling gaps in existing controller skills (e.g., pulling ACI APIC bridge-domain data the REST API doesn't expose), discovering undocumented vendor APIs via network traffic capture, and general one-off web-GUI automation.

No NetClaw-authored MCP server code is written — this is a registration + skill-documentation integration, consistent with the `gitlab-mcp` (008) and `atlassian-mcp` (009) pattern. The one piece of NetClaw-authored tooling is a thin `scripts/chrome-devtools-enable.sh` setup script (mirroring `defenseclaw-enable.sh`, `forward-enable.sh`) that provisions the persistent profile directory and `.env` defaults — it does not reimplement the upstream CLI, it just removes setup friction, satisfying the "MCP + CLI" ask without forking anything.

## Technical Context

**Language/Version**: Node.js 18+ (official `chrome-devtools-mcp` server — no NetClaw-authored server code); Bash (setup/enable script, consistent with `scripts/*-enable.sh` convention); Markdown (skill + MCP documentation)
**Primary Dependencies**: `chrome-devtools-mcp` (npm package, official Chrome DevTools team release, MIT-style OSS), Node.js 18+, a locally installed Chrome/Chromium binary (stable channel by default)
**Storage**: N/A for NetClaw itself (stateless proxy to a local browser process). A persistent Chrome profile directory on disk (`~/.openclaw/chrome-devtools/profile` by default, overridable via `CHROME_DEVTOOLS_PROFILE_DIR`) holds cookies/session state for manually authenticated sites — this is Chrome's own state, not a NetClaw-managed database.
**Testing**: Manual verification per user story — (1) screenshot + console round-trip against a known-good and a known-broken local HTML fixture, (2) one authenticated navigation against a controller dashboard the operator has manually signed into, (3) one network-request listing against a loaded dashboard page. No automated test suite, consistent with other "community MCP, skill docs only" integrations (008, 009, 026).
**Target Platform**: Linux hosts running NetClaw (including headless/no-display hosts such as WSL2 without WSLg or a remote server) — the plan explicitly supports both display and no-display hosts (see Research R4).
**Project Type**: MCP server registration + skill authoring (configuration integration, no application code)
**Performance Goals**: Screenshot + console verdict for a generated visualization returned within 30 seconds (SC-001); bounded page-load wait (default 15s navigation timeout) so a hung page fails fast rather than hanging indefinitely (Edge Cases).
**Constraints**: No credential storage/handling by NetClaw (FR-005); no bespoke domain allowlist (Clarification Q2 — relies on DefenseClaw tool-allow/tool-block); no bespoke audit trail (Clarification Q3 — relies on DefenseClaw's existing "all tool executions" inspection/logging); headless/headed mode must be operator-selectable (FR-015 / Clarification Q1); no per-vendor DOM/selector logic baked into either skill (FR-011).
**Scale/Scope**: Single shared persistent profile, single NetClaw host, single operator at a time for v1 (see spec Assumptions); 2 skills; ~15-20 of the upstream server's ~50+ tools are relevant to the 4 user stories (navigation, input, network, performance/debugging, console — not memory/heap-snapshot or extension tooling, which are out of scope for this feature).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Safety-First Operations | PASS (scoped) | This feature is observation/read-oriented by charter (screenshot, console, network inspection, reading page content). `browser-gui-inspect`'s click/fill-form tools are documented as being for reading/confirming state only — SKILL.md explicitly forbids using them to submit, apply, or commit configuration changes on network infrastructure. Any actual config change belongs to the relevant API-based skill's baseline→apply→verify workflow, not this one. |
| II. Read-Before-Write | N/A | This feature performs no device configuration writes. |
| III. ITSM-Gated Changes | N/A | Reinforced by I — since no config changes are performed via this feature, no CR gating applies to it. |
| IV. Immutable Audit Trail | PASS | Per Clarification Q3, no bespoke audit trail is built. DefenseClaw's documented "Tool Call Inspection... on all tool executions" and SQLite audit log cover this MCP's tool calls the same as every other MCP tool in NetClaw (see Research R7 for the verified basis of this reliance, including the one caveat: audit coverage depends on DefenseClaw security mode being enabled, same pre-existing condition as all other NetClaw MCP integrations). |
| V. MCP-Native Integration | PASS | `chrome-devtools-mcp` implements MCP natively (stdio transport, standard JSON-RPC lifecycle). Registered exactly like other Node.js MCP servers in `config/openclaw.json`. |
| VI. Multi-Vendor Neutrality | PASS | Explicitly controller-agnostic by design (FR-011) — no vendor-specific DOM/selector knowledge is embedded in either skill; any vendor-specific navigation is operator-directed at invocation time, not hardcoded. |
| VII. Skill Modularity | PASS | Split into two focused skills (`browser-viz-verify`, `browser-gui-inspect`) rather than one skill covering all four user stories, keeping each skill's charter narrow. |
| VIII. Verify After Every Change | N/A | No changes are applied by this feature (see I). |
| IX. Security by Default | PASS | Least privilege = ability to spawn/control a local Chrome process and read/write one designated profile directory — no API keys, no elevated host permissions. Documented in `mcp-servers/chrome-devtools-mcp/README.md`. Access scoping relies on DefenseClaw's existing tool-allow/tool-block controls (Clarification Q2) rather than a new bespoke mechanism. |
| X. Observability as First-Class | PASS | `ui/netclaw-visual/` (Three.js HUD) gets a new node for this integration reflecting its registration/operational status, consistent with every other MCP addition. |
| XI. Artifact Coherence | PENDING | Full checklist (README.md, scripts/install.sh, ui/netclaw-visual/, SOUL.md, both SKILL.md files, .env.example, TOOLS.md, config/openclaw.json, mcp-servers/chrome-devtools-mcp/README.md) tracked in Phase 2 tasks. |
| XII. Documentation-as-Code | PENDING | `mcp-servers/chrome-devtools-mcp/README.md` and both `SKILL.md` files created in Phase 2. |
| XIII. Credential Safety | PASS | No credentials are ever read, stored, or transmitted by this feature (FR-005). The only environment variables are non-secret configuration (profile path, headless flag, channel) documented in `.env.example`. |
| XIV. Human-in-the-Loop | PASS | Not applicable in the "external communications" sense (no Slack/Teams/ticket writes), but the same spirit applies to Story 2/4's GUI actions — see I. |
| XV. Backwards Compatibility | PASS | Purely additive: one new MCP registration, two new skills, no changes to any existing tool schema or skill. |
| XVI. Spec-Driven Development | PASS | Following the full SDD workflow (specify → clarify → plan → tasks → implement). |
| XVII. Milestone Documentation | DEFERRED | Applies post-implementation, not at planning time — noted as a Phase 3 (post-`/speckit.implement`) follow-up, not a planning gate. |

## Project Structure

### Documentation (this feature)

```text
specs/048-chrome-devtools-browser-inspection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (MCP tool reference + skill interface contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
mcp-servers/chrome-devtools-mcp/
└── README.md                        # MCP server documentation (tools, env vars, setup, no vendored code)

workspace/skills/browser-viz-verify/
└── SKILL.md                         # P1 — verify NetClaw-generated visualization outputs render cleanly

workspace/skills/browser-gui-inspect/
└── SKILL.md                         # P2-P4 — controller-agnostic navigate/click/fill/screenshot/network-inspect

scripts/
└── chrome-devtools-enable.sh        # Setup script: provisions profile dir, writes .env defaults, checks Node/Chrome present

config/openclaw.json                 # + chrome-devtools-mcp server registration
.env.example                         # + CHROME_DEVTOOLS_PROFILE_DIR / CHROME_DEVTOOLS_HEADLESS / CHROME_DEVTOOLS_CHANNEL
README.md, TOOLS.md, SOUL.md         # + capability descriptions (Artifact Coherence)
ui/netclaw-visual/                   # + HUD node for this integration
```

**Structure Decision**: No server code is authored by NetClaw. The official `chrome-devtools-mcp` package is installed on demand via `npx` and spawned as a local stdio process, exactly like the `gitlab-mcp` (008) and `atlassian-mcp` (009) integrations. `mcp-servers/chrome-devtools-mcp/` contains only a README documenting the integration. Two companion skills (rather than one) provide the operational workflows, split by charter per Constitution VII. One small, NetClaw-authored Bash setup script removes first-run friction (profile directory + `.env` provisioning) without reimplementing or forking the upstream CLI/server.

## Complexity Tracking

> No constitution violations requiring justification. Principle I's scope constraint (this feature is read/observation-oriented; it explicitly excludes being a config-change mechanism) is a documented design decision, not a violation — the alternative (allowing this skill to submit/commit changes via GUI automation) was rejected because it would bypass the existing baseline→apply→verify and ITSM-gating workflow that API-based skills already implement correctly, duplicating a safety-critical mechanism in a place harder to audit than a REST call.
