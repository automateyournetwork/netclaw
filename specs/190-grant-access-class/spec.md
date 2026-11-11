# Feature Specification: Read/Write Access Class on Per-Peer Grants

**Feature Branch**: `190-grant-access-class`
**Created**: 2026-11-11
**Status**: Draft
**Input**: GitHub issue #344, "Separate read and write on per-peer grants". NCFED draft section "Trust Establishment / eN2N" (issue text: 12.1) says remote invocation is default-deny and a call is rejected with NOT_ALLOWLISTED unless a per-peer grant authorizes it; the "Capability Cards" section (issue text: 11) says a card advertises only what a peer may see. In the reference implementation, `InvocationGrant` (`invocation_grant` table, `authorization.py`) is keyed by peer, `target_type` and `target_name` plus `requires_approval` and `timeout_s`; `n2n_grant` takes the same fields. Nothing separates permission to read state from permission to change it. `VisibilitySetting` only controls card advertisement. A read-looking tool can be granted by name, but that fails for tools that mix reads and writes and for skill delegation (`n2n/tasks/submit`), where the prompt decides.

**Stacking**: This work is stacked on spec 189 (PR #350, issue #343), which adds helper methods around `Authorizer.authorize()` / `admit()` and documents (`docs/N2N-PEER-LIMITS.md`) that read versus write classes attach to its counted-operation table. This branch is created from `189-peer-limit-semantics` and must be retargeted to `main` once #350 merges.

**Scope guard**: The default-deny model does not change. A peer still needs a grant for every tool, skill or collection.

## Clarifications

### Session 2026-11-11 (autonomous; no human available, defaults recorded)

- Q: Duplicate grants for the same peer, type and name with different classes? -> A: Creating a grant whose class differs from an existing active grant for the same peer, type and name supersedes it: the older grant is revoked (audited) and the new one is the only active grant. Creating one with the same class behaves as today. This keeps the single-grant lookup deterministic and means narrowing a grant from `read_write` to `read` takes effect immediately without a separate revoke.
- Q: Where does a skill's `read` declaration live? -> A: Only in the operator classification table (an override). There is no self-declaration in SKILL.md, because a skill file is content the peer-facing runtime loads and is not an authorization input. Unclassified skills count as write for a `read` grant. (This replaces the earlier "operator-approved declaration" wording; FR-004 is amended accordingly.)
- Q: How do MCP annotations get in? -> A: By an explicit operator action that submits an MCP `tools/list` payload (or a map of tool to `readOnlyHint`) for a named server to the daemon; each tool is stored as `server/tool` with source `annotation`. The daemon never fetches annotations from a remote peer and never from the callee's MCP servers at call time in this feature (live ingestion is deferred). Absence of an imported annotation means unclassified.
- Q: What error does an access-class refusal use on the wire? -> A: NOT_ALLOWLISTED (-32001) with a generic reason that is the same text as an ungranted target ("not allowlisted"), so a peer cannot learn whether a target exists or how it is classified. The distinction exists only in the callee's audit (`access_class_denied`) and operator tools.
- Q: Ordering of the class check versus approval and limits? -> A: Order inside the gate: hold-down, federated, grant found, access-class check, rate, budget, approval. A class refusal creates no approval, charges no rate slot and no budget, and never triggers a limit action. At admission the same gate is re-run, so a mid-wait reclassification is caught.
- Q: Separate budgets or rates for read and write? -> A: Out of scope. Reads and writes share the spec 189 limits and counted-operation table unchanged.
- Q: Does the Border forward the class to an iN2N member? -> A: Out of scope. The class is evaluated by the node that holds the grant. An aggregate (member-specialty) skill advertised by a Border is unclassified unless the operator classifies it, so it needs a `read_write` grant. Forwarding is recorded as a limitation.
- Q: A task or call already running when the target is reclassified? -> A: Not interrupted. Reclassification affects the next admission only (including approval-wait admission), consistent with how revoke already behaves for admitted work.
- Q: Classification key for tools? -> A: The same `server/tool` string used by grants. Skills use the skill name, with the `skill` type. A classification row is (target_type, target_name, class, source, updated_at).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Grant a peer read-only access (Priority: P1)

An operator wants a federated peer to be able to look at state (list labs, show topology) without being able to change it (start/stop labs, push config). They grant the peer access with the access class `read`. The callee then lets the peer call only targets classified as read and refuses everything classified write or not classified at all.

**Why this priority**: This is the literal ask of issue #344 and the whole value of the feature.

**Independent Test**: Create a `read` grant for a read-classified tool and a write-classified tool; call both through the authorization gate and assert the first is allowed and the second is refused with NOT_ALLOWLISTED.

**Acceptance Scenarios**:

1. **Given** a `read` grant for tool T and T is classified read, **When** the peer calls T, **Then** the call is authorized exactly as today.
2. **Given** a `read` grant for tool T and T is classified write, **When** the peer calls T, **Then** the call is refused with NOT_ALLOWLISTED, no approval is created, no request unit is debited, and an audit row records the refusal reason as access-class.
3. **Given** a `read` grant for tool T and T is unclassified, **When** the peer calls T, **Then** the call is refused the same way (unclassified is never treated as read).
4. **Given** a `read_write` grant, **When** the peer calls any granted target, **Then** behavior is identical to today.

### User Story 2 - Existing grants keep today's behavior (Priority: P1)

An operator upgrades. Every grant created before this feature, and every grant created by a caller that does not mention the access class, behaves exactly as before.

**Why this priority**: The issue asks not to change the default-deny model, and installed meshes must not break.

**Independent Test**: Run the existing authorization test suite unchanged; create a grant with no access class and call a tool that is unclassified; assert it is allowed.

**Acceptance Scenarios**:

1. **Given** a database with grants written before this feature, **When** the daemon starts, **Then** those grants read as `read_write` and no behavior changes.
2. **Given** a caller of the grant API (`n2n_grant`, `POST /n2n/grants`) that omits the access class, **Then** the stored class is the node default, which is `read_write` unless the operator changes it, and the response and `list_grants` show the stored class.
3. **Given** an invalid class value, **Then** the request is rejected with HTTP 400 and nothing is stored.

### User Story 3 - Classify tools, with explicit operator control (Priority: P1)

An operator, or an importer feeding MCP `tools/list` annotations, classifies each tool as read or write. An operator override always wins over an annotation. A tool with neither is unclassified.

**Why this priority**: Without a deterministic classification two implementations cannot interpret a `read` grant the same way.

**Independent Test**: Import annotations with `readOnlyHint: true`, assert read; add an operator override to write, assert write; clear the override, assert annotation again; check an unknown tool is unclassified.

**Acceptance Scenarios**:

1. **Given** imported annotations for `cml-mcp/list_labs` with `readOnlyHint` true, **Then** its class is `read` with source `annotation`.
2. **Given** an operator override to `write`, **Then** the class is `write` with source `operator`, regardless of annotations.
3. **Given** `readOnlyHint` false or absent and no override, **Then** the class is `write` (false) or `unclassified` (absent); both are refused under a `read` grant.
4. **Given** classification changes after a request started waiting for approval, **Then** the re-check at admission uses the new class and refuses if the call is no longer permitted.

### User Story 4 - Skill delegation is write unless declared read (Priority: P1)

A peer delegates a skill with free-form text. The callee does not interpret the text. A skill is read only if the operator classified it as read; otherwise it counts as write and a `read` grant does not cover it.

**Why this priority**: This is issue question 5; the text of a request is attacker-controlled input and must never decide the class.

**Independent Test**: Grant a skill under a `read` grant unclassified and assert refusal; classify it read and assert authorized; submit the same skill with write-looking and read-looking text and assert identical outcomes.

**Acceptance Scenarios**:

1. **Given** a `read` grant for an unclassified skill, **When** the peer submits a task with read-looking text, **Then** the task is refused with NOT_ALLOWLISTED.
2. **Given** the skill is classified read and a `read` grant, **When** the peer submits any text, **Then** it is authorized (text is never inspected for class).
3. **Given** a `read_write` grant, **Then** behavior equals today.

### User Story 5 - Interaction with approvals, visibility, limits and iN2N (Priority: P2)

The access class is an additional check in front of the existing ones. It never grants more than a grant does today, never replaces `requires_approval`, and does not change what a card advertises as permission.

**Why this priority**: Keeps the model predictable and implementers aligned on ordering.

**Independent Test**: Assert that a `read` grant with `requires_approval` creates an approval only for read-classified targets; that a refused write call debits nothing; that card visibility is unchanged by the grant class; that an iN2N (already_trusted) channel is subject to the same class check.

**Acceptance Scenarios**:

1. **Given** a `read` grant with `requires_approval` on a write-classified tool, **Then** the call is refused before any approval is created.
2. **Given** a `read` grant with `requires_approval` on a read-classified tool, **Then** approval is required exactly as today and approving does not widen the class.
3. **Given** a card, **Then** each advertised MCP server carries an advisory per-tool class map and each skill carries an advisory class, and visibility rules are unchanged.
4. **Given** spec 189 limits, **Then** read and write calls count identically against the same budgets, and access-class refusals are not debited and are not counted toward rate or limit actions.

### User Story 6 - Knowledge and inventory stay on their own controls (Priority: P2)

Capability-card pull (`n2n/inventory_get`) stays controlled only by visibility. Knowledge query (`knowledge` grants) and knowledge replication (`knowledge_replica` grants) are intrinsically read targets: they never modify the callee's state, so a `read` grant is sufficient for them, and they remain separate, distinct grants as today.

**Why this priority**: Answers issue question 4.

**Independent Test**: Create `read` grants for a `knowledge` collection and call it; assert allowed. Assert that granting `knowledge` still does not allow `knowledge_replica`.

**Acceptance Scenarios**:

1. **Given** a `read` grant for `knowledge` target, **Then** the query is authorized as today.
2. **Given** only a `knowledge` grant, **Then** replication is still refused as today.

### Edge Cases

- A grant replaced or revoked while a request waits: existing admission revalidation applies, now including the class.
- Classification changes while a task already running: not interrupted (only new admission re-checks); recorded limitation.
- Two grants for the same peer, type and name with different classes: the newer supersedes (revokes) the older (see Clarifications).
- Peer-supplied claims about class (card from a remote peer, tool annotations on the caller side) are never used to authorize.
- An unknown target type with a class: class is ignored for types other than tool, skill, knowledge, knowledge_replica.
- Operator sets node default to `read` for new grants: existing rows stay unchanged because the stored class is explicit.
- Tier-0 (self-asserted) peers still cannot call tools or delegate at all; access class only narrows further.
- iN2N member channels: the member's own self-referential grants are checked with the same class rule; the Border does not forward the class to a member (documented limitation).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every invocation grant MUST carry an access class, one of `read` or `read_write`. The class is a ceiling: `read` permits only targets classified read; `read_write` permits any granted target (today's behavior).
- **FR-002**: Grants created before this feature, and grants created without a class, MUST be stored and reported as `read_write` unless the operator sets a node default of `read`, in which case the default applies only to new grants and is stored explicitly on each.
- **FR-003**: The system MUST classify each tool as `read`, `write` or `unclassified`, resolved in this order: operator override, imported MCP annotation (`readOnlyHint: true` gives read; `false` gives write; absent gives unclassified), unclassified. Annotations are used only after an explicit operator import, never fetched from a peer.
- **FR-004**: A skill MUST be classified `read` only by an operator override (no self-declaration in the skill file); otherwise it is `unclassified`. The text of a delegation request MUST NOT influence the class.
- **FR-005**: Under a `read` grant, a call to a target classified `write` or `unclassified` MUST be refused with NOT_ALLOWLISTED (-32001). No new wire error code is added.
- **FR-006**: An access-class refusal MUST happen before rate counting, budget reservation and approval creation, MUST NOT debit any counter, MUST NOT start a limit action, and MUST be audited with a distinct decision `access_class_denied`.
- **FR-007**: `requires_approval` MUST remain orthogonal: it applies only to calls that pass the class check, and an approval never widens the class.
- **FR-008**: `knowledge` and `knowledge_replica` targets MUST be intrinsically read. `n2n/inventory_get` and card exchange MUST stay controlled by visibility only. No change to grant distinctness between `knowledge` and `knowledge_replica`.
- **FR-009**: The class check MUST be re-evaluated at admission after any wait, so reclassification or a grant change takes effect on the next admission.
- **FR-010**: The capability card MUST add an optional advisory per-tool class map for each advertised MCP server and an optional advisory class for each skill. The map MUST be ignored for authorization by receivers and MUST be absent-tolerant for older peers. Visibility semantics MUST NOT change.
- **FR-011**: The grant API (`n2n_grant`, `POST /n2n/grants`, one-step trust) MUST accept an optional access class, validate it, reject invalid values with HTTP 400 changing nothing, and return it in grant listings. Classification management (list, set override, clear override, import annotations) MUST be available to the operator through the daemon and the n2n MCP server.
- **FR-012**: The same class check MUST apply to internal (iN2N, `already_trusted`) channels, because grants and classification are evaluated unconditionally.
- **FR-013**: Audit MUST record class-denied calls, grant creation with its class, and classification changes.
- **FR-014**: The NCFED draft (grants section, capability cards, semantics, error table note, security considerations, change history) and operator docs MUST specify the model normatively so two implementations interpret it identically; `docs/N2N-PEER-LIMITS.md` MUST be updated to remove the open cross-reference and state the interaction.
- **FR-015**: Backward compatibility: the existing authorization, readmission, chat and limit test suites MUST pass unchanged.

### Key Entities

- **Invocation grant**: peer, target type, target name, requires_approval, timeout, and now access class.
- **Tool/skill classification**: per target, the effective class, its source (operator, annotation) and timestamp.
- **Access class**: `read` or `read_write` on a grant; `read`, `write`, `unclassified` on a target.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the feature present and no operator action, 100% of existing authorization tests pass unmodified and every pre-existing grant behaves identically.
- **SC-002**: For a decision matrix of grant class x target class (read, write, unclassified) x target type (tool, skill, knowledge, knowledge_replica), the reference implementation's outcome matches the normative table in the draft in 100% of cells.
- **SC-003**: A peer holding only `read` grants cannot cause a write-classified or unclassified tool or skill to run through any path (tools/call, tasks/submit), verified for both direct authorization and post-wait admission.
- **SC-004**: A refused class check debits zero request units and creates zero approvals.
- **SC-005**: A second implementer can derive the same allow/deny result for any case from the draft text alone (review of the normative table plus the test matrix).

## Assumptions

- The access class is local callee policy; it is not negotiated on the wire. Only the advisory card hint is advertised.
- Two classes on a grant are enough; `admin` (device or platform administration beyond write) is not introduced because nothing in the current model distinguishes it.
- Enforcement that a skill classified read really does not write inside its own agent turn is outside what the federation layer can verify; the operator classification is an assertion and defense-in-depth stays with the gateway scope approvals and the sandbox.
- No fabricated external facts: MCP tool annotation semantics are used as the project already consumes them; any claim about the upstream MCP specification text is not asserted here beyond the `readOnlyHint` name.
