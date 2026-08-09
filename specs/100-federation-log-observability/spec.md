# Feature Specification: Federation Inbound-Call Observability

**Feature Branch**: `100-federation-log-observability`
**Created**: 2026-08-06
**Status**: Implemented — code complete, 441 tests green, `reconcile-mcp.py` clean. **Live verification (T048) still pending**: it requires a `netclaw-mesh.service` restart, which drops the live federation channel to `as65006-6.6.6.6`, so it is an explicit operator-confirmed step (plan.md "Restart sensitivity"). SC-003 additionally needs a synthetic dead peer, because the manual endpoint clear during the original incident left the defect dormant — see [baseline.md](./baseline.md).
**Input**: Live operational finding, 2026-08-06 — while watching the mesh daemon log for an expected inbound federated call from peer `as65006-6.6.6.6` ("Nate"), the operator could not have spotted the call by eye. The journal was emitting roughly 38 lines per 5 minutes of pure noise about permanently-dead peers, and the inbound-call path itself logs almost nothing at info level. Detecting the call reliably required polling the `remote_invocation_record` audit table instead of reading the log. Three distinct code defects were confirmed against the source.

## Problem Statement

The mesh daemon's log is the primary operator surface for federation activity, but today it fails in both directions at once:

- **It shouts about things that do not matter.** Permanently-unreachable peers are re-dialled forever at a fixed 60-second ceiling, each failure emitting a long WARNING. Benign TCP probes that connect and immediately hang up produce full ERROR tracebacks.
- **It stays quiet about the thing that matters most.** An inbound federated call — the single most operationally significant event in the system — is nearly invisible at info level.

The result is an observability inversion: routine noise is loud and urgent-looking, while the real event is silent. An operator watching the log cannot distinguish "healthy and idle" from "a call just arrived" from "a peer is genuinely broken."

This was not a theoretical concern. It was found while actively waiting for a real call, and the workaround was to bypass the log entirely and poll the database.

## Clarifications

### Session 2026-08-06

- Q: How far should a long-dead peer be backed off, given the current 60s-forever ceiling? → A: Escalate long-dead peers (stale endpoint plus many consecutive failures) to a **15-minute** ceiling; peers that have only recently begun failing keep the existing 60-second behavior. An endpoint change resets the backoff immediately, so a peer that re-registers reconnects within seconds regardless of how long it was dampened.
- Q: A flapping peer currently resets its failure counter on every success, which would defeat dampening entirely. How should that be handled? → A: Clear dampening only after a connection has **stayed up for a sustained period**, not on the mere fact of connecting. A flapping peer therefore remains dampened and summarized.
- Q: How should the "forget a peer's endpoint" operation be exposed? → A: A supported **registry method plus an operator-facing tool**, so a stale endpoint can be retired conversationally without shell access or direct database writes. No HUD control — that is out of scope for this feature.

### Decisions taken without a question (reasonable defaults, recorded for traceability)

- **Correlation reuses the existing per-request identifier.** Every inbound handler already receives a request identifier and already writes it to the audit record, so FR-005 needs no new correlation mechanism — the identifier already present becomes the log correlation key.
- **Inbound-call logging is centralized at the existing audit choke point.** Every inbound handler already funnels each of its decision branches through one audit-recording helper. Emitting operator-facing log entries there yields uniform coverage of every inbound method and every branch, rather than depending on per-handler logging that would inevitably be added inconsistently and drift as handlers are added.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An inbound federated call is unmistakable in the log (Priority: P1)

An operator watching the mesh daemon log can attribute each inbound call to a specific request and can immediately distinguish a routine success from a refusal.

**IMPORTANT — corrected premise.** The original draft of this spec asserted that the inbound-call path logs almost nothing at info level. **That was wrong**, and the correction substantially narrows this story. Every audit write already emits one info-level line carrying direction, peer identity, target type and name, decision, outcome, and provenance reference. Because every inbound handler routes each of its decision branches through that single audit call, an inbound call is *already* visible, and FR-001, FR-002, FR-004, and FR-006 are **already satisfied by existing behavior**.

The error arose from inspecting the invocation module for logging calls and finding almost none, without following through to the audit component it delegates logging to. The practical lesson is recorded here because it shaped the spec: the operational failure on 2026-08-06 was **not** that inbound calls are unlogged — it was that the surrounding noise (User Stories 2 and 3) buried a line that already existed, and that the observer's own log filter omitted the audit channel.

What remains genuinely missing is narrow and specific:

- **Refusals are indistinguishable by severity from successes.** Every audit line is emitted at info, so an authorization denial reads at the same severity as a routine success and cannot be isolated by severity filtering.
- **The log line omits the request identifier** that the audit record itself stores, so entries cannot be tied to a specific request or to their audit row from the log alone.
- **There is no arrival event distinct from the outcome.** A call that hangs or never reaches a decision leaves no trace, because the existing line is written at decision time rather than on receipt.

**Why this priority**: Retained at P1 because refusal-versus-success severity is a security-relevant distinction and because correlation is what makes the other two stories' logs auditable. It is now a much smaller change than first scoped — an enhancement to one existing choke point, not new logging across many handlers.

**Independent Test**: Trigger a permitted inbound invocation and a denied one from a test peer, and read only the log. The reader can tie each entry to a request identifier and can isolate the denial by severity alone.

**Acceptance Scenarios**:

1. **Given** a federated peer, **When** it invokes a capability it is not authorized for, **Then** the refusal is emitted at a severity distinct from and higher than routine success, naming the peer and the refused target.
2. **Given** any inbound call, **When** it is logged, **Then** the entry carries the request identifier already stored on the audit record, so the log line and the audit row can be joined without guesswork.
3. **Given** an inbound call that never reaches a decision, **When** an operator inspects the log, **Then** the call's arrival is nonetheless visible.
4. **Given** a burst of inbound calls, **When** they are logged, **Then** each entry can be attributed to a specific request rather than interleaving ambiguously.
5. **Given** existing audit behavior, **When** this story is implemented, **Then** no inbound call produces duplicate or redundant log lines — the existing line is enriched, not supplemented by a parallel one.

---

### User Story 2 - A dead peer stops drowning out the log (Priority: P2)

A peer whose endpoint is permanently unreachable is reported once, clearly, and then stops repeating itself — while remaining federated and reconnecting promptly if it comes back.

**Why this priority**: This is what made Story 1's signal invisible in practice, so it is a genuine part of the fix rather than cleanup. It is P2 rather than P1 because a log that is quiet but uninformative still fails the operator; the positive signal has to exist first for the quiet to be worth anything.

**Independent Test**: Point a federated peer at an endpoint with nothing listening and watch for an extended period. Failure reporting collapses to a periodic summary rather than one entry per attempt, and total log volume from that peer drops substantially.

**Acceptance Scenarios**:

1. **Given** a peer whose endpoint refuses connections, **When** repeated dial attempts fail with the same cause, **Then** the log reports the condition on first detection and thereafter only at a much reduced, summarized cadence.
2. **Given** a peer that has failed continuously for a long period and whose endpoint information is long stale, **When** the supervisor considers it, **Then** it is dialled markedly less often than a peer that just started failing.
3. **Given** a healthy peer that suffers one transient failure, **When** the next dial opportunity arrives, **Then** its reconnection is not delayed by the dampening applied to long-dead peers.
4. **Given** a long-dead, dampened peer, **When** it re-registers a fresh endpoint, **Then** dialling and normal reporting resume promptly without operator intervention.
5. **Given** a dampened peer, **When** an operator inspects peer health, **Then** the peer's unreachable status and consecutive-failure count remain visible even though it is no longer logging each attempt.

---

### User Story 3 - Benign disconnects are not reported as errors (Priority: P2)

A connection that opens and closes without sending data — a health probe, a port scan, a load-balancer check, an aborted dial — produces a single quiet line, not an error with a stack trace. Genuine protocol violations still produce a full error.

**Why this priority**: Same rationale as Story 2 — it is part of why the log was unreadable. It is separable from Story 2 because it affects the inbound accept path rather than the outbound dial path, and either can ship alone.

**Independent Test**: Open a TCP connection to the daemon's listener, send nothing, close it. Confirm one low-severity line with no stack trace. Then send a malformed protocol preamble and confirm an error-level entry is still produced.

**Acceptance Scenarios**:

1. **Given** the listener is accepting, **When** a peer connects and closes before sending any bytes, **Then** the event is recorded as a single low-severity line naming the source and reason, with no stack trace.
2. **Given** the listener is accepting, **When** a peer sends a truncated preamble and disconnects mid-handshake, **Then** the event is likewise low-severity and traceback-free.
3. **Given** the listener is accepting, **When** a peer sends a preamble that is complete but invalid, **Then** the event is reported at error severity as it is today.
4. **Given** an unexpected internal fault occurs while handling an inbound connection, **When** it is caught, **Then** it is still reported at error severity with a stack trace — dampening must not swallow real bugs.

---

### User Story 4 - An operator can retire a stale endpoint through a supported operation (Priority: P3)

An operator can tell the system to forget a peer's recorded endpoint, leaving the peer federated and ready to reconnect when it re-registers, without hand-editing the federation database.

**Why this priority**: P3 because Story 2's automatic dampening addresses the operational symptom without operator action. This story removes the need for unsupported manual database surgery, which is a correctness and safety concern rather than an observability one — but it is real: resolving the live incident required a direct SQL write against the running system's database.

**Independent Test**: Invoke the operation against a peer with a recorded endpoint. The endpoint is cleared, the peer remains federated, the dial loop skips it, and a subsequent re-registration restores it.

**Acceptance Scenarios**:

1. **Given** a federated peer with a recorded endpoint, **When** an operator forgets its endpoint, **Then** endpoint host, port, and endpoint-freshness marker are cleared together, and the peer's federated state, trust material, and audit history are untouched.
2. **Given** a peer whose endpoint has been forgotten, **When** the reconnect supervisor runs, **Then** the peer is skipped without producing failure entries.
3. **Given** a peer whose endpoint has been forgotten, **When** the peer re-registers an endpoint, **Then** it is recorded and dialling resumes.
4. **Given** any peer, **When** an operator forgets an endpoint, **Then** the action is recorded so the change is attributable after the fact.

---

---

### User Story 5 - An outbound call's outcome is recorded, not left pending forever (Priority: P1)

When this system calls a remote peer, the audit record reflects what actually came back — granted, denied, failed, or timed out — rather than remaining permanently in a "pending" state.

**Why this priority**: P1 because it defeats cross-ledger reconciliation, the core promise of federation auditing. Discovered 2026-08-06 at 18:53Z during a live two-party test with peer `as65006-6.6.6.6`, where the peer's stated protocol was "match the request identifier across your log and my chain." Two outbound calls were recorded and both remain `requested/pending` indefinitely. The response — including an expected **denial** — was returned to the caller but never persisted. A ledger that cannot show the outcome of its own outgoing calls cannot be reconciled against a counterparty's, and a denial that is invisible in the audit trail is precisely the record a security review would need.

**Independent Test**: Invoke a remote tool that is known to be refused. The audit record for that call reflects the refusal rather than staying pending.

**Acceptance Scenarios**:

1. **Given** an outbound invocation to a peer, **When** the peer returns a refusal, **Then** the audit record and log reflect a denied outcome tied to the same request identifier, not a pending one.
2. **Given** an outbound invocation, **When** the peer returns a successful result, **Then** the record reflects success.
3. **Given** an outbound invocation, **When** the call times out or the channel drops, **Then** the record reflects that terminal state rather than remaining pending forever.
4. **Given** a reconciliation against a counterparty's ledger, **When** both sides are compared by request identifier, **Then** each side shows a terminal outcome for the same call.

---

### Edge Cases

- A peer is dampened for being long-dead at the exact moment it comes back. *Resolved by FR-013*: if it re-registers an endpoint it reconnects within seconds; if it returns without re-registering, the worst-case delay is one escalated interval (~15 minutes). This bounded blind spot is an accepted tradeoff, not an oversight.
- Two peers fail with different causes: are their failures summarized separately, or does one mask the other?
- The endpoint-freshness marker is absent entirely (never set) rather than merely old — is that treated as "stale" or "unknown"?
- A peer flaps: repeatedly succeeds and fails. *Resolved by FR-031*: because today's behavior resets the failure counter on any success, flapping would otherwise defeat dampening completely and recreate the storm; dampening therefore clears only after sustained uptime. Note the peer whose reconnect was observed live on 2026-08-06 exhibited exactly this close-then-reopen shape, so this path is real traffic, not a hypothetical.
- An inbound call arrives while its peer is simultaneously being dialled outbound — do both paths log coherently?
- A capability denial and a benign disconnect arrive from the same peer in the same second — can an operator still tell them apart?
- Forgetting the endpoint of a peer with a currently-live channel: is the channel torn down or left running?
- A single inbound connection carries many sequential invocations — does per-call logging scale, or does a chatty peer become the new noise source?
- Log volume under a genuine incident (many peers failing at once) must stay bounded without suppressing the fact that many peers are failing.

## Requirements *(mandatory)*

### Functional Requirements

**Inbound-call visibility**

> Note: FR-001, FR-002, FR-004, and FR-006 were verified to be **already satisfied** by existing audit logging. They are retained as regression guards — the implementation must not lose them — and are marked accordingly. Only FR-003, FR-005, FR-033, and FR-032 require new work.

- **FR-001** *(already satisfied — regression guard)*: The system MUST record, at info level, each inbound federated invocation, identifying the calling peer and the requested target.
- **FR-002** *(already satisfied — regression guard)*: The system MUST record the authorization decision for each inbound invocation, distinguishing granted from denied.
- **FR-003**: The system MUST emit a denied inbound invocation at a severity distinct from and higher than routine success, so refusals can be isolated by severity alone, and MUST NOT allow denials to be suppressed by any noise-dampening behavior.
- **FR-004** *(already satisfied — regression guard)*: The system MUST record the terminal outcome of each inbound invocation, including failures and cancellations, so that no call is left with an unresolved final state in the log.
- **FR-005**: Operator-facing log entries for an inbound invocation MUST carry the request identifier already persisted on the audit record, so a log line can be joined to its audit row without guesswork.
- **FR-006** *(already satisfied — regression guard)*: The system MUST make a newly created pending approval visible in the log at the time it is created.
- **FR-007**: Inbound-call logging MUST NOT emit secrets, credentials, key material, or full invocation payloads.
- **FR-033**: The system MUST make an inbound call's arrival visible even when it never reaches a decision, so a hung or abandoned call is not invisible.
- **FR-032**: Enriching inbound-call logging MUST NOT introduce a second, parallel log line per call. The existing single audit line is to be enriched in place; total log volume per inbound call MUST NOT increase beyond the arrival event required by FR-008.

**Dead-peer dampening**

- **FR-008**: Repeated dial failures against the same peer with an unchanged cause MUST collapse into a periodic summary rather than one entry per attempt.
- **FR-009**: A summarized report MUST convey how many attempts it covers and the period covered, so suppression never hides the scale of a problem.
- **FR-010**: A peer that has failed continuously over a long period AND whose endpoint information is stale MUST escalate to a retry interval of approximately 15 minutes. A peer that has only recently begun failing MUST retain the existing ceiling of approximately 60 seconds.
- **FR-011**: The endpoint-freshness signal MUST be an input to how aggressively a peer is dialled and reported; a peer is eligible for the escalated interval in FR-010 only when both its failure history and its endpoint staleness indicate a durable outage.
- **FR-012**: Dampening MUST NOT delay reconnection for a peer that has failed only transiently.
- **FR-013**: A dampened peer MUST remain federated. A change to a peer's endpoint MUST reset its backoff immediately, so that a peer which re-registers reconnects within seconds no matter how long it was dampened.
- **FR-014**: A peer's unreachable status and consecutive-failure count MUST remain observable to an operator while dampened.
- **FR-031**: Dampening MUST be cleared only after a connection has remained up for a sustained period, not on the mere fact of a successful connection. A peer that repeatedly connects and drops MUST remain dampened and summarized rather than resetting its failure history on each brief success.
- **FR-015**: Successive failures with materially different causes MUST NOT be collapsed into one another.
- **FR-016**: Total log volume attributable to unreachable peers MUST remain bounded as the number of unreachable peers grows, while still conveying that multiple peers are affected.

**Benign-disconnect classification**

- **FR-017**: A pre-handshake disconnect that sends no bytes, or is truncated mid-preamble, MUST be recorded as a single low-severity entry without a stack trace, naming the source and the reason.
- **FR-018**: A complete-but-invalid protocol preamble MUST continue to be reported at error severity.
- **FR-019**: Unexpected internal faults on the inbound path MUST continue to be reported at error severity with a stack trace.
- **FR-020**: Severity assignment MUST be driven by whether an operator needs to act, not by which code path raised the condition.
- **FR-038**: Malformed or non-protocol connections to the publicly-reachable edge listener MUST NOT produce error-level stack traces. Observed live on 2026-08-06 from 14:58 onward: internet background scanning against the listener's port produced repeated multi-frame tracebacks for ordinary probe traffic (plain HTTP sent to a WebSocket endpoint — wrong method, missing upgrade header). These are unsolicited, expected, and never actionable, and because the port is internet-reachable the volume is unbounded and continuous. Such connections MUST be summarized at low severity, subject to the same dampening as FR-008, and MUST remain distinguishable from a genuine enrolled-device connection failure, which an operator does need to see.
- **FR-030**: A benign warning emitted by the underlying async runtime on every secure channel closure — one that reflects a harmless internal detail of how encrypted streams signal end-of-file, is not caused by peer behavior, and requires no operator action — MUST NOT reach the operator at warning severity. Because this warning originates outside the system's own code, the remedy is reclassification or filtering rather than a behavioral change, and it MUST NOT be addressed by suppressing genuine warnings from the same runtime.

**Endpoint retirement**

- **FR-021**: The system MUST provide a supported registry operation to forget a peer's endpoint, clearing endpoint host, port, and freshness marker together, AND MUST expose it as an operator-facing tool so a stale endpoint can be retired without shell access or direct database writes.
- **FR-022**: Forgetting an endpoint MUST leave the peer's federated state, trust material, chat enablement, and audit history unchanged.
- **FR-023**: After an endpoint is forgotten, the peer MUST be skipped by dialling until an endpoint is recorded again.
- **FR-024**: Re-registration of an endpoint MUST restore normal dialling without further operator action.
- **FR-025**: Endpoint-forgetting MUST be recorded such that the change is attributable after the fact.
- **FR-026**: Achieving any requirement in this feature MUST NOT require direct database manipulation by an operator.

**Outbound outcome resolution**

- **FR-034**: An outbound invocation's audit record MUST be updated with its terminal outcome — success, denial, failure, or timeout — rather than remaining permanently in a pending state.
- **FR-035**: The terminal outcome MUST be joined to the same request identifier used when the call was initiated, so both parties to a federated call can reconcile the same call by identifier.
- **FR-036**: A refusal returned by a remote peer MUST be recorded as a denial, not discarded, so refusals are auditable evidence rather than transient responses.
- **FR-037**: A call that times out or whose channel drops before a response MUST reach a terminal recorded state rather than remaining pending.

**Preservation of existing behavior**

- **FR-027**: The audit trail, provenance trail, and approval flows MUST retain their current behavior and completeness; no logging change may reduce what is recorded for audit.
- **FR-028**: Existing tuning controls MUST keep working, and any new dampening behavior MUST be tunable and disableable so an operator can restore verbose reporting when diagnosing.
- **FR-029**: Changes MUST NOT alter federation wire behavior, protocol compatibility, or trust decisions.

### Key Entities

- **Peer dial health**: per-peer liveness view — current state, consecutive failure count, next retry time, last successful contact, last failure cause, and the dampening state governing reporting cadence.
- **Endpoint freshness**: the marker indicating when a peer's endpoint was last recorded, used as a staleness input to dialling and reporting.
- **Inbound invocation log event**: the correlated sequence of operator-visible events for one inbound call — received, authorized or denied, terminal outcome — tied to the invocation's audit identity.
- **Failure summary**: the aggregate standing in for many suppressed identical failures, carrying attempt count and covered period.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator reading only the log can determine that an inbound federated call arrived, from which peer, for what target, and how it ended — without querying any database.
- **SC-002**: Detecting an inbound call no longer requires polling the audit store; the log alone is sufficient.
- **SC-003**: With one or more permanently-unreachable peers configured, sustained log volume attributable to them is reduced by at least 90% compared with today, measured over a period long enough to include many retry intervals.
- **SC-004**: A benign connect-and-close produces exactly one log line and no stack trace.
- **SC-005**: A peer suffering a single transient failure reconnects no later than it does today.
- **SC-006**: A long-dead peer that re-registers an endpoint resumes normal operation within seconds; one that becomes reachable without re-registering resumes within approximately 15 minutes.
- **SC-012**: A peer that repeatedly connects and drops does not defeat dampening — its log volume stays bounded rather than returning to per-attempt reporting.
- **SC-007**: Retiring a stale endpoint is achievable through a supported operation, with zero direct database writes.
- **SC-008**: In a live scenario mixing one healthy peer, one dead peer, and background probe traffic, an inbound call is identifiable in the log within seconds by visual inspection.
- **SC-009**: Audit completeness is unchanged: for any inbound call, the audit record contains everything it contains today.
- **SC-010**: An operator can restore full verbose failure reporting through configuration when diagnosing.
- **SC-011**: A normal secure-channel closure produces no operator-facing warning.

## Assumptions

- The mesh daemon's journal is the primary operator-facing observability surface; no external log aggregation or alerting system is assumed present.
- "Operator" means someone with shell access to the host running the daemon, reading the service journal directly.
- Standard log levels carry their conventional meanings: error implies action may be needed, warning implies attention, info is normal significant activity, debug is diagnostic detail.
- The existing reconnect supervisor, its tuning controls, and the peer health view are the right places to express dampening; no new supervisory component is assumed necessary.
- Peers legitimately come and go. A peer being unreachable is a normal steady state, not an incident — which is why it must not be reported as one indefinitely.
- Concrete thresholds (summary cadence, staleness horizon, maximum retry interval) are implementation-tunable; this spec constrains their required *properties*, not their values.
- No new third-party dependencies. Changes remain within the existing federation and BGP agent code of the protocol MCP server, consistent with the language and structure of features 052–066.
- The endpoint-freshness marker is already recorded on every endpoint-write path, so it is a trustworthy staleness input.
- Existing automatic endpoint re-registration on inbound contact means forgetting an endpoint is safe and self-healing.
- **Channel lifecycle logging is already adequate and is not the gap.** Confirmed by live observation on 2026-08-06 at 14:39, when a peer's channel closed and reconnected: closure, deregistration, inventory caching, and channel re-establishment were each reported clearly at info level. The deficiency is specific to the *invocation* path — what happens once a live channel carries an actual capability call. This narrows the work and means the fix should follow the conventions the channel path already demonstrates rather than invent new ones.
- The benign runtime warning in FR-030 accompanies normal closure of an encrypted channel. It is not a symptom of peer misbehavior, and it is emitted by the async runtime's own stream handling rather than by this system's code, so no change to the system's own connection handling will remove it.

## Out of Scope

- **The `fd00:ee::0` BGP session flap observed alongside these defects is configuration, not code.** It originates from a configured BGP peer with nothing listening, and is corrected by editing the daemon's environment configuration and restarting the service — not by changing code. It is excluded from this feature deliberately. However, it exhibits **the same defect shape as User Story 2**: a session state machine that reports a known-dead peer forever at unchanging cadence. Whether the dampening principle established here should also govern BGP session retry reporting is a legitimate follow-on question this feature should answer explicitly rather than silently leave open.

  **Answered (T047, 2026-08-06): yes — as a follow-on spec, not as scope creep here.**

  The measured case for it is now stronger than when this spec was written. `baseline.md`
  records **241 `Connection failed to fd00:ee::0` lines today** at a flat 5 per 10
  minutes, and unlike the federation storm this one is *still running* — clearing the
  peers' endpoints silenced US2's noise but did nothing for the BGP FSM, which has no
  endpoint-staleness concept to gate on. After this feature lands, `fd00:ee::0` becomes
  the single largest remaining source of mesh-daemon log noise.

  Three reasons it is nonetheless a separate spec:

  1. **Different state machine, different code.** US2's dampening lives in
     `FederationService`'s reconnect supervisor and keys off `federation_peer`
     endpoint freshness. The BGP FSM (`bgp/session.py`) has neither a peer registry row
     nor an endpoint-freshness marker, so FR-011's two-signal test has no second signal
     available. A BGP equivalent needs its own staleness notion (e.g. "never once
     reached Established"), which is a design question, not a port.
  2. **RFC 4271 constrains it.** Federation dial cadence is NetClaw's own invention and
     free to change. BGP `ConnectRetryTimer` behavior is specified, and altering retry
     *scheduling* risks interoperability with real routers. A follow-on spec must
     separate **reporting** cadence (safe to dampen) from **retry** cadence (not), a
     distinction this feature never had to make because both were ours.
  3. **The immediate remedy is config, and it is one line.** Removing the dead peer from
     the daemon's environment eliminates 241 lines/day today, with no code risk. Fixing
     the reporting in code is the durable answer for *operators who legitimately
     configure an unreachable peer* — a real but secondary case.

  **Recommended follow-on scope**: apply the reporting principle (collapse identical
  consecutive FSM transition failures into a periodic summary carrying count and period)
  to `bgp/session.py`, reusing this feature's `_cause_sig` normalization and
  `N2N_RECONNECT_SUMMARY_INTERVAL_S`-style tunable, and explicitly **not** changing
  `ConnectRetryTimer` scheduling. That keeps RFC 4271 conformance untouched while
  removing the noise.
- Changing federation wire protocol, handshake semantics, trust model, or certificate handling.
- Altering audit, provenance, or approval semantics beyond making existing events visible in the log.
- Building log aggregation, metrics export, dashboards, or alerting.
- Reworking the operator HUD or any user interface.
- Changing internal (intra-risk) delegation behavior, except where it shares the inbound logging path.
- Retiring or garbage-collecting peer records themselves; this feature forgets endpoints, it does not delete peers.

## Dependencies

- The existing peer registry and its endpoint-freshness marker.
- The existing reconnect supervisor and its tuning controls.
- The existing inbound connection accept and protocol-discrimination path.
- The existing inbound invocation authorization and dispatch path.
- The existing audit and provenance stores, which this feature must preserve unchanged.
