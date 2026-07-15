# Contract: N2N Async Task Lifecycle (US1)

**Feature**: 053 | **Channel**: NCFED (unchanged framing) | **Semantics**:
A2A-style task lifecycle, JSON-RPC 2.0 — finishing what 052 defined but
implemented synchronously.

## Wire methods (NCFED, requester → executor unless noted)

| Method | Params | Result |
|---|---|---|
| `n2n/tasks/submit` | `{target_type, target_name, input_text, request_id}` | `{task_id, state:"submitted"}` — returns **immediately**, executor runs work in background |
| `n2n/tasks/status` | `{task_id}` | `{task_id, state, progress, detail?}` |
| `n2n/tasks/result` | `{task_id}` | `{task_id, state, output_text?, tokens_used?, error?}` |
| `n2n/tasks/cancel` | `{task_id}` | `{task_id, cancelled: bool}` |

- Every call is short-lived (no call blocks on the operation) → survives ngrok
  idle/reset (FR-005).
- `state`: `submitted | working | completed | failed | cancelled`.
- Executor debits budget + writes the 052 audit record on completion (unchanged).
- Authorization: `submit` runs the same default-deny grant check as 052's
  synchronous path (FR-022 — unchanged); denial returns the existing error codes.
- Unknown/expired `task_id` → `state:"unknown"` (never hangs) (edge case).

## Daemon HTTP routes (operator side, via n2n-mcp)

| Route | Method | Body / Result |
|---|---|---|
| `/n2n/tasks` | POST | `{peer, target_type, target_name, input_text}` → `{task_id}` (submits over NCFED) |
| `/n2n/tasks/<task_id>` | GET | `{state, progress, output?, ...}` |
| `/n2n/tasks/<task_id>/cancel` | POST | `{cancelled}` |
| `/n2n/tasks` | GET | list recent tasks (both directions) for health/HUD |

## n2n-mcp operator tools

- `n2n_delegate(peer, target_type, target_name, input_text)` — submit; returns
  `task_id` and initial state. For convenience it may poll up to a short bound
  and return the result inline if it finishes fast; otherwise returns `task_id`.
- `n2n_task_status(task_id)` / `n2n_task_result(task_id)` / `n2n_task_cancel(task_id)`.

## Requester-side result delivery

The daemon polls `n2n/tasks/status` on a cadence (`15 s`) after submit; on
`completed` it fetches `n2n/tasks/result`, caches it against `task_id`, and makes
it available via `/n2n/tasks/<id>`. Results persist per retention window so an
operator can retrieve them after a channel drop (FR-004).
