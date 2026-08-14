# Feature Specification: Cloudflare Tunnel as a Hardened eN2N Transport

**Feature Branch**: `108-cloudflare-tunnel-transport`
**Created**: 2026-08-14
**Status**: Clarified — ready for planning
**Input**: Live operational finding, 2026-08-14 — while investigating why two eN2N mesh peers (`as65001-4.4.4.4` "John", `as65007-7.7.7.7` "Nick") had been unreachable for 3+ weeks, the root cause traced to free ngrok TCP tunnels: every process restart on either side issues a brand-new random `host:port`, and once a channel has been dead long enough there is no live session left to receive an announced-address update (spec 063 FR-002/FR-003), so the stale address persists indefinitely and requires manual operator intervention (`n2n_forget_endpoint` + out-of-band re-dial) to recover. Separately, a raw ngrok TCP tunnel is an openly reachable public socket gated only by URL obscurity, not by any access-control layer in front of the NCFED listener itself.

## Problem Statement

eN2N federation today reaches peers over ngrok TCP tunnels. Two independent, compounding weaknesses were observed live rather than hypothesized:

1. **Endpoint churn breaks the self-heal loop.** ngrok free-tier tunnels are ephemeral — a new `host:port` is assigned on every restart of the tunneling process. Spec 063's endpoint-persistence fix (FR-001–FR-004) correctly updates the stored address whenever a *live, authenticated* channel exists to carry the announcement — but that mechanism has no way to help a channel that is already dead. If a peer's process cycles while the channel is down (the common case for two consumer/lab operators whose machines aren't always on), the next reconnect attempt dials a `host:port` that no longer exists, and there is no live channel left to receive a fresh one. The result is exactly what was observed: two peers stuck at 23- and 21-day-old dead addresses, silently retried forever (or, post spec-100, dampened and summarized forever) with no path back to `federated` short of an operator noticing, confirming out-of-band, and manually re-dialing.
2. **The transport has no access-control layer of its own.** A raw ngrok TCP tunnel is a real, publicly reachable socket. Reachability is gated only by knowing (or guessing/portscanning for) the current `host:port` — the NCFED discrimination preamble and, once negotiated, TLS (spec 060) authenticate *who* is on the wire, but nothing today decides *whether an unauthenticated connection attempt is even allowed to reach the listener* before that negotiation begins.

Both weaknesses share a root cause: the transport (ngrok) was chosen for zero-config convenience, not for address stability or perimeter control. Cloudflare Tunnel (`cloudflared`) is a drop-in replacement that is outbound-only from both ends (no listening port exposed to the internet on either side, unlike ngrok's forwarded TCP port) and can be bound to a durable, operator-owned DNS name instead of a randomly assigned one. Layering Cloudflare Access in front of the tunnel additionally allows gating connections with mutual TLS/service-token verification *before* they ever reach the NCFED listener — a defense-in-depth control that is independent of, and additional to, the peer-identity certificate work in spec 060.

This feature is a **transport substitution and perimeter-hardening** change. It does not alter NCFED wire format, peer identity semantics, or the certificate/trust model in spec 060 — it changes what carries the bytes and adds an optional gate in front of them.

## Relationship to Existing Specs

- **Spec 060 (Claw Certification)** establishes *who* is on a channel (domain-verified or pinned TLS identity) once a connection is negotiated. This feature is transport-layer and complementary: it does not replace certificate-based peer authentication, and a Cloudflare-tunneled channel still requires 060-style identity verification once the tunnel delivers bytes to the NCFED listener.
- **Spec 063 (Wire Hardening)** fixed endpoint persistence *for channels that are still alive to announce a new address*. This feature removes the underlying reason that mechanism can't help: an address that doesn't change on restart doesn't need announcing. The two are complementary, not overlapping — 063's fix still matters for peers who remain on ngrok or any other rotating-address transport.
- **Spec 059 (NCFED Internet-Draft)** documents the protocol as transport-agnostic (cleartext-over-ngrok today, TLS-over-tunnel per 060). This feature is consistent with that framing: Cloudflare Tunnel is one more transport option, not a protocol change.

## Clarifications

### Session 2026-08-14

- Q: Should Cloudflare Tunnel become the *only* supported eN2N transport, or an additional option alongside ngrok? → **A: Additional option.** Cloudflare Tunnel ships as one more supported transport alongside the existing raw-TCP/ngrok path; a peer without a Cloudflare account/domain is unaffected and continues to federate over ngrok or any other transport with zero forced migration. Per-peer, the two ends of a channel may each independently choose their own transport (FR-001 is a MUST-support, not a MUST-replace).
- Q: Does Cloudflare Access sit in front of every eN2N connection, or is it operator-optional per peer? → **A: Operator-optional, default off.** Enabling Access is a deliberate opt-in per claw. **What changes if it were default-on instead:** every peer — including ones who haven't provisioned an Access client cert/service token — would be locked out at the edge the moment Cloudflare Tunnel is adopted, turning a transport-stability upgrade into a forced, coordinated re-credentialing of every existing federation relationship simultaneously (no partial rollout, no per-peer pacing). Default-off means adopting the tunnel for address stability (US1) and adopting the edge access-control gate (US2) are two separate operator decisions on two separate timelines — an operator can fix the ngrok-churn problem today and layer on Access later, peer by peer, once each peer has a credential ready. This mirrors 060's own rollout philosophy (peers upgrade independently; unpatched peers are refused only for the *specific* thing they haven't adopted, not federation as a whole).
- Q: When Cloudflare Tunnel mode is used, should the tunnel run in HTTP(S) mode (Cloudflare edge terminates TLS) or private-network/TCP mode (edge only relays opaque bytes, NCFED's own TLS from spec 060 is the only thing that can read the payload)? → **A: TCP/private-network mode**, confirmed. Cloudflare's edge relays opaque bytes only; NCFED's own TLS (spec 060) remains the sole layer that can decrypt payload, consistent with spec 063's "encrypt in-protocol, don't rely on an incidental transport" position. HTTP(S) mode is explicitly out of scope for this feature (would regress confidentiality by exposing plaintext NCFED traffic to Cloudflare's edge).
- Q: Does adopting this feature retroactively invalidate any pinned peer identity or consent record? → No — this is transport substitution only; peer identity, consent, grants, and audit history are keyed to `as<ASN>-<router-id>` (per 060's existing decision) and are untouched by a change of carrier.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A peer's address never goes stale (Priority: P1)

As a claw operator federating with peers over the public internet, I want my claw's eN2N endpoint bound to a durable DNS name I control, so that restarting my tunnel process (or my whole host) never changes the address my peers need to reach me at — eliminating the class of failure where a peer's stored endpoint silently rots and requires manual `n2n_forget_endpoint` + re-dial to recover.

**Why this priority**: This is the confirmed, currently-recurring failure this feature exists to fix. It's a pure reliability win independent of the security posture changes in User Story 2.

**Independent Test**: Configure a claw's eN2N listener behind a Cloudflare Tunnel bound to a fixed hostname. Restart the tunnel process (and separately, the whole host) repeatedly over an extended period. Confirm a federated peer's stored endpoint for this claw never needs manual correction and every reconnect succeeds against the same hostname.

**Acceptance Scenarios**:

1. **Given** a claw whose eN2N listener is exposed via a Cloudflare Tunnel bound to a fixed hostname, **When** the `cloudflared` process restarts, **Then** the claw's public address is unchanged and federated peers' next reconnect attempt succeeds with no address update needed.
2. **Given** the same setup, **When** the underlying host reboots, **Then** the hostname remains valid and reachable once the tunnel service comes back up (durable service, consistent with spec 057's durable-runtime pattern).
3. **Given** a peer still on a rotating-address transport (e.g. ngrok), **When** federating with a Cloudflare-Tunnel-hosted claw, **Then** federation is unaffected — this feature changes only the advertising side's stability, not the peer's own transport choice.
4. **Given** an operator migrating an existing federated peer relationship from ngrok to Cloudflare Tunnel, **When** the migration completes, **Then** existing consent, grants, and audit history for that peer identity are preserved unchanged (identity is `as<ASN>-<router-id>`, not the transport address).

---

### User Story 2 - Unauthenticated probes never reach the NCFED listener (Priority: P2)

As a claw operator, I want an access-control gate (mutual TLS client certificates or a Cloudflare Access service token) in front of my Cloudflare Tunnel, so that a connection attempt from anyone other than an already-provisioned peer is rejected at Cloudflare's edge — before it ever reaches my NCFED listener or consumes local resources — rather than relying solely on the difficulty of guessing a tunnel URL.

**Why this priority**: This is defense-in-depth on top of 060's peer-identity TLS, not a replacement for it. It's P2 because User Story 1 (stability) is the confirmed, currently-broken behavior; this is a hardening addition on a transport that, absent this feature, doesn't exist yet.

**Independent Test**: Stand up a Cloudflare Access policy requiring mTLS client-cert or service-token auth in front of a claw's tunnel. Attempt a connection presenting no credential, and one presenting the wrong credential; confirm both are rejected at the edge with no bytes reaching the NCFED listener. Attempt a connection with the correct credential and confirm it reaches the listener and proceeds to normal 060 peer-identity negotiation.

**Acceptance Scenarios**:

1. **Given** a Cloudflare Access policy configured in front of the tunnel, **When** a connection presents no client credential, **Then** it is refused at the edge and no NCFED traffic (not even the discrimination preamble) reaches the listener.
2. **Given** the same policy, **When** an authorized peer's client presents the correct credential, **Then** the connection passes the edge gate and proceeds to normal spec-060 identity negotiation unaffected.
3. **Given** an operator who has not configured Access (feature used for transport stability only), **When** a connection arrives via the tunnel, **Then** behavior is identical to today (no forced Access requirement) — this control is additive and operator-opt-in, never silently mandatory.
4. **Given** a peer's Access credential expires or is revoked, **When** they next attempt to connect, **Then** they are refused at the edge with a reason the operator can see, distinct from a 060 identity-verification failure (different layer, different failure mode — must not be conflated in logs/posture).

---

### User Story 3 - Transport choice and posture are operator-visible (Priority: P3)

As a claw operator, I want to see, per peer, which transport carries the channel (ngrok, Cloudflare Tunnel, or other) and whether an Access-style edge gate is active, alongside the existing 060 trust-model/credential facts, so I can assess my federation's exposure at a glance rather than having to remember which peers I migrated.

**Why this priority**: Pure visibility; depends on User Stories 1–2 existing to have something to display.

**Independent Test**: Federate with a mix of ngrok-transported and Cloudflare-Tunnel-transported peers, one with Access enabled and one without. Confirm the operator posture/HUD view (same surface 060 already extended) shows transport type and edge-gate status per peer without requiring a second tool or view.

**Acceptance Scenarios**:

1. **Given** a mix of peer transports, **When** the operator views posture, **Then** each peer's transport type and edge-gate status (if any) is visible alongside its existing trust-model/credential facts.
2. **Given** a peer migrates from ngrok to Cloudflare Tunnel, **When** the operator next views posture, **Then** the displayed transport updates to reflect the change with no manual record edit.

---

### Edge Cases

- **Operator has a Cloudflare account but no owned domain suitable for a stable tunnel hostname**: must degrade cleanly to today's ngrok behavior; this feature is additive, not a hard requirement to federate at all.
- **Cloudflare Tunnel or Cloudflare's edge has an outage**: the claw's public address (the DNS name) doesn't change, but reachability drops — this must be distinguishable in health/fault reporting (spec 057's `n2n_faults` fault-class model) from a peer being genuinely down, since the two look different (one is "my hostname resolves but times out," the other is "peer's process is gone").
- **Access policy misconfigured to block legitimate peers**: must be detectable and correctable by the operator without needing to fall back to disabling Access entirely (i.e., policy edits, not an all-or-nothing kill switch, should be the recovery path) — though `n2n_kill`/removing the tunnel remain available as an escape hatch.
- **A peer that has not adopted Cloudflare Tunnel at all**: must continue to federate exactly as today (this feature never requires both sides to adopt it simultaneously — the two endpoints of a channel can use different transports independently).
- **HTTP-mode vs TCP/private-network tunnel mode chosen incorrectly**: if HTTP mode is used, Cloudflare's edge terminates TLS and can observe plaintext NCFED traffic in transit — this must be flagged as a documented posture trade-off, not a silent security regression relative to 063's "protocol encrypts itself" stance.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The claw's eN2N listener MUST support being exposed via a Cloudflare Tunnel bound to an operator-supplied, stable DNS hostname, as an **additional** transport option alongside the existing raw-TCP/ngrok path (resolved: added option, not a replacement — see Clarifications). Adopting it for one claw MUST NOT require any peer to adopt it.
- **FR-002**: When a claw's advertised endpoint is a Cloudflare Tunnel hostname, that hostname MUST remain valid and correctly routable across restarts of the `cloudflared` process and of the host, requiring no operator action and no peer-side endpoint update (consistent with, and reducing reliance on, spec 063's endpoint-persistence mechanism).
- **FR-003**: The claw MUST support an optional Cloudflare Access policy (mutual TLS client certificate or service token) in front of the tunnel. When enabled, an unauthorized connection attempt MUST be rejected at the edge before any NCFED bytes (including the discrimination preamble) reach the claw's listener.
- **FR-004**: Enabling the Access edge gate MUST NOT replace or weaken spec 060's peer-identity TLS negotiation — an Access-authorized connection still MUST complete normal peer-identity verification once it reaches the listener. The two layers are independent and both apply when both are configured.
- **FR-005**: The Access edge gate MUST be operator-opt-in per claw (and effectively per peer, since Access policies gate the tunnel a specific peer connects through), **defaulting to off** (resolved — see Clarifications), so adopting Cloudflare Tunnel for stability alone (US1) does not force an unplanned, all-or-nothing access-control migration of every existing federation relationship (US2). An operator MAY enable Access per peer once that peer has provisioned a credential, without affecting peers who haven't.
- **FR-006**: The claw's operator posture/HUD surface (the same one spec 060 extended with trust-model/credential facts) MUST show, per peer channel, which transport is in use and whether an Access-style edge gate is active. [Depends on: existing 060 posture surface being the extension point, not a new one — consistent with 063's cross-cutting requirement to avoid parallel surfaces.]
- **FR-007**: A tunnel/edge-layer reachability failure (e.g., Cloudflare outage, DNS failure, tunnel process down) MUST be distinguishable in fault/health reporting from a peer-process-down condition, extending the existing daemon/member/backend fault-class model (spec 057) rather than introducing an ambiguous new "unreachable" catch-all.
- **FR-008**: This feature MUST NOT change NCFED wire format, peer-identity semantics, consent records, or any 060/063 mechanism — it is additive at the transport layer only. Existing peers on ngrok or any other transport MUST continue to federate unaffected.
- **FR-009**: The tunnel MUST run in **TCP/private-network (opaque-relay) mode** (resolved — see Clarifications), never HTTP(S)/TLS-terminating-at-edge mode, so Cloudflare's edge never sees decrypted NCFED payload. This is not operator-configurable to HTTP mode for eN2N traffic — the confidentiality regression it would introduce is not an acceptable trade-off this feature offers.

### Key Entities

- **Peer channel transport (new attribute on existing peer/channel record)**: which carrier (ngrok, Cloudflare Tunnel, other) currently carries a given peer's channel; extends the existing peer record (per 063's pattern of extending, not replacing, existing durable records).
- **Edge access-gate status (new attribute)**: whether an Access-style pre-listener gate is configured and active for a given claw/peer channel, surfaced alongside existing 060 trust-model/credential facts.

## Success Criteria *(mandatory)*

- **SC-001**: Zero manual `n2n_forget_endpoint` + re-dial interventions are needed for a Cloudflare-Tunnel-hosted claw's address across repeated `cloudflared` restarts and host reboots, measured over an extended observation period equivalent to the ngrok failure window that motivated this feature (weeks, not hours).
- **SC-002**: With an Access edge gate enabled, 100% of connection attempts lacking a valid credential are rejected before any NCFED discrimination-preamble byte reaches the listener (verifiable by absence of any listener-side log/audit entry for the rejected attempt).
- **SC-003**: An operator can determine, for any peer channel, its transport type and edge-gate status within one existing view, with no separate tool required.
- **SC-004**: A tunnel/edge outage and a peer-process-down condition produce distinguishable fault classifications in `n2n_faults`/health output, with zero misattribution in testing (mirroring spec 057 US6's existing fault-isolation bar).
- **SC-005**: Zero regressions: peers who remain on ngrok or any other existing transport continue to federate exactly as before this feature ships.

## Assumptions

- The reference operator (this claw, `as65099-10.255.255.1`, domain `byrnbaker.me`) already owns a Cloudflare-managed domain suitable for a stable tunnel hostname, consistent with how spec 060's reference deployment already assumes DNS-provider access for domain-verified certificates.
- This feature composes with, and should ideally ship after or alongside, spec 060 (peer identity/TLS) — a Cloudflare Tunnel without 060's identity layer still leaves the *content* of the channel exactly as trustworthy as it is today (string-asserted identity); the transport hardening and the identity hardening are separate, complementary axes.
- Cloudflare Tunnel is assumed available at no cost sufficient for this use case (as ngrok's free tier is today); paid-tier features (e.g. reserved ngrok addresses) are an alternative mitigation for User Story 1 alone but do not provide User Story 2's edge-gate capability, so are treated as out of scope for this spec.
- Peers are independent operators (John/as65001, Nick/as65007, etc.) who must separately choose to adopt this on their own claws — this spec covers what the local claw supports and advertises, not a way to force a peer's transport choice.
