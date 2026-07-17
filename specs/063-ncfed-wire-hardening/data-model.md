# Phase 1 Data Model: NCFED Wire Hardening (063)

All state reuses existing stores (FR-013) — no new tables. SQLite `~/.openclaw/n2n/federation.db`.

## 1. `federation_peer` (existing) — endpoint persistence (P1)

No schema change; the columns already exist and are simply *written* now:

| Column | Role in 063 |
|---|---|
| `endpoint_host` / `endpoint_port` | Persisted on a **successful, authenticated** connect (operator dial or peer `n2n/endpoint_update`); the reconnect supervisor reads these. Previously left stale. |
| `endpoint_updated_at` | Bumped on each successful persist — the "freshness" signal surfaced to the operator. |

Write rules (FR-001/002/003/004):
- Operator `/n2n/connect` → dial with supplied host:port → on channel established+authenticated, `upsert_peer(endpoint_host, endpoint_port)`.
- Inbound `n2n/endpoint_update` on an authenticated channel → persist, bound to that channel's identity only.
- No write on failed/aborted dials (a bad address never overwrites a good one).

## 2. Channel security facts (existing 060 surface) — KEX/PQ visibility (P4)

Extends the in-memory/posture view 060 already exposes per channel; not persisted (live negotiation facts):

| Field | Source | On current stack (Python ≤ 3.14; see research R0-addendum) |
|---|---|---|
| `tls_version` | `SSLObject.version()` | populated (e.g. TLSv1.3) |
| `cipher` | `SSLObject.cipher()[0]` | populated (e.g. TLS_AES_256_GCM_SHA384) |
| `kex_group` | `SSLObject.group` (Python 3.15+) | `null` / "unknown" here — not readable (even on OpenSSL 3.5, which may negotiate X25519MLKEM768 by default) |
| `pq` | derived: `available` if the stack can offer **and verify** the hybrid, else `unavailable` | `unavailable` here — means "cannot attest", not "classical" |

## 3. Posture config (env) — PQ posture knob (P4)

| Variable | Values | Meaning |
|---|---|---|
| `N2N_PQ_MODE` | `opportunistic` (default) \| `require` | opportunistic = offer hybrid where possible, accept classical fallback; require = hard-refuse a peer that negotiates classical. On a stack that cannot offer PQ, `require` MUST fail fast at startup with a clear stack-capability error (never silently refuse all peers). |

## 4. Documentation artifacts (not data)

- **Mesh trust-boundary statement** (P2): what protects the mesh/keepalive layer on each leg (now: in-protocol TLS when enforced).
- **Accepted-residual note** (P3): claw-domain SNI (until ECH-capable stack) and AS/router-id preamble (structural) are documented accepted exposures.

## 5. Config surface additions (`.env.example`)

| Variable | Meaning |
|---|---|
| `N2N_PQ_MODE` | PQ posture (above); default `opportunistic` |
| `N2N_MESH_CERT_MODE` (or reuse `N2N_CERT_MODE`) | gate for P2 mesh-session TLS enforcement — decided in tasks: reuse the existing flag unless mesh needs an independent toggle |
