# Tasks: Federated Peer Limit Semantics (max-prefix-style)

**Input**: specs/189-peer-limit-semantics/{spec,plan,research,data-model,contracts/limits,quickstart}.md
**Tests**: requested by the feature (SC-001..SC-004); every story carries tests.
Test runner: `$VENV/bin/python -m pytest -q tests/n2n/...` (Python 3.12 venv, see quickstart.md).
Paths: F = `mcp-servers/protocol-mcp/bgp/federation`.

## Phase 1: Setup

- [X] T001 Record baseline: run `tests/n2n` (full) on the unmodified tree and note pass/fail counts in specs/189-peer-limit-semantics/verification.md

## Phase 2: Foundational (blocks all stories)

- [X] T002 Add `SCHEMA_189` (peer_limit_policy, limit_hold_down, limit_warning per data-model.md) and execute it next to SCHEMA_060 in F/manager.py
- [X] T003 Add policy layer to F/authorization.py: env defaults (N2N_LIMIT_ACTION, N2N_LIMIT_WARN_THRESHOLD, N2N_LIMIT_RESTART_S, N2N_GLOBAL_DAILY_REQUESTS, N2N_GLOBAL_DAILY_TOKENS), `set_policy`/`get_policy`/`clear_policy` with validation, effective-policy resolution; `Decision.teardown: bool=False` (additive)
- [X] T004 Add an auditor handle to Authorizer (`self.audit`, assigned by service; no-op when None) and a `_limit_event()` helper writing `target_type='limit'` rows via Auditor.record in F/authorization.py; wire `self.authz.audit = self.audit` in F/service.py

## Phase 3: User Story 1 - Normative "what counts" (P1)

**Independent test**: operation matrix test asserts debit/no-debit per FR-001, and default behavior unchanged.

- [X] T005 [P] [US1] Write tests/n2n/test_peer_limits_189.py counted-operations matrix: tools/call, skill/task submit, chat message, knowledge query, replicate manifest debit exactly 1; status/result/cancel, chat open/close not debited (read handlers in F/invocation.py, F/chat.py, F/replication.py to confirm)
- [X] T006 [P] [US1] Add default-compat tests: no config -> refuse codes `rate_limited`/`budget_exhausted`, no teardown, no new audit rows besides existing, in tests/n2n/test_peer_limits_189.py
- [X] T007 [US1] Fix any counted/uncounted mismatch found by T005 in F/invocation.py / F/chat.py / F/replication.py (chat must go through one authorizer entry point `admit_chat`)

## Phase 4: User Story 2 - Exceed action per peer (P1)

**Independent test**: each action drives to the limit and asserts outcome; hold-down survives manager restart.

- [X] T008 [P] [US2] Tests: `warn` allows past limit, counts usage, writes `limit_exceeded_warned`; rate in warn is not enforced
- [X] T009 [P] [US2] Tests: `teardown` refuses with existing code, sets `Decision.teardown`, persists hold-down, calls hook, denies during hold-down (`severed`), recovers after timer and after `clear_hold_down`, survives reopening FederationManager
- [X] T010 [US2] Implement exceed handling in `authorize()`, `admit()`, `reserve_request()`, chat path in F/authorization.py (action dispatch, hold-down check first, refusals never debit, refusals still count in rate window)
- [X] T011 [US2] Implement `teardown_hook` in F/service.py: close channel (not manager.sever; consent kept), schedule after response; refuse in `accept_channel` and `_register_channel` while hold-down active
- [X] T012 [US2] (Implemented differently: the hook is invoked inside `Authorizer._exceed`, so no handler change was needed; chat now uses `Authorizer.admit_chat` in F/chat.py)

## Phase 5: User Story 3 - Warning threshold (P2)

- [X] T013 [P] [US3] Tests: single warning at threshold per limit per day, none below, re-arms on new UTC day (monkeypatch `_today`), tokens limit warning
- [X] T014 [US3] Implement edge-triggered latch evaluation after request/token debit in F/authorization.py (`limit_warning` table, audit `limit_warning`)

## Phase 6: User Story 4 - Global cap (P2)

- [X] T015 [P] [US4] Tests: unset=off; cap=50 with two peers; refusal names global scope; teardown affects only crossing peer
- [X] T016 [US4] Implement global counters (budget_counter `'*'`), checks in authorize/admit/reserve_request, global warning latch in F/authorization.py

## Phase 7: User Story 5 - Visibility and reset (P2)

- [X] T017 [P] [US5] Tests: `limit_status` fields (usage, effective limits, action, warned flags, hold-down remaining); `reset_limits` clears counters/window/latch/hold-down and writes `limit_reset`; config change audited
- [X] T018 [US5] Implement `limit_status`, `reset_limits`, `clear_hold_down`, `hold_down_remaining` in F/authorization.py; extend `budget_status` additively
- [X] T019 [US5] Include `limits` block in daemon peer status next to `peer["budget"]` in mcp-servers/protocol-mcp/bgp-daemon-v2.py; check HUD consumer tolerates extra field (grep hud/ for `budget`)

## Phase 8: Documentation and polish

- [X] T020 [P] Edit docs/ietf/draft-capobianco-ncfed-00.md in place: error-codes section (semantics of -32004/-32005), grants (section on budgets/rate limits), Operational Considerations, Denial of service/Security Considerations, Implementation Status; label BGP max-prefix as analogy; change-history note
- [X] T021 [P] Add operator doc docs/N2N-PEER-LIMITS.md (counted table, actions, env vars, recovery, reset, #344 overlap note); update specs/052-n2n-federation/contracts/n2n-mcp-tools.md n2n_config row to point at it; add note in docs/ietf/NCFED-HARDENING-BACKLOG.md
- [X] T022 (reconcile-mcp.py exits 1 on main too: registered servers cannot start in this environment; other checks identical before/after) Run full `tests/n2n` plus `python3 scripts/reconcile-mcp.py` (exit code not through a pipe); compare with T001 baseline
- [X] T023 Write specs/189-peer-limit-semantics/verification.md with real results and unverified items (draft renders not regenerated, no live two-node test)

## Dependencies

Phase 2 -> all. US1 -> US2 -> (US3, US4 independent of each other, both after US2) -> US5. Docs T020/T021 after US2..US5 behavior is fixed. T022/T023 last.

## Parallel examples

T005/T006 together; T008/T009 together; T020/T021 together.

## Strategy

MVP = Phase 2 + US1 + US2 (normative counting + exceed actions). Then US3, US4, US5, docs.
