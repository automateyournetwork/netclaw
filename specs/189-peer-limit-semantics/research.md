# Research: Peer limit semantics

## R1. Where do limits fire today (verified in code)
- `Authorizer.authorize()` checks rate (`_check_rate`, sliding 60 s, in-memory) then budget (`_check_budget`) and returns `rate_limited` / `budget_exhausted`. It does not debit.
- Debit happens in `admit()` / `reserve_request()` (atomic `UPDATE ... WHERE requests_used<? AND tokens_used<?`) and tokens post-hoc via `debit(tokens=)`.
- Callers: `handle_tools_call`, `handle_task_submit` (skill), `handle_knowledge_query` (target knowledge), replicate manifest (target knowledge_replica), chat (`_check_rate` + `reserve_request`). Status/result/cancel, chat open/close, heartbeat, card exchange do not call authorize/reserve: matches FR-001 uncounted set. Confirmed by reading `invocation.py`: `_replicate_gate` (authorize + `_admit`) is used by BOTH `handle_replicate_manifest` and `handle_replicate_batch`, so every batch page is counted today. Spec FR-001 was amended to match the code (default behavior preserved).
- Env defaults are node-global; `n2n_config` overrides are in the 052 contract but no code reads per-peer limits. Verified by grep: no `n2n_config` in any .py.

## R2. Decision: policy resolution
Effective policy = per-peer row in `peer_limit_policy` (NULL column = inherit) else global-default row (`peer_identity='*'` holds optional aggregate caps and default action) else env. Rationale: single table, tiny, backward compatible. Alternative (new columns on federation_peer) rejected: iN2N identities have no federation_peer row.

## R3. Decision: exceed actions
`refuse` default; `warn` (allow, audit); `teardown` (refuse + close channel + persisted hold-down). BGP "drop the excess" equals refuse. BGP max-prefix teardown/restart timer is used as analogy only; no claim about RFC wording is made in the draft beyond naming the operator practice. Alternative: always teardown rejected (breaks default).

## R4. Decision: teardown mechanics
Closing the channel (not `manager.sever`, which revokes consent and requires operator re-consent). `Authorizer` calls an injected `teardown_hook(peer, reason)`; service schedules `ch.close()` after the RpcError response is flushed (create_task with small delay-free await ordering: close scheduled via `loop.call_soon` after returning). Hold-down persisted in `limit_hold_down`; checked in `accept_channel` (before replying handshake) and `_register_channel`, and at the top of `authorize()` (returns `severed`). Outbound dials by the peer fail by closure; our own supervisor redial to that peer is not blocked (hold-down is inbound-side per spec).

## R5. Decision: warning
Edge-triggered latch row `limit_warning(peer_identity, day, limit)`; fires when used/limit >= threshold, once per day per limit. Evaluated in debit paths (after increment).

## R6. Decision: global cap
Counters stored as `budget_counter` rows under `peer_identity='*'`, incremented together with the peer row. Checked in `authorize()` after peer budget; refusal uses `budget_exhausted` with reason "global daily budget exhausted".

## R7. Decision: operator surface
Authorizer/manager methods: `set_policy`, `get_policy`, `clear_policy`, `limit_status`, `reset_limits`, `clear_hold_down`. Exposed via daemon peer status (`limits` block) and via the n2n tool surface if an `n2n_config` handler exists (none does; documented). Config rejected on invalid values.

## R8. Draft convention
`docs/ietf/README.md`: -00 `.md` is the source of truth; edit it, run `render.sh`, commit renders. `kdrfc`/`xml2rfc` are not installed here: the .md is edited and the text/XML renders are NOT regenerated; recorded as a verification gap.

## R9. #344 overlap
#344 splits grants into read vs write. Both edit `authorize()`/`invocation_grant`. This plan keeps `Decision` fields additive (`teardown`) and puts new logic in helper methods called from `authorize`, so a merge conflict is limited to the body of `authorize` and `admit`. A read/write split would classify operations into counted classes; this spec's counted-set table is the natural place to attach "write" vs "read".
