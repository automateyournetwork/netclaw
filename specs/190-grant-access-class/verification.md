# Verification: spec 190 (issue #344)

Environment: macOS, fresh Python 3.12.12 venv outside the repo with `mcp-servers/protocol-mcp/requirements.txt`, pytest, pytest-asyncio, pyyaml, requests, httpx. Not installed: chromadb. Branch stacked on `189-peer-limit-semantics` (spec 189, PR #350).

## Real results

- Baseline before changes (T001): `tests/n2n/test_authorization.py` + `test_peer_limits_189.py`: 41 passed.
- `tests/n2n/test_grant_access_class_190.py`: 30 passed. Covers the grant x target class matrix for tools, the knowledge types, an unknown target type, legacy rows and an old database without the column migrating to `read_write`, node default applying only to new grants, invalid class rejected with nothing stored, supersede and its effect on a pending approval, refusals debiting nothing and never triggering teardown, annotation mapping and override precedence, classification validation and audit, reclassification during a wait and during an approval wait, approval ordering, iN2N `already_trusted`, skill delegation through `handle_task_submit` (same outcome for read-looking and write-looking text, no task row on refusal), `handle_tools_call` wire code -32001 and audit decision `access_class_denied`, card hints and unchanged visibility, and the daemon routes (grants, classifications, trust).
- Mutation check: disabling the class check in `authorize()` makes 12 of these tests fail; restoring it passes all 30.
- Full run `python -m pytest -q tests/n2n` on this branch: `17 failed, 2735 passed, 14 skipped`. All 17 failures are the chromadb-dependent `test_replication_*` tests, the same set that fails on main and on the 189 branch.
- A first full run showed one extra failure, `test_protected_enrollment_172.py::test_actual_isolated_cli_status_is_readonly_and_has_no_secret_output`. I had run `scripts/reconcile-mcp.py` and created a temporary git worktree while it ran. The test passes alone and the clean second full run above has no such failure, so it is attributed to that interference; the cause was not investigated further.
- `config/hermes-hud-tool-policy.json`: the last pinned sha256 for `mcp-servers/n2n-mcp/server.py` was updated to the new file hash; `test_hermes_internal_149.py` passes in the full run.

## Not verified / not done

- `docs/reference/interfaces.json` (and the other generated `docs/reference/*` files) were not regenerated: running `scripts/build-hud-reference.py` produced about 14,000 changed lines of unrelated drift, so the output was discarded. The `n2n_grant` signature and the three new n2n-mcp tools are therefore not in that generated reference.
- `docs/ietf/rendered/*` (txt/xml) not regenerated: kdrfc/xml2rfc are not installed. The Markdown source carries the change and a note in its change history.
- `scripts/reconcile-mcp.py` exits 1 in this environment. A diff against a worktree of the 189 branch showed extra dependency/startup lines on this branch, but the worktree lacks ignored local files, so that comparison is not conclusive. No line mentions n2n.
- No live two-node mesh run, no HUD UI change, no real MCP `tools/list` ingestion (the import takes an operator-supplied payload). Live annotation ingestion at call time, per-class budgets, Border-to-member class forwarding and an `admin` class were not implemented.
- Whether a read-classified skill truly avoids writing inside its agent turn is an operator assertion; the federation layer does not verify it.
- MCP specification wording for `readOnlyHint` was not re-read; only the field name is relied on, as an imported hint.
