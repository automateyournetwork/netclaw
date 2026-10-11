# Editor experience and domain contract

One desktop workspace extension at `extensions/netclaw-vscode/`, minimum VS Code 1.102.0, `extensionKind: ["workspace"]`. It runs locally on macOS/Linux, within WSL2 or on a Remote SSH host. A local Windows window uses an explicit supported SSH destination or offers Reopen in WSL. No silent Windows-to-Linux path conversion. Non-folder and multi-root windows require explicit profile selection, not inferred workspace trust or directory identity.

## Workbench surfaces

- Activity Bar container `netclaw`; views `netclaw.connections`, `netclaw.estate`, `netclaw.operations`, `netclaw.integrations`, `netclaw.knowledge`, `netclaw.security`, `netclaw.help`. Grouped navigation exposes every domain below without one Activity Bar icon per section.
- Commands: `netclaw.addConnection`, `netclaw.selectConnection`, `netclaw.disconnect`, `netclaw.removeConnection`, `netclaw.openOverview`, `netclaw.openChat`, `netclaw.openCanvas`, `netclaw.openAvatar`, `netclaw.addSelectedContext`, `netclaw.openSettings`, `netclaw.prepareChange`, `netclaw.reviewProposal`, `netclaw.openGait`, `netclaw.openTokenomics`, `netclaw.openLogs`, `netclaw.openDocumentation`, `netclaw.configureAssistant`, `netclaw.revokeAssistant`, `netclaw.exportDiagnostics`. Resource actions use typed IDs, not arbitrary URLs/commands.
- Status Bar always names installation, extension-host context, harness and readiness. Output Channel `NetClaw` is redacted and bounded. Operations show cancellation requested separately from cancellation confirmed.
- Restricted Mode supports help, walkthrough and non-executing saved-profile labels only. No auto-connect, process launch, operational call or workspace-driven configuration. Trust changes do not grant backend privileges.
- Mobile PNG is the Marketplace/listing icon. Derive a legible monochrome Activity Bar mark from the same asset and preserve recognizable branding. No generated replacement mascot.

## All-domain implementation map

Planned view files are under `extensions/netclaw-vscode/src/views/`; shared backend adapters under `ui/netclaw-visual/src/management/`. A table row is complete only with real supported behavior plus explicit source/empty/stale/denied/unavailable states.

| Domain | Entry/view | Contract / shared adapter | Required working action and evidence |
|---|---|---|---|
| Overview | `overview.ts` | identity/resources; `identity.js` | Inspect actual binding, readiness, role and next actions. |
| Chat | `chat.ts`, bundled Chat | conversation/request; `conversations.js` | Send explicitly, follow owned result, context preview, model/effort where supported. |
| Canvas | `canvas.ts`, existing Canvas adapter | workspace + conversations; `workspace.js` | Branch/save/resume/import/export versioned investigations without implicit send. |
| Avatar/native harness | `avatar.ts` | conversations + validated navigation | Supported local Avatar conversation; authenticated native UI navigation, no embedded secret URL. |
| Risk / iN2N | `estate.ts` | resources/change/request; `federation.js` | Member identities, enrollment/disable/enable on existing estate, qualified delegation. |
| eN2N | `peers.ts` | resources/change/request; `federation.js` | Trust/peering proposals, permitted peer chat/tool/skill, exact approvals. |
| Mobile/edge | `mobile.ts` | resources + existing consent adapters; `workspace.js` | Inspect enrollment/connectivity, explicitly request only qualified consent-sensitive operations. |
| Science Officer | `science.ts` | assessment-read/reconsider; `workspace.js` | Task-owned advice, original/reconsidered result, budget and influence. |
| Network | `network.ts`, rich topology | resources/evidence/Terminal Intent; `intent.js` | Inventory vs observed/simulated topology, existing terminal investigation and exact scoped intent lifecycle. |
| Knowledge | `knowledge.ts` | memory/gcf/meeting; `workspace.js` | Retrieve provenance/validity-aware context, no current-state claim from memory. |
| Operations | `operations.ts` | events/operation/change; `proposals.js` | Review exact proposal/approval requirements and follow verification/recovery. |
| GAIT | `gait.ts` | evidence; `evidence.js` | Filter/browse append-only session/turns, linked artifacts and deliberate redacted export. |
| Integrations | `integrations.ts` | resources/configure; `configuration.js` | Catalog/install/discovery/reachability/verified states and supported configuration; no dependency installation. |
| Settings | `settings.ts` | snapshot/change; `configuration.js`, `runtime.js`, `lifecycle.js` | Harness/provider/model/mode/budget/settings, real supported service control and restart impact. |
| Configuration/.env | `configuration.ts` | snapshot/change; `configuration.js` | Typed fields, secret presence, explicit replacement/clear, revision conflict and redacted diff. |
| RAG | dedicated `rag.ts` panel, native Knowledge entry and Open RAG command | workspace; `workspace.js`, shared `rag-mcp` | Reviewed bounded upload, durable indexing outcome, collection search, citations, confidence/age warnings and explicit context selection for Chat/Canvas. No implicit LLM request or workspace ingestion. |
| Tokenomics | `tokenomics.ts` | usage snapshot; `evidence.js` | Actual request/local scope, missing Hermes aggregate, budgets and estimate provenance. |
| Documentation | `documentation.ts` | approved local docs index; `workspace.js` | Search guides including Sean's existing guidance, setup/troubleshooting and CLI/API references. |
| Logs | `logs.ts` | evidence; `evidence.js` | Bounded time/source/severity filtering, truncation, diagnostic review and local export. |
| DefenseClaw | `security.ts` | security snapshot/change; `security.js` | Scans/rules/events, supported guardrail settings, actual effective mode. |
| OpenShell | `openshell.ts` | security + service control; `security.js`, `lifecycle.js` | Gateway/sandbox policy and owned lifecycle; distinct host-confinement evidence. |
| Distribution/editor | manifest/walkthrough/help | release contract | Published install/update/preservation, mobile icon and accessible native navigation. |
| Copilot/terminal clients | `clients.ts` and `src/clients/` | assistant contract; `clients.js` | Opt-in discovery/setup, grant/disclosure review, durable requests, revocation. |

## Webview boundary and content

Bundle views locally with restrictive CSP (`default-src 'none'`, nonce-scoped scripts and minimal local resource roots); no direct network requests to HUD/backend, arbitrary command URIs or external script loads. Use VS Code resource URIs for media and typed messages to the extension host. Validate each message against its view instance, installation generation, request ID and allowed command schema before calling MCP. Ignore stale-view responses after profile changes. Enforce result/attachment size bounds, escape Markdown/HTML and validate external URL destinations before explicit navigation. No credentials appear in rendered state or webview persistence.

Per-installation/editor-principal drafts survive reload with explicit local retention. Backend is authoritative for owned requests; existing Canvas browser data is imported only through a versioned explicit export/import, never cookie scraping. Native harness navigation opens its authenticated route without weakening framing or credentials. Avatar uses supported existing assets/providers and sends no prompt simply by switching view or character.

## Accessibility and responsiveness

Every action has a label, keyboard path, visible focus and meaningful disabled reason; status never relies only on color. Light/dark/high-contrast theme tests cover all essential flows. Paginate and virtualize large trees/logs, cancel stale reads, keep failures localized and mark cached values stale. Required fixture sizes and p95 timings are in SC-004. Product telemetry defaults off; local diagnostic export is deliberate and previewed. No remote telemetry service is added in this release.
