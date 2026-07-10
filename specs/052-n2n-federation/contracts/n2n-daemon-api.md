# Contract: Daemon HTTP API — /n2n/* routes

**Feature**: 052-n2n-federation | **Server**: bgp-daemon-v2 HTTP API (127.0.0.1:8179)
**Consumers**: n2n-mcp (operator/agent surface), ui/netclaw-visual server.js (HUD)

All routes are localhost-only (same binding as the existing 8179 API). JSON in/out.

## Read

| Route | Method | Returns |
|---|---|---|
| `/n2n/status` | GET | `{enabled, identity, peers: [{identity, display_name, state, chat_enabled, inventory_version, inventory_received_at, stale}]}` |
| `/n2n/peers/<identity>` | GET | Full FederationPeer + consent state + budget usage today |
| `/n2n/peers/<identity>/inventory` | GET | Cached CapabilityInventory + `received_at` + `stale` flag (FR-009) |
| `/n2n/grants` | GET | All InvocationGrants (optionally `?peer=`) |
| `/n2n/approvals` | GET | Pending ApprovalRequests (research R6; HUD + channels read this) |
| `/n2n/audit` | GET | Recent RemoteInvocationRecords (`?peer=&limit=`) |
| `/n2n/chats` | GET | Active + recent N2NChatSessions |

## Write

| Route | Method | Body → Effect |
|---|---|---|
| `/n2n/consent` | POST | `{peer, display_name?}` → record local consent; if remote consent already present, open channel + exchange inventories (FR-001) |
| `/n2n/kill` | POST | `{peer}` → sever: revoke local consent, notify peer (`n2n/sever`), drop channel, purge cached inventory; BGP untouched (FR-004) |
| `/n2n/visibility` | POST | `{item_type, item_name, visibility, peer_list?}` → update + rebuild/re-advertise inventory (FR-006) |
| `/n2n/grants` | POST | `{peer, target_type, target_name, requires_approval?, timeout_s?}` → create grant (FR-012) |
| `/n2n/grants/<id>` | DELETE | Revoke grant |
| `/n2n/invoke` | POST | `{peer, target_type, target_name, arguments?, input_text?}` → outbound invocation; returns `{request_id}` immediately, poll `/n2n/invoke/<request_id>` for `{status, result}` (tools usually complete inline; skills stream task status) |
| `/n2n/chat/open` | POST | `{peer}` → `{session_id}` |
| `/n2n/chat/send` | POST | `{session_id, text}` → `{reply_stream: [...chunks so far], done}` (poll or long-poll) |
| `/n2n/chat/close` | POST | `{session_id}` |
| `/n2n/approvals/<id>` | POST | `{action: "approve"\|"deny", via}` → resolve pending approval (FR-013) |
| `/n2n/config` | POST | `{peer, chat_enabled?, daily_requests?, daily_tokens?, rate_per_min?}` → per-peer overrides (FR-017/FR-018/FR-020) |

## Error shape

`{"error": {"code": "<not_allowlisted|budget_exhausted|rate_limited|approval_expired|severed|peer_offline|...>", "message": "..."}}`
— codes mirror the wire-protocol reserved codes so audit records match across layers.

## Environment variables (extend .env.example)

| Var | Default | Purpose |
|---|---|---|
| `N2N_ENABLED` | `false` | Master switch for the federation layer |
| `N2N_DISPLAY_NAME` | hostname | Operator display name in `n2n/hello` |
| `N2N_DAILY_REQUESTS` | `200` | Default per-peer daily request budget |
| `N2N_DAILY_TOKENS` | `500000` | Default per-peer daily token budget |
| `N2N_RATE_PER_MIN` | `10` | Default per-peer requests/minute |
| `N2N_APPROVAL_WINDOW_S` | `900` | Approval expiry (FR-013) |
| `N2N_INVENTORY_REFRESH_S` | `21600` | Periodic re-advertisement (FR-008) |
| `N2N_TOOL_TIMEOUT_S` / `N2N_SKILL_TIMEOUT_S` | `120` / `600` | Execution timeouts |
| `N2N_CHAT_IDLE_TIMEOUT_S` | `300` | Chat session idle close |
