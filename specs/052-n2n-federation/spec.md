# Feature Specification: NetClaw-to-NetClaw (N2N) Federation

> **Channel trust superseded by [feature 060](../060-claw-cert-security/spec.md):** the cleartext/pinned channel behavior described here is upgraded to TLS + certificate authentication (eN2N mutual auth, iN2N hub attestation) by claw certification. This spec is unchanged for historical accuracy.


**Feature Branch**: `052-n2n-federation`
**Created**: 2026-07-10
**Status**: Draft
**Input**: User description: "NetClaw-to-NetClaw (N2N) Federation — skills, capabilities, remote tool invocation, and claw-to-claw chat over the existing BGP mesh. Elevates the mesh from route exchange to full agent federation between consenting NetClaw operators: signed capability advertisement, remote capability queries, authorized remote tool/skill invocation, operator-initiated claw-to-claw chat, and a HUD federation view — with mutual consent, default-deny authorization, and full audit."

## Overview

NetClaw instances already peer with one another over the NetClaw Mesh: eBGP sessions
carried over public tunnel endpoints, exchanging identity routes and a mesh directory
of peer endpoints. Today that mesh answers only one question: **who** is out there.
Operators can see remote claws as nodes in the Visual HUD, but cannot learn **what**
a remote claw can do, ask it anything, or use any of its capabilities.

N2N Federation adds the application layer on top of the mesh. Two operators who have
both explicitly opted in can: see each other's advertised skills and tool inventories,
ask their own NetClaw questions about the peer's capabilities, invoke specifically
allowlisted tools or skills on the peer (with the remote operator in control at every
step), and hold attributed, rate-limited conversations with the peer's agent — all
without any credentials or secrets ever leaving either machine.

## Clarifications

### Session 2026-07-10

- Q: How should a claw's stable federation identity be established and verified at
  consent time? → A: BGP identity (AS number + router-id), as presented in the BGP
  OPEN on the established mesh session. Inventory authenticity is anchored to arrival
  over that session (channel-based), not to per-claw signatures. Residual spoofing
  risk (anyone who can dial a claw's public port can claim any AS/router-id) is
  accepted for v1 and mitigated by mutual consent + operator out-of-band confirmation.
- Q: How is the remote operator's compute cost bounded when peers use their claw
  (chat + invocations that engage the remote agent/LLM)? → A: Per-peer daily budget
  (requests and tokens per day, operator-configurable) enforced by the remote side,
  in addition to per-minute rate limits; exceeding either returns a clear "budget
  exhausted" refusal, logged on both sides.
- Q: What carries N2N traffic between peers, given the overlay tunnel currently fails
  to establish while BGP works? → A: N2N rides the peer's existing public mesh
  endpoint using protocol discrimination (multiplexed alongside BGP on the same
  port), as a first-class channel — federation must work wherever a BGP mesh session
  works; no dependence on the current overlay tunnel layer and no new exposed ports.
- Q: Where does the remote operator see and answer human-approval prompts? → A: On
  their existing NetClaw channels (Slack/Webex/CLI — wherever they are connected),
  with approve/deny actions; the HUD federation view also lists pending approvals.
- Q: What is remotely invocable in v1 — tools only, or also skills? → A: Both. Tools
  execute as direct calls; a skill executes as a delegated task on the remote agent
  (its own LLM, policies, and per-peer budget), returning the finished result to the
  requester. Both are allowlisted per peer under the same grant model.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Capability Exchange & Remote Capability Queries (Priority: P1)

John's NetClaw (AS 65001) is mesh-peered with Nicholas's (AS 65007) and Byrn's
(AS 65099). John and Nicholas each run one command (or answer one prompt) consenting
to federate with the other. From then on, each claw advertises an inventory of
its skills, MCP servers, tool names, and coarse platform capabilities ("has CML",
"has pyATS testbed", "has Meraki") to the other. John can then ask his own NetClaw:
"does Nicholas's claw have CML?", "what skills does Nicholas have that I don't?" and
get an answer immediately from the last-received inventory, including how fresh that
inventory is. Items the remote operator marked hidden never appear.

**Why this priority**: Discovery is the foundation every other story builds on —
invocation, chat, and the HUD view all consume the exchanged inventory. It is also
independently valuable: knowing what a peer can do is useful even before any remote
execution exists.

**Independent Test**: Peer two NetClaw instances, complete mutual consent, and verify
each side can answer capability questions about the other from local state — including
correct handling of hidden items, a peer that never consented (no inventory visible),
and a stale inventory (staleness surfaced in the answer).

**Acceptance Scenarios**:

1. **Given** two mesh-peered claws where both operators have consented to federate,
   **When** either operator asks their own claw what the peer can do, **Then** the
   answer lists the peer's advertised skills, tool inventories, and capability badges,
   with the inventory's age indicated.
2. **Given** a mesh-peered claw whose operator has NOT consented, **When** an operator
   asks about that peer's capabilities, **Then** the claw reports that the peer is
   present on the mesh but has not federated, and shows no inventory.
3. **Given** an operator marks a skill or MCP server as hidden, **When** inventories
   are next exchanged, **Then** that item is absent from what peers receive (not
   merely masked at display time).
4. **Given** a received inventory fails its authenticity check, **When** the claw
   processes it, **Then** the inventory is rejected, the previous known-good inventory
   is retained, and the event is logged and surfaced to the operator.
5. **Given** a peer goes offline, **When** the operator queries its capabilities,
   **Then** the last-received inventory is returned clearly marked as stale with the
   time of last refresh.

---

### User Story 2 - Authorized Remote Tool/Skill Invocation (Priority: P2)

Nicholas allowlists exactly two things for John's claw: his CML lab-listing tool and
his network health-summary skill. John asks his own NetClaw "list the labs on
Nicholas's CML server". John's claw sends the request over the established N2N channel;
Nicholas's claw checks the allowlist, (optionally) asks Nicholas for human approval,
runs the tool locally with Nicholas's own credentials, and returns only the result.
Both sides log the full exchange. Anything not allowlisted is refused by default.

**Why this priority**: This is the headline capability — using a peer's lab or platform
through your own claw — but it depends on the P1 inventory to know what is invocable,
and it carries the highest security weight, so it lands second.

**Independent Test**: With a single tool allowlisted between two federated claws,
verify the allowlisted invocation succeeds end-to-end, a non-allowlisted invocation
is refused with a clear reason, human-approval mode blocks until the remote operator
approves or denies, and both sides hold complete audit records of every attempt.

**Acceptance Scenarios**:

1. **Given** a tool is on the remote peer's allowlist for the requesting claw,
   **When** the requesting operator invokes it through their own claw, **Then** the
   tool executes on the remote side and the result returns to the requesting operator,
   attributed to the remote claw.
2. **Given** a tool is NOT allowlisted, **When** invocation is attempted, **Then** the
   remote claw refuses without executing anything, the requester receives an explicit
   denial, and both sides log the attempt.
3. **Given** the remote operator has enabled human approval for a tool category,
   **When** a request arrives in that category, **Then** nothing executes until the
   remote operator approves, and the request expires with a denial if not approved
   within the configured window.
4. **Given** the remote side has its security layer (DefenseClaw) enabled, **When** an
   inbound N2N invocation arrives, **Then** it passes through the same guardrail
   inspection as any local tool call before execution.
5. **Given** any remote invocation completes (success or failure), **Then** both claws
   hold an audit record of who asked, what ran, when, and what was returned.
6. **Given** a remote invocation result arrives, **When** the requesting claw processes
   it, **Then** the result is treated as untrusted input — displayed and reasoned
   about, but never auto-executed as instructions.

---

### User Story 3 - Claw-to-Claw Chat (Priority: P3)

John asks his NetClaw: "ask Byrn's claw why its OSPF area 0 is flapping." John's claw
relays the question over the N2N channel to Byrn's claw, which answers using its own
local knowledge and tools (under its own operator's policies), and the response streams
back into John's session. Both operators see the conversation clearly attributed —
Byrn can see that John's claw is asking, and John sees the answer is Byrn's claw
speaking, not his own.

**Why this priority**: Chat delivers the "converse with a remote expert" experience,
but is only safe and meaningful once consent (P1) and the authorization/audit machinery
(P2) exist to govern what the remote agent may do while answering.

**Independent Test**: Between two federated claws with chat enabled, send a question
and verify an attributed response returns; verify a peer with chat disabled refuses;
verify rate limiting caps a message flood; verify both operators can review the
exchange afterward.

**Acceptance Scenarios**:

1. **Given** both operators have chat enabled for each other, **When** one operator
   directs a question to the peer's claw, **Then** the peer's claw answers and the
   response is delivered attributed to the remote claw, visible in both operators'
   session history.
2. **Given** the remote operator has chat disabled for this peer, **When** a chat
   message arrives, **Then** it is refused with a clear "chat not enabled" response
   and no agent processing occurs.
3. **Given** messages exceed the configured rate limit, **When** further messages
   arrive, **Then** they are rejected with a rate-limit notice until the window resets.
4. **Given** the remote claw uses tools while composing its answer, **Then** those
   tool uses are governed by the remote operator's own local policies, not the
   requester's.

---

### User Story 4 - HUD Federation View (Priority: P4)

John opens the Visual HUD. The claw nodes for Nicholas and Byrn are now expandable:
clicking Nicholas's node shows his advertised skills, MCP servers and tools, capability
badges (CML, pyATS, Meraki, …), and how fresh the inventory is. Remote inventory is
visually distinct from John's local inventory. From the expanded node, John can open a
claw-to-claw chat with Nicholas's claw. A peer that hasn't federated shows as a plain
claw node with a "not federated" state.

**Why this priority**: Pure presentation over data produced by P1–P3; valuable for
demos and situational awareness but not required for any federation function to work.

**Independent Test**: With one federated and one non-federated peer on the mesh, open
the HUD and verify the federated node expands to show inventory, badges, and freshness;
the non-federated node shows its state without inventory; and the chat affordance opens
a working conversation when chat is enabled.

**Acceptance Scenarios**:

1. **Given** a federated peer with a received inventory, **When** the operator clicks
   its claw node, **Then** the node expands to show skills, tools, capability badges,
   and inventory freshness, styled distinctly from local inventory.
2. **Given** a mesh peer that has not federated, **When** viewed in the HUD, **Then**
   it renders as a claw node marked not-federated, with no inventory shown.
3. **Given** chat is enabled with a federated peer, **When** the operator uses the
   node's chat affordance, **Then** a claw-to-claw conversation opens in the HUD.
4. **Given** an inventory goes stale or a peer's N2N is severed, **When** the HUD
   refreshes, **Then** the node's freshness/state indicator updates accordingly.

---

### Edge Cases

- **Consent races**: one side consents and the other hasn't yet — no inventory flows
  in either direction until both have; the pending state is visible to both operators.
- **Consent revocation / kill switch**: an operator severs N2N with a peer — capability
  exchange, invocation, and chat stop immediately for that peer; the underlying BGP
  session and route exchange are unaffected; previously received inventory from that
  peer is discarded or clearly marked revoked.
- **Peer restart with new endpoint**: a claw returns with a different public endpoint
  (tunnel endpoints change) — federation state (consent, allowlists) survives and
  re-attaches to the peer's stable identity, not its transient endpoint.
- **Identity collision or spoofing attempt**: a third claw presents another peer's
  AS/router-id — because federation requires mutual consent per identity AND the
  inventory must arrive over that identity's established session, the impostor gains
  no federation state unless the operator consents to it; conflicting sessions
  claiming an already-federated identity are flagged to the operator and logged.
- **Very large inventories**: a claw with hundreds of skills/tools advertises — the
  exchange completes without disrupting BGP keepalives or the session (inventory
  transfer must never starve the control plane).
- **Long-running remote invocation**: a remote tool runs past its window — the request
  times out on the requester side with a clear status, and the remote side's execution
  outcome is still audited.
- **Remote result containing prompt-injection content**: a remote answer or tool result
  contains instructions ("run this command…") — the requesting claw treats it as data;
  it never executes remote-supplied instructions without local operator action.
- **Simultaneous requests from multiple peers**: two peers invoke tools on the same
  claw concurrently — each is authorized, executed, rate-limited, and audited
  independently.
- **Unknown/legacy peers**: a mesh peer running a pre-federation NetClaw version —
  gracefully appears as not-federated; no errors on either side.

## Requirements *(mandatory)*

### Functional Requirements

**Consent & Trust**

- **FR-001**: Federation with a peer MUST require explicit opt-in from BOTH operators
  (mutual consent) before any capability information is exchanged in either direction.
- **FR-002**: Each claw's federation identity MUST be its BGP identity (AS number +
  router-id) as presented in the BGP OPEN of the established mesh session; federation
  state re-associates by this identity across endpoint changes.
- **FR-003**: Inventory authenticity MUST be anchored to the established mesh session
  it arrives over (channel-based): inventories arriving outside an Established session
  for that AS/router-id, or claiming a different identity than the session's, MUST be
  rejected, retaining the last known-good inventory and logging the rejection. The
  residual v1 spoofing risk is accepted and mitigated by mutual consent (FR-001) plus
  operator out-of-band confirmation at consent time.
- **FR-004**: Operators MUST be able to sever N2N federation with a specific peer at
  any time with a single action (kill switch); severing MUST take effect immediately,
  MUST NOT drop the underlying BGP session, and MUST be reversible only by repeating
  mutual consent.

**Capability Advertisement & Query**

- **FR-005**: A federated claw MUST advertise an inventory comprising: its skills
  (name + description), its MCP servers and their tool names, and coarse platform
  capability badges (e.g. CML, pyATS, Meraki).
- **FR-006**: Operators MUST be able to set per-item visibility (advertise to all
  federated peers / advertise to selected peers / hidden) for every skill and MCP
  server; hidden items MUST be excluded from the advertised inventory itself, not
  merely hidden at display time.
- **FR-007**: Inventories MUST NEVER include credentials, environment/configuration
  secrets, device addresses, testbed contents, or any operator-identifying data beyond
  what the operator explicitly chooses to advertise.
- **FR-008**: Inventories MUST refresh automatically when local capabilities change
  and periodically at a configurable interval; every stored remote inventory MUST
  carry its received-at time.
- **FR-009**: An operator MUST be able to query, through their own claw, any federated
  peer's capabilities (existence checks, listings, and local-vs-remote comparisons)
  answered entirely from locally stored inventory, with staleness indicated whenever
  the inventory is older than its refresh interval.
- **FR-010**: All N2N traffic (capability exchange, invocation, chat) MUST ride the
  peer's existing public mesh endpoint, multiplexed alongside BGP via protocol
  discrimination, and MUST NOT require any new inbound network exposure beyond what
  mesh peering already established; N2N MUST be able to establish wherever a BGP mesh
  session can establish.
- **FR-011**: Inventory transfer MUST NOT disrupt BGP session health (keepalives and
  route exchange take precedence).

**Remote Invocation**

- **FR-012**: Remote invocation MUST be default-deny: a peer may invoke only tools and
  skills the remote operator has explicitly allowlisted for that specific peer. Tools
  execute as direct calls; skills execute as delegated tasks on the remote agent (its
  own reasoning, policies, and per-peer budget), returning only the finished result.
- **FR-013**: The remote operator MUST be able to require human approval per tool,
  per skill, or per category; approval prompts MUST be delivered on the operator's
  existing NetClaw channels (Slack/Webex/CLI — wherever connected) with approve/deny
  actions, and also listed as pending in the HUD federation view; unapproved requests
  MUST expire and be denied after a configurable window.
- **FR-014**: Remote invocations MUST execute with the remote claw's own local
  policies, credentials, and security layer (including DefenseClaw guardrail
  inspection when enabled) exactly as if locally initiated; only results — never
  credentials or session state — return to the requester.
- **FR-015**: Every remote invocation attempt (allowed, denied, approved, expired,
  failed, or timed out) MUST be audit-logged on BOTH sides with requester identity,
  target tool/skill, timestamps, outcome, and returned payload reference.
- **FR-016**: Requesting claws MUST treat all remote results as untrusted input:
  rendered and reasoned over, never automatically executed as instructions.
- **FR-017**: Remote invocations MUST be rate-limited per peer AND bounded by a
  per-peer daily budget (request count and token spend, operator-configurable)
  enforced by the executing side; requests MUST carry a timeout after which the
  requester receives a definitive status, and budget/rate refusals MUST be explicit
  ("budget exhausted" / "rate limited") and logged on both sides.

**Claw-to-Claw Chat**

- **FR-018**: Operators MUST be able to enable/disable chat per federated peer;
  disabled chat MUST refuse inbound messages without engaging the agent.
- **FR-019**: Chat messages MUST relay from the requesting operator through their own
  claw to the remote claw's agent, with responses streamed back and every message
  clearly attributed to its originating claw and operator in both sessions.
- **FR-020**: Chat MUST be rate-limited per peer and MUST draw from the same per-peer
  daily budget as remote invocations (FR-017); full conversation history MUST be
  available to both operators for review.
- **FR-021**: While answering chat, the remote agent's tool use MUST be governed
  solely by its own operator's local policies.
- **FR-022**: Every N2N chat exchange MUST be audit-logged on both sides.

**HUD Federation View**

- **FR-023**: The Visual HUD MUST render each mesh peer's federation state (not
  federated / consent pending / federated / severed) on its claw node.
- **FR-024**: Federated claw nodes MUST expand to show the peer's advertised skills,
  MCP servers/tools, capability badges, and inventory freshness, visually distinct
  from local inventory.
- **FR-025**: The HUD MUST offer a chat affordance on federated peers with chat
  enabled, opening an attributed claw-to-claw conversation.
- **FR-026**: The HUD MUST update federation state, inventory content, and freshness
  without requiring a restart.

**Compatibility & Resilience**

- **FR-027**: Mesh peers running pre-federation versions MUST interoperate unchanged
  (BGP + HUD node) and simply appear as not-federated.
- **FR-028**: Federation state (identity, consent, allowlists, chat settings) MUST
  survive restarts and endpoint changes of either peer and re-associate by federation
  identity, not endpoint.

### Key Entities

- **Federation Peer**: a remote NetClaw known from the mesh, keyed by stable
  federation identity; carries AS number, display name, endpoint (transient),
  federation state (not federated / pending / federated / severed); authenticity of
  what it sends is anchored to its established mesh session (see FR-003).
- **Consent Record**: an operator's decision to federate with a specific peer;
  both directions required for active federation; revocable (kill switch).
- **Capability Inventory**: the versioned set a claw advertises — skill entries
  (name, description, visibility), MCP server entries (name, tool names, visibility),
  capability badges; carries issue time and the advertising identity (AS + router-id).
  Stored remotely with received-at time for staleness.
- **Invocation Grant (Allowlist Entry)**: remote-operator-owned permission tying one
  peer to one invocable tool/skill, with optional human-approval flag, rate limits,
  and timeout. Grants draw against the peer's daily budget (request + token caps,
  shared with chat).
- **Remote Invocation Record**: audit entry for one invocation attempt — requester,
  target, decision path (allowlisted / approved / denied / expired), timing, outcome,
  result reference. Exists on both sides.
- **N2N Chat Session**: an attributed conversation between one operator (via their
  claw) and a peer claw's agent; carries per-peer enablement, rate-limit state, and
  message history.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Two operators can go from mesh-peered to fully federated (mutual consent
  + first inventory exchange) in under 5 minutes without editing files by hand.
- **SC-002**: Capability questions about a federated peer ("does X have CML?") are
  answered from local state in under 5 seconds, with inventory age always shown.
- **SC-003**: 100% of remote invocation attempts are resolved by the authorization
  policy (allowlist / approval / deny) — zero executions of non-allowlisted tools in
  testing — and 100% of attempts appear in both sides' audit logs.
- **SC-004**: No credential, secret, or unadvertised item is ever observable in any
  N2N exchange (verified by inspection of everything a test peer receives).
- **SC-005**: An allowlisted remote tool invocation round-trips (ask → remote execution
  → result displayed) in under 30 seconds for typical tools.
- **SC-006**: Severing a peer (kill switch) halts all N2N exchange with that peer
  within 10 seconds while its BGP session remains Established.
- **SC-007**: A claw-to-claw chat question receives a first response token within 15
  seconds, and both operators can review the full attributed exchange afterward.
- **SC-008**: The HUD reflects a peer's federation state and inventory within 30
  seconds of change, and operators can find a remote capability via the HUD in under
  1 minute.
- **SC-009**: A three-claw mesh (as demonstrated: AS 65001, 65007, 65099) runs
  federation for 24 hours with zero BGP session flaps attributable to N2N traffic.

## Assumptions

- The existing NetClaw Mesh (eBGP over public tunnel endpoints, mesh directory,
  overlay tunnel channel) is the transport; N2N adds no new listening ports beyond
  what mesh peering already uses.
- N2N traffic is multiplexed on the same public endpoint as BGP via protocol
  discrimination (per Clarifications) — the existing TunnelManager's discrimination
  mechanism is the precedent, but N2N does not depend on the current overlay tunnel
  layer establishing. If the N2N channel itself cannot establish, federation degrades
  gracefully to "peered but not federated" rather than falling back to
  unauthenticated paths.
- **Federation wire protocol**: candidate protocols are Agent2Agent (A2A — agent
  cards for capability discovery, task lifecycle for delegated work, streaming for
  chat) and/or exposing each claw's allowlisted tools to peers as a standard MCP
  server surface; both are JSON-RPC 2.0 based, matching the platform's existing
  protocol family. The concrete choice (A2A, MCP-over-mesh, hybrid, or bespoke
  JSON-RPC 2.0) is a plan-phase decision — this spec constrains only the behavior,
  consent, and security properties the chosen protocol must satisfy.
- Federation identity is the BGP identity (AS + router-id) per Clarifications; no
  keys, certificates, or central authority in v1. Operators confirm each other's
  AS/router-id out-of-band (as they already coordinate peering details today) before
  consenting.
- The operator's existing agent surfaces (Slack/CLI/HUD chat) are how N2N questions
  and invocations are initiated; no new operator-facing client is introduced.
- Audit logging reuses the platform's existing audit stores (e.g. GAIT / Memory MCP /
  DefenseClaw logs) rather than introducing a new store.
- Capability badges are derived from which MCP servers/skills are installed and
  advertised — not from probing the operator's devices.
- Default visibility on first run is privacy-leaning: MCP servers start hidden
  (operator opts them in), skill names start advertised to federated peers;
  both are operator-changeable per item (FR-006).
- Rate-limit, approval-window, and refresh-interval defaults will be set at plan time;
  all are operator-configurable per peer.
- Out of scope (per description): multi-hop federation through an intermediate claw,
  a federation marketplace/registry, and any autonomous claw-to-claw action without a
  human operator initiating it.
