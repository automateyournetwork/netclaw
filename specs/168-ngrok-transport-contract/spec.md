# Feature Specification: direct cloud transport and TLS identities

**Feature Branch**: `168-ngrok-transport-contract`
**Roadmap**: R01
**Created**: 2026-11-01
**Status**: Complete for owner-amended R01 lab scope (40/40); qualification limits in verification.md
**Source baseline**: `9ba12ffc8d1033a0130dd8544aa54d95471afcbb`
**Input**: [R01 Specify input](../../docs/roadmap/issue-310/briefs/R01-ngrok-transport-contract.md#specify-input), [global invariants G1–G11](../../docs/roadmap/issue-310/README.md), and the owner's reusable cloud/local installation and migration requirement.

## Owner-approved pivot — 2026-11-01

The owner explicitly requested a full pivot to cloud-native connectivity after
confirming the ngrok Free plan. Direct cloud TCP is the primary R01 transport;
ngrok remains an optional compatibility transport for NAT-constrained Borders.
Keep this feature directory/branch to preserve its work and audit history.
The new choice supersedes mandatory-ngrok wording in the original brief and G2/G9.
It does not waive exact cloud/spend review or advance R02/R03.

A cloud Border has a stable provider address and two distinct TCP ports: iN2N for
its own members, eN2N/NCFED for independent Borders. Members remain outbound-only.
The single-VM pilot uses a static external IP, application TLS and narrowly scoped
VPC/host firewall rules; no TLS-terminating proxy, public shared BGP dispatcher,
public admin API. The separately approved full HTTPS lab HUD has bounded application ingress; IAP/OS Login handles administration.
A future Layer-4 passthrough load balancer can preserve these bytes and application
TLS, but is unnecessary for this one-Border qualification pilot.

A schema-2 registry explicitly chooses `direct_tcp` or `ngrok_tcp`, with an
operator-owned `address_ref`; schema 1 retains its exact ngrok semantics. Direct
listeners bind an explicitly configured unicast interface address, not a wildcard
or multicast address. ngrok listeners remain loopback-only. A direct transport
never requires a token, starts an agent, or inherits ngrok discovery/fallback.
Changing transport or listener/trust requires explicit registry replacement and
an owned daemon restart. Address-only updates cannot silently change transport.

## Clarifications

### Session 2026-11-01

The owner directed recommended defaults unless repository evidence contradicts
them, with a stop for conditional HUMAN decisions. No additional question was
needed: the binding measurement is unambiguous. This record does not invent a
separate human security review or authorize live endpoint changes.

| Decision | Resolution | Evidence / deviation |
|---|---|---|
| Endpoint registry | Versioned installation-owned file; reviewed bundle distributed to members; no connect-time ngrok identity lookup | Recommended default; selected-runtime ownership already exists |
| Remote TLS | TLS 1.3, including the agent's loopback forwarding hop; explicit local compatibility and migration | Recommended default; source's TLS 1.2 minimum is insufficient for the new profile |
| iN2N binding | Defined `tls-exporter` under a versioned strict profile; no fallback to `tls-unique` | Stdlib Python3.12/OpenSSL3.6 returns matching 48-byte `tls-unique` but has no exporter API. RFC9266 leaves that type undefined for TLS1.3. A public exporter API produced matching 32-byte exporters, distinct on fresh handshakes, with name/CA/TLS1.2 refusals. This is local crypto measurement only |
| iN2N trust | Explicit Border CA plus configured TLS name and pre-provisioned application trust | Recommended CA option; public CA permitted only with explicit name verification |
| Supervision | Owned Border daemon with two direct service ports; optional owned ngrok agent with two reserved endpoints | Recommended default; replaces global process matching and first-tunnel selection in registry mode |
| 443-only members | Unsupported for initial raw-TCP profile; no inferred fallback | Recommended default; assigned TCP port must be reachable |
| eN2N preamble | Preserve mandated identification bytes, then mandatory application TLS; disclose metadata | Resolves G2 wording against R01's explicit wire-preservation requirement and spec063; never permits cleartext application payloads |
| Local compatibility | Preserve explicitly selected local/direct/cloudflared contracts or document migration; strict remote profile never inferred from peer IP | Resolves G2/G8 without allowing forwarded loopback to bypass remote protection |
| Owner portability | Stable identities independent of cloud/DNS; revisions for routing moves; clones get new identity | User-added acceptance; full state/authority migration belongs to later deployment/HA briefs |

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Register and inspect stable Border endpoints (Priority: P1)

As an operator, I register independent stable TCP endpoints for my Border's member
and external-federation services, together with their verified TLS names, trust
anchors and application identities. I can see what is configured and which
connections are actually authenticated, without exposing credentials.

**Why this priority**: Remote connectivity must have an explicit identity and
exposure contract before any cloud workload can be admitted.

**Independent Test**: Load a valid two-service registry into an isolated Border;
verify the operator view names both services and distinguishes configured,
transport-reachable and authenticated states. Refuse malformed or incomplete
registrations before starting a listener or tunnel.

**Acceptance Scenarios**:

1. **Given** two operator-registered endpoints, **When** the registry is validated,
   **Then** iN2N and eN2N have distinct addresses and verified identities, and no
   model, MCP, broker, gateway or quorum service is exposed.
2. **Given** another operator's account, domain and runtime home, **When** the same
   configuration contract is used, **Then** no owner-specific hostname, project,
   credential or filesystem path is required by the implementation.
3. **Given** an absent or incompatible registration, **When** startup is requested,
   **Then** it stops with a bounded actionable error rather than allocating an
   ephemeral address or guessing trust from a tunnel hostname.

### User Story 2 — Enroll and reconnect over verified remote channels (Priority: P1)

As an operator, I enroll a member on a separate network through the Border's
registered iN2N address and reconnect using its existing identity. Independently
administered Borders use a different endpoint and retain bilateral eN2N consent.

**Why this priority**: This supplies the connectivity prerequisite for R03 while
preserving credential and administration boundaries.

**Independent Test**: Through a direct socket and an optional transparent TCP forwarder, complete real TLS and
application enrollment with a routing name different from the certificate name,
then reconnect without consuming another enrollment. Separately complete eN2N
identification, TLS and consent with pre-provisioned peer trust. Repeat over actual
direct cloud endpoints from a separate network before marking live-qualified.

**Acceptance Scenarios**:

1. **Given** a registered Border name and CA, **When** a member dials an unrelated
   routing hostname, **Then** it verifies the registered name and enrolled Border
   identity and admits only the expected Border.
2. **Given** an authenticated member, **When** its tunnel or transport restarts,
   **Then** it reattaches to the same stable address without changing identity
   or replaying an application task.
3. **Given** an external peer with approved identity and reciprocal consent,
   **When** it connects through the external address, **Then** only its existing
   approved external capabilities are available; internal members are inaccessible.

### User Story 3 — Refuse impersonation, downgrade and unintended exposure (Priority: P1)

As an operator, I receive auditable refusal when a caller presents the wrong
identity, weak transport, replayed proof, revoked membership or an unapproved
protocol. A public TCP connection never counts as application admission.

**Why this priority**: A public cloud endpoint exposes a service and does not
provide the private-network authorization previously supplied by a tailnet.

**Independent Test**: Exercise each negative case against the isolated real
protocol implementation and record the refusal stage. Repeat the remotely
meaningful cases through actual direct cloud endpoints during the authorized live pass.

**Acceptance Scenarios**:

1. **Given** a wrong TLS name, untrusted CA/pin, altered channel binding, forged
   possession proof, expired/replayed enrollment or revoked member, **When** it
   connects, **Then** admission fails and the rejection is recorded without secrets.
2. **Given** a remote-profile listener forwarded to loopback, **When** a caller
   attempts cleartext, TLS 1.2, PROXY-header injection or an unknown protocol,
   **Then** the listener refuses it and never switches to a weaker profile.
3. **Given** the public eN2N address, **When** a caller sends BGP routing-control
   traffic, **Then** it is refused without adding or changing routing peers.
4. **Given** two members, **When** either attempts to connect to or impersonate
   a Border to the other, **Then** no member-to-member admission is possible.

### User Story 4 — Relocate transport without cloning identity (Priority: P2)

As an operator moving a Border between local and cloud placements, I replace a
routing address using an explicit reviewed registration update. Existing identities
and approved trust remain stable, and invalid changes leave the prior working
registration recoverable. New installations receive new identities.

**Why this priority**: Stable identity makes the transport reusable across GCP,
Azure, AWS and on-premises deployments without binding it to one account.

**Independent Test**: Move between two controlled forwarding addresses, preserving
the identity and enrollment records; reject mismatched identities and stale
registry revisions. Record this as transport relocation, not full runtime migration.

**Acceptance Scenarios**:

1. **Given** an enrolled member and a reviewed address update, **When** it
   reconnects at the new address, **Then** it requires the same approved Border
   identity and does not accept an unrelated certificate or mint a new member ID.
2. **Given** an unusable candidate address, **When** validation or admission fails,
   **Then** no automatic trust downgrade occurs and the operator can restore the
   previous reviewed registration with an audit record.
3. **Given** existing direct-LAN or cloudflared installations, **When** this feature
   is installed, **Then** their transport stays explicitly selected or a documented
   migration is required; no ngrok account access is required for those paths.

### Edge Cases

- The ngrok agent's last hop is loopback but the original peer is remote.
- A tunnel address resolves and accepts TCP while certificate validation fails.
- An enrollment response is lost after its one-use token was consumed.
- The same application identity appears at a different routing address.
- A stale registry update races a newer endpoint revision.
- A restart occurs during configuration persistence or while a channel is open.
- A revoked member has an already-open channel.
- A mixed-version peer lacks the required TLS 1.3 channel-binding profile.
- Members have outbound TCP access only on port 443.
- The ngrok account lacks reserved-address or endpoint entitlement.
- A shared dispatcher receives BGP bytes through the public NCFED endpoint.
- An operator requests a clone rather than relocation, or assumes an address move
  transfers runtime state, approvals or execution authority.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST validate a versioned, installation-owned endpoint
  registry, with separate entries for iN2N and eN2N and separate fields for routing
  address, expected TLS name, trust anchor and enrolled application identity.
- **FR-002**: The remote profile MUST use explicitly registered stable TCP endpoints,
  with separate direct-cloud and optional ngrok transport selections. Refuse missing,
  duplicate or ambiguous registrations. Runtime connection trust MUST NOT be
  discovered from a provider account/API response. Optional ngrok requires reservations.
- **FR-003**: Remote members MUST initiate outbound connections without an ngrok
  agent or reachable member listener. Members MUST accept only enrolled Borders;
  Border role/identity proof cannot be inferred from IP, DNS or shared organization.
- **FR-004**: Both entry points and reconnect paths MUST verify the configured
  Border TLS name independently of the routing hostname, then verify its approved
  application identity. Disabling hostname or chain/pin verification is forbidden.
- **FR-005**: Remote-profile traffic MUST require TLS 1.3 and application TLS
  termination, including when an ngrok agent forwards to a loopback listener.
  No certificate, tunnel, parsing or binding failure may enable cleartext or TLS 1.2.
- **FR-006**: iN2N possession/attestation proofs MUST bind to the actual protected
  connection with a defined TLS 1.3 binding. Missing, altered, incompatible or
  replayed bindings MUST fail closed; wire compatibility changes require an explicit
  version and migration, never an automatic legacy fallback.
- **FR-007**: External federation MUST retain its existing identification preamble
  followed by mandatory TLS 1.3, possession proof, approved peer identity and
  reciprocal consent. The preamble's residual metadata is documented; no operation
  or enrollment payload is permitted before TLS. Public profiles MUST NOT use TOFU.
- **FR-008**: Remote transport MUST preserve bytes without PROXY headers, payload
  transformations or TLS termination outside NetClaw, including optional ngrok. Public external
  listeners MUST reject BGP routing control; private routing listeners are separate.
- **FR-009**: The system MUST refuse wrong TLS name, wrong CA/pin, forged proof,
  expired/replayed enrollment and revoked membership, including terminating or
  rejecting further work on channels whose authority has been revoked.
- **FR-010**: Each Border daemon and optional ngrok lifecycle MUST be installation-owned,
  supervised and restartable at configured stable endpoints. Status/stop/restart
  MUST NOT adopt or affect unrelated processes or other claws. Direct mode uses
  the existing owned daemon controller and never starts an ngrok agent.
- **FR-011**: Endpoint updates MUST be explicit, revision-checked and validated.
  Address changes MUST preserve application identity and enrollment; trust changes
  require a separate explicit review. A failed update must retain a recovery path.
- **FR-012**: The operator surface MUST separately report configured transport,
  observed reachability, certificate/authentication failures and authenticated
  admission. Merely listing a tunnel is not proof of enrollment or workload success.
- **FR-013**: Security decisions, enrollment/revocation, endpoint changes and
  lifecycle actions MUST use the existing GAIT/audit mechanisms with bounded
  sanitized records. Logs MUST exclude credentials, enrollment secrets and keys.
- **FR-014**: ngrok credentials MUST be transport-only, supplied by the selected
  installation's private environment/secret reference, and never included in
  enrollment bundles, committed plans, status or application identity proofs.
- **FR-015**: The feature MUST preserve existing direct-LAN, cloudflared,
  single-user and Hermes paths or ship explicit migration guidance. Remote-profile
  enforcement MUST be determined by trusted configuration, not apparent source IP.
- **FR-016**: A transport outage MUST yield bounded reconnect behavior and a distinct
  unavailable status, without transport downgrade, unsolicited endpoint creation
  or automatic replay of an application operation.
- **FR-017**: Reusable configuration and examples MUST accept operator-owned cloud,
  DNS, certificate, trust and runtime settings without the reference owner's
  credentials or domain. Scope here is transport relocation; clone and later
  runtime migration must preserve their distinct identity/authority semantics.
- **FR-018**: Selected-provider public-address/firewall/instance limits, observed
  access, costs and projected R14 service inventory MUST be recorded. Optional ngrok
  records its account limits separately. Unavailable evidence remains UNQUALIFIED;
  no entitlement, resource permission or price may be assumed.
- **FR-019**: Every R01 acceptance row MUST map to timestamped commands/results or
  explicit UNQUALIFIED/FIXTURE-ONLY status, with positive, negative and recovery
  evidence separated. Live cloud admission requires a separate-network pass.
- **FR-020**: Cloud provisioning, ngrok account/endpoint mutation, paid calls,
  device operations and publication MUST remain outside autonomous test execution.
  Prepare exact reviewable commands for human-controlled live qualification.

- **FR-021**: Direct cloud registries MUST reject wildcard/multicast listen bindings,
  transport ambiguity and ngrok-only fields. Legacy schema-1 ngrok registries MUST
  retain their original loopback/reservation checks without automatic migration.
- **FR-022**: Direct federation deployment MUST expose only the reviewed iN2N/eN2N ports,
  with application TLS, no public routing/admin/workload listener and no ngrok
  credential dependency. Read-only listener/firewall evidence must verify exposure.
- **FR-023**: Public bundles, status, CAS updates and recovery MUST preserve the
  explicit transport and profile. Cross-schema changes require explicit replacement;
  an address-only operation cannot change trust, transport or listener bindings.
- **FR-024**: The transport-only cloud pilot MUST have reviewable IaC, costs,
  expiry, budget alerts, workload identity and teardown before creation. Provisioning
  remains subject to exact approval; source tests never satisfy separate-network evidence.

- **FR-025**: README, setup.sh, installer/catalog, VS Code and operational guidance
  MUST consistently retain home/NAT ngrok, direct cloud with cloud/on-prem members,
  private/air-gapped on-prem topology, and the hybrid/multi-region/multi-cloud roadmap.
  Preserve iN2N member versus eN2N/NCFED peer roles; do not claim offline installer
  or future deployment qualification from topology support.
- **FR-026**: R01 MUST provide a verified cloud-hosted full HUD link with public
  DNS and trusted HTTPS, actual on-prem member iN2N enrollment/reconnect evidence,
  and the owner-requested Sonnet-backed question delegated to that member with
  correlated task/tool/result receipts. The owner explicitly accepts open lab
  access without login. Publish Chat, Canvas, RAG and the existing workspace views
  through reviewed ingress; keep raw configuration, credentials, routing/admin APIs
  and device-write endpoints private. Users, SSO and RBAC remain R15–R17. A page,
  transport probe or model's claim alone does not prove member execution. The
  scoped subnet-calculation demonstration does not qualify pyATS, production
  workloads, execution parity, HA or later deployment briefs.

### Key Entities

- **Endpoint registration**: service, stable application identity, routing address,
  verified TLS name, trust reference, transport/profile, revision and ownership.
- **Enrollment bundle**: approved Border identity/trust and endpoint registration
  plus the existing single-use enrollment mechanism; transport credentials absent.
- **Channel security state**: negotiated profile/version, authenticated identity,
  binding type, admission/refusal stage and current revocation state.
- **Owned tunnel service**: selected installation, declared endpoints, supervision
  identity, sanitized lifecycle/status and private credential reference.
- **Migration receipt**: previous/candidate revisions, unchanged application
  identity, validation/admission outcome and explicit recovery decision.
- **Qualification record**: test scenario, timestamp, command, observed result,
  platform/transport and live/fixture/unqualified classification.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators see both separately registered services and distinguish
  configuration, TCP reachability and authenticated admission for each.
- **SC-002**: A member on a separate network enrolls and reconnects through the
  registered address while verifying a different configured certificate name.
- **SC-003**: An independent peer completes secured federation and consent through
  a second service endpoint without acquiring internal-member access.
- **SC-004**: Every listed identity, downgrade, protocol and topology negative
  case is refused; no negative case causes a weaker connection or routing change.
- **SC-005**: An owned daemon restart and reviewed address relocation preserve enrolled
  identities, require zero re-enrollments after successful enrollment, and produce
  no automatic application replay.
- **SC-006**: Existing direct-LAN and cloudflared regression suites pass; retained
  versus newly qualified runtime/platform behaviors are explicitly recorded.
- **SC-007**: A second isolated installation configured entirely with different
  example identities/paths uses the same transport contract without owner-specific
  code edits or credentials.
- **SC-008**: All six R01 acceptance groups and G1–G11 applicability have evidence
  entries. Human review must accept the actual verification before R03; an
  UNQUALIFIED security prerequisite does not count as a passed gate.

## Assumptions

- The owner authorized this single-brief Spec Kit cycle after the opening
  assessment; the driver permits recommended defaults with recorded deviations.
  Live infrastructure mutation still needs the driver's exact-command review.
- Border transport and the owner's requested pilot HUD observation are in scope.
  R02 owns broker/principal/execution parity, R03 operational cloud deployment
  and runtime migration beyond this isolated pilot, R05 Ollama execution,
  R08 cluster authority, and R15–R17 multi-user identity/authorization.
- The new remote profile is strict even behind loopback forwarding. Previously
  explicit local IPC compatibility is not a remote fallback; compatibility and
  migration boundaries must be documented and tested.
- The existing eN2N identification preamble is the R01-mandated discriminator,
  not an exception permitting unencrypted application payloads. Spec063 already
  documents its metadata exposure; R01 does not replace that wire protocol.
- Members must reach the registered endpoint's configured port. 443-only networks
  are unsupported by this initial raw-TCP profile.
- The selected account's credits identify deployment ownership and do not set
  pricing, available quota, a spend target or a $1,000 ceiling.
- R01 has no roadmap dependencies. Related baselines include specs056/057/063,
  spec108's cloudflared path and spec149's Hermes federation; historical evidence
  is retained as historical, never relabeled as a new live pass.
