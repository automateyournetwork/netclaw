# Feature Specification: iN2N — Internal NetClaw Federation (a "risk" of claws)

**Feature Branch**: `056-in2n-internal-federation`
**Created**: 2026-07-12
**Status**: Draft
**Input**: User description: "iN2N — internal NetClaw federation (a \"risk\" of claws with a Border Claw). Builds on the completed, live-proven eN2N work (spec 052 NCFED protocol + spec 053 ergonomics/reliability). One operator runs a group of focused NetClaws — a \"risk\" — coordinated by a single Border Claw."

## Context & Background

NetClaw already supports **external federation (eN2N)**: independently-operated NetClaws, run by different people on different infrastructure, mutually consent and then discover each other's capabilities, invoke each other's tools/skills, and delegate long tasks over the NCFED protocol (spec 052) with reliability hardening (spec 053). That work is complete and proven live across a three-operator mesh.

This feature adds **internal federation (iN2N)**: a *single* operator running *several* focused NetClaws on their *own* infrastructure, coordinated as one named group. Because NetClaw's mascot is a lobster, the group is called a **"risk"** — the real (and, for a security-adjacent product, fitting) collective noun for a group of lobsters. A standalone NetClaw is simply "a risk of one."

The motivation is **focus and economy**: rather than one NetClaw carrying the entire skill and tool catalog (large, expensive context; broad blast radius), an operator runs a few tightly-scoped member claws — a "CML claw" that only knows CML, a "pyATS claw" that only knows testing — behind one coordinating **Border Claw**. The operator only ever talks to the Border; the Border routes each request to the specialist that should handle it, and is also the single, auditable door to the outside world.

## Clarifications

### Session 2026-07-12

- Q: How does a member prove it legitimately belongs to the risk when it first registers with the Border (esp. a distributed member dialing in from another cloud)? → A: **Enrollment token + runtime self-signed key, pinned (TOFU).** The Border issues a one-time enrollment token at risk creation; each member generates its own self-signed keypair/cert at runtime; on enrollment the member presents the token *and* its public key; the Border validates the token then pins the key; all subsequent channels are authenticated by the pinned key. No CA to run. The token is single-use; cert rotation requires re-enrollment or operator-approved re-pin.
- Q: How are members named/addressed in the registry, audit, and routing — do we need an iBGP-style mesh since members can be anywhere? → A: **Risk-local member ID + hub-and-spoke star; no mesh.** Members are identified by a stable risk-local ID (`<risk>/<member-name>`) bound to the pinned key (the name is the handle, the key authenticates). No iBGP / no full mesh: iN2N is a star centered on the Border (members talk only to the Border, never to each other). Reachability across hosts/clouds is achieved by **each member dialing OUTBOUND to the Border's single reachable endpoint** — so members need no inbound ports, no public address, and no ngrok even when distributed.
- Q: Should a risk deploy default members, should profiles be easy, and are there tools EVERY claw needs? → A: **Defaults + easy profiles already specified; added a mandatory base floor.** Default seed members (FR-022) and catalog-derived profiles + Custom (FR-019–021) were already in the spec. NEW: every member — any profile, including Custom — gets a non-removable **base floor** (iN2N runtime/heartbeat, self-status + capability reporting, audit/GAIT-to-Border, constitutional safety behaviors), and that floor is excluded from the routing specificity tie-break so shared base tools don't distort specialist selection (FR-021a/FR-021b).
- Q: How does a member leave the risk / have its trust revoked? → A: **Operator `remove member` + automatic quarantine.** The operator can remove a member at the Border, which unpins its key, drops it from the registry, and refuses further connections (return requires full re-enrollment with a new token). In addition, the Border **automatically quarantines** a member that repeatedly fails health or authentication — unpinning it and alerting the operator — rather than letting a misbehaving or suspected-compromised member keep reconnecting.

## Terminology

- **Risk**: a named, described group of NetClaws owned and operated by one person/organization on their own infrastructure.
- **Border Claw**: the single coordinating claw in a risk. The only claw the operator interacts with, the only one exposed to the outside (eN2N), and the single point of reporting, audit, and GAIT logging. Exactly one per risk.
- **Member Claw**: an internal, tightly-scoped claw within a risk. Talks only to its Border over the risk's internal transport; carries only the skills/tools it needs for its specialty; does **not** join the public federation mesh or do per-peer mutual consent.
- **Trust domain**: what actually distinguishes iN2N from eN2N. A risk is **one trust domain** (one owner). iN2N is coordination *within* one trust domain (implicit trust). eN2N is federation *between* trust domains (mutual consent). This is a boundary of ownership, **not of physical location** — a risk's members may be co-located on one host or distributed as microservices across multiple hosts, clouds, or datacenters.
- **eN2N** (external N2N): Border-to-Border federation across *different* risks (trust domains) over the existing NCFED mesh (spec 052/053). Unchanged by this feature.
- **iN2N** (internal N2N): Border-to-Member coordination *within* one risk (one trust domain) over the risk's internal transport. New in this feature.
- **Internal transport**: the operator-controlled connectivity between a Border and its members. May be loopback/unix socket (co-located), a private network/VPC, an overlay/VPN (e.g. WireGuard/Tailscale), or the operator's own tunnels when members are geographically distributed. The defining property is that it stays **within the operator's own trust domain** and does not require the public mutual-consent NCFED mesh — **not** that it is physically local.
- **Claw profile**: a pre-defined bundle of skills/tools that gives a member claw its specialty (e.g. "CML claw", "pyATS claw", "security claw"), plus a "Custom" option to hand-pick.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stand up a risk and talk only to the Border (Priority: P1)

An operator installs NetClaw and is asked whether this claw is a **standalone NetClaw** or **part of a risk**. Choosing "part of a risk," they name and describe the risk and choose this claw's **role** — Border or Member. They stand up a Border and at least one Member (e.g. a CML member). From then on, the operator interacts *only* with the Border; the Border knows its members and can reach them over the risk's internal transport (whether they are on the same host or distributed across the operator's own hosts, clouds, or datacenters). Members are never addressed directly by the operator and never join the public federation mesh or do per-peer mutual consent.

**Why this priority**: This is the foundational structure. Without the ability to form a risk, designate a single Border, and register members reachable over a local transport, none of the routing or economy benefits exist. It is the minimum viable slice: a two-claw risk (Border + one Member) that the operator drives entirely through the Border.

**Independent Test**: Install one claw as a Border and one as a Member of the same named risk; confirm the operator's interface reaches only the Border, the Border lists the Member as reachable/healthy over the local transport, and the Member has no internet-facing endpoint configured.

**Acceptance Scenarios**:

1. **Given** a fresh install, **When** the operator chooses "part of a risk" and selects role "Border" with a risk name and description, **Then** the claw is configured as the sole Border of that named risk and exposes the operator-facing interface (gateway).
2. **Given** a Border exists for a risk, **When** the operator installs a second claw as a "Member" of that same risk (co-located or in another cloud/datacenter), **Then** the Member registers with the Border over the risk's internal transport and appears in the Border's member list as reachable, without joining the public federation mesh or performing mutual consent.
3. **Given** a running risk, **When** the operator attempts to interact with a Member directly, **Then** the intended interaction path is through the Border (members do not expose an operator-facing interface).
4. **Given** the operator chooses "standalone NetClaw," **Then** the claw behaves exactly as a NetClaw does today (a "risk of one," its own Border), with no member coordination overhead.

---

### User Story 2 - Ask the Border to route work to the right specialist Member (Priority: P1)

The operator asks their Border a task-shaped request ("recreate my lab in CML," "run the pyATS testbed against these devices"). The Border determines which member claw owns the relevant capability, delegates the work to that member over the local transport, tracks it to completion, and returns the result to the operator — all without the operator needing to know which member did the work.

**Why this priority**: This is the core value of iN2N — a coordinating Border that turns a fleet of narrow specialists into one capable assistant, keeping each member's context small and cheap. Together with US1 it forms the complete "focused fleet" experience.

**Independent Test**: With a Border and a CML member, ask the Border to perform a CML operation; confirm the Border delegates it to the CML member (visible in the Border's audit/trace), the member executes it with its own local tools, and the result returns to the operator through the Border.

**Acceptance Scenarios**:

1. **Given** a risk with a Border and a specialist member that owns a capability, **When** the operator asks the Border for work matching that capability, **Then** the Border delegates it to the correct member and returns the member's result.
2. **Given** a long-running member task (multi-minute build), **When** the operator issues it through the Border, **Then** it runs as a tracked background task (submit → poll → result), survives transport blips, and does not fail as one blocking call. *(Reuses spec 053 async delegation semantics.)*
3. **Given** a request that matches no member's capability, **When** the operator asks the Border, **Then** the Border reports that no member in the risk can perform it (rather than silently failing or attempting it without a capable member).
4. **Given** the Border delegates work internally, **Then** no credentials or secrets are transferred between claws — each member acts with its own local configuration.

---

### User Story 3 - Provision a risk with pre-set member profiles, no hand-assembly (Priority: P2)

When forming a new risk, the operator is offered a set of **pre-set claw profiles** derived from NetClaw's existing skill catalog (e.g. "CML claw," "pyATS claw," "security claw"), plus a **Custom** option to pick individual skills/tools. Selecting profiles provisions those member claws so the operator does not configure each specialist by hand. A new risk can come seeded with a handful of common members.

**Why this priority**: Provisioning is what makes iN2N practical rather than tedious. It's valuable but sits on top of the US1/US2 mechanics — the risk still works if members are added one at a time, so this is P2.

**Independent Test**: Create a new risk and select two pre-set profiles; confirm two members are provisioned, each scoped to only that profile's skills/tools, and each appears in the Border's member list.

**Acceptance Scenarios**:

1. **Given** the risk-formation flow, **When** the operator selects the "CML claw" profile, **Then** a member is provisioned carrying only the CML-related skills/tools of that profile.
2. **Given** the risk-formation flow, **When** the operator selects "Custom," **Then** they can choose an arbitrary subset of the skill catalog for that member.
3. **Given** available profiles, **Then** each profile's contents are derived from the actual installed skill catalog (not a hardcoded list that can drift from reality).
4. **Given** a newly created risk, **When** no explicit choices are made, **Then** the risk is seeded with a small default set of common members (which the operator may edit or remove).

---

### User Story 4 - The Border is the risk's single, auditable face to the outside (Priority: P2)

The operator enables **eN2N**, **iN2N**, or **both** on the Border (only the Border can federate externally). To a peer risk, the whole risk appears as one identity — the Border's — regardless of how many members are behind it. Every internal delegation and every external invocation is recorded centrally at the Border (reporting, audit, GAIT), giving one place to see everything the risk did and everything done to it.

**Why this priority**: Consolidating the external boundary and the audit trail at the Border is the security and observability payoff. It depends on US1's role model, so P2.

**Independent Test**: On a Border with both stacks enabled, have a peer risk query capabilities and delegate a task; confirm the peer sees a single risk identity (the Border), the task is fulfilled (possibly by an internal member) without exposing member identities or secrets externally, and the Border's audit log shows both the external request and any internal delegation it triggered.

**Acceptance Scenarios**:

1. **Given** a Border with eN2N enabled, **When** a peer risk federates and views capabilities, **Then** it interacts with one identity (the Border) and does not receive member-level endpoints or internal topology.
2. **Given** an external request that the Border satisfies by delegating to a member, **Then** the external peer receives a result attributed to the risk, while the Border's audit trail records both the external request and the internal delegation.
3. **Given** the Border's role, **When** the operator opens reporting/audit, **Then** all internal (iN2N) and external (eN2N) activity for the risk is visible in one place.
4. **Given** a Member claw, **Then** it cannot federate externally on its own (only the Border holds the external stack).

---

### User Story 5 - Member scoping is enforced, not just declared (Priority: P3)

A member claw provisioned as a "CML claw" can only do CML-scoped work. If the Border (or a chain of delegation) asks a member to do something outside its scope, the member declines rather than silently expanding its own capability. The Border can see each member's declared scope and health, and surfaces a member that is unreachable or misbehaving.

**Why this priority**: Enforced scoping is what makes the "small blast radius, small context" promise real, and health visibility keeps the fleet operable. It refines US1–US4 rather than enabling them, so P3.

**Independent Test**: Ask a CML-scoped member (through the Border) to perform a non-CML action; confirm it is refused by scope. Stop a member and confirm the Border reports it unreachable.

**Acceptance Scenarios**:

1. **Given** a member scoped to a profile, **When** it is asked to perform work outside that scope, **Then** the request is refused on the grounds of scope, not silently attempted.
2. **Given** a member becomes unreachable, **When** the Border health-checks it, **Then** the Border reports the member's state (e.g. unreachable) and does not route new work to it.
3. **Given** the operator asks the Border, **Then** they can see each member's specialty/scope and current health in one place.

---

### Edge Cases

- **Two Borders in one risk**: A risk MUST have exactly one Border. Configuration attempting a second Border for the same risk MUST be rejected/flagged rather than producing an ambiguous coordinator.
- **Member with no Border / orphaned member**: A member whose Border is unreachable does nothing on its own (it has no operator-facing interface); the operator sees this via the Border once it returns, or via the member's own status if inspected directly.
- **Border down**: If the Border is down, the risk has no operator interface and no external presence until it returns; members hold no external state that could leak in the meantime.
- **Capability overlap**: If two members can satisfy the same request, the Border MUST choose deterministically (documented tie-break) rather than fanning out unpredictably.
- **Standalone → risk migration**: An existing standalone NetClaw that later becomes a Border MUST keep working; its existing skills remain until the operator chooses to slim it down.
- **External identity churn**: eN2N endpoint churn (ngrok address changes) is handled by the existing spec-053 re-announce; this feature does not regress it. Members never have external endpoints to churn.
- **Secret isolation across delegation**: Neither internal (iN2N) nor external (eN2N) delegation ever transfers credentials, `.env` values, device addresses, or testbed secrets between claws.
- **Removed/quarantined member reconnecting**: A member whose key has been unpinned (via operator removal or automatic quarantine) MUST be refused on reconnect and MUST NOT be silently re-trusted; it can only return through full re-enrollment (or explicit operator re-pin).
- **Enrollment token leak/reuse**: A single-use token already spent (a member's key pinned) MUST be rejected if presented again, so a leaked-but-spent token grants nothing.
- **Compromised key suspicion**: The operator can remove/quarantine a member to immediately unpin a suspected-compromised key and cut its access at the single Border boundary, without disturbing other members.

## Requirements *(mandatory)*

### Functional Requirements

#### Risk formation & roles

- **FR-001**: The installer MUST let the operator choose, at install time, whether a claw is a **standalone NetClaw** or **part of a risk**.
- **FR-002**: When "part of a risk" is chosen, the installer MUST capture a **risk name and description** and a **role** for the claw: **Border** or **Member**.
- **FR-003**: A risk MUST have **exactly one Border**; the system MUST prevent or flag configuration of a second Border for the same risk.
- **FR-004**: A **standalone NetClaw** MUST behave identically to today's NetClaw (a "risk of one," its own Border) with no member-coordination behavior imposed.
- **FR-005**: Only the **Border** MUST expose the operator-facing interface (gateway); **Member claws MUST NOT** expose an operator-facing interface.
- **FR-006**: **Member claws MUST NOT join the public federation mesh** (no participation in eN2N mutual consent, no advertised public NCFED endpoint) to function within the risk. Members may be co-located with the Border or distributed across the operator's own hosts, clouds, or datacenters.

#### Internal coordination (iN2N)

- **FR-007**: A Member claw MUST register with, and reach, its Border over the **risk's internal transport** — connectivity within the operator's own trust domain — by **dialing outbound to the Border's single reachable endpoint**. This transport MUST support both co-located members (loopback/socket) and geographically distributed members (private network, overlay/VPN, or operator-controlled tunnel), without requiring per-peer mutual consent, inbound ports on the member, or any public member endpoint.
- **FR-007a**: iN2N MUST be a **hub-and-spoke star** centered on the Border: members communicate only with the Border, never member-to-member. The system MUST NOT require a routing protocol (e.g. iBGP) or a full mesh among members; adding a member adds one spoke.
- **FR-008**: The Border MUST maintain a registry of its members keyed by a **stable risk-local member ID** (`<risk>/<member-name>`) bound to the member's pinned key, recording each member's **declared specialty/scope**, its **transport binding**, and its **current health/reachability**. The member ID MUST be stable across relocation of the member (e.g. moving between clouds); the pinned key, not the network location, is the authenticator.
- **FR-009**: The Border MUST be able to **route/delegate a request to the member** that owns the relevant capability and return that member's result to the operator.
- **FR-010**: Internal delegation of long-running work MUST use **asynchronous task semantics** (submit → status → result → cancel) reusing spec 053's delegation model, so no internal operation depends on a single long blocking call.
- **FR-011**: When **no member** can satisfy a request, the Border MUST report that plainly rather than silently failing or attempting it without a capable member.
- **FR-012**: When **multiple members** can satisfy a request, the Border MUST select one **deterministically** by a documented rule.
- **FR-013**: iN2N coordination MUST reuse the **NCFED JSON-RPC 2.0 semantics and capability-inventory model** from spec 052, bound to the internal transport, with a **relaxed, owner-implicit trust profile** (members of one operator's risk are auto-trusted within the risk — no per-member mutual-consent handshake). Because a member may be reachable over a distributed transport rather than loopback, the internal channel MUST still be authenticated/encrypted end-to-end so a member cannot be impersonated within the trust domain.
- **FR-013a**: Member enrollment MUST use a **one-time enrollment token issued by the Border at risk creation** combined with a **member-generated self-signed key**: on first registration the member presents the token and its public key, the Border validates the token and **pins the key** (trust-on-first-use), and all subsequent internal channels are authenticated by the pinned key. The system MUST NOT require a certificate authority.
- **FR-013b**: An enrollment token MUST be **single-use** (spent once a member's key is pinned); a member rotating or regenerating its key MUST **re-enroll** (new token) or be **re-pinned via explicit operator approval** at the Border. A registration presenting an invalid, expired, or already-spent token, or a key that does not match the pinned key for a known member, MUST be rejected.
- **FR-013c**: The operator MUST be able to **remove a member** at the Border; removal MUST unpin the member's key, drop it from the registry, refuse its further connections, and stop routing work to it. A removed member MUST require **full re-enrollment** (a new token) to rejoin.
- **FR-013d**: The Border MUST **automatically quarantine** a member that repeatedly fails health or authentication (by a documented threshold): unpin its key, stop routing to it, and **alert the operator**. The operator alert is surfaced in-band via `n2n_member_health` and the HUD (no external push — see `contracts/in2n-enrollment.md` §5); it is not an autonomous external notification. A quarantined member MUST NOT silently reconnect on its pinned key; recovery requires operator action (re-pin or re-enrollment).

#### External boundary (eN2N) via the Border

- **FR-014**: Only the **Border** MUST be able to federate externally (eN2N); Member claws MUST NOT hold or use the external federation stack.
- **FR-015**: The Border install/config MUST let the operator enable **eN2N**, **iN2N**, or **both**.
- **FR-016**: To an external peer risk, the entire risk MUST present as a **single identity — the Border's** — and MUST NOT expose member-level identities, endpoints, or internal topology.
- **FR-017**: The Border MUST continue to enforce the **full spec 052/053 external trust model** (mutual consent per external peer, default-deny invocation, budgets, kill switch, no-secrets guard) for eN2N unchanged.
- **FR-018**: The existing **eN2N wire framing, consent, default-deny, and no-secrets guards MUST NOT be changed** by this feature.

#### Provisioning & profiles

- **FR-019**: The risk-formation flow MUST offer **pre-set claw profiles** whose contents are **derived from the installed skill catalog** (so profiles cannot drift from what actually exists).
- **FR-020**: The flow MUST offer a **Custom** option to select an arbitrary subset of skills/tools for a member.
- **FR-021**: Selecting a profile MUST **provision a member scoped to that profile's skills/tools plus the mandatory base floor (FR-021a)** — no hand-assembly of each specialist.
- **FR-021a**: EVERY member, regardless of profile (including Custom), MUST include a minimal **mandatory base floor** that cannot be removed: (a) the iN2N member runtime (enroll/dial/heartbeat), (b) self-status and capability reporting so the Border can discover and route to it, (c) audit/GAIT reporting of its own actions back to the Border (Constitution IV), and (d) the constitutional safety behaviors (read-before-write; no unapproved destructive commands — Constitution I/II). The base floor is the *floor*, not a way to widen a member's specialty.
- **FR-021b**: The base floor MUST NOT count toward the routing "most-specific specialist" tie-break (FR-012): specificity is measured over a member's **specialty** capabilities only, so the base tools every member shares do not distort which member is the true specialist.
- **FR-022**: A newly created risk MAY be **seeded with a small default set of common members** (e.g. a CML claw and a pyATS claw), which the operator can edit or remove.

#### Scoping, audit & security

- **FR-023**: A member's capability MUST be **enforced to its declared scope**: work outside scope MUST be refused, not silently attempted or self-expanded.
- **FR-024**: The Border MUST be the **single point of reporting, audit, and GAIT logging** for the risk, recording **both internal (iN2N) delegations and external (eN2N) activity** in one place.
- **FR-025**: An external request satisfied by internal delegation MUST be recorded as **both** the external request and the internal delegation it triggered, while the external result is attributed to the risk (not the member).
- **FR-026**: **No credentials or secrets** MUST ever be transferred between claws over iN2N or eN2N; each claw acts with its own local configuration only.
- **FR-027**: A Member MUST treat instructions arriving from its Border as trusted-within-the-risk, but MUST still refuse out-of-scope actions (FR-023) — i.e. scope enforcement is independent of the relaxed internal trust.

#### Member runtime model

- **FR-028**: A Member claw MUST be a **standalone OpenClaw process/container** (its own runtime), addressed by its Border over a **network-capable internal transport**. When a member is co-located with its Border, the transport MAY be loopback/socket; when a member is distributed on a different host, cloud, or datacenter, the transport MUST work over the operator's own private network, overlay/VPN, or tunnel. The runtime model MUST be **selectable per member** so the same risk can mix a co-located member and a member in another cloud.
- **FR-029**: Because members are standalone runtimes rather than in-process profiles, the Border MUST address, health-check, and delegate to each member by its **stable risk-local member ID** over the member's **established outbound channel** (not by dialing a member-side address). The member registry (FR-008) MUST record each member's transport binding (loopback vs. distributed) alongside its ID, pinned key, scope, and health.

### Key Entities

- **Risk**: A named, described group of claws owned by one operator. Attributes: name, description, external federation mode (eN2N/iN2N/both), the set of member references. Has exactly one Border.
- **Border Claw**: The sole coordinator and external face of a risk. Attributes: risk it belongs to, enabled stacks, member registry, central audit/GAIT log, operator-facing gateway.
- **Member Claw**: A scoped specialist within a risk. Attributes: parent Border, declared specialty/scope (from its profile), skill/tool set, internal-transport address (co-located or in another cloud/datacenter), health state. No public federation-mesh presence, no operator interface.
- **Claw Profile**: A named bundle of skills/tools derived from the installed catalog (e.g. CML, pyATS, security) or Custom. Used to provision and scope members.
- **Internal Delegation**: A task the Border routes to a member (submit/status/result/cancel), recorded in the Border's audit log. Reuses spec 053 task semantics.
- **Member Registration/Health**: The record of a member being reachable to its Border over the internal transport, plus its **pinned channel key** (from enrollment), its transport binding, and its current reachability/health state.
- **Enrollment Token**: A one-time secret issued by the Border at risk creation, presented once by a member (alongside its self-signed public key) to enroll. Spent on successful pinning; invalid/expired/reused tokens are rejected.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can stand up a working risk (one Border + one specialist member) and successfully route a specialty task through the Border to the member in **under 15 minutes** from a fresh install, without the member joining the public federation mesh or completing any mutual-consent handshake.
- **SC-002**: A specialist member's context/skill footprint is **a small fraction of the full catalog** — a member provisioned from a single profile carries only that profile's skills/tools and none of the others.
- **SC-003**: **100% of member claws** in a risk operate **without joining the public federation mesh** — no eN2N mutual-consent participation and no advertised public NCFED endpoint — whether they are co-located or distributed across clouds/datacenters.
- **SC-004**: For **every** request the operator issues to the Border that is satisfied by a member, the Border's audit log contains a record of both the request and the internal delegation — i.e. **no internal delegation is unlogged**.
- **SC-005**: An external peer risk federating with a Border sees **exactly one identity** and **zero** member-level identities, endpoints, or internal-topology details.
- **SC-006**: A long-running internal task (multi-minute build) delegated through the Border **completes as a tracked background task** and does not fail as a single blocking call, matching eN2N's spec-053 reliability.
- **SC-007**: An out-of-scope request to a scoped member is **refused 100% of the time** rather than executed.
- **SC-008**: Standalone NetClaw installs show **no functional regression** versus today's behavior.
- **SC-009**: Existing eN2N federation (spec 052/053) shows **no regression**: the three-operator mesh behaviors (discover, invoke, delegate, self-heal) still pass their existing tests unchanged.
- **SC-010**: A removed or quarantined member is refused on its next connection attempt **100% of the time** and cannot rejoin without a fresh enrollment token; a member presenting a spent, invalid, or expired token is rejected **100% of the time**.
- **SC-011**: Every member is reachable by the Border with **zero inbound ports opened on the member** — 100% of member connectivity is member-initiated outbound to the Border.

## Assumptions

- **Reused foundations**: iN2N reuses the NCFED JSON-RPC 2.0 semantics, capability inventory, and async task delegation from specs 052/053. The eN2N wire framing, consent, default-deny, and no-secrets guards are frozen and untouched.
- **Single-operator trust, not single-location**: What defines a risk is one owner/one trust domain, *not* one host. Members may be co-located OR distributed as microservices across the operator's own hosts, clouds, or datacenters. Trust *within* a risk is implicit (auto-consent); the mutual-consent model applies only at the eN2N boundary between different risks.
- **Internal transport stays within the trust domain**: The Border↔Member transport is operator-controlled connectivity — loopback/socket when co-located, or a private network / overlay-VPN / operator tunnel when distributed. It is authenticated/encrypted but does not use the public mutual-consent NCFED mesh. If distributed members traverse shared infrastructure, that is the operator's own encrypted transport, not eN2N federation.
- **Border-as-broker**: The operator's mental model and interface is a single Border; members are implementation detail the operator provisions but does not converse with directly.
- **Profiles from the live catalog**: Pre-set profiles are generated from the actually-installed skill catalog rather than a static hardcoded list, so they stay accurate as the catalog evolves.
- **Deterministic routing**: When capabilities overlap, a documented deterministic tie-break is acceptable for this version (no sophisticated load-balancing or scoring required).
- **Installer builds on existing modular installer**: The risk/role/profile choices extend NetClaw's existing installer flow rather than introducing a separate installation system.

## Out of Scope

- **Multi-hop federation** chaining three or more risks together (a request hopping Border → peer Border → that peer's peer). Only two-tier (Border↔Member internally, Border↔Border externally) is in scope.
- **Splitting N2N/NCFED into its own repository** — still deferred until the wire format is versioned and external implementers need it.
- **Changing the eN2N protocol** in any way (framing, consent, trust model).
- **Cross-operator member sharing** (a member of one risk directly serving another operator's risk) — external cooperation goes Border-to-Border only.
- **Sophisticated internal scheduling/load-balancing** across multiple equivalent members beyond a deterministic tie-break.
