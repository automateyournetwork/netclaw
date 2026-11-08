# Plan

- Add `n2n_task_wait` in `mcp-servers/n2n-mcp/server.py` immediately after
  `n2n_task_status`. Poll `GET /n2n/tasks/{task_id}`. Clamp 10–50s and 2–15s.
  Terminal set is the five stored finals. On slice expiry copy the last payload,
  set `still_running` and the hint, and do not overwrite `state`. On `_get`
  exception return `{task_id, state: "error", error: str(exc)}`.
- Mention the wait in the `n2n_delegate` and `n2n_route` docstrings, and in
  `workspace/skills/n2n-federation/SKILL.md` (delegation, replication poll, iN2N
  route, tools list). One `working` status is not a reason to stop.
- In `mcp-servers/rag-mcp/rag_mcp_server.py`, keep the current literal search as
  `_search_one`. `_do_search` sends `investigations` / `snapshots` / `cases` and
  `all` / `*` to `_search_aliased`. Ready snapshot collections come from the
  registry. Merge by score after reranking the full candidate set. Skip an
  unreadable snapshot. A documents index failure on `all` / `*` returns
  `STORAGE_UNAVAILABLE` with the existing message.
- Document the aliases in the `rag_search` docstring, `mcp-servers/rag-mcp/README.md`,
  and `workspace/skills/rag/SKILL.md`.
- Append the new `server.py` sha256 to the Hermes `sourceHashes` list only.
- Tests: `tests/n2n/test_task_wait_181.py` (import the server under a unique module
  name; fake `_get`, `time.monotonic`, and `asyncio.sleep`) and
  `tests/unit/test_rag_investigation_search.py` (set `RAG_DATA_DIR` before import;
  stub registry, count, retrieve, embed, and rerank). No integration tests.
