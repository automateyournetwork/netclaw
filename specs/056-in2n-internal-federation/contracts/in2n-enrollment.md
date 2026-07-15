# Contract: iN2N Enrollment, Pinning, Removal & Quarantine

The trust-bootstrap path for a Member joining a risk. No CA. Single-use token + member self-signed key, pinned trust-on-first-use (spec FR-013a–d; research R3).

## 1. Token issue (Border, operator action)

**Daemon HTTP**: `POST /n2n/enroll/token` → issue a single-use enrollment token.

Request:
```json
{ "label": "cml", "ttl_seconds": 86400 }
```
Response (token shown ONCE; only its hash is stored):
```json
{ "token": "in2n_<opaque>", "token_hash": "sha256:…", "expires_at": "2026-07-13T…Z" }
```
`n2n-mcp` tool: `n2n_enroll_token(label?, ttl_seconds?)` → returns the raw token for the operator to hand to the member at provisioning.

## 2. Member enroll (Member → Border, over the internal channel)

On first outbound dial, before any work, the member sends the enrollment request as the first `in2n/hello` (see internal-transport contract):
```json
{ "jsonrpc":"2.0", "id":1, "method":"in2n/enroll",
  "params": {
    "token": "in2n_<opaque>",
    "member_id": "johns-risk/cml",
    "display_name": "CML claw",
    "public_key": "-----BEGIN PUBLIC KEY-----\n…",
    "runtime_kind": "container",
    "advertised_scope": { "skills": ["cml-lab-lifecycle"], "tools": ["cml_*"] }
  } }
```
Border validates:
1. token exists, unspent, unexpired → else `-32021 ERR_ENROLL_TOKEN_INVALID`
2. `member_id` not already actively pinned to a *different* key → else `-32022 ERR_MEMBER_ID_TAKEN`

On success: pins `public_key` to `member_id`, flips token `spent_at`/`spent_by_member_id`, inserts `member` row `state=enrolled`, records an audit event. Response:
```json
{ "jsonrpc":"2.0","id":1,"result":{ "member_id":"johns-risk/cml","pinned":true,"state":"enrolled" } }
```

## 3. Authenticated reconnect (every subsequent dial)

Member proves possession of the pinned key (channel established with the self-signed key; Border verifies the presented key **equals** the pinned key):
```json
{ "jsonrpc":"2.0","id":1,"method":"in2n/hello",
  "params": { "member_id":"johns-risk/cml", "key_fingerprint":"sha256:…" } }
```
- key ≠ pinned, or member `removed`/`quarantined` → `-32023 ERR_MEMBER_NOT_TRUSTED` (connection refused; SC-010).
- success → member `state=active`, `auth_failures=0`.

## 4. Removal (Border, operator action)

**Daemon HTTP**: `POST /n2n/members/remove` `{ "member_id": "johns-risk/cml" }`
`n2n-mcp` tool: `n2n_member_remove(member_id)` — **confirm with the operator first**.
Effect: `state=removed`, unpin key, drop from routing, refuse reconnect. Return requires a **new** token (§1–2). Audited.

## 5. Auto-quarantine (Border, automatic)

Border increments `member.auth_failures` on each failed auth or health-check miss. At threshold `N2N_QUARANTINE_THRESHOLD` (default 5): `state=quarantined`, unpin key, stop routing, **alert the operator** (surfaced via `n2n_member_health` + HUD). Recovery requires operator re-pin or re-enrollment (FR-013d). Audited.

## Error codes (new, in the iN2N range; eN2N codes unchanged)

| Code | Name | Meaning |
|------|------|---------|
| -32021 | ERR_ENROLL_TOKEN_INVALID | token missing/spent/expired |
| -32022 | ERR_MEMBER_ID_TAKEN | member_id already pinned to another key |
| -32023 | ERR_MEMBER_NOT_TRUSTED | key ≠ pinned, or member removed/quarantined |
| -32024 | ERR_NOT_A_BORDER | enrollment attempted against a non-Border claw |

## Test assertions

- Unspent valid token pins the key and flips to spent; re-presenting the same token → -32021 (single-use, SC-010).
- Expired token → -32021.
- Reconnect with a non-pinned key → -32023; with the pinned key → active.
- `remove` then reconnect on old key → -32023; re-enroll with new token → active again.
- 5 consecutive auth/health failures → quarantined + unpinned + operator alerted; routing skips it.
