# Research

- `n2n-mcp` is a stdio proxy. `n2n_task_status` is `_gcf_dumps(await _get("/n2n/tasks/{task_id}"))`.
  `_gcf_dumps` is unchanged. `NETCLAW_FEDERATION_JSON=1` forces JSON.
- Stored task states in `mcp-servers/protocol-mcp/bgp/federation/tasks.py` are
  `submitted`, `working`, `completed`, `failed`, `cancelled`, `outcome_unknown`,
  and `interrupted`. `recover()` sets `interrupted`. `result()` treats it as final.
  The retention sweep includes it with the other terminals. `unknown` is only the
  lookup-miss response (`status()` also returns it for a task the caller does not own).
- The daemon GET for a missing task returns 404 `{"error": "unknown task"}` and `_get`
  does not raise. Review round 1: waiting out the slice on that body, or on
  `state: unknown`, returned `still_running` for a task that will never appear, so a
  coordinator looped forever. Both now return at once with `not_found: true`.
- A fork of `n2n_task_wait` guessed terminal from `status` and `result` text and
  treated `canceled` and `error` as terminal. This spec does not. State is an exact
  string match on `payload["state"]` only.
- `rag_snapshot` rows use `kind='snapshot'`. `_do_search` used to pass `collection`
  straight to `chroma.count`. An alias has to expand registry rows instead.
  `chroma.count` on a never-created name returns 0 (get_or_create), so the literal
  empty path stays on `chroma.count`. Integration tests that touch `~/.openclaw/rag`
  are not part of this check.
- The reranker passthrough keeps input order and dense score. With the
  cross-encoder on, merging after a full rerank and sorting by `(-score, chunk_id)`
  makes a later collection's higher score win. In passthrough, `hybrid.py` gives
  BM25-only hits `dense_score` 0.0, so a score sort would drop exact-match hits
  (review round 1). Each collection's RRF uses the same `k=60` and leg depth, so
  sorting by `rrf_score` interleaves collections by fused rank; passthrough keeps
  that order. `Reranker.uses_model()` tells the two modes apart. `_result_from_hit` does not emit `collection`; alias hits add
  the collection that was searched, not a metadata value.
- The fork also added an `any` alias and changed the literal empty message.
  Those stay out. Review round 2 asked for `collections_searched` and
  `collections_skipped` as counts on alias responses, so the cap is visible.
- `_get` returns `r.json()` and drops the status, so a 5xx `{"error": ...}` looked
  like a 404 to round 1's wait (review round 2). The scoped broker
  (`bgp/federation/execution.py`) answers 200, 403, or 409 and never 404, and
  `_scoped` raises `HTTPStatusError` on non-2xx, so a 404 can only come from the
  daemon directly.
- Registry rows and their chunks share `ingest_ts`, so filtering rows before the
  cap agrees with the chunk post-filter.
- `config/hermes-hud-tool-policy.json` is a reviewed Hermes subset. `n2n_task_cancel`
  is already absent, and `operator_policy.py` matches that subset. Adding
  `n2n_task_wait` there would advertise a tool `validate_operator` refuses. The live
  sha256 of `mcp-servers/n2n-mcp/server.py` must still be appended to
  `servers.n2n-mcp.sourceHashes` or `tests/test_setup_border_health.py` fails and
  `qualified_servers` skips the server.
- `scripts/check-mcp-tasks.py` locks `config/mcp-task-tools.json` to the spec 141
  catalog. A new tool name fails that check. The name is not added there, and the
  historical catalogs are not rewritten. `external_provenance.py` is a provenance
  set, not a catalog.
- Skill text hashes in `config/components/catalog.json` are refreshed by
  `scripts/build-catalog.mjs` and `scripts/build-catalog.py`. Those steps, plus
  `scripts/check-catalog-metadata.py` and `scripts/reconcile-mcp.py`, are left for
  a later run. `catalog.json` is not hand-edited.
