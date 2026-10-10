# Feature Specification: Hermes NCFED federation

**Feature Branch**: `149-hermes-ncfed-federation`
**Created**: 2026-10-10
**Status**: Implemented; Mac acceptance recorded; Linux/WSL qualification pending T040
**Input**: User description: "spec 149 using well known SDD process - this time we need to fix Hermes-based builds iN2N (and eN2N) if Hermes is the border; it works for OpenShell but I dont think it does for Hermes; we just addressed Hermes and HUD and other integrations (check spec 148) - now we NEED to get NCFED working make sense any questions?"

## Problem and intended outcome

Selecting Hermes must produce a NetClaw deployment that can participate in NCFED federation. A Hermes Border must coordinate its internal members and interact with external peers, and Hermes must also work as a scoped member. Operators must be able to build mixed OpenClaw/Hermes Risks and all-Hermes Risks without installing OpenClaw on Hermes nodes.

Spec 148 delivered the shared Hermes HUD and explicitly reserved federation for spec 149. Existing federation execution, provisioning and capability discovery still assume OpenClaw; the Hermes HUD deliberately marks federation unavailable. The source evidence is recorded in [baseline.md](baseline.md). This paragraph records the pre-implementation baseline; current execution evidence is in verification.md.

A successful connection or capability advertisement is insufficient. Operators must be able to submit authorized work, observe the intended member or peer execute it, retrieve the actual result with provenance, and distinguish a refusal, unavailable dependency or unknown outcome from success. Existing OpenClaw federation and spec 148 conversation isolation must remain intact.

Terminology: **OpenClaw** and **Hermes** are agent runtimes. **OpenShell** is an optional security/sandbox component, not the alternative agent runtime. **iN2N** coordinates one operator's internal **Risk** behind a **Border**; **eN2N** connects consenting external operators. **NCFED** is the existing federation protocol used by these paths. Supporting Hermes does not change those trust boundaries.

## Clarifications

### Session 2026-10-10

- Q: Should spec 149 cover Hermes Borders only, or Hermes Borders and members across mixed and all-Hermes Risks? → A: Hermes Borders and members; mixed and all-Hermes Risks.
- Owner refinement: Carry the node's agent harness type alongside model, tools and other capability-card attributes. Harness identity is distinct from deployment type and security posture.
- Existing scope decision from spec 148: Hermes federation execution belongs to spec 149, separate from the completed HUD integration.
- Workflow: follow specify → human clarification → technical plan → derived tasks → analysis → implementation. On 2026-10-10 the owner authorized proceeding through all remaining stages, with analysis and no further clarification or stage-approval pause. Routine remediation is included; no stage is skipped.

- Owner scope expansion (2026-10-10): include the existing NetClaw mobile app against a Hermes Border, with protected operator execution, text/voice/Siri, permitted delegation, truthful task recovery, harness display, explicit attachment disposition and a verified client build. No additional clarification or app-store publication.

## User Scenarios & Testing

### User Story 1 — Start federation for the selected installation (Priority: P1)

An operator installs or upgrades a Hermes node, selects its Border or member role, and starts federation against that installation's configuration and identity.

**Why this priority**: Every later operation depends on using the correct runtime, identity and scoped credentials.

**Independent Test**: Start an isolated Hermes Border with a custom home and no OpenClaw executable, configuration or service. Restart from a different working directory and verify the same identity, selection and federation readiness.

**Acceptance Scenarios**:

1. **Given** a configured Hermes installation, **When** its federation services start, **Then** they use Hermes and the selected installation without requiring OpenClaw.
2. **Given** both runtimes are installed with different settings, **When** Hermes is selected and restarted, **Then** federation continues using the selected Hermes identity, credentials and state without borrowing the OpenClaw installation.
3. **Given** missing credentials, incompatible runtime or unavailable services, **When** startup is attempted, **Then** the operator receives the specific failing readiness stage and a recovery action; no fallback runtime is started.

### User Story 2 — Delegate internal work from a Hermes Border (Priority: P1)

An operator asks a Hermes Border to discover an internal member's eligible capabilities, route work to that member, and return its actual result.

**Why this priority**: Internal orchestration is the primary reported gap, and is useful independently of external federation.

**Independent Test**: From the Hermes HUD, discover an enrolled member, delegate a harmless skill and invoke a harmless member tool with known outputs. Retrieve asynchronous progress/results and verify Border and member evidence agree.

**Acceptance Scenarios**:

1. **Given** enrolled members and their scoped capabilities, **When** the operator views the Risk or asks Hermes to find a capability, **Then** the Border reports the correct identities, runtime kinds, freshness and availability without exposing secrets.
2. **Given** an authorized matching member, **When** Hermes routes a request or the operator selects that member, **Then** the member executes within its scope and the Border returns the result attributed to that member and task.
3. **Given** a long-running request, **When** the task remains active, **Then** progress and eventual results remain retrievable by their authorized owner without resubmitting the work.
4. **Given** one unavailable member and one healthy member, **When** independent requests target them, **Then** the first failure is reported without blocking the second; ambiguous work is not rerouted automatically.
5. **Given** a mixed Risk, **When** a member advertises its inventory and the operator inspects it, **Then** its harness type and available version appear alongside model/tools, with source and freshness; a legacy member that omits harness metadata is shown as unknown.

### User Story 3 — Run Hermes members in mixed and all-Hermes Risks (Priority: P1)

An operator provisions a Hermes member with a focused role, enrolls it into an existing Risk, and executes work using that member's selected model, tools and credentials.

**Why this priority**: A Hermes deployment must not require hidden OpenClaw members, and existing Risks need an incremental adoption path.

**Independent Test**: Exercise all four Border/member runtime pairs: Hermes/Hermes, Hermes/OpenClaw, OpenClaw/Hermes and OpenClaw/OpenClaw. For each, enroll, discover, delegate and retrieve a known result.

**Acceptance Scenarios**:

1. **Given** an all-Hermes installation without OpenClaw, **When** a member is provisioned and enrolled, **Then** it authenticates and executes authorized work using its own Hermes installation.
2. **Given** an existing OpenClaw Border, **When** a Hermes member joins, **Then** its identity, scope, health and execution integrate with the existing Risk without replacing other members.
3. **Given** a mixed Risk, **When** requests reach different members, **Then** each uses its selected runtime/model and only its assigned tools and credentials.
4. **Given** a supported on-demand or managed member, **When** it is started or recovers after a service restart, **Then** exactly one instance owns execution; production work is refused where required containment cannot be established.

### User Story 4 — Federate externally in both directions (Priority: P1)

Consenting operators use Hermes Borders to exchange capabilities, conduct peer chat and request qualified tools or skills across eN2N.

**Why this priority**: Fixing only internal routing would leave the explicitly requested external Border role incomplete.

**Independent Test**: Use isolated consenting peers to exercise Hermes↔OpenClaw and Hermes↔Hermes. In each direction, exchange inventory, conduct a contextual two-turn peer chat, invoke a known tool and delegate a known skill with result retrieval.

**Acceptance Scenarios**:

1. **Given** authenticated peers with mutual consent, **When** federation becomes ready, **Then** each receives the permitted capability inventory for the actual remote installation.
2. **Given** an enabled peer-chat relationship, **When** either peer sends a message and a contextual follow-up, **Then** the receiving node's selected runtime answers within that peer's conversation, without unrelated operator or peer context.
3. **Given** a valid scoped grant, **When** either peer requests a qualified tool or skill, **Then** execution and the returned result respect that grant and identify the executing node, runtime and task.
4. **Given** missing consent, expired/revoked permission, insufficient budget or a disabled relationship, **When** work is requested, **Then** it is rejected before execution with an actionable reason.
5. **Given** an external peer capability card, **When** harness metadata is present, absent, stale or unrecognized, **Then** consumers preserve the corresponding advertised/unknown/stale state without breaking capability exchange, granting authority or revealing the Border's internal member topology.

### User Story 5 — Retain control across delegation (Priority: P1)

An operator keeps the same approval, scope and disclosure controls when work passes through Hermes, internal members or external peers.

**Why this priority**: Runtime interoperability is not permission to weaken existing federation or network-change controls.

**Independent Test**: Attempt out-of-scope work, stale approvals, cross-peer result retrieval, permission revocation during admission, and external prompts requesting local secrets or broader delegation. Verify zero unauthorized executions or disclosures.

**Acceptance Scenarios**:

1. **Given** external peer input, **When** Hermes receives or forwards it, **Then** it remains attributable to that external peer and cannot acquire local-operator privileges by passing through a Border or member.
2. **Given** an operation requiring approval, **When** it is admitted, **Then** approval is bound to the actual requester, target and operation; denial or revocation prevents subsequent dispatch.
3. **Given** an authorized production configuration request, **When** execution is considered, **Then** the existing approved ServiceNow change, baseline, verification and audit controls still apply. A federation grant alone never approves a device change.
4. **Given** unavailable enforcement or an unqualified operation, **When** the request arrives, **Then** it is refused rather than executed through an unrestricted tool, different runtime or alternate path.

### User Story 6 — Observe results and recover without repeating work (Priority: P1)

An operator uses the existing HUD and command-line federation views to see real readiness, task progress, failures and audit records, then recovers from service or connection failures without duplicate execution.

**Why this priority**: A Border that appears healthy while dropping or duplicating tasks is not usable for network operations.

**Independent Test**: Interrupt a connection before dispatch, after dispatch and after result persistence; restart the Border and a member; attempt cancellation and reconnect. Verify truthful outcomes and zero automatic re-execution of possibly completed work.

**Acceptance Scenarios**:

1. **Given** Hermes is selected, **When** federation panels or commands are opened, **Then** they report the selected installation's actual Risk, peers, capabilities and posture rather than a blanket unsupported banner or another runtime's state.
2. **Given** a request awaiting approval or still running, **When** status is inspected, **Then** it is distinguishable from refusal, failure, completion or unknown outcome.
3. **Given** loss of a response after possible execution, **When** the operator reconnects or restarts, **Then** retained evidence is recovered where available; otherwise the outcome remains explicitly unknown and the work is not automatically replayed.
4. **Given** cancellation after dispatch, **When** the system cannot confirm that execution stopped, **Then** it does not report the task as safely cancelled.

### User Story 7 — Adopt Hermes without losing existing work (Priority: P2)

An operator upgrades federation support while retaining existing identities, trust relationships, grants, member settings, records and HUD work.

**Why this priority**: Operators need an adoption path that preserves the completed HUD integration and existing federation.

**Independent Test**: Compare populated installation state before/after installation, repeated upgrade and documented rollback. Run existing OpenClaw federation and spec 148 Chat/Canvas/Avatar regression journeys.

**Acceptance Scenarios**:

1. **Given** an existing Risk or peer relationship, **When** support is upgraded repeatedly, **Then** identities, trust material, permissions, scopes and retained evidence are preserved without widening access.
2. **Given** existing OpenClaw federation and Hermes HUD conversations, **When** spec 149 is installed, **Then** those supported journeys remain functional and their state remains isolated.
3. **Given** a host that lacks required production controls, **When** deployment guidance and status are consulted, **Then** the limitations and refused operations are explicit; testing success is not represented as production qualification.

### User Story 8 — Use NetClaw Mobile with a Hermes Border (Priority: P1)

An operator uses an enrolled phone to converse with a Hermes Border, including voice-transcribed input and Siri, and obtains permitted member/peer results through the existing NCFED methods.

**Why this priority**: Mobile is an existing operator entry point; selecting Hermes must not strand authenticated phone requests or disguise uncertain execution.

**Independent Test**: Enroll/authenticate a mobile client against an isolated Hermes Border; exercise text, contextual follow-up, permitted iN2N/eN2N delegation, voice origin, progress, result, cancellation and disconnect/reconnect. Compare with existing OpenClaw mobile regressions and build the changed Flutter client.

**Acceptance Scenarios**:

1. **Given** an authenticated enrolled device, **When** it submits Ask Border, **Then** the backend mints a device-owned operator scope and the protected Hermes runtime executes within its permitted tools; a peer or forged device cannot obtain this authority.
2. **Given** an ongoing conversation or delegation, **When** the phone reconnects or a response is lost, **Then** it retrieves the owned result/progress without resubmitting possibly executed work or reading another device's tasks.
3. **Given** voice-transcribed text or Siri origin voice, **When** Hermes answers, **Then** the original text is processed and voice composition remains concise/plain-spoken without changing authority.
4. **Given** uncertain/interrupted work or a stop request, **When** status appears on mobile, **Then** uncertainty, interruption, cancellation requested and confirmed cancellation are distinct and never silently remain pending.
5. **Given** a photo/video request, **When** the selected protected runtime lacks qualified media handling, **Then** it reports attachment support unavailable before inference and the app explains the limitation. Text support does not imply media parity.
6. **Given** an old mobile app or missing harness metadata, **When** it uses the existing enrollment/methods, **Then** compatible journeys remain usable, unavailable metadata remains unknown, and any required client update is documented with its minimum version.

### Edge Cases

- Conflicting runtime selection, custom homes, two installations on one host, stale selection and missing runtime executables.
- Installed/advertised capabilities whose dependencies are missing, registrations changed, credentials are unavailable or grants no longer apply.
- Single-use enrollment token replay, peer/member identity collision, failed authentication, trust rotation and revoked membership.
- Concurrent requests for the same skill from different peers, conversations or operators; same display name on different authenticated identities.
- Missing required production containment, model guard, component qualification or audit service; preserve the documented distinction between execution-blocking controls and audit-degraded posture.
- Budget exhaustion or approval expiry while work is queued, awaiting approval or ready to dispatch.
- Lost responses, process death, stale progress, repeated result queries, cancellation races and ambiguous execution after reconnection.
- External requests inducing further delegation, tool access, memory access or disclosure outside the original grant.
- Runtime switching while tasks are active; retained tasks must stay bound to their original owner, installation and execution identity.
- Missing, malformed, unknown or stale harness metadata; an authenticated peer's self-reported harness is not independently verified execution evidence and must not select a local executable or confer authority.
- Existing NCFED knowledge/replication/edge paths share federation infrastructure; regression must be checked even including the newly included Hermes mobile client behavior.

## Requirements

### Functional Requirements

- **FR-001**: Federation MUST honor the selected runtime and installation for startup, configuration, credentials, identity, state, capability discovery and execution. Hermes nodes MUST NOT depend on an OpenClaw executable, configuration or service.
- **FR-002**: Runtime selection MUST remain consistent across installation, interactive launch, background service launch and restart. Invalid or incompatible selections MUST fail explicitly without runtime fallback.
- **FR-003**: Hermes MUST support both Border and member roles, including mixed and all-Hermes Risks and all four OpenClaw/Hermes Border/member runtime pairs.
- **FR-004**: Member provisioning and enrollment MUST preserve scoped tools, credentials, model selection, identity and trust. Hermes members MUST support the existing supported lifecycle choices, including on-demand execution and managed operation where the host provides their controls.
- **FR-005**: A Hermes Border MUST support internal member discovery, health, capability routing, explicit delegation, direct qualified member-tool invocation, asynchronous progress and authorized result retrieval.
- **FR-006**: Hermes Borders MUST support eN2N capability exchange, peer chat, qualified tool invocation and skill delegation as both requester and responder with Hermes and OpenClaw peers.
- **FR-007**: Operators MUST be able to initiate federation work through the Hermes HUD conversation and inspect/manage supported federation functions through existing HUD and command-line surfaces. Installation alone MUST NOT count as successful agent discovery or invocation.
- **FR-008**: Capability reporting MUST identify the actual node/runtime and distinguish configured, advertised, eligible, unavailable and execution-verified capabilities. Advertisements MUST respect existing visibility controls and exclude secrets.
- **FR-009**: Existing NCFED peer identity, mutual consent, enrollment trust, scoped grants, expiry/revocation, budgets and kill-switch behavior MUST remain enforced across runtime combinations. Runtime interoperability MUST NOT require a separate incompatible federation network.
- **FR-010**: Every execution MUST retain its authenticated requester, origin trust, installation, target, scope and task identity through each delegation. External peer input MUST NOT gain local-operator authority through routing or re-delegation.
- **FR-011**: Authorization and required controls MUST be enforced at dispatch, including after waiting for approval or other work. Model instructions, capability labels and successful discovery MUST NOT substitute for enforcement.
- **FR-012**: Approval MUST be bound to the specific requester, target and operation. Rejected, expired, revoked, mismatched or previously consumed one-time approvals MUST NOT authorize execution.
- **FR-013**: Federation MUST preserve production change control, real pre-change baselines, post-change verification and audit. The Terminal Intent Local/Lab exception MUST NOT become a general federation bypass. Operations whose required controls cannot be enforced MUST be refused before dispatch.
- **FR-014**: Member scope and production posture MUST remain enforceable for Hermes. Missing execution-blocking controls MUST stop affected work; any existing permitted audit-degraded state MUST be reported explicitly and never presented as fully enforced production.
- **FR-015**: Peer chat and delegated tasks MUST isolate unrelated requesters, tasks and installations, including concurrent calls to the same skill. History, results, credentials and local private context MUST NOT cross those boundaries without applicable authorization.
- **FR-016**: Accepted work MUST expose a stable task reference and truthful progress/outcome. Results MUST include sufficient provenance to distinguish local Border answers, member execution and external-peer execution; unavailable usage MUST NOT appear as zero measured usage.
- **FR-017**: Recovery, reconnect and retry MUST NOT automatically repeat an operation that may have executed. Cancellation MUST distinguish a request to stop from confirmed cessation; uncertain work MUST remain explicitly uncertain until evidence resolves it.
- **FR-018**: Failures MUST be isolated per request/member/peer, respect configured deadlines and budgets, and identify whether runtime, transport, authentication, authorization, capability or backend readiness prevented completion.
- **FR-019**: Federation operations and authorization decisions MUST produce correlated GAIT evidence under the existing audit policy. Status and logs MUST let the operator follow a task through Border and executor without leaking secrets or unauthorized private data.
- **FR-020**: Installation, upgrade and documented rollback MUST preserve existing identities, trust material, permissions, member scope, retained records and spec 148 HUD work. Runtime switching MUST NOT silently adopt another installation's state or in-flight tasks.
- **FR-021**: Existing OpenClaw federation behavior and the qualified spec 148 Hermes HUD journeys MUST remain functional. Shared knowledge, replication and edge behavior MUST receive regression coverage wherever shared federation paths change.
- **FR-022**: Delivered documentation and readiness reports MUST state the exact qualified host/runtime/role combinations, supported operations and remaining limitations. Each supported operation MUST have end-to-end evidence; simulated and live results MUST be labeled separately.
- **FR-023**: Internal member inventories and external NCFED capability cards MUST carry the advertising node's agent harness type (including OpenClaw and Hermes) and version when available, alongside existing model, tools, skills and posture attributes. Harness metadata MUST come from the selected local installation, remain distinct from deployment type and security controls, and retain source/freshness when received and displayed in HUD/CLI views. External cards describe the advertising Border, not its private member topology. Missing, malformed or unrecognized metadata MUST be handled without rejecting an otherwise valid legacy card or inferring OpenClaw; unavailable values MUST be explicit. The addition MUST preserve compatibility and existing disclosure controls. Advertised harness identity MUST NOT grant permissions, count as execution verification or control which local executable is launched.

- **FR-024**: Authenticated NetClaw Mobile Ask Border requests MUST execute through the protected selected Hermes runtime using backend-created operator scope bound to installation, enrolled device, conversation, task/request and body. Preserve device ownership, enrollment/trust checks and authorization; external peers cannot obtain operator scope.
- **FR-025**: Mobile MUST support text conversations, permitted internal/external delegation, progress, owned result retrieval, cooperative cancellation and reconnect recovery. Lost admission receipts and uncertain work MUST never cause automatic resubmission or silent indefinite pending state.
- **FR-026**: Voice-transcribed requests and Siri origin voice MUST preserve their text and existing voice-composition semantics through protected Hermes execution, without changing authorization.
- **FR-027**: Backend and mobile MUST represent outcome_unknown, interrupted, cancellation requested and confirmed cancellation distinctly. Preserve existing methods/enrollment; provide an explicit legacy projection where older apps cannot render new states, and document the minimum client version for complete new-state behavior.
- **FR-028**: Mobile MUST display safe Border harness metadata alongside model/capability information where appropriate; absence/malformed values remain unknown. Photo/video attachments MUST be qualified end to end or explicitly unavailable before execution, with no untested parity claim.
- **FR-029**: Verification MUST include Hermes/mobile acceptance, existing OpenClaw mobile regressions and a produced build for changed mobile source. Record actual device/platform/build/signing coverage and unrun checks. Do not publish an app-store release as part of this work.

### Key Entities

- **Runtime installation**: Selected runtime kind, installation identity, configuration/state ownership and qualification/readiness status.
- **Harness descriptor**: Agent harness type and available version for one advertising node, distinct from deployment type, model and security posture; local observation or peer-advertised provenance, freshness and unknown/unrecognized states.
- **Risk and node**: Operator's internal group; Border/member identity, runtime, role, scope, lifecycle and reported security posture.
- **External peer relationship**: Authenticated peer identity, consent, trust material, visibility, grants, budgets and revocation state.
- **Capability**: Node-owned tool or skill with scope, advertised visibility, dependency readiness and execution evidence.
- **Federated task**: Stable request reference, authenticated origin/owner, target, permitted scope, approvals, progress, result, usage and outcome certainty.
- **Peer conversation**: Context owned by the authenticated peer relationship and selected installation, independent of local operator conversations.
- **Audit evidence**: Correlated authorization, dispatch and outcome observations linking Border, executor and task while protecting private content.

## Success Criteria

### Measurable Outcomes

- **SC-001**: An all-Hermes Risk completes installation/startup, enrollment, discovery, skill delegation, direct tool invocation and result retrieval with no OpenClaw executable, configuration or running service on its nodes.
- **SC-002**: All four Border/member runtime combinations pass the same core internal acceptance journey, including one real harmless tool result and one real skill result with matching provenance.
- **SC-003**: Hermes↔OpenClaw and Hermes↔Hermes external pairs pass inventory, two-turn contextual chat, tool invocation and asynchronous skill/result journeys in both directions under valid consent and grants.
- **SC-004**: The negative authorization matrix produces zero unauthorized executions or disclosures for absent/revoked grants, out-of-scope targets, stale approvals, cross-owner access, external-input privilege escalation and missing required enforcement.
- **SC-005**: The failure/recovery matrix produces zero automatic duplicate executions after possible dispatch. Every accepted request is either observably active, completed with evidence, refused/failed before execution, confirmed cancelled, or explicitly uncertain within its configured deadline.
- **SC-006**: An operator can initiate an internal and an external federation task from Hermes HUD Chat and retrieve the correctly attributed outcome through the existing task/status views. Chat, Canvas and local Avatar retain their qualified conversation behavior after the change.
- **SC-007**: Every acceptance task has correlated requester/Border/executor identity and outcome evidence; inventory or connectivity alone is never counted as a successful execution. Runtime, transport and policy failures remain distinguishable in operator-facing status.
- **SC-008**: Repeated installation/upgrade and the documented rollback preserve all captured identity, trust, permission, scope and unrelated owner-state baselines; existing OpenClaw regression journeys pass.
- **SC-009**: The release qualification matrix has recorded pass/fail/unverified dispositions for every declared host/role/runtime combination, with zero unsupported production-enforcement claims and zero unlabeled substitution of simulated evidence for live execution.
- **SC-010**: Every node in the internal/external runtime acceptance matrix reports its correct harness type and available version through capability exchange and operator views. Legacy, malformed, unknown and stale metadata cases remain interoperable and are labeled accurately; no case changes execution authority or exposes private member topology.

- **SC-011**: The Hermes/mobile acceptance journey completes text, contextual follow-up, one qualified internal and external delegation, owned progress/result, voice-origin composition and reconnect recovery with zero unauthorized cross-device access or automatic uncertain resubmissions.
- **SC-012**: Every mobile failure/cancellation/unknown/interrupted case renders an explicit bounded outcome on current clients and a useful compatible fallback on legacy clients. Photo/video has an actual tested support or unavailable disposition.
- **SC-013**: Existing OpenClaw mobile regressions pass, a changed mobile client build is produced, and evidence distinguishes automated protocol tests, simulator/emulator execution and physical-device testing with no unrun coverage claim.

## Assumptions

- The existing NCFED protocol and federation trust model are retained. This is runtime integration and parity for the defined core journeys, not a new protocol, transport, commerce system or enterprise tenancy redesign.
- The owner explicitly selected both Hermes roles and mixed/all-Hermes Risks. Existing OpenClaw nodes must remain usable without mandatory migration.
- The working-runtime reference in the initial prompt is interpreted as OpenClaw; OpenShell remains a separate security concern. Runtime portability does not imply that a particular sandbox is qualified on every host.
- Start host qualification from spec 148's actual macOS and Ubuntu WSL environments; planning must define exact federation role/control coverage and any additional Linux evidence needed. Native Windows Hermes remains outside scope. Spec 148's host results do not certify federation or production member confinement.
- Qualify the federation operations required by these journeys and representative harmless executor tools/skills. Registration of arbitrary network tools does not establish eligibility; unsupported operations remain explicit and do not count toward a passing supported-operation claim.
- Existing knowledge/replication behavior is preserved and shared-path regressions are tested. New knowledge features and Slack/Webex channel porting remain outside this feature. Existing NetClaw Mobile compatibility, voice-transcribed input and Siri voice origin are now included; photo/video must receive an explicit qualified-or-unavailable disposition. Planning must inventory shared ingress call sites and report any Hermes-specific unsupported behavior instead of silently routing it to OpenClaw.
- Peer communications, provider use and device operations for live qualification require applicable existing authorization and scoped fixtures. Drafting this spec performs none of them.
- Exact supported runtime versions, integration mechanisms, lifecycle implementation and bounded operating deadlines belong in the technical plan, based on verified source and tests.

### Owner steering — mobile summary and distribution

On 2026-10-10 the owner explicitly requested the Border type field on the mobile summary page, version bumping, and pushing to App Store Connect. This supersedes the earlier no-upload scope: build, validate and upload the tested release candidate to App Store Connect/TestFlight. Public App Review submission/release is not included. Report actual processing and device coverage; missing harness metadata remains unknown.

### Owner steering — source release and public article

The owner requests NetClaw 1.8.0, README/version-history updates, and a published article titled “Good news for Hermes users!” on automateyournetwork.com in NetClaw articles and Latest, using all five spec149 infographics and links to the spec148 and spec149 PRs. Publishing and the necessary PR creation/push are authorized. Claims must match verified implementation and explicitly state outstanding platform/media limitations.
