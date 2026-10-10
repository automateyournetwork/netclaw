# Feature Specification: NetClaw for Visual Studio Code

**Feature Branch**: `150-vscode-extension`
**Created**: 2026-10-10
**Status**: Clarified draft — ready for design review; not yet ratified for implementation
**Input**: Build a full, published VS Code extension that people install and point at their NetClaw installation, comparable to managing Docker or Kubernetes from VS Code. Cover the HUD sections, GAIT, Tokenomics, LLM providers, OpenClaw/Hermes harnesses, standalone/Risk operation, eN2N/iN2N, environment settings, DefenseClaw, OpenShell and the wider NetClaw experience. Use the mobile app logo. Follow SDD, clarify and analyze before implementation.

## Product scope

NetClaw for VS Code is an operator workbench for existing NetClaw installations. Engineers connect an installation, inspect its capabilities, converse with its selected runtime, operate its permitted tools and federation, manage configuration, and follow work through approval, execution, verification and audit without leaving their editor.

The extension manages an existing standalone NetClaw or an existing Risk of Claws. It includes permitted settings, selection among installed qualified harnesses/providers, federation management and supported start/stop/restart controls. Installing, bootstrapping or upgrading NetClaw, its harnesses and their dependencies is outside scope. Membership/enrollment controls operate on the existing estate and do not imply provisioning new hosts or installing runtimes. Installing and updating the VS Code extension itself remains in scope.

The first release supports desktop VS Code on macOS, Windows and Linux, including Remote SSH and WSL workspaces. Existing NetClaw hosts on native Linux, Linux within WSL and macOS are required targets. WSL support is a release requirement, including Windows desktop VS Code managing a NetClaw inside WSL. Dev Containers, Codespaces, browser-based VS Code and native Windows NetClaw hosting are outside the first-release matrix.

The extension provides a NetClaw Activity Bar entry, resource explorer, context actions, Command Palette commands, active-installation status, diagnostic output and rich editor views. Chat, Canvas, topology and detailed dashboards remain usable inside VS Code. Opening the existing HUD or native harness interface is a secondary navigation action. Core operations must be available within the extension.

The product also supports natural-language access through VS Code's built-in Copilot and terminal agents such as Claude Code and Codex, using explicit client connections to NetClaw's MCP interface. These clients can inspect, delegate natural-language work and propose managed changes under existing NetClaw authorization and approval rules. They do not replace its selected OpenClaw/Hermes harness or inherit human approval authority.

All existing HUD domains are in scope. The [coverage inventory](baseline.md) identifies the current source and minimum extension treatment. Priorities sequence delivery; they do not remove lower-priority domains from the first complete release. A missing backend management operation is a delivery dependency that must be tracked, rather than silently replaced with a nonfunctional button. Runtime-specific limitations remain visible and do not authorize expanding a runtime's tool or security qualification.

Actors are the installation owner/operator, an operator with restricted backend permissions, and the extension release maintainer. The extension respects existing authority; a UI role, workspace trust decision, capability card or successful connection never grants additional operational permission.

The requested outcome includes a publicly installable Visual Studio Marketplace release and a downloadable VSIX of the same version. This specification session does not implement or publish it.

## Clarifications

### Session 2026-10-10

- Q: Should the extension manage existing installations only, or also install/bootstrap/upgrade NetClaw and its runtime dependencies? → A: A — manage an EXISTING NetClaw / Risk. Include permitted configuration and supported service controls; exclude NetClaw/runtime installation, bootstrapping and upgrades.
- Q: Which VS Code environments should the first release support? → A: A — desktop VS Code on macOS, Windows and Linux, including Remote SSH and mandatory WSL support. Existing NetClaws run on Linux, WSL Linux and macOS; all three host families are required targets.
- Q: How much control should Copilot, Claude Code and Codex have through NetClaw's MCP interface? → A: Inspect, delegate, and propose managed changes. Execution remains governed by NetClaw's existing authorization and approval rules; assistants cannot approve their own changes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Install and connect to the right NetClaw (Priority: P1)

An engineer installs the NetClaw extension from the Marketplace, recognizes the mobile app branding, adds an existing installation, and sees its identity, version, harness, readiness and operating mode. They can keep multiple named connections and select the intended target explicitly.

**Why this priority**: Every later action depends on a correct, authenticated installation binding.

**Independent Test**: Install the packaged extension into a clean editor profile, connect two distinct installations, switch between them, and confirm isolated configuration, tasks and history.

**Acceptance Scenarios**:

1. **Given** an installed, reachable NetClaw, **When** the operator connects using an explicit location and approved credentials, **Then** the explorer shows verified installation identity, backend version, OpenClaw or Hermes, standalone or Risk role, and supported/unavailable capabilities.
2. **Given** an invalid credential, changed host identity, incompatible version or stopped service, **When** connection is attempted, **Then** the failure identifies that condition and offers a recovery action without silently choosing another installation.
3. **Given** two profiles with identical display names, **When** the active target changes, **Then** stable identity distinguishes them and drafts, credentials, selected entities, requests and audit references do not cross targets.
4. **Given** an untrusted workspace, **When** it is opened, **Then** no workspace-defined executable, automatic connection or remote mutation runs; the extension explains its restricted capabilities.
5. **Given** a missing or incompatible NetClaw installation or harness, **When** the connection is checked, **Then** the extension reports the unmet prerequisite and links the existing setup/upgrade guidance without installing or upgrading backend software.
6. **Given** Windows desktop VS Code attached to a WSL Linux workspace with an existing NetClaw, **When** the operator connects, performs qualified work and reconnects after a WSL restart, **Then** the extension uses that Linux installation and its actual credentials, paths and services, preserves owned work and never substitutes the Windows host or another WSL distribution.
7. **Given** a local macOS/Linux workspace or a Remote SSH workspace targeting an existing Linux, WSL Linux or macOS NetClaw, **When** the operator connects, **Then** the active editor/extension-host context and managed installation are explicit and the same authorization, isolation and recovery rules apply.

---

### User Story 2 - Work with NetClaw from the editor (Priority: P1)

An engineer asks NetClaw questions, reviews proposed operations, shares selected editor context, and follows tool activity and results using their existing provider and selected harness. They use ordinary Chat or the branching Canvas and can inspect available Avatar and native harness views.

**Why this priority**: The extension must drive real NetClaw work and retain its investigation experience.

**Independent Test**: Complete a permitted read-only task through each harness, attach deliberately selected context, inspect sourced output, and recover the same owned request after the editor reloads.

**Acceptance Scenarios**:

1. **Given** a connected installation and qualified tool, **When** a request is submitted, **Then** the selected backend executes it with visible task identity, source, progress, actual outcome and available usage evidence.
2. **Given** text selected in an editor, **When** Add to NetClaw Context is invoked, **Then** a reviewable draft identifies the selection and source; transmission requires sending that draft. Merely opening or switching files sends nothing.
3. **Given** an interrupted request, **When** the editor reloads or reconnects, **Then** it reconciles the owned task and distinguishes running, completed, failed, cancellation requested and unknown outcomes without replaying the request.
4. **Given** an unavailable harness feature, **When** its view is selected, **Then** the limitation and recovery or qualification requirement are shown without substituting another harness or generating fictional results.
5. **Given** saved Canvas investigations, **When** they are opened and continued through the extension, **Then** branches, evidence references and saved content survive; switching Chat, Canvas or Avatar does not send a prompt.

---

### User Story 3 - Inspect and manage the NetClaw estate (Priority: P1)

An operator navigates a standalone installation or a Risk of Claws, sees Border and member roles, inspects per-Claw harness/provider/tools/skills, and operates internal and external federation within their permissions.

**Why this priority**: Standalone, iN2N and eN2N are central deployment models, not separate extension products.

**Independent Test**: Inspect a standalone installation, a mixed Risk, an all-Hermes Risk and an external peer; perform qualified delegation and a permitted lifecycle operation, including a denied operation.

**Acceptance Scenarios**:

1. **Given** a Risk, **When** its explorer is expanded, **Then** Border, internal members, external neighbours, mobile/edge devices and advisors have distinct identities, trust boundaries, timestamps, harnesses and advertised versus verified capabilities.
2. **Given** an eligible internal member or external peer, **When** the operator requests supported work, **Then** existing delegation, peer trust, admission, expiry and exact-action approval rules govern execution and the originating request retains its evidence.
3. **Given** a permitted membership or peering change, **When** the operator reviews and applies it, **Then** the exact target and impact are displayed, baseline and audit are captured, and authoritative post-change state is verified.
4. **Given** a stale card, disconnected edge device or missing enforcement evidence, **When** status is rendered, **Then** the extension preserves stale, disconnected and unknown states without inferring removal, trust or production readiness.

---

### User Story 4 - Manage configuration and runtime operation (Priority: P1)

An owner manages provider/model choices, harness selection, integration environment settings, budgets, installation mode and supported service lifecycle actions with clear scope, validation and recovery.

**Why this priority**: Configuration and operational control distinguish the requested workbench from a status viewer.

**Independent Test**: Change a nonsecret setting and replace a synthetic secret, review the redacted change, reject a concurrent edit, apply a supported update and verify actual state after any necessary restart.

**Acceptance Scenarios**:

1. **Given** a selected installation, **When** Settings opens, **Then** the source and effective scope of every field are clear, unset differs from unreadable, and secret values are not revealed.
2. **Given** a supported change, **When** Apply is selected, **Then** validation, a redacted before/after review, required approval, baseline, recovery and post-change verification occur; unrelated settings are preserved.
3. **Given** a changed backend configuration revision, **When** an older draft is submitted, **Then** the conflict is reported and no newer value is silently overwritten.
4. **Given** a running operation, **When** a harness switch, restart or mode change would affect it, **Then** the operator sees the affected work and required disposition before any change. Merely selecting a connection profile does not change the backend harness.
5. **Given** a value saved but not yet applied by the service, **When** status refreshes, **Then** configured, pending restart and running state remain distinguishable.

---

### User Story 5 - Follow approvals, GAIT and security enforcement (Priority: P1)

An engineer follows an operation through its change record, baseline, approval, execution, verification and immutable GAIT trail, while inspecting DefenseClaw and OpenShell evidence and controls.

**Why this priority**: A new frontend must retain NetClaw's operational boundaries and make them understandable.

**Independent Test**: Attempt an unapproved production change, inspect its refusal, then exercise an approved synthetic workflow and trace its complete evidence. Verify separate testing, production, degraded and unavailable security states.

**Acceptance Scenarios**:

1. **Given** a production configuration action without an approved Implement-state CR, **When** it is requested, **Then** the backend refuses it and the extension explains the unmet gate.
2. **Given** a Terminal Intent Local/Lab request, **When** it is prepared, **Then** only explicitly designated endpoints and the existing API-created record, real artifacts and APPLY phase can enable its scoped change; an extension-wide lab toggle cannot approve other operations.
3. **Given** an audited task, **When** GAIT is opened, **Then** its session branch, turns, baseline, approval references, verification and outcome can be followed without rewriting prior records.
4. **Given** a DefenseClaw or OpenShell setting change, **When** it is reviewed, **Then** the UI names the actual enforcement mechanism and affected scope, applies only authorized supported changes and verifies effective posture.
5. **Given** missing confinement or guardrail evidence, **When** production posture is shown, **Then** missing/degraded controls remain explicit and operations requiring them stay denied.

---

### User Story 6 - Understand usage, integrations, logs and network evidence (Priority: P2)

An operator uses Tokenomics, MCP/skill inventory, network views, telemetry, logs and diagnostic reports to understand costs, availability and problems.

**Why this priority**: Everyday operation needs more than chat results and service-up indicators.

**Independent Test**: Load known usage records with missing fields, an unavailable integration, stale network observations and redacted logs; filter them and open their supporting evidence.

**Acceptance Scenarios**:

1. **Given** recorded usage, **When** Tokenomics is opened, **Then** provider/model, time window, input/output/cache tokens, costs, budgets and data gaps are shown for the actual reported scope; unknown cost is not zero and estimates are labeled.
2. **Given** configured MCP servers and skills, **When** Integrations is opened, **Then** configuration, installation, discovery, endpoint access and successful execution evidence are distinct; a configured tool is not described as tested.
3. **Given** logs and task events, **When** a filter or diagnostic export is requested, **Then** results identify installation, source, time and truncation, and secrets are redacted before display/export.
4. **Given** inventory and topology evidence, **When** Network is opened, **Then** configured inventory, observed topology, federation relationships and simulation have distinct labels and source times.

---

### User Story 7 - Use the wider HUD workspace (Priority: P2)

An engineer retrieves RAG knowledge, recalls memory, reviews Science Officer advice, inspects mobile devices and opens NetClaw documentation and guides from the same workspace.

**Why this priority**: Full HUD coverage includes the supporting evidence and guidance that make operations useful.

**Independent Test**: Upload a selected nonsensitive test document, retrieve a citation, distinguish a memory observation from current state, open a task-owned Jev assessment and inspect mobile capability limits.

**Acceptance Scenarios**:

1. **Given** authorized RAG collections, **When** a selected document is uploaded or searched, **Then** indexing state, scope, citations and retrieval errors are visible; workspace-wide ingestion never happens automatically.
2. **Given** memory, GCF or meeting context, **When** it informs an investigation, **Then** provenance, recorded validity and measured versus estimated quantities remain visible.
3. **Given** a Jev assessment, **When** it is opened, **Then** original/reconsidered advice, budget and effect on the recommendation belong to the originating task; advice does not supply execution authority.
4. **Given** an enrolled mobile device, **When** capabilities or capture controls are inspected, **Then** existing consent and harness limitations remain enforced; offline does not mean unenrolled.
5. **Given** an operator seeking help, **When** Documentation is opened, **Then** searchable setup, troubleshooting, CLI/API references and existing guides explain the selected version and context.

---

### User Story 8 - Install, update and support the published extension (Priority: P2)

A user discovers a complete Marketplace listing, installs a tested version, connects using the walkthrough, updates without losing profiles, and can diagnose or roll back an incompatible release.

**Why this priority**: Publication, installation and maintenance are part of the requested product outcome.

**Independent Test**: Install the actual published package in a clean supported environment, complete connection, update from the previous candidate and verify retained state; compare its version and contents with the release VSIX.

**Acceptance Scenarios**:

1. **Given** the public listing, **When** a user installs it, **Then** the mobile logo, publisher identity, supported environments, backend requirements, screenshots, setup, privacy behavior, license and support links match the shipped extension.
2. **Given** an extension update, **When** the editor reloads, **Then** profiles and owned history references remain valid and a backend incompatibility produces an actionable error rather than migration or execution without consent.
3. **Given** the release package, **When** its contents are inspected, **Then** it contains no operator environment file, credentials, private network evidence, local audit databases or unrelated runtime installation.
4. **Given** publication completion, **When** release evidence is reviewed, **Then** it includes the Marketplace URL, observed published version and clean-install connection result; producing a local VSIX alone does not close delivery.

---

### User Story 9 - Drive NetClaw through Copilot and terminal agents (Priority: P1)

An engineer uses natural language in VS Code Copilot, Claude Code or Codex to inspect an explicitly connected NetClaw/Risk and ask NetClaw to perform work within the client's granted scope. Other MCP-compatible clients can use the documented interface without claiming untested client support.

**Why this priority**: Natural-language control should be available in the engineer's chosen assistant, alongside NetClaw's own editor views.

**Independent Test**: Connect each named client to an existing qualified installation, ask for its Risk members and harnesses, submit an allowed request, inspect the owned outcome and confirm that the client cannot approve its own change or access another client's records.

**Acceptance Scenarios**:

1. **Given** an explicitly connected installation and enabled Copilot MCP access, **When** the user asks which Claws and harnesses are present, **Then** Copilot can discover and invoke the scoped NetClaw tools and return sourced results tied to that installation.
2. **Given** Claude Code or Codex configured for that host's NetClaw MCP connection, **When** the user makes an allowed natural-language request, **Then** the client can submit and follow it with stable request identity and correlated GAIT; VS Code need not remain open for this terminal connection.
3. **Given** a request outside the client's grant or requiring approval, **When** an assistant attempts it or supplies an approval-like statement, **Then** the backend refuses or returns the actual pending approval state; client tool confirmation, model text and client name do not substitute for NetClaw approval.
4. **Given** a WSL/Remote SSH context or multiple connected installations, **When** a client discovers or invokes tools, **Then** its execution host and installation remain explicit; the current editor selection does not silently retarget an existing conversation.
5. **Given** an external assistant and delegated NetClaw inference, **When** results and costs are shown, **Then** the external assistant's model and NetClaw's harness/provider are distinct, and only measured usage is attributed to each. Private evidence is shared only under the operator's explicit disclosure scope.

### Edge Cases

- The same display name occurs on different installations, members or tenants; identity must not depend on that label.
- A local and remote extension host both have a loopback address and similarly named configuration files; the selected execution host and installation must remain explicit.
- Multiple WSL distributions contain similarly named installations; distribution shutdown/restart, changed forwarding ports and Windows/Linux path differences must not redirect a profile, expose a credential or replay uncertain work.
- A service restarts, the selected harness changes, credentials are revoked, or a profile is switched while a request is running; uncertain work must not be replayed or rebound.
- An external peer advertises unavailable tools, a forged harness label or instructions in metadata; metadata remains data and never authorizes execution.
- Authentication succeeds but discovery, a capability or an individual tool is denied; partial access must be reported accurately.
- A log/usage source is unavailable, truncated or outside the retained time range; absent data is not a zero count or healthy result.
- A settings form contains a mask, blank field, unknown key, multiline value or concurrent external edit; secrets and unrelated content must be preserved.
- Runtime configuration is saved but the running daemon still uses old values, or restart/rollback fails; the actual state and unresolved work must be retained.
- An SSH host key or certificate changes, a tunnel drops, a port is occupied, or a server redirects elsewhere; credentials and actions must not follow an unverified destination.
- Multiple editor windows act on the same installation; ownership, configuration revisions and approval scope prevent cross-window interference.
- Restricted Mode, no-folder windows, multi-root workspaces, offline startup, inaccessible secret storage, keyboard-only input and high-contrast themes must have defined behavior.
- Oversized files, hostile Markdown/links, malformed events and large federation inventories must not enable commands, reveal secrets or freeze the editor.
- Extension removal must not uninstall NetClaw, stop independently owned backend services, remove backend data or revoke unrelated credentials.
- Copilot or a terminal agent is disabled by organization policy, lacks MCP/tool support, runs in another host context or loses a client grant; report that condition without weakening policy or registering unrestricted tools.
- External assistants may send tool results to their own model providers; a client connection must disclose the boundary and use explicit minimal result-sharing scope. A client label is not authentication and its native tool confirmation is not a NetClaw change approval.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The extension MUST ship as a discoverable Visual Studio Marketplace extension and an installable VSIX with versioned release notes, backend compatibility requirements and independently verifiable release evidence.
- **FR-002**: Branding MUST reuse the existing mobile app logo at `mobile/netclaw-mobile/assets/icon/icon.png`; required size/theme adaptations MUST preserve that identity, and the Activity Bar mark MUST remain legible in light, dark and high-contrast themes.
- **FR-003**: The extension MUST provide native navigation, contextual actions, searchable commands, active-target status and diagnostic output alongside rich views; every HUD domain in the coverage inventory MUST have a tested extension entry point and functional supported workflows.
- **FR-004**: Operators MUST be able to add, validate, rename, select, disconnect and remove named installation profiles without changing backend state merely by changing the active profile.
- **FR-005**: Connections MUST verify endpoint and installation identity, backend compatibility, harness, role and capabilities before enabling operations; local and authenticated remote access MUST preserve existing trust boundaries and reject unverified destinations.
- **FR-006**: Profiles, credentials, drafts, task references, history and selected resources MUST be isolated by installation and operator scope, including across editor windows and remote execution hosts.
- **FR-007**: The extension MUST manage an existing standalone NetClaw or Risk of Claws through inspection, permitted configuration and supported start/stop/restart controls. It MUST NOT install, bootstrap or upgrade NetClaw, its harnesses or their dependencies. Missing or incompatible prerequisites MUST produce actionable guidance. Installation and updates of the extension itself remain required.
- **FR-008**: The first release MUST support desktop VS Code on macOS, Windows and Linux with local, Remote SSH and WSL workspace contexts as applicable, managing existing NetClaw installations on native Linux, WSL Linux and macOS. Windows desktop VS Code with a WSL Linux NetClaw MUST pass dedicated live acceptance before release; it is not optional or satisfied by native-Linux simulation. Profiles MUST retain the intended host/distribution identity across reconnect/restart. Dev Containers, Codespaces, browser-based VS Code and native Windows NetClaw hosting are outside this release matrix.
- **FR-009**: Core NetClaw operation MUST use the selected installation's existing provider/model credentials and permitted backend execution path without requiring a Copilot subscription or separately configuring provider secrets in the editor.
- **FR-010**: Chat MUST support owned conversations, drafts, streaming or reported progress, sourced tool activity, result artifacts and backend-supported model/effort selection, with explicit unavailable states per runtime.
- **FR-011**: Chat, Canvas and supported Avatar workflows MUST be accessible within the editor and preserve existing saved work; native harness UI navigation MUST retain its own authentication without credentials in URLs or framing bypasses.
- **FR-012**: Sharing editor selections/files or RAG uploads MUST require deliberate selection and a reviewable destination; the extension MUST NOT automatically ingest workspace content or treat embedded instructions as authority.
- **FR-013**: Long-running work MUST expose durable owned request references and distinguish admission, running, waiting for approval, completion, failure, cancellation requested, confirmed cancellation, interruption and unknown outcome. Reload/reconnection MUST reconcile without automatic resubmission.
- **FR-014**: The explorer MUST represent standalone, Border/member roles, iN2N membership, eN2N neighbours, mobile/edge nodes and advisors separately, with stable identity, scope, source time and freshness.
- **FR-015**: Every inspected Claw MUST expose available harness type/version, provider/model, MCP servers, tools, skills, knowledge and posture, distinguishing advertised/configured information from verified execution and unknown metadata.
- **FR-016**: Supported member lifecycle, peering/trust management, delegation, peer conversation and permitted remote tool/skill actions MUST be operable through the existing authority and audit model, with exact target and impact review for mutations.
- **FR-017**: OpenClaw, Hermes, mixed Risks and all-Hermes Risks MUST be represented without silently falling back between runtimes. The extension MUST enforce reported and independently qualified capability limits; unsupported Hermes writes, media or production controls MUST remain unavailable.
- **FR-018**: Settings MUST cover selected harness, provider/model, standalone/Risk configuration, integration environment fields, budgets and supported lifecycle controls. The editor MUST distinguish client preferences, backend configured state and effective runtime state.
- **FR-019**: Secret fields MUST expose only set/unset/unreadable status; replacement and clearing MUST be explicit operations. Masks, omitted fields and empty drafts MUST NOT overwrite existing secrets. Provider/integration credentials MUST remain in the installation's approved credential source.
- **FR-020**: Configuration changes MUST validate against supported settings, show a redacted difference and target, detect concurrent edits, preserve unrelated data, capture baseline/recovery information, honor applicable approval and verify effective state. Restart-required, failed and rolled-back outcomes MUST be visible.
- **FR-021**: Runtime lifecycle and harness/mode changes MUST identify affected active work and owned processes, use supported management operations and preserve installation state. Reconnecting or uninstalling the extension MUST NOT terminate unrelated services.
- **FR-022**: Production mutations MUST retain incident prechecks, approved Implement-state change control, real baseline/rollback evidence, authoritative verification and failure escalation. No extension action may bypass a denied backend tool or create approval evidence.
- **FR-023**: Terminal Intent Local/Lab MUST retain the exact scoped exception in AGENTS.md: designated endpoints, explicit configuration intent, API-created local record, real preparation artifacts, APPLY phase and verification. Questions grant no writes; collector grants remain read-only.
- **FR-024**: Operational sessions and changes MUST be recorded in GAIT with installation, actor, target, request, approval, baseline and outcome references. GAIT must be inspectable/filterable without rewriting history; audit failure MUST visibly prevent operations that require it, except the existing scoped Local/Lab local-audit rule.
- **FR-025**: DefenseClaw views MUST cover configured versus effective guardrail mode, component scans, tool rules, security events and supported settings; OpenShell views MUST cover observed gateway/sandbox status, policy and supported lifecycle/settings actions.
- **FR-026**: Posture MUST distinguish testing, production enforced, degraded, observe-only, disabled and unavailable controls as applicable. OpenShell sandboxing, host confinement, guardrails and audit are separate evidence; no UI preference may assert enforcement or enable denied production execution.
- **FR-027**: Tokenomics MUST expose available provider/model/request usage, input/output/cache tokens, recorded/estimated cost, budgets and observation window/scope. Missing usage and unsupported aggregation MUST remain explicit; no cross-member total may be invented from local records.
- **FR-028**: Integration and skill inventory MUST distinguish catalogued, installed, configured, discovered, reachable and execution-verified states and provide descriptions, prerequisites, diagnostics and supported management entry points.
- **FR-029**: Logs, task events and diagnostic exports MUST support source/time/severity filtering where supplied, bounded retrieval, visible truncation, redaction and deliberate local export, while retaining source references for audit.
- **FR-030**: Network and topology views MUST preserve configured versus live versus historical versus simulated provenance. Federation relationships MUST NOT be presented as physical cabling or device-health observations.
- **FR-031**: RAG, memory, GCF and meeting-context workflows MUST preserve distinct stores, owner/scope, citations, recorded validity and data-quality limits; retrieval is not a current network observation.
- **FR-032**: Science Officer views MUST preserve task ownership, advice-only authority, original/reconsidered assessments, budget and reported effect on a recommendation.
- **FR-033**: Mobile/edge inventory and permitted operations MUST preserve enrollment versus connectivity state, existing consent and runtime restrictions. The extension MUST NOT auto-quarantine endpoints or silently initiate capture/notifications.
- **FR-034**: Documentation MUST include searchable NetClaw guides, setup, troubleshooting, CLI/API references, version compatibility and contextual help; external communication and public publication retain explicit release/operator authorization.
- **FR-035**: Restricted Mode MUST permit safe onboarding/help but MUST block workspace-defined execution, automatic connections, configuration writes and operational dispatch until the required trust and backend authority exist. Trusting a workspace MUST NOT grant backend privileges.
- **FR-036**: Backend text, files, metadata and links MUST be treated as untrusted content. Commands, credential access, executable paths and outgoing destinations MUST be validated against the selected operation and installation; secrets MUST NOT reach ordinary settings, source control, logs, rendered content or extension telemetry.
- **FR-037**: The extension MUST remain responsive under partial failure and large inventories, expose loading/empty/stale/denied/incompatible states distinctly, and support keyboard navigation, accessible labels and native theme changes.
- **FR-038**: Private network evidence and content MUST remain within the operator-authorized installation/client boundary. Product telemetry MUST default off, and any optional diagnostics MUST disclose and minimize their contents before transmission.
- **FR-039**: Backend additions needed for complete workflows MUST be designed through NetClaw's existing MCP integration and authority patterns. Existing HUD/mobile/CLI behavior and runtime isolation MUST receive regression coverage; extension controls MUST NOT duplicate vendor/device execution outside those paths.
- **FR-040**: Release completion MUST include the supported environment/runtime matrix, package-content inspection, clean installation, upgrade/recovery checks, applicable installer/catalog/HUD/skills/configuration/documentation coherence, and an observed public Marketplace installation of the exact released version.
- **FR-041**: The extension MUST offer explicit opt-in discovery/connection of scoped NetClaw MCP tools for VS Code Copilot, with visible installation/host binding, supported-client prerequisites, organization-policy failures and a disconnect/revocation path. Core extension functionality MUST remain usable without Copilot.
- **FR-042**: The product MUST provide verified setup and natural-language workflows for Claude Code and Codex using the same versioned agent-facing NetClaw MCP contract. Terminal access MUST use an existing installation and work independently of the editor process after configuration; client configuration changes MUST be reviewable and preserve unrelated registrations.
- **FR-043**: External assistants MUST be able to inspect permitted state, delegate natural-language requests within their grants and submit reviewable managed-change proposals. NetClaw MUST enforce existing authorization and approval rules for execution, including within delegated harness/tool calls. External assistants MUST NOT approve their own operations, receive private human-management tools, bypass denied tools or broaden their grants by supplying client names, origins, prompts or identifiers. A proposal is not execution authority; refusal or pending approval MUST remain visible to the originating client.
- **FR-044**: Each external-client connection MUST bind authenticated principal, grant, installation and owned requests; support explicit revocation; distinguish client versus NetClaw harness/provider usage; retain GAIT provenance; and disclose/control tool-result sharing to the client's model provider. No provider credentials or unrestricted workspace ingestion may be exposed through the connection.

### Key Entities *(include if feature involves data)*

- **Connection profile**: Operator-owned label, explicit connection location, host context, credential reference and last verified installation identity; label is not identity.
- **Installation**: Stable identity, backend version, selected harness/root, role, capability and readiness evidence, effective configuration revision and security posture.
- **Resource**: Installation-scoped Border, member, external neighbour, edge device, advisor, integration, skill or network object; includes authoritative identifier, source, freshness and permitted actions.
- **Conversation and operation**: Owned conversation/request identifiers, origin context, selected installation, inputs, lifecycle state, events, usage, artifacts and uncertainty/cancellation information.
- **Configuration change**: Target/scope, prior revision, redacted proposed difference, secret replacement intentions, baseline/recovery references, approval, restart impact and verified result.
- **Audit and approval record**: Immutable evidence linking actor, operation, exact authority, baseline, change-control decision and observed outcome; local lab records remain a distinct scoped type.
- **Usage observation**: Provider/model, request and reporting scope, time window, measured tokens, estimated/recorded costs, budget and missing-data indicators.
- **Release**: Publisher/extension identity, extension version, compatible backends/environments, approved icon, packaged artifact identity, qualification evidence and observed publication status.
- **External assistant connection**: Authenticated principal and installation, client label/version as descriptive metadata, server-enforced grant, result-disclosure scope, owned request references, revocation/expiry and observed client compatibility. Distinct from the NetClaw runtime harness and the human operator connection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On each supported environment, a new user with a reachable compatible installation and valid credentials can install, connect and complete one qualified read-only request within five minutes using the shipped walkthrough. Release evidence MUST include real macOS and Linux clients, Windows desktop with WSL Linux, and Remote SSH connections to the required host families; WSL acceptance additionally covers distribution identity and shutdown/reconnect without request replay.
- **SC-002**: All coverage-inventory domains have a tested entry point and documented action disposition; every required workflow works on a qualified reference deployment. A missing implementation cannot pass by being labeled unavailable. Genuine backend/runtime limitations are tested separately.
- **SC-003**: Qualification covers standalone OpenClaw/Hermes, the four internal Border/member harness pairings, Hermes↔Hermes and Hermes↔OpenClaw external interaction in both directions, and OpenClaw regression. Existing qualification limits and selected environment evidence are recorded individually.
- **SC-004**: With 100 members, 100 external peers and 1,000 integration/tool rows in qualification fixtures, local navigation/filtering completes within one second at the 95th percentile; after a successful source refresh, updated state is visible within two seconds. Backend/inference latency is reported separately.
- **SC-005**: All profile-switch, multiple-window, host-identity-change, revocation and cross-installation tests preserve isolation; no request, secret, history item or approval is applied to a different installation.
- **SC-006**: Every tested mutation produces linked baseline, applicable approval, audit, verification and recovery outcome; every tested unapproved production request and out-of-scope lab request is refused.
- **SC-007**: In disconnect, editor-reload and backend-crash tests, no uncertain mutation or conversation request is automatically re-executed; existing owned work can be reconciled and genuine unknown outcomes remain visible.
- **SC-008**: All synthetic secret markers are absent from package contents, logs, ordinary settings, UI messages, exports and telemetry in the security qualification suite; secret replacement preserves unspecified values and rejects concurrent changes.
- **SC-009**: Known usage fixtures reconcile exactly within their stated reporting scope, with all unavailable usage and estimation flags preserved and no fabricated zero costs or estate-wide totals.
- **SC-010**: Keyboard-only users can complete connection, navigation, chat, settings review and GAIT inspection; light, dark and high-contrast checks reveal no inaccessible essential control or status.
- **SC-011**: Installing, updating, disabling and uninstalling the extension preserves backend configuration, independent processes and saved investigations in every lifecycle acceptance case.
- **SC-012**: Release evidence identifies a live Marketplace listing, observed published version, downloadable matching VSIX and a successful clean-profile install/connection. Local packaging alone does not satisfy this criterion.
- **SC-013**: Actual VS Code Copilot, Claude Code and Codex each complete discovery, a natural-language inventory question and an allowed owned request against NetClaw; denial, self-approval attempts, revocation, cross-client isolation and lost-response/no-replay cases pass. Include real WSL and Remote SSH client contexts, record exact client versions and exercise OpenClaw and Hermes targets within qualified scope. A generic MCP fixture alone does not satisfy named-client acceptance.

## Assumptions

- The owner confirmed management of an existing NetClaw / Risk only. FR-007 excludes backend installation, bootstrapping and upgrades while retaining permitted settings, federation and supported existing-service lifecycle controls. Harness selection requires an already installed, qualified runtime.
- The owner confirmed desktop VS Code on macOS/Windows/Linux with Remote SSH and mandatory WSL. Required managed-host families are native Linux, WSL Linux and macOS. Planning must name concrete tested versions and valid client/context/host combinations; WSL evidence cannot be replaced by a Linux fixture or silently deferred beyond release. The owner also requested a handoff and runnable continuation prompt for their real Windows/WSL NetClaw, with all SDD artifacts committed and pushed for transfer; see [windows-wsl-handoff.md](windows-wsl-handoff.md).
- Native VS Code navigation and rich editor views are the default product approach. Dedicated NetClaw chat works independently of other AI products. Copilot, Claude Code and Codex MCP access are additional required client integrations; users supply their own enabled client/account and explicit grants. No Copilot subscription is required for the extension's own workflows.
- Local installation paths and authenticated remote access are required. Exact connection protocol, extension-host placement, credential mechanism and compatibility versions belong to planning, grounded in [baseline.md](baseline.md).
- Readiness and support are established per installed backend capability. This feature does not itself qualify every possible Hermes tool or introduce new federation authority, wire protocols or a multi-tenant cloud service.
- Existing avatar/capture functionality is exposed only where supported; this feature does not create a new avatar generation, model-training or mobile application product.
- Public Marketplace distribution is required. Additional registries and other editor products are outside this spec unless explicitly added. The owner will identify an authorized Marketplace publisher before publication; none is assumed registered or available.
- Exact backend and extension release numbers will be selected under the repository release policy at implementation/release time; source, mobile and extension components need not have matching version numbers.
- This branch starts from spec149 commit `d332344d5a039e5ee0f2a2202c556ba28e2af206`. Spec149's outstanding Linux/WSL and physical-mobile qualifications remain limitations, not inherited passes.
- Clarifications precede technical planning. Plan and tasks will be generated before formal cross-artifact analysis, then reviewed before implementation; this draft is not ratified by its creation.
