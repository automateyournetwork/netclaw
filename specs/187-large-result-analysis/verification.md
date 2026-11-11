# Verification: spec 187 (real results, 2026-11-11)

| Check | Result |
|---|---|
| `tests/result-analysis` via `scripts/run-contract-tests.py --suite result-analysis` (isolated env) | PASS, 46 pytest tests |
| Same tests, scratch venv with fastmcp 4.0.11 / mcp 2.3.0 | 46 passed |
| `tests/runner/test_run_contract_tests.py` | 19 passed, 0 failed |
| `scripts/verify-spec-artifacts.py` | PASS |
| `scripts/verify-inventory-counts.py`, `scripts/verify-catalog-coverage.py`, `scripts/build-catalog.py --check` | exit 0 |
| `scripts/reconcile-mcp.py` (exit captured directly, not piped) | exit 1, but only on failures that exist on main: `dependencies` (humanrail pin) and `startup` (31 servers missing deps on this host, same count before and after). `catalog`, `docs`, `portability`, `packages`, `meraki-ids` pass. `result-analysis-mcp` is not among the startup failures. |

## What was demonstrated (synthetic data only)
- A 1,920-interface Genie-shaped table over 170 KB: 420 Tunnel interfaces counted exactly, split 300 up / 120 administratively down, `coverage.complete: true`, all 1,920 scanned.
- Envelope for the same payload is under 15,000 chars, `inline_complete: false`, sha256 matches the retained original.
- Retention-capped copy, page results, scan-budget hit, unplaceable timestamps, stream drops and gaps: never `complete: true`.
- Unknown, malformed (path traversal), expired and tampered handles are explicit errors.
- No eval/exec/subprocess/SQL/regex in the new modules (static test).

## NOT verified
- OpenClaw's 20,000-char cap and its rationale (OpenClaw is not installed here; taken from the issue).
- No live router, no live OpenClaw agent or Tool Search broker end to end; the envelope's fit under the real host path is by budget design, not measured.
- multivendor-cli-mcp wiring is asserted statically and via `bounded_dict`; its own suite needs nornir/napalm and was not run here.
- pyATS_MCP not integrated (untracked pinned upstream). Log and stream scenarios are synthetic only; syslog-mcp wiring is a follow-up.
