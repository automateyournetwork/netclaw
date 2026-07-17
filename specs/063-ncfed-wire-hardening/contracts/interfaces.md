# Contract: Operator & Wire Interface Deltas (063)

Deltas only — everything else is unchanged from 060.

## Daemon HTTP (localhost:8179)

| Route | Change |
|---|---|
| `POST /n2n/connect` | On a **successful, authenticated** channel to the peer, persist `endpoint_host`/`endpoint_port` to the peer record (P1). Response unchanged; behavior: the address is now durable, so the supervisor reconnects to it. No persist on failure. |
| `GET /n2n/certs` | Each peer/channel entry gains `tls_version`, `cipher`, `kex_group` (null when the stack can't read it), and `pq: "available"\|"unavailable"` (P4). |
| `GET /n2n/posture` | `channel_security` gains `pq_mode` (opportunistic\|require), `pq_available` (bool for this host's stack), and per-channel `kex_group` where known (P4). |

## Wire — mesh session (P2, gated by enforcement flag)

```
TCP connect (shared port)
  → first-byte discrimination: 0xFF = BGP mesh (unchanged)
  → mesh peers exchange/identify via BGP OPEN (unchanged)
  → [NEW] if mesh-TLS enforced on both ends: upgrade connection to TLS 1.3
          (tls.upgrade_to_tls, host credential + peer pin from 060)
  → BGP FSM (KEEPALIVE/UPDATE) now runs inside TLS
```
- A mesh peer that has not upgraded: handled explicitly per the enforcement model (refused with an actionable reason in enforce mode; not silently downgraded).
- Discrimination byte and BGP message framing are unchanged; only the transport is wrapped.

## Wire — NCFED channel (P3/P4)

- **Preamble: unchanged** (Clarify Q2) — still `NCFED`+AS+router-id in the clear for port discrimination; documented accepted residual.
- **SNI**: unchanged on the current stack (ECH unavailable); ECH-ready seam is a no-op until `ssl` exposes ECH. Documented residual.
- **PQ key exchange**: offered opportunistically where the stack supports it; `require` refuses classical. No wire *format* change — this is TLS handshake negotiation.

## Env / config

| Variable | Contract |
|---|---|
| `N2N_PQ_MODE=opportunistic\|require` | posture; `require` on a non-PQ-capable stack → fail fast at startup with a clear capability error |
| mesh-TLS enable | reuse `N2N_CERT_MODE` unless tasks find the mesh needs an independent gate |

## Degradation contract (honesty)

On a stack lacking ECH/PQ (the reference host): connections still succeed, `pq` reports `unavailable`, `kex_group` reports `unknown`, SNI remains visible and is documented — the daemon MUST NOT fail a connection or mislabel a channel as PQ-protected.
