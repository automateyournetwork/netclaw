# Feature Specification: Cloud eN2N Federation Parity

**Feature Branch**: `177-external-en2n-federation`
**Created**: 2026-11-06
**Status**: Owner-directed scope; planning
**Input**: R06 needs two different cloud Borders representing two independent organizations, plus a local Border, fully federating over existing eN2N. The owner requested a new branch, the full SDD process and completion to 100%, and clarified that non-cloud eN2N already works: this feature confirms cloud support and corrects actual gaps rather than redesigning federation.

## Clarifications

### Session 2026-11-06

- Q: Does the local Border represent a third organization, with every pair tested both ways? → A: Yes: three independent organizations, full triangle.
- Q: Are separate resources in the existing GCP project sufficient, or are separate projects required? → A: Separate resources in the existing GCP project.
- Owner correction: Reuse working non-cloud eN2N. This is cloud parity and actual qualification, not a new federation protocol, trust model or replacement workflow.
- Source-planning default: qualify fresh ordinary full Border installations, preserving their existing eN2N controls. The optional runtime-profile clarification remains open; no cloud activation is inferred from silence. Existing protected installations and their guards remain unchanged. Ordinary eN2N evidence is not R02 protected-operation/ACK qualification.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Federate three independent organizations (Priority: P1)

The operator connects cloud organization A, cloud organization B and local organization C using the existing Border peer workflow. Each Border retains its own identity, state, trust decisions, exports and budgets.

**Why this priority**: Cloud placement must not prevent the same external federation already available between non-cloud Borders.

**Independent Test**: Deploy isolated participants, establish all three peer relationships, and observe verified identity and bilateral consent separately from transport reachability.

**Acceptance Scenarios**:

1. **Given** independently owned Border state and approved peer identities, **When** A↔B, A↔C and B↔C federate, **Then** all three relationships become usable through the existing eN2N protocol.
2. **Given** one established connection per pair, **When** each peer initiates an application request, **Then** all six requester/responder directions work, regardless of which endpoint opened the transport connection.
3. **Given** a local Border behind NAT, **When** it connects to the registered cloud endpoints, **Then** bidirectional federation does not require exposing local members or weakening endpoint identity.
4. **Given** the existing GCP project, **When** A and B are provisioned, **Then** their virtual machines, networks, service identities, private installation state and NetClaw authority are separate; this is not represented as separate GCP organizations or independent billing administrators.

### User Story 2 - Use the existing complete peer workflow (Priority: P1)

The operator sees a peer's permitted capabilities, holds a contextual peer conversation, invokes an approved tool and delegates an approved skill through the same eN2N workflows used locally.

**Why this priority**: A connected badge or handshake alone does not establish functional federation.

**Independent Test**: For each of the six directions, exchange permitted inventory, conduct a two-turn peer conversation, invoke the real subnet tool and complete an asynchronous subnet skill request with result retrieval. Correlate actual selected-runtime and native MCP execution with the original peer request.

**Acceptance Scenarios**:

1. **Given** approved exports, **When** peers exchange inventory, **Then** each sees only the permitted external capability view, with the correct source Border identity and no internal member identities, topology or credentials.
2. **Given** two independent peer conversations, **When** each sends a contextual follow-up, **Then** context stays with its peer relationship and does not mix with operator or other-peer conversations.
3. **Given** an explicitly permitted read-only subnet tool and skill, **When** either direction requests their use, **Then** actual native execution returns correct, attributable results within its configured bounds; an echo, synthetic response or model assertion alone is insufficient.
4. **Given** an asynchronous request, **When** the operator obtains progress and the final result, **Then** the original peer/request identity and terminal or unknown outcome remain visible.
5. **Given** established non-cloud behavior, **When** cloud-specific integration is corrected, **Then** its wire protocol, peer semantics and supported non-cloud workflows remain compatible.

### User Story 3 - Preserve external trust boundaries (Priority: P1)

Each organization decides which peer may use each exported capability, retains its own budgets and can revoke the relationship without granting internal authority.

**Why this priority**: Moving working federation to public cloud endpoints must preserve its existing controls.

**Independent Test**: Exercise missing, one-sided, expired and revoked consent; wrong identity or pin; altered endpoint bindings; out-of-scope capabilities; exhausted budgets; and attempts to cross the internal member or operator boundary.

**Acceptance Scenarios**:

1. **Given** missing or withdrawn permission, **When** a peer requests work, **Then** it is refused before new execution with an attributable reason.
2. **Given** an unapproved identity, key or endpoint binding, **When** a connection is attempted, **Then** it is refused without automatic trust adoption or weaker transport fallback.
3. **Given** an authenticated external peer, **When** it attempts direct member access, prohibited enumeration, local-operator impersonation, cluster authority or routing control, **Then** all attempts are refused.
4. **Given** A trusts B and B trusts C, **When** A requests an unapproved transit or re-export through B, **Then** bilateral trust does not silently confer authority over C.
5. **Given** a budget is exhausted or a peer is disabled, **When** a new request arrives, **Then** no additional provider or native workload executes.

### User Story 4 - Operate federation from HUD and VS Code (Priority: P1)

The operator uses the normal HUD and VS Code cloud connection experience to inspect peers, use existing peer chat and follow an external answer back to its source. Consent/export administration reuses the existing native MCP/CLI controls; a new administration UI is not required.

**Why this priority**: Backend-only qualification would leave the requested cloud federation unusable from the supported operating interfaces.

**Independent Test**: Use an actual browser and actual Mac VS Code against the selected cloud Border. Exercise the normal connection/view flow, peer state, consent and an approved external result, including reload or reconnect without resubmission.

**Acceptance Scenarios**:

1. **Given** a selected cloud connection, **When** the operator opens federation views, **Then** they operate on that installation and accurately distinguish transport, trust, consent and capability availability.
2. **Given** an external answer, **When** it is displayed, **Then** the peer and request provenance are visible and external content does not acquire local-operator authority.
3. **Given** an existing operation and a client restart, **When** its result is reopened, **Then** recovery retrieves the original state without silently executing again.
4. **Given** normal Chat, Canvas, RAG and local profiles, **When** cloud federation is added or repaired, **Then** those existing experiences remain available.

### User Story 5 - Use Mobile Ask Border across eN2N (Priority: P1)

An enrolled Mobile client asks its selected Border for a permitted external capability and receives progress and a correctly attributed answer.

**Why this priority**: Roadmap G13 requires affected mobile work and actual client evidence in this stage.

**Independent Test**: Use the existing QR/scanner and an actual native iPhone simulator with the selected cloud Border, complete an external read-only request, then cold-launch and reconnect to the same request.

**Acceptance Scenarios**:

1. **Given** the existing enrolled-device identity, **When** Ask Border delegates to an external organization, **Then** peer consent, export scope and requester provenance are preserved through the answer.
2. **Given** an unavailable or revoked external peer, **When** a request cannot proceed, **Then** the client reports the actual condition without switching peers, widening scope or replaying uncertain work.
3. **Given** disconnect/background/cold launch, **When** the client resumes, **Then** the original request/result remains attributable with no repeated execution.

### User Story 6 - Deliver usable, bounded cloud qualification (Priority: P1)

The operator receives working cloud/local federation, its actual evidence and a clearly bounded resource lifecycle, preserving existing deployments and their cleanup obligations.

**Why this priority**: Source tests alone do not prove cloud support, and temporary qualification must not silently replace the intended usable delivery.

**Independent Test**: Reconcile the exact provisioned resources, endpoints and source revisions with real cloud and client observations, export private evidence, and verify any disposable cleanup against actual inventory.

**Acceptance Scenarios**:

1. **Given** the deployment plan, **When** qualification runs, **Then** only the scoped R06 resources change, existing owner installations and R05 retirement obligations remain preserved, and each resource has an explicit lifetime.
2. **Given** a lost response, peer restart or revocation, **When** the operator reconciles the request, **Then** it remains the original operation and uncertain work is not automatically replayed.
3. **Given** completion evidence, **When** the stage is handed off, **Then** qualified behavior, historical failures, retained resources, cleanup status and platform limits are reported separately.

### Edge Cases

- Both peers attempt to connect simultaneously; multiple pairs reuse the same public source address.
- Cloud routing address changes while approved application identity stays constant; stale or altered registry revisions.
- Local outbound-only connectivity, cloud ingress restrictions and separate internal/external listeners.
- Consent changes after inventory exchange or while a task is running; stale cached capability data.
- Valid peer presents an incorrect application identity, key, transport name or certificate binding.
- Identical capability names exported by different organizations; context or result attached to the wrong selected cloud profile.
- Provider or native-tool timeout after dispatch, lost receipt, duplicate client submission, pending cancellation or service restart.
- Unapproved re-export, direct member request, external-origin request attempting to become an operator request.
- One unavailable peer while the other pair remains healthy; no automatic rerouting of uncertain work.
- Resource expiry during an operation; cleanup after evidence export, with disk/address residues accounted for.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Support three independent NetClaw organizations, one Border each: two in separate resource sets within the existing GCP project and one local; qualify all three pairs in all six application directions.
- **FR-002**: Reuse existing eN2N/NCFED framing, peer lifecycle, identity, consent, capability, chat, tool and asynchronous skill workflows. Limit changes to demonstrated cloud or client integration gaps and regressions.
- **FR-003**: Keep identities, private state, keys, exports, budgets and organization administration separate; shared GCP project ownership MUST NOT be misrepresented as separate cloud tenants or GCP organizations.
- **FR-004**: Use the existing strict registered endpoint path for remote federation, preserving encrypted transport and verified application identity with no first-contact trust adoption, discovery fallback or unapproved endpoint replacement.
- **FR-005**: Require and enforce bilateral consent, scoped exports, applicable expiry/revocation and existing budgets independently for every peer relationship.
- **FR-006**: Qualify permitted inventory exchange, contextual peer chat, real read-only tool invocation, asynchronous skill delegation and original-result retrieval in all six directions.
- **FR-007**: Preserve external origin and request attribution end to end; peer content or authenticated transport MUST NOT grant local-operator, cluster, routing or unapproved downstream authority.
- **FR-008**: Expose only approved Border-level capabilities. Refuse internal member enumeration/access, integration-secret disclosure, unapproved capabilities, implicit transit and re-export.
- **FR-009**: Preserve existing internal delegation and confinement. A cloud qualification gap MUST NOT be bypassed by exposing MCP/model services, moving member credentials to a Border or using a raw alternate execution route.
- **FR-010**: Preserve known, failed, cancellation-requested and unknown outcomes through lost responses, disconnects and restarts without automatic repeated execution. Reconciliation MUST use the original request rather than create a replacement request for uncertain work.
- **FR-011**: Implement and actually verify affected HUD and VS Code paths against cloud federation, retaining installation selection, peer/answer attribution and existing normal operating views.
- **FR-012**: Implement and actually verify affected Mobile Ask Border and result-recovery paths against cloud federation using the existing enrollment/device identity flow.
- **FR-013**: Distinguish transport reachability, authenticated admission, consent, advertised capability, real execution and client completion in reports. Retain source/runtime pins, actual effect counts and original failure witnesses.
- **FR-014**: Provision only isolated, tagged, bounded R06 resources with reviewed ingress, finite execution budgets, private evidence, explicit retention and complete teardown accounting; preserve existing owner resources and pending R05 retirement.
- **FR-015**: Maintain backward compatibility with working non-cloud eN2N and existing supported harness contracts. Label the exact real cloud runtime/provider/platform matrix; tests do not imply unrun platform qualification.
- **FR-016**: Finish specify, clarify, plan, tasks, cross-artifact analysis, implementation, applicable artifact coherence checks and actual acceptance evidence. No completion claim may substitute fixtures or documentation for required live work.

### Key Entities

- **Organization/Risk**: Independently administered NetClaw trust and capability boundary; distinct from its cloud project or billing account.
- **Border participant**: Organization identity, local/cloud placement, runtime identity, endpoints and private state.
- **Peer relationship**: Two approved Border identities, endpoint bindings, bilateral consent, grants, budgets and current lifecycle state.
- **Exported capability**: Approved Border-level tool or skill with bounded inputs and permission; internal execution placement remains private.
- **External request**: Original principal/origin, requesting and responding Borders, approved scope, request identity, execution evidence and outcome.
- **Client reference**: Selected installation and existing enrolled/native client identity with a bounded reference to the original request.
- **Qualification record**: Exact topology, source/runtime pins, positive and refusal evidence, effect counts, historical unknowns, lifecycle and platform limits.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three peer pairs are admitted with independently verified identities and bilateral consent; all six requester/responder directions complete the existing external workflows.
- **SC-002**: Each direction passes permitted inventory exchange, a two-turn contextual chat, one real subnet tool call and one real asynchronous subnet skill/result journey; returned subnet facts match independently calculated expected values.
- **SC-003**: Every selected identity, consent, scope, budget, member-access, authority and transit refusal case produces zero new unauthorized native/provider execution.
- **SC-004**: Actual browser, actual Mac VS Code and native iPhone simulator each complete a cloud-mediated external request with correct peer attribution and retrieve its original outcome after reconnect without additional effects.
- **SC-005**: Actual peer/service loss and lost-response cases preserve original outcomes and effect counts; no uncertain request is replayed or silently rerouted.
- **SC-006**: Non-cloud federation regressions pass, every acceptance scenario has traceable evidence, and all retained or removed R06 resources have an observed state and bounded lifecycle.

## Assumptions

- Two cloud organizations share the existing GCP project by explicit owner choice, with separate virtual machines, networks, service identities and private NetClaw state. The local Border is a third independent organization.
- Existing OpenClaw/Sonnet qualification is the initial live-runtime reference; installed runtime contracts and non-cloud Hermes compatibility remain preserved. A broader runtime matrix is not implied by cloud placement.
- Fresh ordinary Border installations use their existing eN2N grants, exact request-bound approval where configured, budgets and runtime controls. They MUST NOT claim the separate R02 signed protected-operation/member-ACK execution contract. Any new ordinary-cloud client capability must identify this distinction explicitly; existing protected homes may not be converted by clearing markers or disabling guards.
- Read-only subnet calculation supplies safe deterministic acceptance data; no production/device writes, private network data exports or external infrastructure/Ollama execution are added by this feature.
- Cloud listeners use existing direct TCP. The local Border may initiate outbound sessions to both clouds; application requests must work in both directions over those authenticated sessions.
- Full eN2N means the existing capability/chat/tool/skill workflows above, not new transitive routing, HA, multi-region authority, commerce, user identity/SSO/RBAC or replication privileges.
- Existing no-user-login development client behavior and enrolled Mobile identity are preserved; R15–R17 user controls are not pulled into R06.
- Exact new resource lifetime and any retained owner-facing deployment are specified in the concrete deployment plan before activation. Existing R05 November7 cleanup and the original Border December1 scope do not change.
- Roadmap release/version/public-rollout holds remain in force. R07 recovery gate, R08 HA and later milestones do not start merely because R06 completes.
