# Private operator MCP contract — major 1

Design, not an existing endpoint. Official Node MCP SDK 2.3.1 supplies protocol negotiation and JSON-RPC lifecycle. Transport is stdio; stdout contains MCP messages only. Local process or existing OpenSSH alias launches a fixed installed `scripts/netclaw-operator.mjs` with explicit installation selection. No listener is added, no HUD Origin rule changes, no arbitrary command dispatcher. It is never registered in an agent's tool catalog.

## Authentication and binding

The backend derives local/SSH OS principal and installation from the verified launcher context. Remote SSH uses the user's normal credentials and known-host verification; no forwarded agent or automatic new/changed host-key acceptance. Arguments use a fixed safely quoted remote launcher and nonsecret installation identifier; structured inputs travel through stdin. `shell:false` on the client alone does not sanitize remote-shell arguments. Workspace settings cannot supply executable code.

`operator_identity` returns `{contract:{major:1,minor:0}, installationId, principalId, sourceVersion, harness, role, configurationRevision, capabilities, observedAt}`. All later calls bind that immutable connection. Supplying a different installation or principal is an error. Runtime drift triggers re-handshake and draft invalidation. Capabilities report supported and qualified separately, with version/evidence and denial reasons.

This interface trusts the authenticated operator account for initiation. It cannot distinguish a human from an unrestricted shell agent holding the same account. Human approval of production work therefore comes from independently verified change control with approver authority separate from the executing principal; no approve-CR tool or approver credential is exposed here. Grant separation confines authenticated MCP calls, not unrestricted same-UID filesystem/process access. Stronger OS confinement must be separately qualified before claiming it.

## Common shapes and bounds

Read calls return `{contractVersion:1, installationId, source, observedAt, data, freshness, warnings, nextCursor?}`. Command/admission calls return `{operationId, state, sequence, proposalId?, approvalRequired?, retryAfterMs?}`. `isError` results include a stable code and safe explanation: `UNAUTHENTICATED`, `DENIED`, `INCOMPATIBLE`, `IDENTITY_CHANGED`, `UNSUPPORTED`, `UNQUALIFIED`, `STALE_REVISION`, `NONCE_CONFLICT`, `EXPIRED`, `AUDIT_UNAVAILABLE`, `BUSY`, `UNKNOWN_OUTCOME`, `INVALID_INPUT` or `SOURCE_UNAVAILABLE`. Errors never echo secrets or private exception dumps.

All schemas reject unknown fields. Reads default to 100 rows, maximum 500; response maximum 1 MiB, visible truncation plus pagination. Prompts maximum 64 KiB UTF-8, reviewed attachments maximum 10 MiB each/20 MiB per request; binary content uses bounded staged opaque upload IDs, not inline tool-result expansion. Read deadlines default 15 seconds and may return partial state with reason; admission is separate from job duration. Events have monotonic per-operation sequence and cursor replay; gaps request a snapshot, never replay the action. MCP disconnect closes only the façade, not durable work.

## Tool inventory

Each row becomes fixed JSON schemas in `mcp-servers/netclaw-operator-mcp/schemas.mjs`. Action/kind enums below are closed unions, not routing to arbitrary methods. Health and diagnostics use the same identity gate.

| Tool | Inputs | Result / restrictions |
|---|---|---|
| `operator_identity` | none | Verified handshake; no secret values. |
| `operator_resources` | kind overview/member/peer/edge/advisor/integration/skill/network, filters, cursor, limit | Scoped observations and explicit supported actions. |
| `operator_snapshot` | domain settings/security/usage/knowledge/documentation, resource ID, optional window/cursor | Typed domain snapshot; separate configured/effective and measured/estimated state. |
| `operator_conversation_open` | nonce, optional owned conversation ID, selected view and qualified model/effort | Opens/resumes owned session; opening/switching view does not send a prompt. |
| `operator_request_submit` | nonce, conversation ID, prompt, reviewed context IDs | Durable request and runtime policy binding; downstream authorization and audit enforced. |
| `operator_operation_get` / `operator_events` | owned operation ID, sequence/cursor | Durable status, permitted artifacts, approval and usage references. No implicit resubmission. |
| `operator_cancel_request` | owned operation ID, nonce | Requests backend cancellation, never reports confirmed cancellation without evidence. |
| `operator_change_prepare` | nonce, action enum, exact target IDs, expected revision, typed patch/intents | Observe and record real baseline/rollback, impact and redacted proposal. Preparation has no configuration effect. |
| `operator_change_apply` | proposal ID, nonce, expected revision, authoritative approval reference where required, transient secret replacements | Revalidate identity, grant, revision, qualification, audit and independent approval; execute exact admitted change, verify and roll back on failure. No `approved` boolean or arbitrary shell. |
| `operator_evidence` | kind gait/log/artifact/approval, owned ID or approved filters, cursor | Bounded redacted evidence; GAIT is inspect-only except backend-generated session/turn recording. |
| `operator_workspace` | action rag-search/rag-stage/rag-index/memory-search/gcf-read/meeting-read/assessment-read/assessment-reconsider/canvas-import/canvas-export/mobile-capture-request, typed arguments | Per-action permission and consent. Advice is never authority. Index/reconsider/capture are admitted owned operations with budget/consent. Capture accepts only qualified `camera.capture` or `audio.record`, an exact enrolled edge ID and current consent; preserve declined/cancelled/offline and Hermes unavailable states. No arbitrary file path or automatic notification. |
| `operator_client_prepare` / `operator_client_apply` | client type, installation, targets/actions/disclosure, expiry; reviewed proposal ID on apply | Owner-scoped grant configuration, exact preview and existing change-control rules where applicable; generates only the intended client credential in backend `.env` source. No client can mint its own grant. |
| `operator_client_revoke` | grant ID, nonce | Revoke that grant generation, invalidate cached tools and prevent further dispatch; report actual in-flight cancellation state. |

Supported managed action enum: `settings.patch`, `runtime.select`, `service.start`, `service.stop`, `service.restart`, `risk.role`, `member.enroll`, `member.disable`, `member.enable`, `peer.trust`, `peer.untrust`, `security.patch`, `budget.patch`, `integration.configure`, `terminal-intent.prepare`, `terminal-intent.apply`. Each action must map to a reviewed shared domain adapter; enum presence is not qualification. Enrollment only targets existing installations. Production and external-communication effects require their actual existing gates. Forbidden destructive device operations are never added through generic enum values.

## Configuration and lifecycle transaction

1. Read current source/effective state; validate supported schema and exact targets. Unknown executable/path/environment injection keys are refused; advanced unsupported fields receive external-editor guidance without claiming managed support.
2. Lock resource, verify opaque revision, capture real baseline/rollback privately, record GAIT before effects. Secret intents are `keep`, `replace`, `clear`; blank/mask/omission means keep. Prepare stores no replacement bytes.
3. Human reviews target/diff/affected requests. Production incident precheck and live Implement-state CR validation precede execution; CR withdrawal stops further dispatch and invokes authorized recovery. No automatic ticket/message creation.
4. Atomically preserve unrelated `.env`/configuration data and private file permissions. Use env references for provider/companion credentials, with reviewed migration and fallback compatibility; do not silently rewrite legacy config on connect.
5. Start/stop/restart only verified installation-owned services using narrow adapters outside the service being stopped. No install/build/upgrade, broad `pkill`, unit deletion or remote bootstrap. Explicitly resolve active-work impact before disruption.
6. Verify effective running state. A saved field alone is pending restart. Failure attempts captured authorized rollback, verifies recovery, retains failed/unknown outcome, leaves production CR open or failed and reports escalation for human action.

Terminal Intent is a separate scoped path, not an estate-wide lab mode. Only designated endpoints, API-created local record, explicit configuration intent, real baseline/rollback and the API's APPLY phase permit local execution; question/delegation text alone does not create that approval. Collector grants stay read-only.

## Durability and GAIT

Persist canonical admission/ownership before effects, then dispatch to an existing durable runtime or installation-owned worker. Worker startup uses only the admitted operation ID, not user command text, and rechecks authority. Lost receipts resolve through nonce lookup. Do not retry uncertain writes; reattach/read authoritative state instead. WSL shutdown can interrupt services; restart reads journal and preserves unknown outcomes.

Use explicit per-installation GAIT root and sticky-file location; verify root before branch/record/log. Missing required GAIT denies dispatch except the already defined scoped Local/Lab record. Existing CLI/HUD operations must share concurrency controls for resources managed by this interface.
