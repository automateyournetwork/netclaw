# Verification

No credentials are recorded here. The fastmcp4 runtime was used read-only.
Nothing was installed into it.

## Tests

Interpreter: `/home/ubuntu/.openclaw/python-runtimes/fastmcp4/bin/python3`.
`PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.

After review round 1, 121 passed in 9.41s:

- `tests/n2n/test_task_wait_181.py` (20): immediate terminal return for
  `completed`, `failed`, `cancelled`, `outcome_unknown`, and `interrupted`;
  `working` then `completed` sleeps the default 5s; `working` and `submitted`
  end the slice with `still_running` and the original `state`; free text in
  `status`/`result` does not count as terminal; the daemon's 404 body
  `{"error": "unknown task"}`, a peer's `state: unknown`, and payloads with a
  non-string, null, or missing `state` (or not a dict) return at once with
  `not_found: true`, no sleep, and no `still_running`; an `error` beside
  `state: working` keeps waiting; a raised `_get` returns
  `{task_id, state: "error", error}`; timeout 3s / interval 0.5s sleeps 2s;
  timeout 90s / interval 30s sleeps 15+15+15+5 and stops at 50s.
- `tests/n2n/test_robustness.py` (4) and `tests/test_setup_border_health.py` (2),
  including the live sha256 of `mcp-servers/n2n-mcp/server.py` in the Hermes
  `sourceHashes` list.
- `tests/unit/test_rag_*.py` (95), including `test_rag_investigation_search.py`
  (22): snapshot aliases, `all`/`*`, score merge and top-k, case-sensitive
  literal `Investigations`, empty snapshot corpus, skipped unreadable snapshot,
  fatal documents index failure on `all`, and a broken snapshot kept beside a
  readable document corpus. Round 1 added: passthrough merges a BM25-only
  exact match (dense 0.0, best RRF) ahead of higher dense scores while the
  cross-encoder path keeps score order on the same hits; every snapshot
  unreadable at count, or failing at retrieve, is `STORAGE_UNAVAILABLE`; one
  unreadable plus one empty snapshot is still an empty corpus; a documents
  retrieve failure on `all` is the `STORAGE_UNAVAILABLE` envelope; the fan-out
  cap keeps the newest collections on both aliases; each collection is
  pre-trimmed to `2k` before reranking; the retrieval log records
  `investigations -> snapshot_a,snapshot_b` with the broken one left out; and
  `ingested_after` / `ingested_before` through `investigations`, `snapshots`,
  and `all` filter on `ingest_ts`, ignoring `capture_ts`.
  `test_failed_chroma_count_is_not_an_empty_corpus` still passes.

## Checks

- `python3 scripts/verify-spec-artifacts.py`: PASS (170 specs checked, 4 legacy exceptions).
- `git diff --check`: clean.

## Not run

- `node scripts/build-catalog.mjs`
- `python3 scripts/build-catalog.py`
- `python3 scripts/check-catalog-metadata.py`
- `python3 scripts/reconcile-mcp.py`
- `tests/integration/test_rag_mcp.py` (can touch `~/.openclaw/rag`)

`workspace/skills/n2n-federation/SKILL.md` and `workspace/skills/rag/SKILL.md`
changed. Their sha256 values in `config/components/catalog.json` were left as
they are. `check-catalog-metadata.py` will fail on those skill hashes until
`build-catalog` refreshes them.

## Registration left unchanged

`n2n_task_wait` is not in the Hermes tool allowlist or `operator_policy.py`.
That list is a reviewed subset and already omits `n2n_task_cancel`. Only the
new server digest was added to `sourceHashes`
(`a264aafced7e14dab10c0ced60f05055998780e5c7d49e5ceda005313111ed19`). It
replaces the round-0 digest `ed79cd71…` from this branch, which was never
merged and carried the missing-task wait loop.
`config/mcp-task-tools.json`, the spec 141 catalogs, and `external_provenance.py`
were not edited. `VERSION` and `CHANGELOG.md` were not bumped.

## Judgments

- `interrupted` is terminal because `tasks.py` sets it in `recover()`, `result()`
  treats it as final, and the retention sweep includes it with the other terminals.
- `unknown` is not a stored state, but it does end the wait: the task is
  missing, purged, or not owned by the caller, and waiting cannot change that.
  The same holds for a body with no string `state` (the daemon's 404
  `{"error": "unknown task"}`, which `_get` does not raise on). Those return at
  once with `not_found: true`; `state` is passed through, never invented. An
  unrecognised string state other than `unknown` still waits, so a new open
  state added later does not end the wait early.
- Alias date filters use `ingest_ts`, matching literal-collection search, not
  `capture_ts`. Documented in the rag skill, README, and `rag_search` docstring.
- `n2n_task_status` and `n2n_task_result` both GET the same path. That was
  already true and was left as-is.
