# Phase 1 Data Model: NCFED Edge Node Foundation + Border-to-Phone Push Channel

No new top-level store. This feature extends the existing `member` table (one new column)
and reuses the existing `enrollment_token` and `approval_request` tables as-is. Entities
below are (1) the schema extension, (2) transient wire entities, and (3) app-local (phone)
state that has no server-side equivalent.

## Entity: Member row — extended (`member` table, `manager.py`)

Existing feature-056 table. Extended for this feature:

| Field | Type | Change | Notes |
|-------|------|--------|-------|
| `node_type` | TEXT | NEW, default `'agent'` | `agent` (existing NetClaw member) \| `service` \| `edge` (capability-only, no agent runtime). Migration is additive — every existing row defaults to `agent`, preserving current behavior exactly (Constitution XV). |
| `pinned_key` | TEXT | reused, unchanged | The edge node's self-generated public key, pinned via TOFU after the enrollment-token exchange — same column, same semantics as any other member. |
| `key_fingerprint` | TEXT | reused, unchanged | Sha256 fingerprint of `pinned_key`, same as today. |
| `runtime_kind` | TEXT | unchanged | Existing `process`\|`container` values are meaningless for an edge node (no local process); left `NULL` for `node_type='edge'` rows rather than adding a placeholder value. |
| `health` | TEXT | unchanged, new source | Now also updated from the edge node's built-in heartbeat responses (D5), not only from skill-delivered `member_report_audit` calls. |

**Invariants**: A `node_type='edge'` row MUST NOT be required to have delivered
`n2n-member-runtime` or any other skill to satisfy `BASE_FLOOR` (D5) — enforcement branches on
`node_type` instead. An edge node's `pinned_key` is set only after the enrollment-token
exchange verifies possession (spec FR-003) — never on a bare, unauthenticated first
connection.

## Entity: Enrollment Token — reused (`enrollment_token` table, `manager.py`)

Existing feature-056 table (`token_hash`, `label`, `issued_at`, `expires_at`, `spent_at`,
`spent_by_member_id`), unchanged. This feature's only addition is a new *presentation* of the
same token (QR-encoded, D6) — the token's lifecycle (single-use, consumed atomically by
`RiskManager.consume_token`) is identical for an edge node's enrollment to any other member's.

## Entity: Enrollment QR Payload (wire/presentation, transient)

Not persisted — encoded into the QR image at issuance time, decoded by the app at scan time,
then discarded.

| Field | Type | Notes |
|-------|------|-------|
| `border_host` | string | Where the app dials outbound (the ephemeral tunnel address is irrelevant to identity, per feature 060 — this is the *dial* target). |
| `border_port` | int | The edge WebSocket listener's port. |
| `claw_domain` | string | The domain the Border's certificate should be certified for (e.g. `netclaw.automateyournetwork.ca`) — the app compares this against the actual TLS-verified hostname before trusting the connection (D7). |
| `enrollment_token` | string | The single-use token (`RiskManager.issue_token()`'s existing format) — proof of Border-side legitimacy, consumed on first successful enrollment. |

## Entity: Pushed Message (wire, and app-local on the phone)

Server-side, this is not a new persisted row — it's the payload of one `n2n/edge/message`
call (D8), audited via the existing `Auditor.record()` path like any other inbound/outbound
event. On the phone, it becomes a row in the app-local message feed (no server-side
equivalent — the Border does not keep a copy of what it pushed beyond the audit trail).

| Field | Type | Notes |
|-------|------|-------|
| `content_type` | enum | `text` \| `voice` \| `image` — one of the three content forms FR-009 requires. |
| `content` | bytes/string | The actual payload (text string, or audio/image bytes — subject to the same NCFED channel framing/size handling every other in-mesh message already has). |
| `designated_by` | string | Free-text provenance of who/what explicitly designated this for phone delivery (an operator via Slack/TUI/HUD, or "agent") — for the operator's own context, not a security boundary. |
| `pushed_at` | timestamp | When the Border sent it. |

**Invariants**: A `Pushed Message` MUST always originate from content the Border already has
(FR-010) — this entity is never a *request* for the phone to produce new content (that's
spec 068's Capture entity, explicitly a different concept). A message not explicitly
designated for phone delivery (FR-008) never becomes one of these — there is no path from
"ordinary channel traffic" to this entity without an explicit designation step.

## Entity: Edge Connection State (app-local, phone-only — no server-side table)

Exists only in the mobile app's own local state; the server-side `member` row's `state`
column (existing, e.g. `enrolled`/`quarantined`/`removed`) is the server's view, which need
not match the phone's local connection state exactly (e.g., the phone can be locally
"reconnecting" while the server simply sees "not currently connected").

| Field | Type | Notes |
|-------|------|-------|
| `connection_state` | enum | `disconnected` \| `connecting` \| `connected` \| `reconnecting` (backoff in progress, D4). |
| `backoff_attempt` | int | Current retry count, driving the 5s→60s exponential delay (ported from `_in2n_member_dialer`'s proven values). |
| `last_connected_at` | timestamp? | For the operator's own visibility in the app UI. |

## State / lifecycle summary

1. **Issue** — Border operator runs the enrollment CLI with `--edge`; a QR code is rendered
   encoding the Enrollment QR Payload (D6); the underlying token is a normal, single-use
   `enrollment_token` row (unchanged mechanism).
2. **Scan & verify** — the app scans the QR, dials `wss://<border_host>:<border_port>` and
   lets standard TLS verify the certificate; before trusting the connection, the app confirms
   the TLS-certified hostname matches `claw_domain` from the QR (D7) — any mismatch aborts
   enrollment outright (spec US1 scenario 2).
3. **Prove possession, pin** — the app generates its keypair in secure hardware, signs the
   Border's nonce (existing `self_sign`/`verify_possession` protocol, unchanged), and presents
   the enrollment token; the Border consumes the token atomically and pins the key
   (`pinned_key`/`key_fingerprint`), setting `node_type='edge'` on the new `member` row.
4. **Heartbeat** — the connected edge node responds to the Border's built-in heartbeat/
   self-status methods (D5), keeping `health` current without any skill delivery.
5. **Push** — an operator (via Slack/TUI/HUD) or the agent calls `n2n_notify_phone` (D8); the
   Border calls `n2n/edge/message` on the connected edge channel; the phone renders it into
   its local message feed. If disconnected, delivery falls back to a platform push
   notification (FR-011) rather than being silently dropped.
6. **Reconnect** — on any drop, the phone's Dart-ported backoff loop (D4) redials
   automatically; no operator action required (SC-003).
7. **Revoke** — removing/quarantining the edge node's `member` row (existing mechanism,
   unchanged) revokes its pinned key; no edge-specific removal path exists (FR-013).
