# Phase 1 Data Model: Cloudflare Tunnel Transport (108)

All state reuses existing stores (mirrors 063's own rule) — no new tables, no new databases. SQLite `~/.openclaw/n2n/federation.db`, same `FederationManager`-owned schema 060/063 already extended.

## 1. `federation_peer` (existing) — transport display fields (US1/US3)

Two new columns, additive only, default values preserve current behavior for every existing row (no backfill required beyond the default):

| Column | Type | Default | Role in 108 |
|---|---|---|---|
| `transport` | text | `'ngrok'` | Which carrier currently reaches this peer: `ngrok` \| `cloudflare_tunnel` \| `other`. Set by the operator at connect/config time (mirrors how `endpoint_host`/`endpoint_port` are already operator/peer-supplied); not auto-detected from the address string, since a Cloudflare Tunnel hostname is just a DNS name indistinguishable from any other by pattern-matching alone. |
| `edge_gate` | text | `'none'` | Whether an edge-level access-control gate sits in front of this peer's channel from *this claw's* side: `none` \| `cloudflare_access`. Defaults to `none` per FR-005 (opt-in, not auto-enabled by adopting `cloudflare_tunnel` transport). |

Write rules:
- Set alongside `endpoint_host`/`endpoint_port` when an operator configures a peer's transport via `/n2n/connect` (extended, see contracts/interfaces.md) — an explicit `transport` argument, defaulting to `ngrok` when omitted so existing callers/scripts are unaffected (FR-008, SC-005).
- `edge_gate` is set independently (US2 is a separate opt-in decision from US1's transport choice, per Clarifications) — never implied by `transport=cloudflare_tunnel` alone.
- Neither field affects `_recompute_state`/`PeerState` (FEDERATED/etc.) — they are descriptive/display only, consistent with `display_name` and other non-trust-bearing peer attributes already in the row.

## 2. Local tunnel/DNS health probe (new, but no new store — computed on read)

Not persisted; computed live when `n2n_health`/`n2n_faults`-equivalent status is requested, mirroring how 063's `kex_group`/`pq` fields are live negotiation facts rather than stored rows (data-model.md #2 in 063).

| Field | Source | Meaning |
|---|---|---|
| `local_transport_healthy` | Local check: does the configured Cloudflare Tunnel hostname resolve and is the local `cloudflared` service active (systemd unit state, per spec 057's durable-service pattern)? | `true`/`false`/`n/a` (n/a when this claw is not using `cloudflare_tunnel` transport at all). Independent of any specific peer — this is about *this claw's own* advertised endpoint's reachability, not a peer's. |
| `fault_class` (extends existing 057 enum) | Derived | Existing values `daemon`\|`member`\|`backend`\|`none` from spec 057 gain a new distinguishable cause: a peer channel down **while** `local_transport_healthy=false` is attributable to *this claw's own transport*, not the peer — reported as a transport-layer fault, never folded into a generic "member down." A peer channel down while `local_transport_healthy=true` (or `n/a`) is classified exactly as today (peer/member-down), unaffected by this feature. |

## 3. Posture surface (existing 060/063 view) — transport/edge-gate visibility (US3)

Extends the per-peer posture record 060 already populates (trust model, fingerprint, issuer, expiry) and 063 already extended (kex_group, pq), following the same "extend, don't parallel" pattern both those specs established:

| Field | Source | Notes |
|---|---|---|
| `transport` | `federation_peer.transport` (§1) | Displayed alongside existing trust-model/credential facts for the same peer row. |
| `edge_gate` | `federation_peer.edge_gate` (§1) | Same placement. |
| `local_transport_healthy` | §2 (live) | Shown once, for this claw's own row/summary — not per-peer, since it describes this claw's own advertised endpoint, not each peer's. |

## 4. Config surface additions (ops-level, not `.env.example` — `cloudflared` is external)

Unlike 063's `N2N_PQ_MODE` (an in-process Python env var), the Cloudflare Tunnel itself is configured via `cloudflared`'s own config file (`config.yml` / tunnel credentials JSON) and a systemd unit generated the same way spec 057's `in2n-services.py` generates the mesh daemon unit. The federation daemon's own env surface gains only:

| Variable | Meaning |
|---|---|
| `N2N_TRANSPORT_HEALTH_CHECK` (optional, default enabled) | Whether the daemon performs the local tunnel/DNS health probe (§2) at all — allows disabling the check entirely for operators who never adopt Cloudflare Tunnel, so `local_transport_healthy` simply reports `n/a` without attempting any check. |

No env var is needed to "turn on" `cloudflare_tunnel` as a transport option for a given peer — that's the per-peer `transport` field (§1), set via the connect call, not a global mode switch (consistent with FR-001: additive, per-peer, never a global replacement of ngrok).

## 5. Documentation artifacts (not data)

- **Transport-mode statement**: TCP/private-network mode only, never HTTP(S) ingress, with the confidentiality rationale (R1) — a fixed statement in quickstart.md/README, analogous to 063's "mesh trust-boundary statement."
- **Access opt-in rollout note**: default-off, per-peer, and what changes if an operator enables it for one peer vs. globally (the Clarifications answer) — recorded so a future operator revisiting this doesn't have to re-derive the reasoning.
