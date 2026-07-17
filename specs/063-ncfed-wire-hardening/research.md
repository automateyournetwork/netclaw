# Phase 0 Research: NCFED Wire Hardening (063)

Ground truth: read the running code (`bgp/agent.py`, `bgp/session.py`, `bgp/federation/{tls,service,manager,channel}.py`, `bgp-daemon-v2.py`) and probed the live crypto stack. The single most important finding reshapes P3/P4.

## R0 — Crypto-stack reality (gates P3 and P4)

Probed on the reference host: **Python 3.10.12, OpenSSL 3.0.2 (Mar 2022)**.

| Capability | Available here? | Consequence |
|---|---|---|
| TLS 1.3 | ✅ | P1/P2 secured channels fine |
| `SSLContext.set_groups()` (choose KEX groups) | ❌ (Python 3.15+ — see R0-addendum) | cannot programmatically require/prefer a group |
| Negotiated-group readout (`SSLObject.group`) | ❌ (Python 3.15+ — see R0-addendum) | cannot show PQ-vs-classical directly from Python |
| `X25519MLKEM768` PQ hybrid | ❌ (OpenSSL 3.5+, 2025) | this host cannot even *offer* PQ |
| ECH (Encrypted Client Hello) | ❌ (no `ssl` ECH; not in OpenSSL 3.0.2) | SNI cannot be concealed on this stack |

**Decision**: P1 and P2 are fully buildable on the current stack. **P3 (ECH) and P4 (PQ) are stack-gated** — the *mechanisms* require OpenSSL ≥ 3.5 and Python ≥ 3.15 (group control/readout; see R0-addendum), which the reference host does not have. Per the spec's Q2/Q3 ("where supported" / opportunistic), on this stack P3 reduces to **documenting the SNI residual** and P4 to **the posture/visibility scaffolding that activates when the stack supports it**, degrading cleanly (never breaking connectivity) today.
**Rationale**: honest to observed capability; the capture's PQ offer came from *Nick's* host (a newer stack), not this one. **Alternatives considered**: vendoring a newer OpenSSL/Python for the daemon — rejected (heavy, out of the "no new deps" constraint, and a separate infra decision).

### R0-addendum — re-probed 2026-07-17 after the host upgrade (Ubuntu 26.04)

The reference host is now **Python 3.14.4 / OpenSSL 3.5.5**. Two corrections to R0's version claims, both empirically verified on this stack:

1. **`SSLContext.set_groups` and `SSLObject.group` are Python 3.15+ features, not 3.13+.** Both are absent on 3.14.4 (`hasattr` → False), so `pq_available()` correctly still returns False here. The `-01`-era "3.13+" claims in code comments and docs were wrong and have been corrected. (The RFC 5705 tls-exporter is likewise still absent on 3.14.)
2. **OpenSSL 3.5 negotiates X25519MLKEM768 *by default*.** Verified on loopback: both `openssl s_server`↔`s_client` and a plain Python 3.14 `ssl` server↔OpenSSL client negotiate `X25519MLKEM768` with zero configuration. So two upgraded NCFED hosts get PQ hybrid key exchange on the wire today — but Python ≤ 3.14 can neither request nor observe it. Posture semantics stay honest: `pq_available=false` means "cannot offer-and-verify", never "the wire is classical". ECH remains unavailable (no `ssl` ECH API on 3.14).

## R1 — Endpoint persistence (P1) — buildable now, low risk

**Decision**: In `bgp-daemon-v2.py` `/n2n/connect`, persist the peer's endpoint via `manager.upsert_peer(pa, rid, endpoint_host=host, endpoint_port=port)` **only after** `open_channel` reports a successfully established + authenticated channel (Clarify Q4). `service.open_channel` records the endpoint on success; `_on_endpoint_update` already receives a peer-announced endpoint and MUST likewise `upsert_peer(..., endpoint_host/port)` bound to the authenticated channel identity. The reconnect supervisor already reads `endpoint_host/endpoint_port` from the peer row — once persisted, it auto-targets the current address.
**Rationale**: the columns already exist (`federation_peer.endpoint_host/endpoint_port`, `endpoint_updated_at`); the bug is simply that connect/dial never write them. On-success write prevents a bad dial clobbering a good address (Q4).
**Alternatives considered**: persist-on-attempt (rejected, Q4 — poisons the record); a separate "attempts" table (rejected — over-engineered, reuse the peer row per FR-013).

## R2 — Mesh-layer in-protocol TLS (P2) — buildable, the heavy lift

**Decision**: Apply 060's STARTTLS-style pattern to the **BGP mesh session**. Discrimination stays first-byte (`0xFF` → BGP); immediately after the mesh peers identify (the OPEN read in `agent.py`), upgrade the connection to TLS via the existing `tls.upgrade_to_tls()` before the BGP FSM exchanges KEEPALIVEs, reusing the claw's host credential + peer pin from 060. Gate behind the same `N2N_CERT_MODE`/enforcement model so it is a coordinated, staged rollout (a non-upgraded mesh peer is handled explicitly, not silently downgraded).
**Rationale**: reuses the proven 060 TLS+auth primitives and the same discrimination point; TLS 1.3 is available on the current stack; keeps one shared port.
**Alternatives considered**: documented-underlay only (rejected at Clarify Q1 — operator chose in-protocol); a brand-new mesh transport (rejected — reuse `tls.py`). **Risk**: this touches the BGP mesh/routing core and is a flag-day wire change for mesh peers — the largest and riskiest slice of 063; it should ship last, behind the enforcement flag, with two-node loopback tests mirroring 060.

## R3 — Metadata: SNI/ECH (P3) — document now, mechanism gated

**Decision**: Per Clarify Q2, the discrimination preamble is unchanged. For the SNI: ECH is unavailable on this stack (R0), so 063 **documents the claw-domain SNI as an accepted residual on the current stack** and adds an ECH-ready seam (a single place that would set an ECH config when `ssl` exposes it) that is a no-op today. The AS/router-id preamble exposure is documented as accepted (structural — port discrimination).
**Rationale**: honest to R0; Q2 explicitly scoped this to "where supported + document."
**Alternatives considered**: routing SNI-less and carrying the domain inside TLS (rejected — the domain-verified model needs SNI for the server to select its cert; and it wouldn't help until ECH exists anyway).

## R4 — PQ posture + visibility (P4) — scaffolding now, real PQ gated

**Decision**: Add the operator posture knob `N2N_PQ_MODE` = `opportunistic` (default) | `require` (Clarify Q3). On a stack that can offer the hybrid, the default already offers it (OpenSSL picks groups); `require` hard-refuses a peer that negotiates classical. **On the current stack (R0) the hybrid cannot be offered**, so: (a) default `opportunistic` behaves exactly as today (classical), and (b) `require` MUST fail fast at startup with a clear "PQ not available on this crypto stack (needs OpenSSL ≥ 3.5 / Python ≥ 3.15)" error rather than silently refusing every peer. Visibility: surface the negotiated **cipher + TLS version** now (readable on 3.10 via `SSLObject.cipher()`), and the **negotiated group** when the stack exposes it (`SSLObject.group`, Python 3.15+; see R0-addendum); the `/n2n/certs` + posture views show `pq: available|unavailable` and the group when known.
**Rationale**: gives operators the posture + honest visibility today, and activates real PQ automatically on a newer stack, without faking a capability the host lacks.
**Alternatives considered**: claiming PQ support/readout on 3.10 (rejected — dishonest, would mislabel channels).

## R5 — Cross-cutting

**Decision**: All new state reuses existing stores (`federation_peer` columns for endpoints; the credential/posture surfaces from 060 for KEX/PQ visibility) per FR-013/014. No new Python packages. The `-01` NCFED draft revision reflecting P2's mesh encryption + the P3/P4 stack notes is out of scope (spec assumption), but the research here is written to lift into a future `-02`.
**Sequencing**: P1 first (isolated bug fix, shippable alone), then P4 scaffolding + P3 documentation (low risk), then P2 last (the flag-day mesh TLS).
