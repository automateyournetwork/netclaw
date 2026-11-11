# Feature Specification: Federated Peer Limit Semantics (max-prefix-style)

**Feature Branch**: `189-peer-limit-semantics`
**Created**: 2026-11-11
**Status**: Draft
**Input**: GitHub issue #343, "Define max-prefix-style limit semantics for federated peers". NCFED draft section 9.3 defines BUDGET_EXHAUSTED (-32004) and RATE_LIMITED (-32005); section 12.1 says grants MAY carry budgets and rate limits; section 14.6 says deployments SHOULD constrain grants. Nothing says what counts toward a limit, whether limits are per-peer or global, what happens beyond the error, or how counters recover. The reference implementation enforces a per-peer 60-second sliding rate and a per-peer UTC-day budget of requests and tokens, always by refusing the request and keeping the channel.

## Clarifications

### Session 2026-11-11 (autonomous; no human available, defaults recorded)

- Q: Which operations count? -> A: Every inbound operation that causes the receiving side to do work or spend model tokens: tool calls, skill invocations, task submits, chat messages, knowledge queries, and every knowledge-replication request (manifest AND each batch page). Handshake, heartbeat, capability-card exchange, task status/result/cancel and chat open/close do NOT count. Correction found while implementing (analyze finding C3): the first draft of this spec exempted replication batch pages, but the reference implementation (and its 065 tests) authorizes and debits every batch page through the same gate as the manifest. Changing that would alter default behavior, so the spec follows the code and records the operational consequence: replicating a large collection consumes one request unit and one rate slot per page, so operators SHOULD raise the replication peer's limits.
- Q: Per-peer only or also global? -> A: Per-peer is always on. An OPTIONAL global (all-peers) aggregate cap is added, default off (unset).
- Q: On exceed? -> A: Three operator-selectable actions per peer: `refuse` (default; today's behavior, channel kept), `warn` (record and allow the request through; never stops traffic), `teardown` (refuse, then close the channel and hold the peer down for a restart timer). "Drop" in the BGP sense is the same as `refuse` here and is not a separate action.
- Q: Warning threshold? -> A: A fractional threshold, default 0.8 of the hard daily limit, edge-triggered once per limit per day, observable only through audit/status (no wire change).
- Q: Restart timer? -> A: Default 300 seconds, per-peer configurable, applies only to `teardown`; operator can clear it early.
- Q: Counter recovery? -> A: Rate: sliding 60 s window. Budget: UTC day rollover. Teardown hold-down: restart timer expiry. Operator reset: explicit, audited, clears the day counters, the rate window, the hold-down and the warning latch.

- Q: Does the global cap include the per-minute rate? -> A: No. Global scope covers the UTC-day request and token budgets only; a global rate cap adds little over per-peer rate and is deferred.
- Q: Which limit crossings trigger `teardown`? -> A: Any hard-limit exceed (rate, daily requests, daily tokens, global daily requests/tokens). Rate exceed under `teardown` uses the same restart timer. The warning threshold applies to daily request and token budgets only (not rate, which is a short sliding window).
- Q: Tokens are only known after execution; how are they limited? -> A: Unchanged: admission is refused once recorded tokens_used has reached the limit; the request that crosses it completes (no mid-flight abort). A crossing by token debit after completion emits the warning (if newly crossed) and is enforced at the next admission, where the exceed action applies.
- Q: Where does hold-down apply? -> A: Receiver-side, per peer identity, on channel establishment and on every inbound request; it does not affect outbound requests this node makes to the peer.
- Q: Is `warn` allowed to disable the rate limit? -> A: In `warn` the per-minute rate is also warn-only for that peer (consistent "warn means never stop traffic"); operators wanting a hard rate must choose `refuse` or `teardown`.
- Q: Is the global cap's refusal charged to a peer's own counters? -> A: No; a refusal never debits anyone. Admitted requests debit both the peer and the global counter.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Documented, deterministic "what counts" and "what happens" (Priority: P1)

An implementer of a second NCFED agent reads the draft and the reference docs and can predict, for any inbound federated operation, whether it is debited against the limits and what the receiver does when a limit is exceeded, so two implementations behave the same.

**Why this priority**: This is the literal ask of issue #343; without it nothing else is checkable.

**Independent Test**: Review the draft text and the table of counted vs uncounted operations; run the test matrix that feeds each operation type to the reference implementation and asserts the table.

**Acceptance Scenarios**:

1. **Given** a federated peer with a grant, **When** it sends a tool call, skill invocation, task submit, chat message, knowledge query, or replication manifest/batch request, **Then** exactly one request unit is debited and the request counts against the per-minute rate.
2. **Given** the same peer, **When** it sends task status, result, cancel, chat open/close, or heartbeat, **Then** no request unit is debited.
3. **Given** default configuration, **When** a limit is exceeded, **Then** the request is refused with the existing -32005 or -32004 code and the channel stays up, identical to behavior before this feature.

### User Story 2 - Operator picks the exceed action per peer (Priority: P1)

An operator chooses, per peer, whether exceeding a limit only warns, refuses (default), or tears the channel down with a restart timer, and can set the warning threshold and restart timer.

**Why this priority**: This is the max-prefix analogue the issue asks for and the main behavior change.

**Independent Test**: Configure each action on a test peer, drive it past the limit, and assert the outcomes.

**Acceptance Scenarios**:

1. **Given** action `warn`, **When** the peer exceeds the daily request budget, **Then** the request is allowed, an audit record with decision `limit_exceeded_warned` is written, and traffic is never stopped.
2. **Given** action `teardown` and a 300 s restart timer, **When** the peer exceeds a limit, **Then** that request is refused, the channel is closed, an audit record is written, and reconnection attempts within the timer are refused with SEVERED.
3. **Given** a peer in hold-down, **When** the timer elapses or the operator clears it, **Then** the peer can re-establish the channel and counters are unchanged by the clear (only by reset).
4. **Given** action `refuse` (or no configuration), **Then** behavior equals pre-feature behavior.

### User Story 3 - Warning before the hard cap (Priority: P2)

An operator is warned when a peer crosses the warning threshold of its daily request or token limit, before refusals start.

**Why this priority**: Max-prefix practice; lets the operator react before an outage.

**Independent Test**: Debit a peer up to the threshold and assert exactly one warning event per limit per day; cross midnight UTC and assert it re-arms.

**Acceptance Scenarios**:

1. **Given** threshold 0.8 and a 200 request budget, **When** the 160th request is admitted, **Then** one warning audit record is written and later requests that day add none for that limit.
2. **Given** a new UTC day, **When** the peer again crosses the threshold, **Then** a new warning is written.

### User Story 4 - Optional global cap across peers (Priority: P2)

An operator caps the aggregate federated load (all peers combined) so many individually-compliant peers cannot together exhaust the node.

**Why this priority**: Issue question 2; defense against fan-in.

**Independent Test**: Set a global daily request cap below the sum of per-peer caps and assert the cap triggers refusals for any peer once reached.

**Acceptance Scenarios**:

1. **Given** global cap unset, **Then** only per-peer limits apply (default, unchanged).
2. **Given** global cap 50 and two peers each admitted 25 requests, **When** either sends another, **Then** it is refused with BUDGET_EXHAUSTED and the audit reason names the global scope.
3. **Given** global scope exceeded and the peer action `teardown`, **Then** the channel of the peer that crossed it is torn down (global exceed never tears down other peers' channels).

### User Story 5 - Visibility and operator reset (Priority: P2)

The operator and HUD can see each peer's usage, limits, warning state and hold-down remaining, and can reset a peer's counters.

**Why this priority**: Recovery (issue question 5) and observability.

**Independent Test**: Query peer status after traffic, warning, and teardown; reset and observe cleared state plus an audit record.

**Acceptance Scenarios**:

1. **Given** traffic, **Then** status shows used/limit for requests and tokens, rate used/limit, warning flag, action, hold-down remaining.
2. **Given** a reset, **Then** counters, rate window, warning latch and hold-down are cleared and a reset audit record exists.

### Edge Cases

- A refused request never debits the budget (refusals stay free) and, as before this feature, is still subject to the rate check; a refusal does not add a slot to the rate window.
- `warn` action beyond the limit: counters keep incrementing so usage stays truthful; per-minute rate in `warn` is not enforced.
- Teardown while approvals or tasks are in flight: already-admitted work continues; only new admission stops.
- Hold-down must survive a daemon restart (persisted), otherwise a restart defeats it.
- Invalid override values (negative, non-numeric, threshold outside (0,1]) are rejected and leave prior config in place.
- Internal (iN2N) channels using `already_trusted` keep going through the same limits with the same defaults; teardown for an internal channel is not enabled in this feature (documented limitation).
- Limits of 0 mean "deny all"; unset/absent means inherit.
- Clock skew: day boundary uses the receiver's UTC clock only.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define the counted operation set: tool call, skill invocation, task submit, chat message, knowledge query, knowledge-replication request (manifest and each batch page); and MUST NOT debit handshake, heartbeat, card exchange, task status/result/cancel, chat open/close.
- **FR-002**: Per-peer limits MUST remain: sliding 60 s request rate, UTC-day request budget, UTC-day token budget, with today's defaults (10, 200, 500000).
- **FR-003**: The system MUST support per-peer overrides of rate, daily requests, daily tokens, exceed action, warning threshold and restart timer, persisted across restarts; env values remain the global defaults for peers without override.
- **FR-004**: The system MUST support an optional aggregate (all-peers) daily request cap and token cap, disabled by default.
- **FR-005**: The exceed action MUST be one of `refuse`, `warn`, `teardown`; default `refuse` reproduces pre-feature behavior exactly.
- **FR-006**: `warn` MUST allow the request, MUST write an audit record, MUST still count usage, and MUST NOT alter the wire response.
- **FR-007**: `teardown` MUST refuse the triggering request with the existing code, close the peer's channel, persist a hold-down until now+restart timer, refuse new channels from that peer during hold-down, and write audit records for the exceed and teardown.
- **FR-008**: A warning threshold fraction (default 0.8) MUST yield one edge-triggered warning audit record per peer per limit per UTC day.
- **FR-009**: Counters MUST recover by: sliding window (rate), UTC rollover (budget and warning latch), restart-timer expiry (hold-down), and explicit audited operator reset.
- **FR-010**: Refusals MUST stay free of budget debit and MUST still count toward the rate window (existing 052 contract).
- **FR-011**: Every limit event (warning, exceed, warned-through, teardown, hold-down refusal, reset, config change) MUST be recorded in the existing audit trail with scope (peer or global) and the limit name.
- **FR-012**: Peer status exposed to operator and HUD MUST include usage, effective limits, action, warning state, hold-down remaining.
- **FR-013**: No new wire error code or method is required; existing -32004, -32005, -32007 are reused (wire compatibility with draft -00 peers).
- **FR-014**: The NCFED draft source and operator docs MUST normatively describe FR-001..FR-012 without claiming external standards behavior that was not verified; any BGP max-prefix comparison MUST be labelled as analogy.
- **FR-015**: The authorization changes MUST keep the decision/grant API shape stable so the concurrent work on separate read/write grants (issue #344) can be reconciled; the overlap MUST be documented.

### Key Entities

- **Peer limit policy**: per-peer effective rate, daily request and token limits, exceed action, warning threshold, restart timer; defaults inherited from node configuration.
- **Global limit policy**: optional aggregate caps.
- **Usage counters**: per peer per UTC day requests and tokens; sliding rate window; warning latch.
- **Hold-down**: per peer expiry timestamp after a teardown.
- **Limit event**: audit record of warning, exceed, teardown, reset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With no configuration, the existing federation test suite passes unchanged and refusals, codes and channel state are identical to before.
- **SC-002**: For each counted operation and each uncounted operation, an automated test or an explicit code-path assertion confirms the documented debit behavior (100% of table rows covered; knowledge query and replication are asserted by code-path inspection because they need a Chroma store that is not installed in the test environment).
- **SC-003**: Each of the three exceed actions has an automated test proving its outcome, including hold-down persistence across a manager restart.
- **SC-004**: A warning fires exactly once per limit per day in 100% of tested sequences, and re-arms next UTC day.
- **SC-005**: An operator can read the full limit state of a peer and reset it in a single status/reset operation each, with an audit record for the reset.
- **SC-006**: A reader of the draft can answer the five questions of issue #343 from the text alone.

## Assumptions

- Receiver-side enforcement only; the sender is not obliged to self-limit (SHOULD back off on -32004/-32005).
- Applies to eN2N peers; iN2N uses the same counters, with teardown not enabled (limitation recorded).
- The draft source is edited in place (docs/ietf/draft-capobianco-ncfed-00.md) because -00 is the unsubmitted working source per docs/ietf/README.md; a later -01 cut will carry it forward.
- The `n2n_config` tool in the 052 contract is not implemented in code today; this feature supplies the persisted override store and the operator surface behind it.
- Overlap with issue #344 (separate read and write per-peer grants): both touch `Authorizer.authorize()` and `invocation_grant`; this feature adds a separate limit-policy table and counting hooks and does not change grant schema.
