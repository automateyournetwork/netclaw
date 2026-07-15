# Phase 1 Data Model: iN2N — Internal NetClaw Federation

Extends the existing SQLite at `~/.openclaw/n2n/federation.db` (spec 052/053). All new tables are additive; existing eN2N tables are untouched except one additive column on `remote_invocation_record`. Keys/tokens live under `~/.openclaw/n2n/keys/` (runtime-generated, never committed).

Timestamps are ISO-8601 UTC strings (`_now()`), matching `manager.py`.

---

## New table: `risk`

Identity and configuration of this claw's risk membership. Exactly one row per claw (this claw's own role in its risk).

| Column | Type | Notes |
|--------|------|-------|
| `id` | INTEGER PK | always 1 (singleton for this claw) |
| `risk_name` | TEXT | name of the risk; NULL when `role='standalone'` |
| `description` | TEXT | risk description |
| `role` | TEXT NOT NULL | `standalone` \| `border` \| `member` |
| `enabled_stacks` | TEXT | Border only: `en2n` \| `in2n` \| `both` |
| `border_endpoint` | TEXT | Member only: host:port it dials outbound to reach the Border |
| `self_member_id` | TEXT | Member only: this claw's risk-local id `<risk>/<name>` |
| `created_at` | TEXT NOT NULL | |
| `updated_at` | TEXT NOT NULL | |

**Rules**:
- `role='standalone'` ⇒ behaves exactly as pre-054 NetClaw (FR-004); `risk_name`/stacks ignored.
- Exactly one Border per risk (FR-003) — enforced at config time; a Member's `border_endpoint` points at that one Border.
- `enabled_stacks` gates whether the Border runs eN2N, iN2N, or both (FR-015).

---

## New table: `member`

The Border's registry of its Members (rows exist only on a Border). Keyed by risk-local member id, bound to a pinned key.

| Column | Type | Notes |
|--------|------|-------|
| `member_id` | TEXT PK | `<risk>/<name>`, stable across relocation (FR-008) |
| `display_name` | TEXT | human label |
| `pinned_key` | TEXT | member's self-signed public key (PEM/fingerprint), pinned at enrollment (FR-013a) |
| `profile` | TEXT | provisioning profile (`cml`, `pyats`, `security`, `custom`) |
| `scope` | TEXT | JSON: advertised/allowed skills + tools (advertised == allowed, FR-023). Each entry tagged `base` (mandatory floor, FR-021a) or `specialty`; only `specialty` entries count toward the routing tie-break (FR-021b) |
| `runtime_kind` | TEXT | `process` \| `container` (R1, selectable per member) |
| `transport_binding` | TEXT | `loopback` \| `distributed`; last-seen source info |
| `state` | TEXT NOT NULL | `enrolled` \| `active` \| `unreachable` \| `quarantined` \| `removed` |
| `health` | TEXT | JSON: last_seen, heartbeat state, in-flight task count |
| `auth_failures` | INTEGER NOT NULL DEFAULT 0 | consecutive health/auth failures → quarantine threshold (FR-013d) |
| `enrolled_at` | TEXT | |
| `updated_at` | TEXT | |

**State transitions**:
```
(none) --enroll(valid token+key)--> enrolled --dial+auth(pinned key)--> active
active --heartbeat miss / dial drop--> unreachable --re-dial+auth--> active
active|unreachable --repeated auth/health failure (≥ threshold)--> quarantined   [auto, alert operator]
any --operator remove--> removed        [unpin key; refuse reconnect]
removed|quarantined --re-enroll(new token) OR operator re-pin--> enrolled
```
- `quarantined`/`removed` ⇒ pinned key no longer honored; reconnect on the old key is refused (FR-013c/d, SC-010).
- The Border routes work only to `active` members (FR-013d, US5).

---

## New table: `enrollment_token`

Single-use tokens issued by a Border for members to join (FR-013a/b).

| Column | Type | Notes |
|--------|------|-------|
| `token_hash` | TEXT PK | hash of the token (raw token shown once to the operator, never stored) |
| `label` | TEXT | optional (e.g. intended member name/profile) |
| `issued_at` | TEXT NOT NULL | |
| `expires_at` | TEXT | optional TTL |
| `spent_at` | TEXT | set when consumed (pins a member key); NULL = unspent |
| `spent_by_member_id` | TEXT | which member consumed it |

**Rules**: single-use (reject if `spent_at` set), reject if past `expires_at` (SC-010). A leaked-but-spent token grants nothing.

---

## New column on existing `remote_invocation_record`

Discriminate internal vs external activity so the Border's one audit query covers everything (FR-024/FR-025, R8).

| Column | Type | Notes |
|--------|------|-------|
| `channel_kind` | TEXT | `en2n` \| `in2n` (additive migration; default `en2n` for existing rows) |
| `linked_record_id` | INTEGER | for an external request satisfied by internal delegation: links the outer eN2N record ↔ the inner iN2N delegation (FR-025) |

Added via the same idempotent `ALTER TABLE … ADD COLUMN` migration pattern already in `manager.py`.

---

## Reused table: `delegated_task` (spec 053, unchanged schema)

Internal delegations reuse the 053 async task table as-is. `peer_identity` holds the **member_id** for iN2N tasks (vs the BGP identity for eN2N). `direction`:
- On the **Border**: `outbound` (Border → member runs it).
- On the **Member**: `inbound` (member runs work its Border delegated).

Persistence already guarantees results survive channel drops and daemon restarts (SC-006) — inherited free.

---

## Files on disk (not DB)

```
~/.openclaw/n2n/keys/
├── border_self.key / border_self.pub     # the Border's own self-signed keypair (also its member-facing identity)
├── member_self.key / member_self.pub      # a Member's own self-signed keypair (generated at runtime, R3)
└── pinned/<member_id>.pub                  # keys the Border has pinned (mirror of member.pinned_key)
```
Path is gitignored (Constitution XIII); keys are runtime-generated, never in the repo or config.

---

## Entity relationships

```
risk (this claw: standalone | border | member)
  │
  ├─ (border) 1───* member ──1 pinned_key
  │                     │
  │                     └── scope (allowed skills/tools) ── enforced == advertised
  │
  ├─ (border) 1───* enrollment_token (single-use)
  │
  └─ delegated_task (reused): peer_identity = member_id for iN2N
       └─ audited in remote_invocation_record (channel_kind=in2n [, linked to en2n row])
```

## Validation rules (from FRs)

- FR-003: at most one `role='border'` per risk (config-time guard).
- FR-006/FR-007a: a `member` never has a public/inbound endpoint; `border_endpoint` is dialed *by* the member (outbound).
- FR-013a/b: `member.pinned_key` set only via a valid unspent token; token flips to spent atomically.
- FR-013c/d: `remove` → `state=removed` + unpin; `auth_failures ≥ threshold` → `state=quarantined` + unpin + alert.
- FR-023: `member.scope` is both what the member advertises and the ceiling of what it will execute; out-of-scope refused.
- FR-016: nothing in `member`/`enrollment_token` is ever exposed over eN2N — external peers see only the Border identity.
- FR-026: no credential/secret column exists on any of these tables; inventories carry names/descriptions only.
