# Research: Chrome DevTools Browser Automation & Inspection Skill

**Feature**: 048-chrome-devtools-browser-inspection
**Date**: 2026-07-07

## R1: Server Selection

**Decision**: Use the official `chrome-devtools-mcp` npm package (published by the Chrome DevTools team, source at `github.com/ChromeDevTools/chrome-devtools-mcp`).

**Rationale**: This is the tool the feature was scoped around; there is no competing "official vs. community" choice to make here (unlike, say, GitLab's dual official/community MCP landscape) — there is exactly one maintained server for this capability, and it is maintained by the team that owns Chrome DevTools itself. It exposes ~50+ tools across navigation, input automation, network inspection, performance tracing, console/debugging, memory (heap snapshots), extensions, and third-party/WebMCP tool execution.

**Alternatives considered**:
- Building a NetClaw-authored Puppeteer/Playwright-based MCP server from scratch: rejected — would duplicate a well-maintained, actively-developed official tool for no benefit, and would violate the "no bespoke integration patterns outside MCP" spirit by taking on maintenance burden NetClaw doesn't need.
- A generic community browser-automation MCP (e.g., a Puppeteer-MCP wrapper): rejected — the official Chrome DevTools team package has first-party support for the CDP-level features this feature specifically needs (performance tracing, Lighthouse audits, console capture), which generic Puppeteer wrappers don't consistently expose.

## R2: Transport Protocol

**Decision**: stdio transport, spawned locally via `npx -y chrome-devtools-mcp@latest`.

**Rationale**: Consistent with the majority of NetClaw's Node.js-based MCP registrations (`gitlab-mcp`, `jenkins-mcp`) — no network transport, no additional attack surface, matches the "each MCP server MUST declare their transport protocol explicitly" requirement (Constitution V) trivially.

**Alternatives considered**: None seriously — the server's own CLI daemon model (a background process reached via Unix socket for repeated CLI invocations) is an internal implementation detail of the upstream package, not something NetClaw needs to configure differently; the MCP registration itself is a straightforward stdio spawn.

## R3: Persistent Profile & Headless/Headed Mode (resolves Clarification Q1)

**Decision**: Default to headless with a persistent, NetClaw-managed profile directory at `~/.openclaw/chrome-devtools/profile` (overridable via `CHROME_DEVTOOLS_PROFILE_DIR`). Headless/headed is controlled by a `CHROME_DEVTOOLS_HEADLESS` env var (default `true`), matching FR-015. Two supported patterns are documented for the one-time interactive sign-in, so this works regardless of whether the NetClaw host has a display:

- **Pattern A — host has a display** (desktop Linux, or WSL2 with WSLg): set `CHROME_DEVTOOLS_HEADLESS=false` temporarily, launch the server, sign in in the visible window, then flip back to headless for normal automated use. The same `--userDataDir` is reused across both modes, so the cached session carries over.
- **Pattern B — headless/no-display host** (a remote Linux server, or WSL2 without WSLg): the operator runs their own local Chrome with `--remote-debugging-port=9222 --user-data-dir=<path matching CHROME_DEVTOOLS_PROFILE_DIR>` on a machine that does have a display, tunnels port 9222 to the NetClaw host (e.g., `ssh -R 9222:localhost:9222 <netclaw-host>`), signs in normally in that visible Chrome, and NetClaw's `chrome-devtools-mcp` registration attaches to it via `--browserUrl=http://127.0.0.1:9222` (or `--autoConnect` on Chrome 144+) instead of launching its own instance for that session.

This directly matches the upstream server's own documented guidance: *"For maintaining login state between manual and agent-driven testing, connect to an already-running Chrome instance via `--autoConnect` or `--browserUrl` rather than launching a new profile."* Both patterns reuse the identical on-disk profile, so Chrome's own cookie/session cache — not NetClaw — is what makes the "sign in once" model work (FR-004, FR-005).

**Alternatives considered**:
- Mandating a headed browser on the NetClaw host always: rejected — fails outright on headless server deployments, which is a realistic NetClaw deployment target (Constitution's Technology Stack lists Linux server as a first-class target).
- Building a NetClaw-side credential-injection flow to avoid interactive sign-in entirely: explicitly out of scope per the spec's Assumptions — this would mean NetClaw handling credentials, which FR-005 and Constitution XIII forbid.

## R4: Access Scoping (resolves Clarification Q2)

**Decision**: No bespoke domain/URL allowlist inside either skill. Governance relies on NetClaw's existing general permission-prompt model plus DefenseClaw's documented `tool block <tool>` / `tool allow <tool>` controls — the same mechanism that governs every other MCP tool in NetClaw.

**Rationale**: Building a second, skill-specific allowlist mechanism would duplicate a control NetClaw already operates generically, adding a second place operators would need to configure and keep in sync. `docs/DEFENSECLAW.md` confirms DefenseClaw's "Tool Call Inspection" already "Enforces 6 rule categories on all tool executions" — this skill's tool calls are not special-cased or exempt from that.

**Alternatives considered**: A configurable domain allowlist baked into `browser-gui-inspect`'s own config — rejected as scope creep per the Clarification decision; can be revisited later if real-world usage shows a gap DefenseClaw's controls don't cover.

## R5: Audit Trail (resolves Clarification Q3)

**Decision**: No feature-specific audit logging code. Rely entirely on DefenseClaw's existing generic tool-call inspection/logging.

**Verified basis for this reliance**: `docs/DEFENSECLAW.md` documents "Audit Logging | DefenseClaw | SQLite database with compliance-ready exports" and "Tool Call Inspection | DefenseClaw | Enforces 6 rule categories on all tool executions" as blanket, tool-agnostic capabilities — not something each MCP integration has to opt into individually. This satisfies Constitution IV ("every session... MUST be recorded", "no operation MAY execute silently") for this feature the same way it does for every other registered MCP server today.

**One inherited (not new) caveat**: audit coverage is contingent on NetClaw running in `"security": {"mode": "defenseclaw"}` rather than `"hobby"` mode (see `CLAUDE.md` / `docs/DEFENSECLAW.md`). This is a pre-existing, repo-wide condition affecting all MCP tools, not a gap introduced by this feature — no additional mitigation is warranted here beyond what already applies repo-wide.

**Alternatives considered**: A dedicated GAIT-backed log of every URL/action this skill touches (as GitLab's integration does at the skill level, per its R7) — considered but rejected for v1: unlike GitLab (which performs state-changing writes like issue/MR creation that Constitution IV's write-focused language most directly targets), this feature's charter is explicitly read/observation-oriented (see Constitution Check, Principle I), so the generic DefenseClaw coverage is judged sufficient without an extra bespoke logging layer. Revisit if `browser-gui-inspect` usage patterns in practice trend toward more state-changing interactions than anticipated.

## R6: Skill Decomposition (Constitution VII)

**Decision**: Two skills instead of one monolithic skill:

| Skill | User Stories Covered | Charter |
|-------|----------------------|---------|
| `browser-viz-verify` | US1 (P1) | Verify a NetClaw-generated visualization file renders cleanly: screenshot, console check, optional Lighthouse audit. Local files only — no external sites, no authentication. |
| `browser-gui-inspect` | US2, US3, US4 (P2-P4) | Controller-agnostic navigate/click/fill/screenshot/network-inspect toolkit for filling controller-skill gaps, discovering undocumented vendor APIs, and general one-off web-GUI automation against authenticated or public sites. |

**Rationale**: Constitution VII requires each skill to "perform a single, well-defined operational function" and to be decomposed if it grows beyond a reasonable scope. US1 is qualitatively different from US2-US4 — it never touches an external site, never needs the persistent authenticated profile, and is invoked automatically as a QA step by other skills, whereas US2-US4 are operator-initiated, externally-facing, and share one authenticated-session code path. Splitting also means `browser-viz-verify` can be safely auto-invoked (e.g., chained after `threejs-network-viz`) without ever touching the higher-trust authenticated profile that `browser-gui-inspect` uses.

**Alternatives considered**: One skill with an internal mode switch (`--target=local|external`) — rejected as it blurs the "single, well-defined operational function" boundary the constitution asks for, and makes it harder to reason about which invocations ever touch the authenticated profile.

## R7: CLI Delivery (resolves the "MCP + CLI" requirement)

**Decision**: Do not reimplement or fork a CLI. The upstream `chrome-devtools-mcp` package already ships its own full CLI (`npx chrome-devtools-mcp@latest start|stop|status`, plus all the flags in R3). NetClaw's own contribution is a thin `scripts/chrome-devtools-enable.sh` setup script — matching the existing `defenseclaw-enable.sh` / `forward-enable.sh` / `ipfabric-enable.sh` convention — that: (1) checks Node.js 18+ and a Chrome/Chromium binary are present, (2) creates `CHROME_DEVTOOLS_PROFILE_DIR` if missing, (3) writes the three new env vars into `.env` if not already set, and (4) prints the two sign-in patterns from R3 with the operator's actual profile path filled in.

**Rationale**: Writing a NetClaw-specific CLI wrapper around an already-complete upstream CLI would be pure duplication (violates "don't add abstraction beyond what the task requires"). What operators actually lack today is the one-time setup step (profile dir, env vars, dependency check) — that's what the enable script solves, and it satisfies FR-009's "standalone CLI for direct manual use" by pointing operators at the upstream CLI directly rather than reinventing it.

**Alternatives considered**: A NetClaw-authored Python/Node CLI that wraps every upstream tool with NetClaw-flavored subcommands — rejected as unnecessary surface area for a feature whose upstream dependency already has a complete, well-documented CLI.

## R8: Safety Scoping for Interactive Tools (click/fill_form/handle_dialog)

**Decision**: `browser-gui-inspect`'s `SKILL.md` explicitly documents that click/fill-form/dialog-handling tools are for reading, filtering, searching, and confirming state on a target page — not for submitting, applying, or committing configuration changes to network infrastructure. Any actual config change remains the job of the relevant API-based skill (which already implements Constitution I/II/III/VIII's baseline→apply→verify and ITSM-gating workflow).

**Rationale**: The upstream server's `click`/`fill_form` tools are generic browser actions with no awareness of NetClaw's safety model — nothing stops an operator from asking the agent to "click Commit" on a vendor GUI. Since GUI automation bypasses the observe→baseline→modify→verify pattern and ITSM CR gate that API-based skills enforce, allowing this skill to perform config-committing actions would silently create a side door around Constitution I/III/VIII. Scoping this at the documentation/charter level (reinforced by the four user stories, all of which are read/reporting-oriented) keeps the feature's actual behavior aligned with what was specified, without needing new enforcement code.

**Alternatives considered**: A runtime allowlist of "safe" DOM actions vs. "risky" ones (e.g., blocking clicks on buttons labeled "Submit"/"Commit"/"Apply") — rejected as brittle (label text varies per vendor, defeats the controller-agnostic design goal) and as scope creep beyond what the spec asked for; the documentation-level scoping plus existing DefenseClaw tool-level controls (R4) are judged sufficient for v1.
