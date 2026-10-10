# Private Hermes MCP and companion contract

## Boundary and lifecycle

Transport is **stdio**, FastMCP server and official Node MCP client. Launch through existing component isolation, with selected environment and a fixed component ID; no browser-supplied executable/arguments/URL. Standard `initialize`, `tools/list`, `tools/call` lifecycle and structured tool errors. No invented JSON-RPC framing. Bridge conversation tools are HUD-private and absent from agent-native registries. A restarted MCP process uses the same private SQLite ledger; no conversational context lives only in process memory.

Trusted backend scope fields are `installationId`, `conversationId`, `requestId` where applicable. They are not sufficient browser authorization: HUD bindings must authorize first. The bridge verifies installation consistency and mapping existence; it never accepts an arbitrary upstream session/run ID as a replacement. Cap text at 64 KiB, one-time seed at 1 MiB, upstream bodies at 4 MiB, history pages at 200 and progress pages at 20 events.

## Tool inventory

All inputs reject unknown fields. Required fields are written without `?`; JSON types are string unless indicated. IDs are bounded opaque identifiers, not paths or commands.

| Tool | Input | Output / effect |
|---|---|---|
| `hermes_hud_status` | installationId | Safe compatibility/readiness/capabilities, inventory source/quality; no provider call. |
| `hermes_hud_conversation_open` | installationId, conversationId, seed?: array of role/content, seedDigest?, acknowledgedUncertainRequestId? | Durable private session mapping; idempotent; no inference. Seed roles only user/assistant text; system/tool roles refused. Optional uncertainty reference must match the installation and an uncertain request already authorized by HUD; persist acknowledgment without unlocking/replaying the old conversation. |
| `hermes_hud_history` | installationId, conversationId, cursor?, limit?: integer 1–200 | Owned sanitized transcript page and evidence; never global history. |
| `hermes_hud_submit` | installationId, conversationId, requestId, clientNonce, text, bodyDigest, deadlineMs: integer | Persisted admission then at most one upstream POST; returns state and request ID. Skill text is resolved server-side through the approved installed-root reader, never arbitrary paths. |
| `hermes_hud_request_status` | installationId, conversationId, requestId | State, bounded result/error, actual provider/model when known, usage provenance. |
| `hermes_hud_events` | installationId, conversationId, requestId, cursor? | Sanitized progress, bounded cursor and gap indicator. No raw reasoning, provider credentials or unowned output. |
| `hermes_hud_approval` | installationId, conversationId, requestId, approvalId, choice: once or deny | Resolve exactly one currently pending approval; cannot grant unavailable tools. |
| `hermes_hud_stop` | installationId, conversationId, requestId | Cooperative stop request; reports stopping until observed terminal outcome. |

Eight private tools. SDK discovery returns exactly this interface. Capabilities contain configured model/skill/tool metadata from fixed local/upstream sources; no generic API/config passthrough is exposed. Settings actions remain typed HUD adapter operations, with unsupported Hermes edits rejected.

## Upstream allowlist

Protected companion uses pinned `APIServerAdapter(PlatformConfig(...))`, `connect()` and `disconnect()`. Inject private response/idempotency/session databases and no-op memory checkout before construction/use as required by the runtime-selection contract; constructor defaults must not write owner databases. Override `_http_route_table()` and reject profile-prefix routing. The bridge may call only:

| Method | Route | Purpose |
|---|---|---|
| GET | `/v1/capabilities`, `/health/detailed` | Compatibility/health; never execution proof. |
| GET | `/api/model/options`, `/v1/skills`, `/v1/toolsets` | Sanitized inventory; toolsets are not effective-tool attestation. |
| POST | `/api/sessions` | New owned session. |
| GET | `/api/sessions/{mapped-id}`, `/api/sessions/{mapped-id}/messages` | Mapped metadata/history. |
| POST | `/v1/runs` | Agent submission with native server-owned session ID and Idempotency-Key. |
| GET | `/v1/runs/{mapped-id}`, `/v1/runs/{mapped-id}/events` | Status and progress. |
| POST | `/v1/runs/{mapped-id}/approval`, `/v1/runs/{mapped-id}/stop` | Exact approval and cooperative stop. |

No generic HTTP proxy, session deletion, native fork, room/federation dispatch, jobs, remote profile, arbitrary file or browser-control endpoints. Only the bridge knows the generated API key. Any necessary upstream internal initialization route must remain private and cannot expand this external allowlist without updating contracts/tests.

## Protected factory and qualification

Before starting the dedicated companion, substitute a `ProtectedAIAgent` subclass into its local `run_agent.AIAgent` import once. Never patch a running owner process, swap a factory per request, or accept unsigned external policy from the browser. Retain original base class separately. The API's own `_create_agent` retains its provider/session construction; the subclass forces these arguments:

- Individually qualified toolsets; explicit denial of terminal/code/delegate/config/admin/unscoped-history/native-memory/alternate-connector execution.
- `skip_memory=True`, `skip_background_review=True`, `memory_manager=None`; memory toolset excluded.
- Static context loading through a named fixed allowlist; no arbitrary runtime home traversal. Qualified skill text uses a constrained root, byte cap and path/symlink checks. A skill cannot expand tools or install dependencies.
- Server-set request budget. Reject command/ACP/native-agent backends that execute outside guarded Hermes tool dispatch.

After construction, freeze actual `tools`, `valid_tool_names`, tool schema and selected MCP configuration digests. Set `_skip_mcp_refresh=True` and separately check the frozen contract in `_build_api_kwargs`, `_execute_tool_calls` and `_invoke_tool`. An unexpected schema, plugin/tool addition, config mutation, missing guard or signature mismatch blocks inference/dispatch. Do not trust tool name or annotations as read-only evidence. The initial policy manifest records reviewed implementation identities and schema digests for a small read-only tool set; arbitrary installed tools stay unqualified. Owner edits trigger requalification instead of silent expansion.

Tool failures never trigger alternate tools with broader scope. Mutating tools stay unavailable unless an existing server mechanically validates applicable production CR or scoped Local/Lab endpoint/phase/artifact controls; broad Hermes approval cannot supply that evidence. Preserve baseline/rollback/verify/audit requirements whenever such a tool is qualified. This contract does not implement a new write-policy engine.

Before run admission, the authenticated bridge supplies its trusted request scope to the companion through a fixed private request header and body fingerprint. Validate it against the pre-created session mapping and install exactly one active request scope per conversation before any worker starts. Propagate that immutable context explicitly across worker threads/tasks, not via a mutable global current-request variable. Guarded tool invocation/result recording uses actual call IDs and that scope; bind the native run ID once assigned. Native history corroborates the companion ledger but cannot reassign proof when compression changes rows/lineage. Tests must force compression and concurrent independent runs.

Release-blocking tests exercise a real pinned Hermes agent with controlled provider outputs: forged forbidden calls, plugin-added schemas, post-construction mutation, refresh, callback failure, global-memory sentinel, alternate agent providers and write bypass requests all produce **zero forbidden handler/provider invocations** at their respective guard boundary. A qualified real MCP canary must still execute. No always-deny implementation may satisfy the feature's tool acceptance criterion.

## Admission, errors and recovery

Metadata deadline 5s, admission 10s, configured run deadline default 900s bounded 1–3600s. Status reads may recover known run IDs; POST replay never occurs automatically, even when upstream advertises durable idempotency. Persist before sending and fence concurrent admissions by conversation. Failed persistence means no submission. Upstream response loss during admission means unknown, not safe-to-retry.

Error codes: `selection_invalid`, `not_installed`, `configuration_missing`, `runtime_stopped`, `authentication_failed`, `compatibility_unsupported`, `policy_unverified`, `provider_unavailable`, `capability_unsupported`, `owner_invalid`, `conversation_busy`, `input_invalid`, `response_invalid`, `deadline_exceeded`, `outcome_unknown`, `interrupted`, `upstream_failed`. Include a safe recovery instruction and whether a request may have executed. Never include keys, raw upstream bodies or private paths in browser-facing errors. Stop/deny/control errors do not automatically close an outstanding operation as failed.
