# Feature Specification: Hermes integration with the NetClaw HUD

**Feature Branch**: `148-hermes-hud-integration`
**Created**: 2026-10-10
**Status**: Implemented for acceptance — Mac automated qualification passed; real-browser, owner-provider and Windows/WSL gates remain open (see validation.md)
**Input**: User description: "Hermes does NOT currently connect to NetClaws HUD if the user deploys Hermes instead of OpenClaw; I need this addressed please"

## Problem and intended outcome

NetClaw offers Hermes as an installation choice, but its HUD still depends on OpenClaw for agent conversations and several runtime-dependent views. Selecting Hermes must lead to a usable NetClaw HUD backed by the selected Hermes installation. Operators must not need to install, configure or start OpenClaw to make a Hermes deployment work.

The HUD must retain its existing shared experience while accurately representing the runtime, capabilities and evidence available to it. A working page is not evidence that the selected agent can answer or use its configured tools. The existing OpenClaw experience must remain functional.

The reported gap is corroborated by repository inspection, recorded in [baseline.md](baseline.md). Live Hermes operation has not been reproduced or certified during specification.

## Clarifications

### Session 2026-10-10

- Q: Should spec 148 also make Hermes execute n2n/iN2N federation? → A: Federation will be a separate spec, 149. Spec 148 covers Hermes HUD integration and accurate reporting of federation availability; it does not port federation execution to Hermes.
- Workflow direction: The owner delegated planning through analysis and authorized automatic remediation of analysis findings, with a report before implementation starts.
- Validation direction: After implementation/Mac tests, prepare a Windows WSL Ubuntu test handoff if needed; the owner can switch machines to finish validation and then return to Mac for the next spec.

## User Scenarios & Testing

### User Story 1 — Launch the HUD for the selected runtime (Priority: P1)

An operator installs NetClaw with Hermes, starts the HUD through the documented launch path, and sees that it is connected to the intended Hermes installation.

**Why this priority**: The installation choice must carry through to the product the operator uses.

**Independent Test**: Use an isolated Hermes installation without an OpenClaw executable, configuration or running service. Launch the HUD and verify its runtime identity and connection status.

**Acceptance Scenarios**:

1. **Given** a configured Hermes deployment, **When** the operator launches the HUD, **Then** the HUD selects that Hermes installation and reports its actual readiness without requiring OpenClaw.
2. **Given** the operator uses a custom Hermes home, **When** the HUD starts, **Then** configuration, credentials and runtime-owned records come from that selected home rather than a default or another runtime.
3. **Given** both runtimes are installed, **When** Hermes is selected, **Then** the HUD continues to use Hermes after restart and does not silently select an available OpenClaw installation.
4. **Given** no explicit runtime selection on an existing OpenClaw installation, **When** it is upgraded and started, **Then** existing OpenClaw behavior remains the default.

### User Story 2 — Converse with Hermes and use authorized NetClaw tools (Priority: P1)

An operator sends a HUD message to Hermes, receives its real response, and can use eligible tools and skills already configured for that installation under the existing authorization controls.

**Why this priority**: A HUD connection must reach the selected agent and its operational capabilities, not stop at a model-only conversation.

**Independent Test**: Complete a five-turn conversation through the HUD, including a follow-up that depends on prior context and a harmless registered tool with a known result. Verify execution through the selected Hermes agent and retain the tool result's provenance.

**Acceptance Scenarios**:

1. **Given** Hermes is ready, **When** the operator sends a message, **Then** the request reaches Hermes and the HUD displays the returned answer with truthful runtime attribution.
2. **Given** an ongoing conversation, **When** the operator asks a contextual follow-up, **Then** Hermes receives the correct conversation context without unrelated conversation content.
3. **Given** an installed, eligible and authorized tool, **When** a request requires it, **Then** Hermes can invoke that tool through the established NetClaw access path and the result can be traced to the actual invocation.
4. **Given** a missing tool or denied operation, **When** the request cannot complete, **Then** the HUD reports the limitation and does not fabricate a successful result or obtain broader permissions through another runtime.
5. **Given** a request requiring production approval or a scoped Local/Lab change record, **When** it originates in the Hermes HUD, **Then** the same applicable authorization, baseline, verification and audit requirements are enforced as for other supported ingress paths; if those controls cannot be enforced, the operation is refused before dispatch.

### User Story 3 — Keep conversations usable across HUD views (Priority: P1)

An operator uses standard Chat, Canvas and the existing local Avatar presentation with Hermes while retaining the intended conversation and keeping separate work isolated.

**Why this priority**: Runtime selection should not remove the established HUD workspace or mix independent investigations.

**Independent Test**: Exercise a Hermes conversation in Chat and the local Avatar view, create two independent Canvas branches, and reopen an owned HUD conversation. Compare each result with its intended context and another browser session's records.

**Acceptance Scenarios**:

1. **Given** a Hermes chat, **When** the operator switches between Chat and the existing local Avatar view, **Then** the same chat remains selected and switching alone sends no message or tool request.
2. **Given** existing saved Canvas work and two conversation branches, **When** the operator continues either branch with Hermes, **Then** saved content remains intact and only the chosen branch's context is used.
3. **Given** a saved HUD conversation owned by the current authenticated session, **When** the operator reopens it after refresh, **Then** its available transcript is restored and follow-up messages continue the corresponding Hermes conversation.
4. **Given** another browser session or a different selected runtime, **When** it requests a conversation it does not own, **Then** access is refused and neither messages nor tool results leak across that boundary.
5. **Given** the selected runtime has no supported native browser interface, **When** the operator sees native-interface navigation, **Then** the HUD explains its unavailability and does not offer a misleading OpenClaw link.

### User Story 4 — Inspect and manage the selected runtime honestly (Priority: P2)

An operator can understand the active runtime's configuration, available models, installed tools and skills, logs and usage without being shown another installation's state.

**Why this priority**: Correct operational context is needed to troubleshoot and use the agent reliably.

**Independent Test**: Use distinct synthetic configuration, model, tool, log and usage values for Hermes and OpenClaw. Select Hermes and verify that the HUD presents only the selected runtime's values or a specific unavailable state.

**Acceptance Scenarios**:

1. **Given** Hermes is selected, **When** runtime and configuration panels load, **Then** the HUD names Hermes and shows only safe, relevant information from its configured sources; secret values remain masked or absent.
2. **Given** a model or effort control is offered, **When** the operator applies a selection, **Then** it is supported by the selected runtime and takes effect for the intended conversation, or the HUD reports rejection before sending a message with misleading settings.
3. **Given** configured tools, skills, logs or usage records, **When** their HUD views load, **Then** the source and availability are accurate. Configured tools are not described as executable solely because a registration exists.
4. **Given** a metric or control is unsupported, unavailable or unverified, **When** its panel loads, **Then** it displays that specific state rather than a fabricated value, a false zero or an OpenClaw value.
5. **Given** an existing HUD action permits configuration edits, **When** an authorized edit is made on a Hermes deployment, **Then** it changes only the selected installation's intended setting and preserves unrelated configuration and credentials.

### User Story 5 — Recover from connection failures without duplicating work (Priority: P1)

An operator gets actionable Hermes-specific failures and can recover without losing context or accidentally repeating an operation that may already have executed.

**Why this priority**: Network automation requires a distinction between a failed connection and an operation with an unknown outcome.

**Independent Test**: Exercise missing configuration, stopped runtime, rejected authentication, unsupported compatibility, interrupted responses and runtime restart using controlled fixtures.

**Acceptance Scenarios**:

1. **Given** a readiness failure, **When** the operator opens or uses the HUD, **Then** it identifies the affected runtime, distinguishes the failure category and provides a relevant recovery action.
2. **Given** a request times out or loses its response after submission, **When** the HUD cannot establish its outcome, **Then** it reports the outcome as unknown and does not automatically replay a potentially executed tool action.
3. **Given** Hermes becomes available again, **When** the operator retries a readiness check, **Then** the HUD updates its status and permits new requests without switching runtime or resetting unrelated work.
4. **Given** an unsupported or invalid runtime selection, **When** the HUD starts, **Then** it reports the selection error rather than falling back to OpenClaw or issuing requests elsewhere.

### User Story 6 — Adopt Hermes HUD support without breaking existing installations (Priority: P1)

An operator updates an existing NetClaw installation and retains their runtime configuration, credentials, tools, skills and saved work.

**Why this priority**: The fix must be usable by existing Hermes users and safe for the established OpenClaw path.

**Independent Test**: Upgrade isolated, populated Hermes and OpenClaw installations, compare their preserved data, and run the relevant HUD acceptance flows against each runtime.

**Acceptance Scenarios**:

1. **Given** an existing Hermes installation, **When** the operator follows the documented update steps, **Then** the HUD can connect without reinstalling OpenClaw, replacing personal configuration or re-entering preserved credentials.
2. **Given** an existing OpenClaw installation, **When** the update completes, **Then** Chat, Canvas, local Avatar, history, model controls and relevant operational panels retain their established supported behavior.
3. **Given** runtime-specific support limits, **When** the operator reads installation and HUD guidance, **Then** the tested versions, supported features and any necessary migration steps are explicit.

### Edge Cases

- Both runtimes are installed, but only the unselected runtime is reachable.
- A custom runtime home contains spaces, is missing, is unreadable or has malformed configuration.
- Launching from a new shell or a different working directory loses installation-time environment variables.
- Hermes is running, but its model provider, a registered tool or a required permission is unavailable.
- A response is empty, malformed, partial or arrives after the client disconnected.
- Two conversations submit concurrently; one browser session expires while a request or history read is in progress.
- A saved conversation belongs to an old runtime selection or an unavailable runtime installation.
- Usage or tool activity is unsupported, stale or inaccessible; an empty result must not imply a healthy or idle system.
- A model or effort option disappears between discovery and submission.
- Local speech is unavailable on a host even though text chat works; this does not make the agent connection appear broken.
- A runtime-native interface or an OpenClaw-only federation feature is unavailable on Hermes.

## Requirements

### Functional Requirements

- **FR-001**: The documented HUD launch path MUST honor the selected installation runtime and its configured home across startup and restart. Existing default OpenClaw behavior MUST remain supported. (US1)
- **FR-002**: A Hermes HUD deployment MUST function without an installed or running OpenClaw agent or its configuration. It MUST NOT silently substitute OpenClaw or bypass Hermes by answering directly through a model provider. (US1, US2, US5)
- **FR-003**: The HUD MUST display the selected runtime and distinguish configuration availability, connection readiness and verified agent/tool execution. A running HUD alone MUST NOT establish agent readiness. (US1, US4, US5)
- **FR-004**: HUD chat MUST reach the selected Hermes agent, preserve the intended conversation context and display its real response. Local explanatory or error text MUST NOT be represented as an agent answer. (US2)
- **FR-005**: Hermes HUD requests MUST use eligible tools and skills configured for the selected installation under its access restrictions. Eligibility requires verified authorization and conversation-isolation properties; registration alone is insufficient. Ineligible operations MUST be visibly unavailable. Successful operational claims MUST retain evidence from the actual tool invocation. (US2)
- **FR-006**: Production change control, explicit Terminal Intent Local/Lab scope, baseline capture, rollback readiness, post-change verification, audit, destructive-command restrictions and tool-level authorization MUST remain applicable. Runtime integration MUST NOT create an alternative path around them. (US2)
- **FR-007**: Chat, Canvas and the existing local Avatar presentation MUST remain usable with Hermes for their shared conversation functions, including Canvas branch isolation and existing saved-work preservation. Existing platform limits on local presentation features MUST be identified separately from agent readiness. (US3)
- **FR-008**: Conversation ownership MUST bind to the authenticated HUD session, intended conversation and selected runtime installation. History, responses and tool results MUST NOT cross those boundaries. View changes MUST NOT submit work. (US2, US3)
- **FR-009**: Operators MUST be able to list and reopen their available Hermes-backed HUD conversations and continue the intended conversation. Missing or inaccessible history MUST be reported without overwriting current work. (US3)
- **FR-010**: Runtime identity, model information, configuration inventory, tool/skill availability, logs and usage views MUST use the selected runtime's relevant sources. Missing, failed, unsupported and unverified information MUST remain distinguishable. (US4)
- **FR-011**: Model and effort choices offered by the HUD MUST reflect supported capabilities. Applied selections MUST be confirmed or visibly rejected; unsupported controls MUST be unavailable with a reason. (US4)
- **FR-012**: Existing authorized configuration actions MUST target the selected runtime only, preserve unrelated data and continue to protect secrets from browser responses, navigation links, transcripts and diagnostic output. (US4, US6)
- **FR-013**: Runtime-native navigation MUST be offered only when a supported, configured destination exists. Hermes selection MUST NOT imply that OpenClaw's native interface is available or applicable. (US3)
- **FR-014**: Connection and compatibility failures MUST identify the selected runtime and provide a relevant recovery action. Responses MUST terminate within the documented request deadline rather than leaving an indefinite pending state. (US5)
- **FR-015**: Interrupted or timed-out work with an unconfirmed execution outcome MUST be reported as unknown. Reconnection MUST NOT silently replay potentially executed operations. (US5)
- **FR-016**: Browser access controls, session expiry/revocation, local access restrictions and credential protection MUST remain effective for both runtimes. Hermes support MUST NOT require exposing an unauthenticated runtime service. (US2, US3, US4)
- **FR-017**: Installation and update flows MUST preserve owner-managed configuration, credentials, registered components, skills and saved work. Any required migration MUST be explicit and verifiable. (US6)
- **FR-018**: Shared HUD features MUST retain existing OpenClaw behavior. Runtime-specific unsupported features, including Hermes federation capabilities deferred to spec 149, MUST be clearly identified without disabling unrelated working HUD features. Spec 148 MUST NOT claim that connecting Hermes to the HUD enables federation execution. (US4, US6)
- **FR-019**: Delivery MUST include documented runtime/platform compatibility, runtime-specific setup and troubleshooting, acceptance evidence and the applicable constitution artifact-coherence updates. Source inspection or simulated responses alone MUST NOT certify live Hermes integration. (US1–US6)
- **FR-020**: Agent-assisted Terminal Intent MUST use the selected runtime boundary for supported operations. An operation whose required authorization cannot be enforced MUST be refused before dispatch, including configuration apply; direct terminal presentation MUST remain independent. Runtime integration MUST NOT weaken collector read-only grants or interpret an agent approval as change approval. (US2, US5, US6)
- **FR-021**: Browser persistence and server ownership MUST both identify the originating runtime installation. Existing OpenClaw work MUST be preserved through a documented migration; work from another installation MUST NOT be silently submitted as context. Global runtime memory or history retrieval MUST NOT expose another private HUD conversation. (US3, US6)
- **FR-022**: Pending requests MUST expose attributable progress and, where supported, an exact-operation approval or stop action. Approval MUST be scoped to the current owner and request; bulk or enduring authorization is prohibited. Stop acknowledgement MUST NOT be described as completed cancellation or rollback. Unsupported attachments or interaction modes MUST be rejected before submission while preserving the user's draft. (US2, US3, US5)

### Key Entities

- **Runtime installation**: The selected agent runtime, installation identity, configuration location, readiness state and supported capabilities.
- **HUD conversation**: An owned conversation associated with a runtime installation, its context, saved transcript and lifecycle state.
- **Agent request**: A conversation-bound user request with submission status, execution outcome and attributable response or failure.
- **Capability availability**: Whether a control, tool, skill or information source is supported, configured, verified, unavailable or failed.
- **Execution evidence**: Correlated observations establishing which runtime and tools handled a request, including authorization and verification results where applicable.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Every declared supported Hermes test environment completes HUD launch and a real five-turn conversation without an OpenClaw installation. At least one contextual follow-up and one harmless registered-tool invocation succeed with attributable results.
- **SC-002**: All tested Chat/local Avatar transitions and independent Canvas branches retain the intended context; owned saved conversations can be reopened and continued. Unauthorized cross-session and cross-runtime retrieval attempts disclose zero conversation content.
- **SC-003**: In coexistence and custom-home acceptance cases, Hermes HUD activity uses zero credentials, conversations or runtime-owned configuration from the unselected OpenClaw installation, and makes zero unintended writes to it.
- **SC-004**: All tested runtime-dependent controls and panels either operate against the selected runtime or show a specific limitation. No unsupported or unverified state is displayed as working, successful or a fabricated zero.
- **SC-005**: Each failure category in US5 produces an actionable result within its documented deadline. Timeout/restart tests produce zero automatic replays of operations whose execution outcome is unknown.
- **SC-006**: All applicable security and approval acceptance cases pass for Hermes and OpenClaw, including denied writes, expired sessions and unauthorized history access; no credential values appear in public HUD output.
- **SC-007**: Existing OpenClaw regression checks and the declared Hermes acceptance matrix pass without weakening assertions. Upgrade checks preserve all seeded owner-managed configuration and saved work, and any untested live/platform case is explicitly recorded as unverified.

## Scope, Assumptions and Dependencies

- This feature covers the NetClaw HUD connection to a selected Hermes installation, its shared conversation views, runtime-dependent controls and supporting installation/update guidance.
- Initial scope assumes one selected runtime installation per HUD instance. Safe coexistence is required; simultaneous runtime aggregation, per-message runtime switching and automatic history migration between runtimes are not required.
- Hermes is expected to have completed its own supported setup and have a usable provider/model and any tools needed for the requested operation. The HUD must report missing prerequisites; it must not assume that installation proves readiness.
- macOS and Linux are the intended host families, consistent with current NetClaw deployment work. The planning phase must establish the exact supported runtime versions and host matrix before implementation claims compatibility.
- Ubuntu under WSL2 is included in the qualification plan. Any required cross-machine handoff is decided after Mac implementation/testing; unrun platform acceptance remains open until evidence is collected.
- The shared HUD experience includes text Chat, Canvas, local Avatar conversation presentation and supported agent-assisted Terminal Intent. Initial Hermes attachment input, hosted avatar execution, exact model locks and effort controls may be unavailable where the qualified interface cannot honor them; rejection must precede submission. This does not require building a new Hermes-native browser interface, speech engine, hosted avatar service or model provider.
- Initial Hermes operational support requires qualified read-only tools and skills. Configuration execution is available only through a mechanically enforced existing authorization boundary; otherwise it is explicitly unavailable, including Terminal Intent APPLY. This feature does not create a new production change-control engine or grant raw shell/code execution to bypass unavailable tools. OpenClaw's existing supported change workflow remains covered by regression tests.
- The owner assigned Hermes federation support to separate spec **149**. Porting federation execution to Hermes is outside spec 148. Relevant HUD surfaces must still report their actual availability rather than imply Hermes federation parity; existing OpenClaw federation behavior must remain intact. No spec 149 branch or specification is created by this clarification.
- Porting mobile ingress or channel runtimes to Hermes is also outside spec 148. Their future scope is not decided here.
- Implementation design, transport choice and any new integration capability must satisfy the constitution, including MCP-native integration, least privilege, audit, backward compatibility and artifact coherence. Technical feasibility questions belong in planning; this specification does not presume that Hermes implements OpenClaw's interfaces.
- Human clarification is complete. The owner delegated technical planning, task generation and automatic analysis remediation. The next handoff reports implementation readiness and scope; it does not start implementation in this stage.
