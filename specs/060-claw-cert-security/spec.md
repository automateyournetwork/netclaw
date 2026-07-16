# Feature Specification: NCFED/N2N Certificate-Based Channel Security ("Claw Certification")

**Feature Branch**: `060-claw-cert-security`
**Created**: 2026-07-15
**Status**: Draft
**Input**: User description: "NCFED/N2N certificate-based channel security (claw certification). Close the eN2N crypto gap (cleartext TCP, string-asserted identity) with mutual TLS: ACME domain-bound identity via DNS-01 or pinned self-signed TOFU fallback. iN2N Border-as-CA hub attestation so members verify the hub. Automatic cert rotation before expiry with dual-trust overlap. HUD certificate panel with trust model, fingerprint, expiry, aging thresholds, rotation events in posture and audit."

## Problem Statement

External federation (eN2N) today runs over cleartext TCP across public tunnels. A peer's identity is a string it asserts in the handshake (`as<ASN>-<router-id>`), gated only by a previously recorded consent for that string. Consequences:

- **Impersonation**: any host that learns a claw's tunnel endpoint can claim to be an already-federated peer and receive chat, delegated tasks, and inventory.
- **Eavesdropping/tampering**: all federation traffic (chat, task payloads, inventory, audit exchanges) crosses the public internet unencrypted.

Internal federation (iN2N) is stronger — encrypted channels with per-member keys pinned by the hub at enrollment and signed-nonce authentication — but trust is one-way: **members never cryptographically verify that the hub (Border) they dial is the legitimate one**. A rogue process on the same host, or anything that can intercept the member's dial, could pose as the Border.

Finally, whatever credentials exist today are effectively static (10-year self-signed certificates, pinned once). There is no expiry hygiene, no rotation, and no operator visibility into what credential secures which channel.

This feature also folds in the remaining trust-hardening fixes the NCFED draft (spec 059) flags in its Security Considerations: the failed-authentication quarantine counter is a denial-of-service hazard (an attacker who can reach the internal listener can unpin a legitimate member by submitting failing authentications), and enrollment-fingerprint confirmation is described but not surfaced as a first-class operator step.

## Reference Deployment (normative example for testing and instructions)

All acceptance testing, documentation, and onboarding instructions in this feature use one concrete, real deployment as the worked example: the operator owns **`automateyournetwork.ca`** and certifies their claw as **`netclaw.automateyournetwork.ca`**. The exact operator steps this feature must make true:

1. **Name the claw**: choose the claw's identity name `netclaw.automateyournetwork.ca`. No address record is required for identity — the name never has to resolve to the claw's tunnel; it exists to be certified.
2. **Grant DNS automation**: `automateyournetwork.ca` is hosted at GoDaddy. If the account has DNS API access, create an API credential scoped to editing records in that zone (the DNS-challenge path works by writing and removing a temporary `_acme-challenge.netclaw.automateyournetwork.ca` TXT record). If not (GoDaddy restricts its API for small accounts), create **one manual CNAME once** — `_acme-challenge.netclaw.automateyournetwork.ca` → an API-capable challenge zone the claw controls — after which issuance and renewal are fully automatic with GoDaddy unchanged as registrar and primary DNS. Both paths MUST be documented; the reference deployment uses whichever the operator's account supports.
3. **Configure the claw**: set the claw's domain identity to `netclaw.automateyournetwork.ca` and supply the DNS credential to the claw's certificate manager (stored with the same protection as other claw secrets).
4. **Obtain the certificate**: the claw requests and receives a publicly-trusted certificate for `netclaw.automateyournetwork.ca` automatically — no inbound connectivity, no port 80/443, no stable IP required. Renewal thereafter is automatic (US3).
5. **Advertise and federate**: the claw's handshake now declares `netclaw.automateyournetwork.ca`; peers verify the public chain of trust and that the certified name matches the declared domain. The ngrok endpoint remains transport only and may keep changing freely.
6. **Verify in the HUD**: the operator sees their own credential (trust model "domain-verified", identity `netclaw.automateyournetwork.ca`, issuer, days remaining, auto-renew on) and each peer's, per US4.

A peer without a domain (e.g. a lab partner) federates with this claw asymmetrically: they verify `netclaw.automateyournetwork.ca` against public trust, while this claw pins their self-signed key (TOFU). Quickstart documentation and the patch/installer flows (US6) MUST be written against this exact example.

## Clarifications

### Session 2026-07-15

- Q: How does the certified claw domain relate to the existing `as<ASN>-<router-id>` identity? → A: The domain is an additional **verified attribute** of the existing identity; consent records, grants, tasks, and audit rows remain keyed to `as<ASN>-<router-id>` unchanged. The certificate proves the connection is the peer the operator consented to.
- Q: How do secured (encrypted) channels coexist with BGP on the shared listening port? → A: Same shared port — the protocol discriminator additionally recognizes an incoming TLS handshake and routes it to the secured federation path; BGP and legacy cleartext (lab mode only) discrimination are unchanged. No second port or tunnel is required.
- Q: How does warn-only become enforced? → A: It doesn't need to — **certificates are a prerequisite of eN2N**. In production posture, cleartext external federation is refused from this feature's release onward; there is no operator toggle, grace timer, or release gate to run cleartext eN2N in production. The single-command patch is the migration path, and a peer that hasn't patched cannot federate externally until it does. Lab/testing mode remains the only cleartext allowance. iN2N legacy members retain their compatibility window (FR-011) since they are inside the operator's own host.
- Q: Who hosts DNS for `automateyournetwork.ca` (reference deployment)? → A: GoDaddy — but the solution MUST be DNS-provider-agnostic.
- Q: Is enrollment fingerprint confirmation blocking or advisory? → A: Verified + advisory — a fingerprint mismatch always hard-aborts enrollment automatically; matching fingerprints are displayed and logged on both sides for operator spot-check with no interactive pause, so scripted/bulk member provisioning keeps working. Direct API automation is supported for common providers (Cloudflare, Route53, GoDaddy-with-API-access, etc.) via pluggable provider automation, and **challenge delegation** (a one-time CNAME of `_acme-challenge.<claw-domain>` to an API-capable challenge zone the claw controls) is the universal fallback that makes issuance/renewal fully automatic on any provider — including restricted-API accounts like small GoDaddy plans. The reference deployment documents both paths against GoDaddy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Authenticated, Encrypted External Federation (Priority: P1)

As a claw operator, when I federate with another claw over the public internet, I want the channel encrypted and the peer's identity proven by a cryptographic credential — not just an asserted string — so that nobody can impersonate my peers or read our traffic.

Two trust models are available per peer, chosen by what the peer operator has:

- **Domain-verified**: the peer's claw identity is bound to a DNS name its operator controls (e.g. `nick.claws.example.com`) via a publicly-trusted certificate obtained through an automated certificate authority (ACME, DNS-challenge based — works behind changing tunnel endpoints because issuance never requires inbound reachability). My claw verifies the public chain of trust and that the certified name matches the peer's declared claw domain. The tunnel hostname (which changes freely) is irrelevant to identity.
- **Pinned (trust-on-first-use)**: a peer without a domain presents a self-signed credential; on first federation (confirmed out-of-band, as consent already is today) my claw pins its key. Later connections must present the same key. Still encrypted, still key-authenticated.

Cleartext federation channels are refused, except in an explicit, operator-set lab/testing mode where they are accepted but visibly flagged as degraded.

**Why this priority**: This is the crypto gap itself — the highest-impact security defect in the protocol. Everything else in this feature builds on the channel being encrypted and key-authenticated.

**Independent Test**: Federate two claws in each trust model; confirm traffic on the wire is encrypted; attempt to connect as a federated identity from a host with the wrong key/certificate and confirm refusal.

**Acceptance Scenarios**:

1. **Given** two claws where the dialed peer presents a domain-verified certificate matching its declared claw domain, **When** the channel is opened, **Then** the channel establishes encrypted and the peer record shows trust model "domain-verified".
2. **Given** a peer federated under the pinned model, **When** a host connects asserting that peer's identity but presenting a different key, **Then** the channel is refused, no federation traffic is exchanged, and the event is recorded in the audit trail.
3. **Given** a peer presenting a domain-verified certificate whose certified name does not match the declared claw domain, **When** the channel is opened, **Then** it is refused with a reason the operator can read.
4. **Given** production posture, **When** a peer attempts a cleartext (legacy) connection, **Then** it is refused; **Given** lab/testing mode, the same connection is accepted but the peer is flagged degraded in posture and HUD.
5. **Given** a peer whose tunnel endpoint hostname/port changed but whose certificate/key is unchanged, **When** the peer is re-dialed at the new endpoint, **Then** federation resumes without re-consent (identity travels with the credential, not the endpoint).

---

### User Story 2 - Hub Attestation for Members (Priority: P2)

As a claw operator running a risk (hub + members), I want each member to cryptographically verify at dial time that the Border it connects to is my legitimate hub — using a risk-local certificate authority whose trust anchor the member receives during enrollment — so that no other process can pose as the hub and receive member traffic or dispatch work to my members.

The hub becomes the risk's certificate authority: it issues each member's credential at enrollment (replacing today's independent per-member self-signed credentials) and presents a hub credential signed by the same risk authority on every internal channel. Authentication becomes mutual: hub verifies member (as today), member verifies hub (new).

**Why this priority**: Completes the trust story inside the risk. Lower than P1 because the internal channel is already encrypted and member-authenticated; this closes the remaining direction.

**Independent Test**: Enroll a member and confirm its channel records mutual verification; present a hub credential not signed by the risk authority and confirm the member refuses to proceed.

**Acceptance Scenarios**:

1. **Given** a member enrolled under the risk authority, **When** it dials the hub, **Then** it verifies the hub's credential chains to the risk authority before authenticating itself, and the channel records mutual verification.
2. **Given** a process presenting a credential not issued by the risk authority, **When** a member dials it as if it were the hub, **Then** the member refuses, does not authenticate, and the refusal is auditable.
3. **Given** members enrolled before this feature (pinned, pre-authority credentials), **When** the risk upgrades, **Then** existing members keep working and are flagged for migration to authority-issued credentials; re-enrollment is not forced without operator action.

---

### User Story 3 - Automatic Rotation Before Expiry (Priority: P3)

As a claw operator, I want every certificate in the system — public domain-verified certificates (typically 90-day lifetime) and risk-internal credentials — renewed automatically well before expiry, with an overlap window during which both old and new credentials are accepted, so that no federation or member channel ever drops because a certificate aged out, and I never have to remember a renewal date.

**Why this priority**: Without rotation, P1/P2 create a new failure mode (expiry outages). Comes after them because rotation is meaningless until certificates secure the channels.

**Independent Test**: Shorten lifetimes in a lab risk; observe automatic renewal at the threshold, dual-acceptance during rollover, and zero dropped channels across the rotation.

**Acceptance Scenarios**:

1. **Given** a domain-verified certificate approaching expiry, **When** the renewal threshold is reached (default: two-thirds of lifetime elapsed, i.e. ~30 days remaining on a 90-day certificate), **Then** renewal happens automatically without operator action and the new certificate is served on subsequent connections.
2. **Given** a risk-internal credential due for rotation, **When** rotation runs, **Then** the new credential is delivered over the existing authenticated channel before the old one expires, both are accepted during the overlap window, and no member or peer channel drops.
3. **Given** a renewal that fails (e.g. certificate authority unreachable), **When** the failure occurs, **Then** the system retries on a backoff schedule, the operator is warned in the HUD well before expiry, and the credential's aging status escalates (amber → red).
4. **Given** a peer that was offline throughout a pinned-key rotation overlap window, **When** it reconnects after the old credential expired, **Then** the operator is presented with a clear re-verification path (out-of-band confirmation, as at first federation) rather than a silent failure.

---

### User Story 4 - Certificate Visibility in the HUD (Priority: P4)

As a claw operator, I want the HUD to show, for every external peer and every member: the trust model in effect (domain-verified / pinned / risk-authority), the certified identity, the credential fingerprint, issuer, expiry date with days remaining, and auto-renewal status — with aging colors (amber under 30 days, red under 14 days) — and I want rotation and verification-failure events to appear in the posture and audit views, so the trust state of my whole mesh is inspectable at a glance.

**Why this priority**: Pure visibility; valuable but depends on P1–P3 producing the data.

**Independent Test**: Open the HUD against a risk with a mix of trust models and ages; verify every channel shows its trust facts and thresholds render correctly; trigger a rotation and a verification failure and confirm both surface.

**Acceptance Scenarios**:

1. **Given** a running mesh with federated peers and enrolled members, **When** the operator opens the HUD, **Then** every peer and member row shows trust model, certified identity, fingerprint, expiry with days remaining, and renewal status.
2. **Given** a credential within 30 days of expiry with auto-renewal failing, **When** the operator views the HUD, **Then** the credential shows amber (or red under 14 days) and the renewal failure reason is visible.
3. **Given** a rotation completes or a peer fails verification, **When** the operator views posture/audit, **Then** the event appears with timestamp, identity, and outcome.

---

### User Story 5 - Trust Hardening from the 059 Review (Priority: P2)

As a claw operator, I want the remaining trust weaknesses documented in the NCFED draft's Security Considerations fixed alongside certification: the failed-authentication quarantine must count failures per source (rate-limited), so an attacker can no longer unpin a legitimate member by spraying failing authentications at the internal listener; and enrollment must surface the credential fingerprint to the operator as an explicit confirmation step, so an intercepted enrollment is detectable at enrollment time rather than discovered later.

**Why this priority**: These are published, known weaknesses in the same trust layer this feature rebuilds; shipping certification while leaving them open would leave the draft's Security Considerations only half-addressed.

**Independent Test**: Submit repeated failing authentications for a member identity from a non-member source and confirm the member is not quarantined/unpinned; enroll a member and confirm the operator is shown matching fingerprints on both ends before the member is trusted.

**Acceptance Scenarios**:

1. **Given** an enrolled, healthy member, **When** an attacker submits repeated failing authentications asserting that member's identity from another source, **Then** the member's standing with the hub is unaffected, the attacking source is rate-limited, and the attempts are audited.
2. **Given** a member being enrolled, **When** enrollment completes, **Then** the credential fingerprint is displayed and logged on both the hub side and the member side (no interactive pause), and a fingerprint mismatch automatically aborts trust with no partial state.

---

### User Story 6 - Install, Patch, and Heartbeat Coverage (Priority: P2)

As a claw operator, I want (a) fresh installations to come up certificate-secured by default — the installer provisions the claw's credential (pinned model by default, with an optional guided domain-verified setup that asks for the claw domain and DNS credential), (b) a **single-command patch upgrade** that operators of existing claws (Nick, Byrn, AB) run to adopt certification without losing their federation state, consent records, members, or pinned peers — coming up enforcing, with channels to patched peers resuming automatically and unpatched peers refused with an actionable reason, and (c) channel heartbeats extended to carry credential health, so both ends of every channel continuously know the peer's credential status and days-to-expiry between reconnects, and a peer whose credential expires or rotates mid-session is detected at the next heartbeat rather than the next redial.

**Why this priority**: Certificates are a prerequisite of eN2N (FR-021) — the mesh only keeps working if every operator has a one-command path to adopt them, so the patch installer is what makes mandatory enforcement humane rather than a cutoff.

**Independent Test**: Run the fresh installer on a clean host and confirm the claw comes up credentialed and enforcing; run the patch installer on a claw with live federation state and confirm zero lost peers/members, enforcement active, and unpatched peers refused with an actionable reason; observe heartbeats carrying credential status and a mid-session rotation being reflected at the next heartbeat.

**Acceptance Scenarios**:

1. **Given** a clean host, **When** the operator runs the installer, **Then** the claw starts with a generated credential, encrypted channels, and rotation scheduled — with no extra steps; **and When** the operator opts into domain-verified setup, **Then** the installer collects the claw domain and DNS credential and the claw obtains its public certificate before first federation.
2. **Given** an existing claw with federated peers, enrolled members, grants, and audit history, **When** the operator runs the patch installer, **Then** the claw restarts certificate-secured and enforcing with every peer, member, consent record, and grant intact; channels to already-patched peers resume automatically, and the HUD shows exactly which peers are refused pending their own patch.
3. **Given** two claws with an established channel, **When** heartbeats are exchanged, **Then** each side learns the other's credential status (fingerprint, days remaining, renewal state) and surfaces it in HUD/posture; **and When** a peer's credential rotates mid-session, **Then** the change is reflected at the next heartbeat and validated at the next reconnect without operator action (within a rotation overlap) or flagged (outside one).
4. **Given** a peer that stops answering heartbeats, **When** the liveness threshold is crossed, **Then** the channel is marked down, the peer's HUD row reflects it, and reconnect attempts follow the existing retry policy — credential checks never weaken existing liveness detection.

---

### Edge Cases

- **Pin mismatch on a known peer**: a pinned peer presents a different key outside any rotation window. This is indistinguishable from compromise — the channel must be refused, the peer flagged prominently (not silently re-pinned), and re-verification must require the same out-of-band confirmation as first federation.
- **Clock skew**: certificate validity checks require sane clocks; lab devices in this project famously run without NTP. Validation failures caused by implausible local time must produce an operator-readable reason (not a generic refusal), and the posture should warn when the host clock is untrustworthy.
- **Downgrade attempts**: a connection must not be silently negotiable down to cleartext or to a weaker trust model than the peer record specifies. Lab/testing mode is an operator-set state, never something a remote peer can trigger.
- **Certificate authority outages / rate limits**: public ACME authorities enforce issuance rate limits and can be unreachable; renewal must begin early enough that multi-day outages don't cause expiry, and repeated failures must escalate visibly rather than loop silently.
- **Domain loss**: a peer's domain-verified identity stops being renewable (domain expired/transferred). The peer's existing certificate remains valid until expiry; afterward the operator must be offered an explicit fallback to the pinned model rather than losing federation silently.
- **Risk authority re-key**: if the risk's authority credential itself must be replaced (scheduled rotation or suspected compromise), members need a trust-anchor update path over authenticated channels, with dual-trust overlap; compromise-driven re-key must support forced immediate distrust of the old anchor at the operator's command.
- **Enrollment token interception**: the enrollment token now bootstraps both member identity and the risk trust anchor; it remains single-use and expiring, and a replayed/expired token must fail enrollment entirely (no partial trust).
- **Both-sides-pinned first contact**: two domain-less claws federating for the first time must both complete TOFU pinning in one exchange without either side observing a "changed key" during the handshake sequence.

## Requirements *(mandatory)*

### Functional Requirements

**Channel security (eN2N)**

- **FR-001**: All external federation channels MUST be encrypted; the system MUST refuse cleartext channels except when the operator has explicitly enabled lab/testing mode, in which case accepted cleartext peers MUST be flagged degraded in posture and HUD.
- **FR-001a**: Secured channels MUST share the existing listening port: protocol discrimination MUST additionally recognize an incoming encrypted-channel handshake and route it to the secured federation path, leaving BGP and legacy (lab-mode) discrimination unchanged, so operators continue to need exactly one tunnel/port.
- **FR-002**: Every external peer MUST be authenticated by a cryptographic credential under exactly one of two trust models recorded per peer: (a) **domain-verified** — a publicly-trusted certificate whose certified name matches the peer's declared claw domain, or (b) **pinned** — a self-signed credential whose key is pinned at first federation after out-of-band confirmation.
- **FR-003**: Domain-verified identity MUST bind to an operator-owned DNS name and MUST NOT bind to the tunnel endpoint; endpoint changes MUST NOT require re-consent or re-verification when the credential is unchanged (or validly rotated).
- **FR-003a**: The claw domain is a verified **attribute** of the existing `as<ASN>-<router-id>` peer identity, not a replacement: consent records, grants, tasks, and audit rows remain keyed to the existing identity, and adopting (or later changing) a claw domain MUST NOT re-key or invalidate any existing record.
- **FR-004**: Certificate issuance and renewal for domain-verified identities MUST work without inbound reachability (DNS-challenge based), so claws behind dynamic tunnels or NAT can hold and renew publicly-trusted certificates.
- **FR-004a**: DNS automation MUST be provider-agnostic: direct API automation for common DNS providers (e.g. Cloudflare, Route53, GoDaddy where the account has API access) via pluggable provider support, plus **challenge delegation** (one-time CNAME of `_acme-challenge.<claw-domain>` to an API-capable challenge zone) as a universal fallback so any operator on any provider — including restricted-API accounts — gets fully automatic issuance and renewal.
- **FR-005**: A connection asserting a federated identity but failing credential verification (wrong key, name mismatch, expired, untrusted chain) MUST be refused before any federation traffic is exchanged, and the refusal MUST be recorded in the audit trail with identity, reason, and timestamp.
- **FR-006**: A pinned peer presenting a different key outside a rotation overlap MUST be refused and flagged for operator re-verification; the system MUST NOT re-pin automatically.
- **FR-007**: The trust model and verification requirements for a peer MUST NOT be downgradeable by the remote side; only the local operator can change a peer's trust model or enable lab/testing mode.

**Hub attestation (iN2N)**

- **FR-008**: Each risk MUST have a risk-local certificate authority whose trust anchor is stored with the risk's key material and delivered to members during enrollment.
- **FR-009**: Member credentials MUST be issued by the risk authority at enrollment, replacing independently generated per-member credentials for newly enrolled members.
- **FR-010**: The hub MUST present an authority-issued credential on every internal channel, and members MUST verify it chains to their enrolled trust anchor before authenticating themselves; verification failure MUST abort the dial and be auditable.
- **FR-011**: Members enrolled before this feature MUST continue to work unmodified (compatibility mode), be visibly flagged for migration, and migrate to authority-issued credentials only on operator action or member re-enrollment.

**Rotation**

- **FR-012**: Every certificate the system manages MUST renew automatically before expiry — default at two-thirds of lifetime elapsed — without operator action; renewal timing MUST honor authority-provided renewal hints where available.
- **FR-013**: Rotation of risk-internal credentials MUST deliver the successor credential over an existing authenticated channel before the predecessor expires, and both MUST be accepted during a bounded overlap window such that no channel drops during rotation.
- **FR-014**: Renewal failures MUST retry on a backoff schedule and escalate operator-visible warnings as expiry approaches; a certificate MUST NOT be allowed to expire silently while renewal is failing.
- **FR-015**: The operator MUST be able to trigger immediate rotation of any credential, and — for the risk authority — an emergency re-key that forces immediate distrust of the old anchor.
- **FR-016**: All rotation lifecycle events (renewed, rotated, overlap opened/closed, renewal failed, emergency re-key) MUST be recorded in the audit trail.

**Visibility**

- **FR-017**: The HUD MUST display, for every external peer and every member: trust model, certified identity, credential fingerprint, issuer, expiry timestamp with days remaining, and auto-renewal status.
- **FR-018**: The HUD MUST apply aging indicators — amber below 30 days to expiry, red below 14 days — and MUST surface verification failures and degraded (cleartext/legacy) channels distinctly.
- **FR-019**: Posture reporting MUST include channel-security state: counts of channels by trust model, any degraded channels, any credentials in amber/red, and any failing renewals.

**Migration & coexistence**

- **FR-020**: Certificate and trust metadata MUST live in the existing federation state store alongside features 052/053/056/057 records (no parallel store), keyed to the existing peer and member identities.
- **FR-021**: Certificates are a prerequisite of external federation: in production posture, cleartext eN2N is refused from this feature's release onward, with no operator toggle, grace timer, or release gate to weaken it. The single-command patch (FR-028) is the migration path; the HUD/posture MUST clearly show any formerly-federated peer that can no longer connect because it has not patched, so the operator can chase them out-of-band. Lab/testing mode remains the only cleartext allowance (FR-001).

**Trust hardening (059 Security Considerations fold-in)**

- **FR-022**: Failed-authentication accounting toward member quarantine MUST be attributed per source and rate-limited; unauthenticated failures from a source other than the member's established origin MUST NOT count toward unpinning that member. Quarantine remains available for genuine repeated failures from the member itself.
- **FR-023**: Enrollment MUST display and log the credential fingerprint on both the hub and member sides; a fingerprint mismatch MUST automatically hard-abort enrollment with no partial trust retained. Matching fingerprints do NOT pause enrollment (no interactive gate — scripted/bulk provisioning keeps working); the logged pair gives the operator a spot-check record.

**Heartbeat and liveness**

- **FR-024**: Channel heartbeats MUST carry credential-health status (credential fingerprint, days to expiry, renewal state) in both directions, and each side MUST reflect the peer's reported credential health in HUD and posture.
- **FR-025**: A credential rotation occurring while a channel is up MUST be observable at the next heartbeat; within a rotation overlap the successor credential MUST be accepted at next reconnect without operator action, and outside an overlap the change MUST be flagged for re-verification (per FR-006).
- **FR-026**: Credential verification MUST NOT weaken existing liveness behavior: missed-heartbeat detection, channel-down marking, and reconnect policy continue to operate unchanged on secured channels.

**Installation and upgrade**

- **FR-027**: A fresh installation MUST come up certificate-secured by default (generated pinned-model credential, encrypted channels, rotation scheduled) with no additional operator steps; the installer MUST offer an optional guided domain-verified setup that collects the claw domain and DNS automation credential and obtains the public certificate before first federation.
- **FR-028**: A single-command patch upgrade MUST exist for existing claws that: preserves all federation state (peers, consent, grants, members, tasks, audit), migrates the state store schema in place, generates the claw's credential and the risk authority, brings the claw up enforcing (FR-021) with channels to patched peers resuming automatically, and reports the resulting posture — including which peers are refused pending their own patch — on completion. It MUST be safe to re-run (idempotent).
- **FR-029**: The patch upgrade MUST NOT require peer coordination to run safely: a patched claw keeps all its state and comes up enforcing (FR-021); unpatched peers are refused with a clear, logged reason ("peer requires certificate-secured federation — run the patch") that the refusing side ALSO communicates in its close/error so the unpatched operator learns *why* and *how to fix it* rather than seeing a silent drop.

**Documentation**

- **FR-030**: All federation onboarding and peering documentation — the project README's federation sections, the risk/peering guides (`docs/N2N-RISK.md`, `docs/N2N-RISK-MIGRATION-FOR-PEERS.md`), and the peering setup flow — MUST be updated to describe the two trust models, the enrollment fingerprint step, the upgrade path, and heartbeat credential health, using the reference deployment (`netclaw.automateyournetwork.ca`) as the worked example end to end.
- **FR-031**: Related feature specs that describe the trust model (052/053/056/057 documents) MUST gain a cross-reference note pointing to this feature where their described behavior is superseded (no rewriting of historical specs); the NCFED Internet-Draft revision itself remains a separate follow-on effort.

### Key Entities

- **Claw Credential**: the certificate + key material a claw presents on a channel; attributes: certified identity (claw domain or self-signed subject), fingerprint, issuer, validity window, trust model it supports.
- **Peer Trust Record**: per external peer — the trust model in effect (domain-verified | pinned), the declared claw domain (if any, as a verified attribute of the unchanged `as<ASN>-<router-id>` identity key), the pinned key (if any), verification state, and degradation flags. Extends the existing federation peer record.
- **Risk Authority**: the risk-local certificate authority — its anchor credential, validity, rotation schedule, and the set of member credentials it has issued. One per risk.
- **Member Credential Record**: per member — issuing authority, fingerprint, validity, migration state (legacy-pinned vs authority-issued). Extends the existing member record.
- **Rotation Event**: an audit record of any credential lifecycle transition — subject identity, event kind (renewed/rotated/failed/re-keyed), timestamps, overlap window bounds, outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An impersonation attempt — correct identity string, wrong credential — is refused in 100% of attempts, in both trust models, with an audit record produced each time.
- **SC-002**: In production posture, zero federation channels operate cleartext; a wire capture of any external federation channel contains no readable protocol payloads.
- **SC-003**: A claw operator with a domain and API-capable DNS can go from "no certificate" to domain-verified federation in under 15 minutes; an operator without a domain reaches pinned, encrypted federation in under 5 minutes.
- **SC-004**: Across a full rotation cycle (external and risk-internal), zero channels drop due to credential replacement, and every managed certificate is renewed with at least 25% of its lifetime remaining.
- **SC-005**: No managed certificate ever reaches expiry without the operator having been warned in the HUD for at least 14 consecutive days beforehand.
- **SC-006**: The operator can determine the trust model, certified identity, and days-to-expiry for any peer or member from a single HUD view in under 10 seconds.
- **SC-007**: The patch upgrade preserves 100% of federation state (peers, consent, grants, members, audit) with zero forced re-federations or re-enrollments; once both ends of a channel are patched, federation resumes with no operator steps beyond the patch itself. An unpatched peer is refused with an actionable reason, never a silent drop.
- **SC-008**: The reference deployment is reproducible as documented: following the published steps, the operator of `automateyournetwork.ca` reaches domain-verified federation as `netclaw.automateyournetwork.ca` on the first attempt using only the written instructions.
- **SC-009**: An existing claw operator completes the patch upgrade in under 10 minutes with zero lost peers, members, consent records, or grants (verified by state counts before/after).
- **SC-010**: A quarantine-DoS attempt (repeated failing authentications for a member identity from a foreign source) leaves the member's trust standing unchanged in 100% of attempts while producing rate-limit and audit evidence.
- **SC-011**: For any established channel, the peer's credential health visible in the HUD is never staler than one heartbeat interval.

## Assumptions

- **Domain ownership is optional**: some operators will have a DNS name with API-driven record management (required for the DNS-challenge issuance path); those who don't use the pinned model. Neither path requires a stable IP or inbound reachability.
- **Public tunnel hostnames are transport only**: tunnel endpoints (e.g. ngrok hosts) remain untrusted transport; no identity meaning is ever attached to them, and public authorities will not certify them.
- **Issuance via an existing ACME client**: driving a proven external ACME tool is acceptable; a hand-rolled issuance protocol implementation is out of scope.
- **Key/cert operations reuse the existing cryptography dependency** already required by the repo; no new crypto primitives.
- **Default lifetimes**: domain-verified certificates follow the public authority's lifetime (~90 days); risk-internal member and hub credentials default to 90-day lifetime with rotation at two-thirds elapsed; the risk authority anchor defaults to a 2-year lifetime with scheduled overlap rotation. All defaults operator-configurable.
- **Roughly sane host clocks**: certificate validation assumes host clocks within minutes of true time; the posture warns when the clock is implausible. Enrolling NTP-less lab devices as *managed network targets* is unrelated — this applies to claw hosts only.
- **Revocation scope**: for pinned and risk-internal credentials, "revocation" means pin removal / member quarantine / authority re-key (already-supported operator actions extended to credentials); integration with public revocation infrastructure beyond normal chain validation is out of scope.
- **NCFED Internet-Draft (spec 059)**: a Security Considerations update reflecting this work is expected later but is explicitly out of scope here.
- **Existing consent flow is unchanged**: out-of-band operator confirmation remains the root of trust for first contact in the pinned model, exactly as consent works today; this feature adds cryptographic continuity after that first confirmation.
- **Reference deployment specifics**: the operator of record owns `automateyournetwork.ca` at a DNS provider offering API-driven record management; `netclaw.automateyournetwork.ca` is reserved as the claw identity for all worked examples, tests, and documentation. Peers in the current mesh (Nicholas, Byrn, AB) are assumed to adopt via the patch upgrade in the pinned model first, with domain-verified upgrades at their own pace.
- **Heartbeat mechanism exists**: NCFED channels already exchange periodic heartbeats; this feature extends their payload and interpretation, it does not introduce liveness from scratch.
- **Installer conventions**: fresh-install and patch flows follow the repo's existing installer patterns (interactive prompts with safe defaults, idempotent re-runs, component manifest awareness).
