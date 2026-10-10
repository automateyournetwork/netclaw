# HUD adapter and browser contract

## Shared server adapter

`resolveInstallation()` produces an immutable startup descriptor. `createRuntimeAdapter(installation)` supplies `readiness`, `capabilities`, `openConversation`, `submit`, `requestStatus`, `events`, `approve`, `stop`, `history`, `models`, `usage`, `toolInventory`, `skillInventory`, `logs`, `configuration`, `updateSetting`, `nativeUi`. Each returns typed data or a reasoned capability error. Existing OpenClaw modules are wrapped, preserving supported wire behavior while fixing selected-environment/ownership handling. Hermes uses the private MCP boundary for agent interactions and safe selected-home projections for local metadata.

No adapter method may consult another runtime as fallback. Cache keys include installation ID, relevant config/policy revision and conversation where applicable. Pure reads neither run inference nor start hosted services. Runtime-specific controls are disabled before submission when the adapter cannot confirm their effect.

## Existing and new routes

Existing `/api/chat`, `/api/chat/history`, `/api/chat/models` and operational panels retain compatible supported payloads for owned clients. Add capability/runtime metadata rather than silently reinterpreting a model preference. Existing clients without an owner/thread must obtain a private conversation binding before agent dispatch; update classic `src/main.js` alongside React. Global `/api/sessions` and `/api/session/:id/tools` become owned projections; raw runtime identifiers are not public lookup keys.

New control endpoints under the existing protected local HUD API:

| Route | Request | Response |
|---|---|---|
| `GET /api/runtime` | Existing HUD authentication | Opaque installation identity, safe runtime/capability/readiness snapshot. |
| `POST /api/chat/conversations` | Existing HUD authentication, optional owned `acknowledgedUncertainRequestId` | New opaque owned conversation; persist explicit uncertainty acknowledgment when supplied without changing the prior request's outcome. |
| `POST /api/chat/requests` | Owned hudThread, clientNonce, text, optional validated Canvas context | `202 {requestId,state,runtime}`; validation/unsupported errors before admission. |
| `GET /api/chat/requests/:id` | Authenticated owner | Owned state, bounded result or safe error, actual runtime metadata. |
| `GET /api/chat/requests/:id/events?cursor=...` | Authenticated owner | Bounded progress page, next cursor, explicit gap. |
| `POST /api/chat/requests/:id/approval` | Exact approvalId, choice once/deny | Scoped pending approval result; conflict if stale. |
| `POST /api/chat/requests/:id/stop` | Owned request | Stop requested/current state, never assumed rollback. |

Keep synchronous `/api/chat` as a compatibility wrapper over the same admission ledger and timeout policy, not a second executor. New React clients use bounded admission + polling so approvals and long runs are accessible. Apply existing local-origin/authentication/CSRF protections to new control routes. Unknown/non-owned IDs share the same non-disclosing response, before upstream calls; recheck after I/O. Safe pending results contain no content for expired/revoked owners. Polls never resubmit work.

## UI behavior

- Runtime label names Hermes or OpenClaw and distinguishes API reachability from verified execution.
- Preserve draft on every validation/admission failure and show unknown outcome distinctly from failed/unsubmitted. A known result may be recovered through owned status/history; no automatic resend button action after reconnect.
- Show pending approvals with exact safe action summary and once/deny only. Stop displays stopping until confirmed; outstanding network work may remain uncertain.
- Model/effort controls reflect the capability snapshot. Initial Hermes configured/actual model is visible; strict model selection and effort controls are unavailable until qualified, without affecting OpenClaw controls.
- Text-only Hermes transport rejects attachments before submission. Canvas error text is not a synthetic agent node. Local Avatar shares Chat state and switching presentation sends no work.
- Browser storage uses installation identity inside keys and payloads. A different runtime's preserved workspace cannot be submitted as current context. Same-origin visibility does not confer another authenticated session's transcript rights.
- Federation and hosted Pal actions reject unsupported Hermes execution in the backend as well as disabling controls. Direct terminal presentation remains independent; supported agent-assisted read requests use Hermes, unsupported APPLY is refused before dispatch.

## Settings, logs and evidence

All existing configuration writers—including env, budget and Terra key routes—must resolve selected source or reject an unsupported operation before touching disk. Allowlisted edits use existing access controls, atomic writes and preservation checks. Never send keys back as values or move secrets into query strings.

Tool inventory has separate registration, qualification and observed-execution states. Actual tool evidence must match the companion's request-scoped invocation ledger; transcript rows/lineage only corroborate it. Logs/configuration/usage/reference views use typed sanitized projections. Unknown usage is null/unavailable, not zero; derived values are labeled. Strip internal reasoning, credentials and unsafe raw tool output before event/history/browser projection. Missing evidence remains unverified.
