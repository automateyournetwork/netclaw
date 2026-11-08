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
