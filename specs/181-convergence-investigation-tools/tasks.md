# Tasks

- [x] T001 Add `n2n_task_wait` with clamped slices, stored terminal states, and `still_running`.
- [x] T002 Read `state` only from the payload `state` string. Map `_get` failures to `state: error`.
- [x] T003 Point delegate, route, and the n2n-federation skill at wait-until-terminal.
- [x] T004 Search ready investigation snapshots for `investigations`, `snapshots`, and `cases`.
- [x] T005 Search documents plus those snapshots for `all` and `*`. Leave every other name literal.
- [x] T006 Skip an unreadable snapshot. Keep a documents index failure fatal on `all` / `*`.
- [x] T007 Document the aliases in the rag skill, the rag-mcp README, and the `rag_search` docstring.
- [x] T008 Append the n2n-mcp server digest to the Hermes source hash list. Do not extend the allowlist.
- [x] T009 Unit tests for wait and for alias search. No network and no model download.

## Review round 1

- [x] T010 `n2n_task_wait`: 404 body, `state: unknown`, or no string `state` returns at once with `not_found: true`.
- [x] T011 Alias merge uses RRF order in reranker passthrough; score order with the cross-encoder.
- [x] T012 Every snapshot unreadable returns `STORAGE_UNAVAILABLE`, not an empty corpus.
- [x] T013 A documents retrieve failure on `all` / `*` returns the `STORAGE_UNAVAILABLE` envelope.
- [x] T014 Cap alias fan-out (`RAG_INVESTIGATION_MAX_COLLECTIONS`, default 50) and pre-trim to `2k` per collection.
- [x] T015 Log the collections searched; document that alias date filters use `ingest_ts`.
- [x] T016 n2n-federation skill: `n2n_task_wait` when available, else poll `n2n_task_status` every 5–15 s.
- [x] T017 Tests for each of the above, plus date filters through aliases. Replace this branch's Hermes digest.
