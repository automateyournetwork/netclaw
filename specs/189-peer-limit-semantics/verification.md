# Verification: spec 189 (issue #343)

Environment: macOS, Python 3.12 venv outside the repo with `mcp-servers/protocol-mcp/requirements.txt`, pytest, pytest-asyncio, pyyaml, requests. Not installed: chromadb.

## Real results

- Baseline (unmodified main, replication files only re-run): `17 failed, 7 passed` in `tests/n2n/test_replication_*`; cause `ModuleNotFoundError: No module named 'chromadb'`. Environmental, pre-existing.
- Final full run `python -m pytest -q tests/n2n` on this branch: `17 failed, 2705 passed, 14 skipped`. The 17 failures are exactly the same chromadb-dependent replication tests as baseline. No other failures.
- `tests/n2n/test_peer_limits_189.py`: 31 passed (counted/uncounted operations, defaults unchanged, warn, teardown, hold-down persisted across manager restart, iN2N never torn down, warning once per day and re-arm for requests and tokens, global cap, precedence over env, status/reset, validation, chat path, service channel close, daemon config/status/reset routes).
- Existing authorization, readmission, chat boundary and cloud boundary tests pass unchanged.
- A first full run showed one extra failure, `test_hermes_internal_149.py::test_installer_n2n_endpoint_is_removed_from_protected_discovery`, because `mcp-servers/n2n-mcp/server.py` is hash-pinned in `config/hermes-hud-tool-policy.json`. The pinned hash was updated following the repository precedent (commit b1712d78); the test passes.
- `python3 scripts/reconcile-mcp.py` exits 1 both on main and on this branch; the output apart from the `startup` check is identical (startup fails because registered servers' Python dependencies are not installed here).

## Not verified

- Draft renders: `docs/ietf/rendered/*.xml|txt` were NOT regenerated. `kdrfc` (kramdown-rfc) converts the edited source to XML including the new section, but `xml2rfc` 3.35.0 rejects the document, and it rejects the unmodified HEAD draft identically ("numbered section under an unnumbered parent", the spec149 note under Acknowledgments). idnits was not run. Regenerate with `docs/ietf/render.sh` in the toolchain used for -00.
- No live two-node federation test of teardown over a real socket; channel close is tested with a stub channel, and the real `FederationChannel.close` path was not exercised.
- Knowledge query and replication admission are asserted by code-path inspection only (they need chromadb).
- iN2N paths are tested at the Authorizer level only.
- HUD UI rendering of the new `limits` fields was not checked; only the daemon JSON is tested.

## Findings recorded

- Analyze C3: replication batch pages DO count in the reference implementation; the spec was amended to match rather than changing default behavior.
- The `n2n_config` MCP tool already sent `daily_requests`/`daily_tokens`/`rate_per_min` but the daemon ignored them; they are now honored.
- Warn-mode records at most one `limit_exceeded_warned` row per peer per limit per 5 s (a single request passes several gates).
- Overlap with issue #344: same methods in `authorization.py` (`authorize`, `admit`); see docs/N2N-PEER-LIMITS.md.
