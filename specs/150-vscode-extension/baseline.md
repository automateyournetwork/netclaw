# Spec150 source baseline and coverage inventory

Inspected 2026-10-10 at source commit `d332344d5a039e5ee0f2a2202c556ba28e2af206` (NetClaw source 1.8.0, spec149 branch). This is a source-based product gap assessment, not live qualification or the formal Spec Kit cross-artifact analysis. No extension implementation exists in this change.

## Existing product evidence

- [HUD navigation and guide inventory](../../ui/netclaw-visual/src/dashboard/model.js) defines Overview, Chat, Canvas, Risk of Claws, External neighbours, Mobile devices, Science Officer, Network, Knowledge, Operations, Integrations, Settings, RAG, Configuration, Tokenomics, Documentation, Logs, Security and Avatar. Avatar is a conversation interface; the HUD also links classic utilities.
- [Dashboard](../../ui/netclaw-visual/src/dashboard/Dashboard.jsx) provides observed status, entity inspectors, source/freshness labels, per-Claw inventory, investigation drafts and rich views. Several operations are investigation entry points rather than management forms.
- [HUD server](../../ui/netclaw-visual/server.js) exposes configuration, chat, RAG, budget, federation, topology and terminal routes. Route availability differs by selected runtime; route presence does not establish suitability as a remote extension contract.
- [Local access controls](../../ui/netclaw-visual/src/security/local-access.js) and [access guide](../../docs/HUD-ACCESS.md) establish a trusted-local boundary. The documented authenticated remote path is SSH. Binding a trusted interface is not user authentication. A VS Code extension must preserve these boundaries rather than exposing the HUD publicly or relaxing origin checks.
- [Configuration projection](../../ui/netclaw-visual/src/hud-server/configuration.js) returns names/presence and catalogue information. The classic environment editor accepts replacements without returning cleartext. The extension needs explicit conflict detection, redacted review, secret replacement semantics and authoritative verification for managed edits.
- [Runtime settings](../../ui/netclaw-visual/src/hud-server/runtime-settings.js) describe selected configuration; [runtime selection](../../ui/netclaw-visual/src/hud-server/runtime/selection.js) and [bindings](../../ui/netclaw-visual/src/hud-server/bindings.js) establish installation and conversation boundaries to preserve.
- [Tokenomics](../../ui/netclaw-visual/src/hud-server/tokenomics.js) aggregates bounded local OpenClaw records, with missing/malformed/truncated evidence. Hermes reports owned-request usage; current HUD aggregate Tokenomics is unavailable for Hermes. Per-Claw availability must remain explicit.
- [Security posture](../../ui/netclaw-visual/src/hud-server/security-posture.js) reads configuration and queries OpenShell status. It is not proof that every configured control is active. [Risk security guidance](../../docs/SECURITY-MODES.md) and [Risk architecture](../../docs/N2N-RISK.md) distinguish host enforcement from sandbox concepts.
- [Hermes HUD guide](../../docs/HERMES-HUD.md), [federation guide](../../docs/HERMES-FEDERATION.md) and [spec149 verification](../149-hermes-ncfed-federation/verification.md) limit qualification. Do not expand support claims merely because this extension can render a control.
- [Mobile build configuration](../../mobile/netclaw-mobile/pubspec.yaml) selects [assets/icon/icon.png](../../mobile/netclaw-mobile/assets/icon/icon.png), a 1024×1024 PNG, as the launcher image. This is the required extension branding source, rather than an invented logo or a similarly named unused asset.

## Complete domain coverage

Every row is required for the complete product. Planning must map rows to exact extension entry points, backend contracts, supported actions, tests and documentation. Existing unsupported runtime features receive an honest limitation state; missing extension work on an otherwise supported reference backend is not an acceptable release substitute.

| HUD/domain | Required extension experience | Requirements |
|---|---|---|
| Overview | Active identity, harness, role, readiness, partial failures, source freshness and next actions | FR-003–006, FR-014–015, FR-037 |
| Chat | Owned conversations, explicit selected context, provider/model/effort where supported, task/tool activity and results | FR-009–013 |
| Canvas | Branching investigations, sourced artifacts, saved work and context transfer without implicit send | FR-011–012, FR-030 |
| Avatar/native harness interfaces | Supported Avatar in editor; authenticated native interface entry, preserving capability restrictions | FR-011, FR-017 |
| Risk of Claws / iN2N | Border and members, harness/model/tools/skills, posture, delegation and permitted lifecycle controls | FR-014–017, FR-021–026 |
| External neighbours / eN2N | Identity/trust, advertised inventory, peering, peer conversations, qualified tool/skill work and exact approvals | FR-014–017, FR-022, FR-024 |
| Mobile and edge | Enrollment/connectivity, capabilities, consent-sensitive actions and runtime limits | FR-014, FR-017, FR-033 |
| Science Officer / Jev | Task-owned assessments, reconsideration, budgets, influence and advice-only authority | FR-032 |
| Network | Configured inventory, routing, observed topology, rich relationship views and supported terminal/intent investigation | FR-013, FR-022–023, FR-030 |
| Knowledge | Memory validity, GCF measurements, meeting evidence and provenance-aware context | FR-031 |
| Operations | Incidents/changes, pending approvals, current work, evidence and verification | FR-013, FR-022–024, FR-034 |
| GAIT | Branch/turn browsing, task links, pre/post evidence, outcome, immutable export | FR-024, FR-029 |
| Integrations | MCP and skills inventory, dependencies, configuration/discovery/reachability distinctions and management entry points | FR-015, FR-018–020, FR-028 |
| Settings | Provider/model, harness, operating role, supported service lifecycle, client versus backend preferences | FR-007–009, FR-018–021 |
| Configuration / .env | Searchable inventory, field status, secret replacement, redacted diff, conflict protection and verification | FR-018–020, FR-036 |
| RAG | Explicit upload/indexing, collection scope, retrieval and citations | FR-012, FR-031 |
| Tokenomics | Source-qualified tokens, cache, costs, budgets and honest unavailable aggregation | FR-027 |
| Documentation / guides | Setup, troubleshooting, Sean's existing guidance, contextual CLI/API references | FR-034 |
| Logs / diagnostics | Source/time/severity filtering, task correlation, bounded reads, redacted local export | FR-029 |
| Security / DefenseClaw | Guardrail mode, tool rules, scans, events, settings and actual enforcement evidence | FR-022, FR-025–026 |
| OpenShell | Gateway/sandbox status, policy and supported lifecycle controls; distinct host-confinement evidence | FR-021–022, FR-025–026 |
| Distribution and editor integration | Mobile branding, native navigation, trust/accessibility, compatibility, VSIX and observed Marketplace release | FR-001–008, FR-035–040 |
| Copilot and terminal agents | Opt-in NetClaw MCP access for VS Code Copilot, Claude Code and Codex; explicit installation/grant/disclosure scope, owned requests and denial of self-approval | FR-041–044 |

## Preliminary findings for planning

| ID | Priority | Finding | Required resolution |
|---|---|---|---|
| B01 | High | Existing trusted-local HUD access is not a general authenticated remote API. | Choose a supported local/SSH/remote-host model with endpoint identity, installation binding, scoped credentials and no origin/auth bypass. |
| B02 | High | The HUD mixes viewers, investigation prompts and direct controls. Full platform management exceeds several current forms/contracts. | Identify and implement missing permitted management operations through existing authority/MCP paths; cover denial, conflict, baseline and verification. |
| B03 | High | Harnesses expose different capabilities and evidence. | Pin a tested backend compatibility matrix; do not promise arbitrary Hermes tool/write/media/production support. |
| B04 | High | Displaying an approval or selecting lab mode cannot approve arbitrary work. | Reuse exact backend approvals and the scoped Terminal Intent API lifecycle. Keep collector authority read-only. |
| B05 | High | Multiple profiles and extension hosts introduce target confusion and uncertain outcomes. | Bind state and operations to installation/operator identity, disclose host location and reconcile unknown work without replay. |
| B06 | Medium | Runtime, source and extension versions need separate release evidence. | Define compatibility, upgrade/migration/recovery checks and an actual Marketplace installation gate. |
| B07 | Medium | Publisher account, unique publisher/extension identifiers and publishing credentials have not been inspected. | Obtain owner-selected publisher details during release preparation; do not invent registration or availability. |
| B08 | Medium | Some package/privacy risks do not exist in the current HUD deployment shape. | Inspect the packaged file allowlist; exclude private evidence and secrets; test untrusted content, Restricted Mode and redacted diagnostics. |
| B09 | High | External assistants can share the operator's OS user and send tool results to their own model providers. | Separate server-enforced grants, minimal explicit result disclosure and independently validated human/backend approvals; client names, tool lists or separate executables are not isolation. |

## Official VS Code constraints consulted

Checked 2026-10-10; these are planning inputs, not a commitment to a particular library or implementation.

- VS Code exposes workbench contribution points for commands, views and other native integration, supporting the requested resource-oriented experience. [Extension capabilities](https://code.visualstudio.com/api/extension-capabilities/overview).
- Rich custom editor content can use webviews, whose security and resource handling need deliberate design. [Webview guidance](https://code.visualstudio.com/api/extension-guides/webview).
- Remote development changes where an extension runs and where files, loopback services and persisted data live. Host placement must be tested explicitly. [Remote development guidance](https://code.visualstudio.com/api/advanced-topics/remote-extensions).
- Restricted Mode can declare limited support and restrict workspace-supplied configuration; enabling workspace trust is distinct from backend authorization. [Workspace Trust](https://code.visualstudio.com/api/extension-guides/workspace-trust).
- Marketplace publication requires an actual publisher identity and release process; a VSIX can also be distributed. The listing icon cannot be SVG, so the mobile PNG is suitable source material. Publishing credentials and the current supported automation mechanism must be reviewed when preparing release. [Publishing extensions](https://code.visualstudio.com/api/working-with-extensions/publishing-extension).
- Extension identity, supported editor version and declared capabilities belong in the manifest and must agree with the tested product. [Manifest reference](https://code.visualstudio.com/api/references/extension-manifest).

## Constitution and workflow gates

- Owner clarification: this extension manages an EXISTING NetClaw / Risk. Backend installation, bootstrap and upgrades are outside scope; extension installation/updates, settings, federation and supported existing-service lifecycle remain required. Missing prerequisites lead to guidance, not automatic provisioning.
- Owner platform clarification: desktop VS Code on macOS/Windows/Linux, including Remote SSH and mandatory WSL; managed hosts are native Linux, WSL Linux and macOS. Plan a real Windows-desktop/WSL-Linux acceptance gate and separate host/distribution identity. Browser/Codespaces/Dev Containers and native Windows NetClaw hosting are outside the first release. Existing spec149 WSL qualification gaps are dependencies, not grounds to waive this requirement.
- Owner assistant clarification: built-in Copilot, Claude Code and Codex must inspect, delegate and propose managed changes through MCP, subject to existing NetClaw authorization and approvals. Self-approval is excluded. Private human controls are not registered with those assistants. See [research.md](research.md) for official client support and the revised minimum editor version.
- Principles I–IV and VIII: observation, real baseline, change control, GAIT and verification apply to extension-initiated operations. The user-provided AGENTS.md defines the exact Local/Lab exception and the stricter destructive-command prohibition.
- Principles V and VII: new operational capabilities remain MCP-native; presentation reuse does not justify implementing vendor/device execution directly in the extension. Planning must explain any new client-facing presentation contract without treating it as an independent authority path.
- Principles IX, XIII and XIV: least privilege, approved credential sources and human-directed external communication/publication remain mandatory. Client connection credential handling must explicitly reconcile with the repository's credential policy; do not copy backend provider keys into editor settings.
- Principles X–XII and XV: plan all applicable installer/catalog, HUD, skill, environment-example, configuration and documentation touchpoints, plus preservation of current clients and dependency isolation. Applicability must be justified per artifact rather than silently waived.
- Principle XVI: ratified requirements precede implementation. Technical planning and task derivation precede formal analysis. The [analyze skill](../../.agents/skills/speckit-analyze/SKILL.md) states: “This command MUST run only after `/speckit.tasks` has successfully produced a complete `tasks.md`.” No plan or tasks are fabricated to claim a completed cross-artifact review.

## Evidence limits

No extension package, live extension connection, Marketplace identity, release, network operation or new harness qualification was tested in this session. Startup `pyats_list_devices` returned the existing unsupported `connections.defaults.arguments` testbed-schema error. MemPalace could not resolve its installed component. GAIT session branch and recording worked. These observations are not live network-state evidence.
