# Phase 0 Research: Cloudflare Tunnel as a Hardened eN2N Transport (108)

Ground truth: read the running code (`bgp-daemon-v2.py`, `bgp/federation/{service,tls,manager,channel}.py`) on the reference host (`as65099-10.255.255.1`, domain `byrnbaker.me`, Cloudflare-managed) and confirmed live symptoms via `n2n_health`/`n2n_status`/`n2n_chat` against the two dead peers (`as65001-4.4.4.4` "John", `as65007-7.7.7.7` "Nick") that motivated this feature.

## R0 — Confirming the failure mode against the actual code (gates US1)

The eN2N listener is a plain `asyncio.start_server(on_conn, "0.0.0.0", port)` in `bgp-daemon-v2.py`. Outbound dials go through `service.py`'s `open_channel(peer_as, router_id, host, port)`, which does `asyncio.open_connection(host, port)` against whatever `host:port` is stored on the peer row.

**Confirmed via code read**: endpoint persistence (spec 063 FR-001/FR-002, already shipped) writes `manager.upsert_peer(peer_as, router_id, endpoint_host=host, endpoint_port=port)` in exactly two places:
1. `open_channel()`, only after a dial **succeeds and authenticates** (comment in code: "so the reconnect supervisor re-dials this current address instead of a stale one").
2. `_on_endpoint_update()`, when a **live, authenticated channel** delivers an `n2n/endpoint_update` notification from the peer.

**This confirms the exact gap this feature exists to close**: both write paths require an already-working channel (either a dial that just succeeded, or a live session to carry an announcement). Neither path helps when the channel has been dead long enough that no dial has succeeded *and* no live session exists to announce a new address — which is precisely the state `n2n_health` showed for both John and Nick (`channel_state: reconnecting`, `endpoint_updated_at` 21–23 days stale). The reconnect supervisor (referenced in `open_channel`'s docstring context, driven by `_health_for(ident)`) keeps re-dialing the *stored* stale address forever (dampened per spec 100, but never corrected) because there is no mechanism to learn a new address without a live channel.

**Decision**: This is not a bug to fix in the persistence logic (063 already did that correctly for the case it covers) — it is a structural limitation of any transport whose address changes on every process restart. The fix is to remove the precondition (an address that doesn't change doesn't need to be re-learned), which is exactly what a Cloudflare Tunnel bound to a fixed hostname provides. `open_channel(peer_as, router_id, host="tunnel.example.com", port=<fixed>)` never needs a fresh `host` value across restarts, so the "no live channel to announce over" failure mode structurally cannot occur for a Cloudflare-Tunnel-hosted claw's *own* advertised address (a peer's transport choice is independent — see Assumptions in spec.md).

**Alternatives considered**:
- *Reserved/paid ngrok static address*: solves US1's address-stability problem alone, at a recurring cost, but provides none of US2's edge-gate capability and doesn't change the "openly reachable socket" property (a reserved ngrok TCP endpoint is still just as reachable as a free one, just at a fixed address — arguably *worse* for scanning since it never rotates away from anyone who's found it). Rejected as the sole fix per spec.md Assumptions (kept as a peer-side option outside this feature's scope, since peers choose their own transport independently).
- *Fix the reconnect supervisor to brute-force rediscovery somehow*: no mechanism exists or is proposed anywhere in the codebase for a dead peer to be rediscovered without an out-of-band signal; rejected as unbuildable without the peer proactively re-announcing, which requires exactly the live channel that's missing.

## R1 — Cloudflare Tunnel mode: TCP/private-network vs HTTP(S)

`cloudflared` supports exposing an arbitrary TCP port via **TCP tunnel mode** (`cloudflared access tcp` / `cloudflared tunnel --url tcp://...` depending on client-side tooling) as opposed to **HTTP(S) ingress mode**, which terminates TLS at Cloudflare's edge and proxies HTTP(S) semantics.

The eN2N listener speaks a custom framed protocol (`NCFED_MAGIC` handshake bytes, then either cleartext or — post spec-060 — TLS-upgraded JSON-RPC 2.0 frames per `channel.py`). This is **not HTTP**. Terminating "TLS" at Cloudflare's edge in HTTP(S) mode would require the connection to look like HTTP to Cloudflare, which the NCFED wire protocol does not; forcing it through HTTP ingress would require wrapping the whole protocol (e.g. inside WebSocket), which is a wire-format change out of scope for a transport-substitution feature.

**Decision (confirmed by operator, Clarifications session)**: use `cloudflared`'s **private-network / raw TCP tunnel mode**, which relays opaque bytes end-to-end with no protocol awareness at Cloudflare's edge. This is the *only* mode compatible with the existing NCFED discrimination preamble and 060's TLS-upgrade-in-place design without any wire change, and it satisfies the confidentiality goal (Cloudflare's infrastructure never observes decrypted NCFED payload — consistent with spec 063 R2's "encrypt in-protocol, don't rely on an incidental transport" stance for the mesh layer, applied here to the transport choice itself rather than a protocol change).

**Rationale**: zero NCFED protocol changes required (FR-008); the existing `asyncio.start_server`/`asyncio.open_connection` pair on both ends is unaffected — `cloudflared` simply becomes the thing that makes the listening/dialing addresses resolve, transparently to the Python code, exactly as ngrok does today. This is a deployment/ops change, not a code change to `service.py`/`channel.py`/`tls.py`.

**Alternatives considered**: HTTP(S) ingress with a WebSocket wrapper — rejected (wire-format change, violates FR-008; also reintroduces the exact plaintext-at-edge regression the operator explicitly rejected in Clarifications).

## R2 — Where Cloudflare Access fits relative to the existing 060 TLS layer

Spec 060 established that eN2N channels negotiate TLS (or refuse, per production posture) at the application layer, inside the TCP stream, using `bgp/federation/tls.py` (`server_context`/`client_context`, `upgrade_to_tls`). This happens **after** the raw TCP connection is already established — i.e., after `asyncio.start_server`'s `on_conn` callback fires, or after `asyncio.open_connection` returns.

Cloudflare Access, when placed in front of a private-network tunnel, operates as an **edge-level gate on the tunnel connection itself** — a client must authenticate to Cloudflare's edge (mTLS client cert or service token) before Cloudflare will even open the far side of the tunnel to the origin (the claw's listener). This happens **before** any bytes reach `asyncio.start_server`'s `on_conn` — i.e., strictly earlier than even the NCFED discrimination-magic read, let alone 060's TLS upgrade.

**Decision**: these are two independent, stackable gates at different layers:
1. Cloudflare Access (edge, pre-listener, optional per FR-005) — rejects unauthorized *connections* before the claw's process sees any bytes.
2. NCFED/060 TLS + peer-identity verification (application, post-connection, already mandatory in production posture) — authenticates *who* is on an already-accepted connection.

**Rationale**: this composition requires zero changes to `channel.py`/`tls.py`/`service.py` — Access operates entirely at the Cloudflare edge and the tunnel client, invisible to the Python federation code, which continues to see exactly the same `asyncio.start_server` callback and TLS upgrade flow it does today. This is why FR-004 ("Access MUST NOT replace or weaken 060's peer-identity TLS") is true by construction rather than requiring enforcement code — there is no code path by which enabling Access could bypass the existing TLS negotiation, since Access sits strictly earlier in the connection lifecycle and the federation code is unaware it exists.

**Alternatives considered**: implementing Access-awareness inside the Python federation code (e.g., reading a Cloudflare-injected header/claim) — rejected as unnecessary complexity; the edge-gate/app-auth separation is cleaner and requires no code changes, matching this feature's "transport + ops hardening only" scope (FR-008).

## R3 — Fault classification for tunnel/edge failures (extends spec 057's fault-class model)

Spec 057 (`n2n_faults`) already distinguishes `daemon` (mesh daemon down) / `member` (a specific member unreachable) / `backend` (member up, its device/API unreachable) / `none`. This feature's FR-007 requires a tunnel/edge-layer failure (Cloudflare outage, DNS failure, `cloudflared` process down) to be distinguishable from a peer-process-down condition.

**Observation from the live incident**: `n2n_health`'s existing per-peer fields (`channel_state: reconnecting`, `endpoint`, `endpoint_updated_at`, `attempts`) already carry enough raw signal to distinguish "my own tunnel is down" (a *local* `cloudflared`/DNS health check, independent of any peer) from "the peer's process is gone" (repeated dial failures against a peer's endpoint that is otherwise DNS-resolvable and TCP-connectable up to the point cloudflared or the origin refuses). The distinction is really: is the *unreachability signal local to my own egress/tunnel* (I can't get out, or my own inbound tunnel is down — checkable independently of any specific peer) vs. *remote* (I can reach the transport fine, but nothing answers NCFED on the other end)?

**Decision**: extend `n2n_faults`' existing per-peer/per-member fault classification with a new checkable signal (a local tunnel/DNS health probe, independent of peer state) that can be consulted *before* attributing a dead channel to "peer down." This reuses the existing fault-class enum's pattern (name a specific, checkable cause) rather than inventing a new ambiguous top-level state. Concretely, this composes as: if the local tunnel health probe fails, report a transport-layer fault for *this claw's own* advertised endpoint (distinct from any peer's fault); if the local tunnel is healthy but a specific peer's channel is still down, classification proceeds exactly as today (peer/member-down, unaffected by this feature).

**Rationale**: mirrors 057's stated principle exactly ("Always report the specific cause, never a generic 'something's down'") and reuses the existing `n2n_faults`/`n2n_health` surface (FR-006, avoiding a parallel surface) rather than introducing new tooling.

**Alternatives considered**: a generic "transport degraded" catch-all — rejected, repeats the exact misdiagnosis pattern 057 was built to fix (a poll bug reported as a member flap).

## R4 — Posture/HUD surface extension point

Spec 060 already extended the operator posture/HUD surface with trust-model, credential fingerprint, issuer, and expiry per peer. FR-006 requires this feature's transport type and edge-gate status to appear in that same surface.

**Decision**: extend the existing per-peer posture record (the same one 060 populates) with two additional display fields — `transport` (`ngrok` | `cloudflare_tunnel` | `other`) and `edge_gate` (`none` | `cloudflare_access`) — rather than building a second view. This is directly analogous to how 063 added `negotiated_kex_group`/`pq_indicator` to the same existing surface (063 R4/FR-014) instead of a parallel one.

**Rationale**: consistent with the repo's established pattern (both 060 and 063 explicitly avoid parallel surfaces); operators already look in one place for channel trust facts.

**Alternatives considered**: a separate "transport health" panel — rejected, violates FR-006 and the established cross-cutting pattern from both prior specs.

## R5 — Cross-cutting

**Decision**: No new Python packages in the federation code itself — `cloudflared` is an external ops-level binary/service (like ngrok is today), configured and run as a durable service per spec 057's pattern (`scripts/in2n-services.py`-style systemd unit), not a library dependency of `bgp/federation/*`. The federation code's only awareness of the transport is the `host:port` (or Cloudflare-tunnel-resolved equivalent) it already dials/listens on today — this feature changes *what infrastructure makes that address stable and gated*, not the Python connection logic itself. New state is limited to: (a) the per-peer `transport`/`edge_gate` display fields (R4), reusing the existing peer/posture record; (b) the local tunnel health probe (R3), a new lightweight check, not a new store.

**Sequencing**: US1 (stable endpoint via `cloudflared`, ops-only, zero code changes to `service.py`/`channel.py`) ships first and is fully independent — it is pure infrastructure substitution and can be validated against the two currently-dead peers (John, Nick) once *they* also adopt it, or unilaterally by confirming this claw's own endpoint survives `cloudflared`/host restarts. US3 (posture display) is a small, low-risk addition to the existing 060/063 surface and can follow immediately. US2 (Access edge-gate) is operator-config + a local health/status read of Access policy state — no core federation code changes — and can ship independently and later, consistent with its default-off, opt-in-per-peer resolution.
