# Data Model: N2N Federation

**Feature**: 052-n2n-federation | **Date**: 2026-07-10
**Store**: SQLite `~/.openclaw/n2n/federation.db` + JSON inventory cache
`~/.openclaw/n2n/inventories/` (see research.md R4)

## Entity: FederationPeer

One row per remote claw known from the mesh.

| Field | Type | Notes |
|---|---|---|
| identity | TEXT PK | `as<AS>-<router-id>` (e.g. `as65007-7.7.7.7`) — FR-002 |
| peer_as | INTEGER | AS number from BGP OPEN |
| router_id | TEXT | Router-id from BGP OPEN |
| display_name | TEXT | Operator-assigned label (e.g. "Nicholas") |
| endpoint_host | TEXT | Last-known public endpoint (transient — never a key) |
| endpoint_port | INTEGER | |
| state | TEXT | `not_federated` \| `consent_pending_local` \| `consent_pending_remote` \| `federated` \| `severed` |
| chat_enabled | INTEGER | 0/1, per-peer (FR-018) |
| created_at / updated_at | TEXT | ISO 8601 |

**Terminology**: the operator action is the **kill switch** (`n2n_kill` tool,
`/n2n/kill` route); the wire notification is `n2n/sever`; the resulting peer
state is `severed`. One action, three layer-appropriate names.

**State transitions** (FR-001, FR-004):

```
not_federated → consent_pending_local    (remote consented first; awaiting us)
not_federated → consent_pending_remote   (we consented first; awaiting them)
consent_pending_* → federated            (both consents present → channel opens, inventories exchange)
federated → severed                      (kill switch, either side — < 10 s, BGP untouched)
severed → consent_pending_remote         (re-consent required from scratch)
```

## Entity: ConsentRecord

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| peer_identity | TEXT FK → FederationPeer | |
| direction | TEXT | `local_grant` (we consented to them) \| `remote_grant` (they to us) |
| granted_at | TEXT | |
| revoked_at | TEXT NULL | Set by kill switch; row retained for audit |

Active federation requires one unrevoked row in each direction.

## Entity: CapabilityInventory (JSON cache, one file per peer + one local)

```json
{
  "identity": "as65007-7.7.7.7",
  "issued_at": "2026-07-10T15:00:00Z",
  "version": 3,
  "skills": [ {"name": "cml-lab-lifecycle", "description": "...", "invocable": true} ],
  "mcp_servers": [ {"name": "cml-mcp", "tools": ["list_labs", "start_lab"], "invocable_tools": ["list_labs"]} ],
  "badges": ["CML", "pyATS"]
}
```

- Local inventory built from `config/openclaw.json` + `workspace/skills/`, then
  filtered by visibility before send (FR-005/FR-006 — hidden items absent from
  the payload, not masked).
- Remote cache files carry `received_at` sidecar metadata for staleness (FR-009).
- Invariant (FR-007, tested): no value from `.env`, testbed files, or credential
  stores may appear anywhere in the document.

## Entity: VisibilitySetting (local only)

| Field | Type | Notes |
|---|---|---|
| item_type | TEXT | `skill` \| `mcp_server` |
| item_name | TEXT | |
| visibility | TEXT | `all_federated` \| `selected_peers` \| `hidden` (default: `hidden` for MCP servers, `all_federated` for skill names — FR-006) |
| peer_list | TEXT NULL | JSON array when `selected_peers` |

## Entity: InvocationGrant

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| peer_identity | TEXT FK | Grantee |
| target_type | TEXT | `tool` \| `skill` (clarification Q5) |
| target_name | TEXT | e.g. `cml-mcp/list_labs` or `network-health-check` |
| requires_approval | INTEGER | 0/1 (FR-013) |
| timeout_s | INTEGER | Default 120 tool / 600 skill (research R8) |
| created_at / revoked_at | TEXT | |

Default-deny: no row ⇒ refusal (FR-012).

## Entity: BudgetCounter

| Field | Type | Notes |
|---|---|---|
| peer_identity | TEXT | |
| day | TEXT | `YYYY-MM-DD` (UTC) |
| requests_used | INTEGER | Shared across invocations + chat (FR-017/FR-020) |
| tokens_used | INTEGER | |

PK (peer_identity, day). Compared against per-peer limits
(`N2N_DAILY_REQUESTS`, `N2N_DAILY_TOKENS` or per-peer overrides).

## Entity: RemoteInvocationRecord (audit — both sides)

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| direction | TEXT | `inbound` \| `outbound` |
| peer_identity | TEXT | |
| target_type / target_name | TEXT | |
| request_id | TEXT | JSON-RPC id, correlates the two sides |
| decision | TEXT | `allowlisted` \| `approved` \| `denied` \| `expired` \| `budget_exhausted` \| `rate_limited` |
| outcome | TEXT | `success` \| `error` \| `timeout` |
| requested_at / completed_at | TEXT | |
| result_ref | TEXT | Path/offset of stored result payload (FR-015) |
| gait_ref | TEXT | GAIT commit reference (Constitution IV) |

## Entity: ApprovalRequest

| Field | Type | Notes |
|---|---|---|
| id | INTEGER PK | |
| invocation_id | INTEGER FK → RemoteInvocationRecord | |
| status | TEXT | `pending` \| `approved` \| `denied` \| `expired` |
| requested_at / resolved_at | TEXT | |
| expires_at | TEXT | requested_at + `N2N_APPROVAL_WINDOW` (default 15 min) |
| resolved_via | TEXT | `slack` \| `webex` \| `cli` \| `hud` (research R6) |

## Entity: N2NChatSession

| Field | Type | Notes |
|---|---|---|
| id | TEXT PK | UUID |
| peer_identity | TEXT | |
| direction | TEXT | `initiated` \| `received` |
| started_at / last_activity_at | TEXT | |
| message_count | INTEGER | |
| transcript_ref | TEXT | Path to append-only transcript (FR-020 review; FR-022 audit) |

Messages stream over the channel; the transcript file is the durable record.
Idle sessions close after `N2N_CHAT_IDLE_TIMEOUT` (default 300 s).

## Relationships

```
FederationPeer 1—2 ConsentRecord           (one per direction)
FederationPeer 1—1 CapabilityInventory     (remote cache; local inventory is peer-less)
FederationPeer 1—N InvocationGrant
FederationPeer 1—N BudgetCounter           (one per day)
FederationPeer 1—N RemoteInvocationRecord —0..1 ApprovalRequest
FederationPeer 1—N N2NChatSession
VisibilitySetting —N (applies to local inventory build)
```
