# Implementation Plan: Hermes integration with the NetClaw HUD

**Branch**: `148-hermes-hud-integration` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)
**Input**: User's Hermes HUD request, federation exclusion for spec 149, and delegated planning through automatically remediated analysis.
**Stage**: Implementation and Mac acceptance complete. See [closure.md](closure.md) for tested fixes, exact platform scope and final matrix/release disposition; [validation.md](validation.md) retains prior evidence.

## Summary

Make runtime selection reach every shared HUD entry point and state source. Retain OpenClaw through an adapter and add Hermes through a private stdio MCP bridge plus a protected, version-pinned Hermes API companion. Deliver real text conversations, qualified installed tools/skills, owned history, Canvas branches, local Avatar, runtime-specific panels and predictable recovery. Preserve existing installations and decline unsupported actions explicitly.

Initial Hermes operational support is qualified read-only tools. Mutating operations require an independently enforced existing NetClaw policy boundary; otherwise they are unavailable. Exact effort/model locking, attachment input, hosted Avatar and federation execution are not promised by this initial Hermes transport. Federation is spec 149. These limits are visible capabilities, not silent fallback behavior.

## Technical Context

**Language/Version**: JavaScript ESM; HUD Node.js >=24.19 <25 or >=26.1 (qualified on 24.19.0); general OpenClaw installer policy remains >=24.16 <25 or >=26.1; isolated Python 3.12 bridge/tool and Python 3.14 companion; Bash; existing PowerShell launchers.
**Primary Dependencies**: Existing Express 4/React 18/Vite 6; official MCP Node client 2.3.1; isolated FastMCP 4.0.11/MCP Python SDK 2.3.0; Hermes v0.21.6 at `818c13be1dc4fd28987e1e881a9408224afd4535`; bounded HTTP client pinned during component installation work.
**Storage**: Existing private HUD bindings upgraded to schema 2; bridge SQLite request/session ledger (0600 under 0700 directory); runtime selection JSON; runtime-namespaced browser sessionStorage/IndexedDB; no external database.
**Testing**: Node built-in tests, existing UI/browser suites, Python unittest/pytest contract harness, isolated real MCP process, pinned Hermes with controlled provider/tool fixture, separate live acceptance matrix.
**Target Platform**: macOS 26.5.2 arm64 (actual qualification host), Ubuntu 24.04 x86_64, Ubuntu 24.04 on Windows 11 WSL2 (qualification targets). Native Windows Hermes refuses early; OpenClaw Windows launch behavior preserved.
**Project Type**: Existing local web application plus private MCP component and version-specific Hermes companion.
**Performance Goals**: Readiness/metadata requests finish in 5 seconds; run admission returns within 10 seconds; progress poll at most once/second per active request; default run deadline 900 seconds, configurable 1–3600 seconds by existing HUD timeout policy. No unbounded pending browser request.
**Constraints**: Loopback authenticated companion only; no browser credentials or upstream identifiers; no replay after ambiguous submission; one selected installation per HUD; no owner config overwrite; no raw reasoning projection; 4 MiB upstream response cap, 64 KiB text input, 1 MiB seeded context, 200 history messages/page, 20 progress events/poll, at most four concurrent runs and one per conversation.
**Scale/Scope**: Six user stories, 22 functional requirements; no multi-runtime aggregation, federation backend, new change-policy engine, new model provider or hosted avatar service.

## Constitution Check

Pre-research check: principles I–IV, V, VIII–XVI and XVII apply; design must include an MCP boundary, private ownership, change-policy preservation, isolated dependencies and full artifact coverage. No exception requested.

Post-design check:

| Principles | Design and required delivery evidence |
|---|---|
| I–IV, VIII | Read-only qualified tool set; no raw execution bypass; existing CR/Local-Lab endpoint/phase/baseline/rollback/verification gates required before enabling writes; local logs + GAIT. Current AGENTS Local/Lab policy governs its explicit exception. |
| V | Official SDK stdio MCP lifecycle; HTTP is internal transport behind the MCP integration, never a bespoke browser tool protocol. |
| VI–VII | Reuse existing vendor MCP implementations and installed skill documentation; one focused HUD diagnostics skill, no duplicated network automation. |
| IX–X, XIII | Least privilege, selected-home environment, protected companion, sanitized status/logs and graph node; provider keys in selected private `.env`, companion key in private `companion-auth.json`; never descriptors, browser output or argv. |
| XI–XII | Catalog/profile/install function, manifests/readiness, README architecture/counts/setup, SOUL, TOOLS, `.env.example`, server README, skill, HUD node and generated references all assigned below and in tasks. Agent-native registration is deliberately **not applicable** for the private bridge, following Tavus precedent, with explicit coverage/exclusion tests. |
| XIV | No messages, tickets, PRs or publications in this stage. Future milestone draft remains local pending review. |
| XV | OpenClaw adapter regression, explicit schema/storage migration, upgrade preservation, isolated bridge dependencies and source-qualified Hermes companion. |
| XVI–XVII | Numbered spec/design/tasks/analysis before code; local milestone blog draft and release evidence before completion. |

Result: design gate passes; implementation evidence is still required. No constitution deviation or waiver.

## Architecture and ownership

1. `scripts/runtime-selection.py` (Unix installer) and `scripts/runtime-selection.mjs` (HUD/Windows) implement the same small canonical selection contract and golden fixture set. This avoids adding Python to existing Windows OpenClaw launch prerequisites. A private stable UUID identifies the installation without exposing its home to the browser. Installer, launcher and HUD bootstrap resolve before loading `.env` or initializing state. Resolution, recorded Hermes interpreter identity and migration details are in [contracts/runtime-selection.md](contracts/runtime-selection.md).
2. `src/hud-server/runtime/` exposes the shared adapter contract. OpenClaw wraps existing `chat-runtime`, `chat-history`, `chat-usage` and gateway behavior with consistent selected environment. Hermes uses an official MCP client, never directly calls model providers.
3. `mcp-servers/hermes-hud-mcp/` provides private conversation/status tools and a durable ledger. `hermes_api.py` runs in the recorded, verified Hermes interpreter, installs its protected agent factory and private response/idempotency/session-store factories before construction, then exposes only allowed upstream routes. All companion databases reside under selected-home `netclaw-hud/hermes/`; the owner's native databases stay untouched. The bridge runs in its isolated component environment. It cannot be registered as an agent conversation tool. The companion lifecycle belongs to the explicit launcher; ordinary readiness checks do not start services.
4. HUD bindings authorize owners/conversations; the bridge ledger maps opaque handles to upstream sessions/runs and provides durable admission serialization. Every bridge call includes installation and conversation scope from the trusted HUD backend. Browser-supplied raw upstream IDs are never accepted. UI reads/polls revalidate ownership after I/O.
5. Browser storage also includes installation ID. Preserve old OpenClaw work with an explicit idempotent migration and backup; a Hermes selection displays other-origin work read-only until the matching installation is selected. No automatic cross-runtime transcript transfer.
6. Standard Chat and local Avatar share the same conversation. Canvas creates independent upstream sessions at branch points, with validated ancestor text seeded once. Progress is informational; companion-owned invocation/result records tied to the request establish actual tool execution, with native history as corroboration even after compaction. Unknown/interrupted output does not become a synthetic successful answer.

## Protected execution contract

The companion uses the selected Hermes provider configuration and qualified installed MCP tools. Its API route allowlist, constructor overrides and per-inference/per-dispatch guards are specified in [contracts/hermes-mcp.md](contracts/hermes-mcp.md). Pin all private source seams; compatibility mismatch stops readiness. Disabling optional hooks must not widen permission.

Runtime metadata distinguishes registered, qualified and execution-verified tools. A tool is read-only only after implementation/schema review and negative tests, not because of a discovery annotation. Skill content comes from a constrained installed root. Preserve explicit static instructions; suppress dynamic shared memory/history and alternate agent backends. Configuration apply is refused when an independent server-side policy cannot prove the existing authorization requirements. Preserve OpenClaw's established supported workflows; do not claim the HUD orchestration is a sandbox.

## Full HUD dependency treatment

| Surface/state | Implementation treatment |
|---|---|
| Chat, legacy chat, history, session tools | Common adapter and owner mapping; update classic `src/main.js`; remove global/latest-session fallback and migrate owned OpenClaw access explicitly. |
| Chat/Canvas/Avatar persistence | Runtime-namespaced `dashboard/chat-storage.js`, `canvas-chat/App.jsx`, server bindings; no view-switch dispatch or heuristic agent answers. |
| Terminal Intent | `terminal-intent-execution.js` and `terminal-intent-live.js` use adapter submission/evidence; existing `terminal-change-policy.js` and scoped records stay authoritative; unsupported Hermes APPLY denied before submission. |
| Models/settings/budgets/usage | Typed adapter capabilities; Hermes unavailable controls reject before dispatch/write. No fabricated zero usage. Include `server.js` budget writers and Terra key action. |
| Environment/configuration/logs/skills | Selected home only, safe projections and redaction; no repository credential fallback; separate shipped skill inventory from installed eligible tools. |
| Graph/readiness/security/Jev/native UI | Identify selected runtime and source; discovery is not execution verification; native link and Jev proof only when supported and attributable. |
| Other owned paths | Startup SSH known-hosts, aliases, topology grants, local change records, layout, RAG defaults and Jev interpreter resolve through selected installation; never change process HOME. |
| Federation/hosted Pal | Explicit Hermes unsupported state and backend rejection before dispatch; existing OpenClaw behavior intact. Local Avatar stays functional. |
| Installer/launch/upgrade | Persist selection, custom homes, component-private registration, source guards, preservation tests; native Windows early refusal for Hermes. |

## Delivery phases and validation

Foundation establishes schemas, pinned compatibility probes and deterministic fixtures before UI work. US1 delivers selection/readiness; US2 real agent execution and protections; US3 ownership and views; US5 recovery; US6 preservation/launch; US4 full panels. Cross-cutting completion requires all stories, coherence, regression and real acceptance. A launch-only checkpoint is useful but is not feature completion.

See [quickstart.md](quickstart.md) for validation and conditional WSL handoff. After Mac implementation/testing, determine whether Linux/WSL evidence can be collected locally. If another machine is required, prepare `validation-handoff.md` with exact branch/commit, setup, commands, checks and return criteria; the owner offered to switch then. Unrun environments remain unverified and feature validation remains open.

Source-only planning does not establish safety or live compatibility. The protected-agent bypass suite is a release-blocking gate, not an optional follow-up. Failure requires a fix or an explicit scope/design revision; never mark the feature complete by merely hiding its required read-only tool functionality.

## Project Structure

```text
specs/148-hermes-hud-integration/
  spec.md baseline.md research.md plan.md data-model.md quickstart.md tasks.md
  contracts/{runtime-selection,hermes-mcp,hud-runtime}.md
  checklists/requirements.md
mcp-servers/hermes-hud-mcp/                    # new private integration
  server.py ledger.py hermes_api.py protected_agent.py policy.py README.md
config/python-components/hermes-hud.txt
config/hermes-hud-compatibility.json           # revision/schema qualification
config/hermes-hud-tool-policy.json             # curated identities/schema digests, no secrets
scripts/runtime-selection.{py,mjs}
ui/netclaw-visual/src/hud-server/runtime/
  index.js selection.js openclaw.js hermes.js mcp-client.js capabilities.js
ui/netclaw-visual/src/hud-server/               # existing bindings/history/settings/etc.
ui/netclaw-visual/src/{dashboard,canvas-chat}/  # existing views/stores
tests/hermes-hud/                              # controlled provider/tool/agent fixtures
tests/unit/                                   # selection/installer/coherence regressions
workspace/skills/hermes-hud-diagnostics/SKILL.md
```

Existing component launcher, installer catalog/steps/access/runtime manifests, auto-registration filters, root PowerShell launchers, UI `server.js`, Terminal Intent files, CI/contract registry and generated references are updated in place. No new frontend application or network automation implementation.

## Complexity Tracking

No constitution violations. The extra companion is justified by effective-tool and memory isolation missing from the unrestricted upstream API. The private source seam is small, pinned and tested; an unqualified upgrade is a reported compatibility failure, not an opportunity for fallback.
