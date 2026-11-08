# Verification

No credentials are recorded here. The fastmcp4 runtime was used read-only.
Nothing was installed into it.

## Tests

Interpreter: `/home/ubuntu/.openclaw/python-runtimes/fastmcp4/bin/python3`.
`PYTHONDONTWRITEBYTECODE=1`, `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`.

106 passed in 9.01s:

- `tests/n2n/test_task_wait_181.py` (15): immediate terminal return for
  `completed`, `failed`, `cancelled`, `outcome_unknown`, and `interrupted`;
  `working` then `completed` sleeps the default 5s; `working`, `submitted`, and
  `unknown` end the slice with `still_running` and the original `state`; free
  text in `status`/`result` and a non-string `state` do not count as terminal;
  a raised `_get` returns `{task_id, state: "error", error}`; timeout 3s /
  interval 0.5s sleeps 2s; timeout 90s / interval 30s sleeps 15+15+15+5 and
  stops at 50s.
- `tests/n2n/test_robustness.py` (4) and `tests/test_setup_border_health.py` (2),
  including the live sha256 of `mcp-servers/n2n-mcp/server.py` in the Hermes
  `sourceHashes` list.
- `tests/unit/test_rag_*.py` (85), including `test_rag_investigation_search.py`
  (12): snapshot aliases, `all`/`*`, score merge and top-k, case-sensitive
  literal `Investigations`, empty snapshot corpus, skipped unreadable snapshot,
  fatal documents index failure on `all`, and a broken snapshot kept beside a
  readable document corpus. `test_failed_chroma_count_is_not_an_empty_corpus`
  still passes.

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
new server digest was appended to `sourceHashes`
(`ed79cd71f23528178549bcc478074f666965c0cc432943499cc1357086e420a9`).
`config/mcp-task-tools.json`, the spec 141 catalogs, and `external_provenance.py`
were not edited. `VERSION` and `CHANGELOG.md` were not bumped.

## Judgments

- `interrupted` is terminal because `tasks.py` sets it in `recover()`, `result()`
  treats it as final, and the retention sweep includes it with the other terminals.
- `unknown` does not stop the wait. It is a missing-task response, not a stored
  state. A body with no `state` (the daemon's `{"error": "unknown task"}` on
  404, which does not raise) also waits out the slice. Callers still see `state`.
- `n2n_task_status` and `n2n_task_result` both GET the same path. That was
  already true and was left as-is.
