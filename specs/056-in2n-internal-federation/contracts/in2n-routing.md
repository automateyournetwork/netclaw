# Contract: iN2N Border Routing (capability match → member select → delegate)

How the Border turns an operator request into work on the right Member. Reuses the spec 052 capability inventory and spec 053 async delegation; adds deterministic member selection and scope enforcement (FR-009–FR-013, FR-023; research R5).

## Operator entry point

`n2n-mcp` tool: `n2n_route(request_text, target_hint?)` — the operator asks the Border to handle a task-shaped request. Daemon HTTP: `POST /n2n/route`.

The Border MAY use reasoning to interpret `request_text`, but **member selection among capability matches is deterministic** (below), so the same request lands on the same member every time.

## Selection algorithm (deterministic)

1. **Match**: find all `active` members whose advertised scope (skills/tools, from the reused inventory) covers the request's required capability.
2. **No match** → return `-32030 ERR_NO_CAPABLE_MEMBER` with a plain message: "No member in risk `<risk>` can perform that." (FR-011). The Border does **not** attempt the work itself.
3. **One match** → select it.
4. **Multiple matches** → deterministic tie-break:
   - (a) **most-specific scope**: the member advertising the fewest **specialty** capabilities that still cover the request (the true specialist) wins. The mandatory base floor (FR-021a) is tagged `base` and **excluded** from this count so shared base tools don't distort specialist selection (FR-021b);
   - (b) if still tied, **lexicographically smallest `member_id`**.

## Delegation (reused 053 async lifecycle)

Selected member gets the work as an async delegated task over the internal channel:
```json
{ "jsonrpc":"2.0","id":7,"method":"n2n/tasks/submit",
  "params":{ "target_type":"skill","target_name":"cml-lab-lifecycle","input_text":"<build spec>" } }
  → { "result": { "task_id":"…","state":"submitted" } }        # returns in ~seconds
```
Then `n2n/tasks/status` (poll) and `n2n/tasks/result` (fetch). The operator-facing `n2n_route` returns the `task_id` immediately for long work; `n2n_task_status`/`n2n_task_result` (existing 053 tools) poll it. Short work may return inline. Persistence (053) means the result survives a member restart or channel blip mid-build (SC-006).

## Scope enforcement (member side, FR-023)

- A member's **advertised scope == its allowed scope**. When it receives a `tasks/submit` for a target outside its scope, it refuses with `-32031 ERR_OUT_OF_SCOPE` rather than attempting or self-expanding.
- This holds even though the member trusts its Border (relaxed internal trust ≠ unlimited authority — FR-027).

## Secret isolation (FR-026)

- The submit carries only the request/input text — never credentials, `.env` values, device addresses, or testbed secrets. The member executes with **its own local configuration**. Enforced by the reused no-secrets guard.

## Audit (FR-024/FR-025, research R8)

- Every route/delegate writes a `remote_invocation_record` with `channel_kind='in2n'`.
- If an **external (eN2N) request** is satisfied by internal delegation, the Border writes the outer eN2N record **and** the inner iN2N record, `linked_record_id` joining them; the external result is attributed to the risk, not the member (FR-016/FR-025).

## Error codes (new)

| Code | Name | Meaning |
|------|------|---------|
| -32030 | ERR_NO_CAPABLE_MEMBER | no active member covers the requested capability |
| -32031 | ERR_OUT_OF_SCOPE | member asked to act beyond its advertised/allowed scope |

## Test assertions

- Request matching exactly one member routes there; result returns through the Border.
- Request matching two members always selects the more-specific one; identical specificity → lexicographic member_id (deterministic, repeatable).
- Request matching no member → -32030, and the Border performs no work itself.
- Out-of-scope target on a scoped member → -32031.
- Long build over `n2n_route` returns a `task_id` fast and completes as a background task surviving a member restart.
- An eN2N request fulfilled internally produces two linked audit records (external + internal).
