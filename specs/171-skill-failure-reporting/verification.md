# Verification

Operator Risk on Ubuntu 24.04 amd64, OpenClaw 2026.10.9, Node 24.22.1, member
`byrns-risk/viz` on `ollama/gemma4:31b-cloud` in testing mode. Commands ran with
`umask 077`. No credentials are recorded here.

## T001 diagnosis (live)

- Transcripts of the three 2026-11-01 `markmap-viz` tasks, read from a copy of the
  member's agent database. Two ended with the model writing a fixed SVG itself and
  returning its path. The third ran 1 h 43 min, used about 300k input tokens over 268
  `process poll` calls, and ran `npm install -g jsdom`. All three were audited
  `in_scope/success`.
- `scripts/mcp-call.py "node …/markmap-mcp/dist/index.js" markmap_generate …` returns
  `Error: ResizeObserver is not defined` with no agent involved. With `ResizeObserver`
  stubbed, the server process crashes on `requestAnimationFrame`.
- The member's environment lacked `MCP_CALL` and `MARKMAP_MCP_SCRIPT`, and so did the
  Border's runtime `.env`.

## T003 tests

- `tests/n2n/test_skill_failure_reporting_171.py`: the peer request names the skill,
  ends with the request text, and has the rule before it.
- `tests/n2n/test_member_delegation.py::test_route_and_delegate_completes` asserts the rule
  reaches the member's embedded turn.
- `tests/n2n`: 797 passed, 5 skipped, 1 failed. The failure,
  `test_hermes_internal_149::test_official_n2n_mcp_operator_permit_and_owned_handle`, is
  inherited and fails identically on main. Three R01 files (`test_direct_transport_168`,
  `test_exporter_tls_168`, `test_ngrok_transport_168`) were not collected on this host:
  the system pyOpenSSL is incompatible with the installed `cryptography`, which is
  unrelated to this change.
- `ruff check --select F,E9` on the changed files reports the same four findings as main
  and no new ones. `git diff --check`, `prepare-release.py --check` (1.18.4),
  `verify-spec-artifacts.py`, catalog metadata and links pass. The hash-pinned
  `mcp-servers/n2n-mcp/server.py` is unchanged.

## T004 live

Applied to the operator Risk: the rule was backported, the member's two missing paths
were added, and the markmap server ran with its separate rendering fix. Only the viz
member was restarted.

- The same request as on 2026-11-01, routed through the Border (`POST /n2n/route`,
  `markmap-viz`), completed in 50 s using 192k tokens. The member called
  `markmap_generate` through `MCP_CALL` and saved the returned SVG. The saved file is
  byte-identical to the tool's output for the same input.
- One request for a skill whose requirement is absent (`ue5-network-viz`, no
  `UE5_MCP_URL`) failed after 40 s with no output and no substitute file. OpenClaw
  withheld the skill ("not available to this agent"). The model retried a misnamed
  search tool until the turn exited, and never reached a failing tool. So this run
  shows an honest failure, but not the rule changing a decision.

## Not covered

Whether the rule changes the decision of a model that does reach a failing tool, as on
2026-11-01. That depends on the model and is not deterministic. Also found and not
changed: the Border advertises a member's scoped skill even when the member's OpenClaw
withholds it for a missing requirement.
