# Verification notes: spec 191 (Cisco IQ remote MCP)

Date: 2026-11-11. Host: macOS, Python 3.14 system interpreter (contract runner uses 3.12 per manifest).

## Run, with real results

| Check | Result |
|---|---|
| `bash tests/cisco-iq/run-tests.sh` | 35 tests (14 enable, 13 operate, 8 policy/docs): all pass; offline, loopback mocks only |
| `python3 scripts/run-contract-tests.py --suite cisco-iq` | PASS (4.0 s); `NEEDS_LIVE_CREDENTIALS` reported separately, not counted as a pass |
| `python3 tests/runner/test_run_contract_tests.py` | 19 passed, 0 failed |
| `python3 scripts/build-catalog.py` / `check-catalog-metadata.py` | PASS (113 components, 241 skills) |
| `python3 scripts/verify-catalog-coverage.py` | PASS, zero unexplained gaps |
| `python3 scripts/verify-inventory-counts.py` | PASS (241 skills, 179 MCP integrations; README/SOUL updated) |
| `python3 scripts/verify-spec-artifacts.py` | PASS |
| `python3 scripts/check-catalog-links.py` | 0 dead (3 needs_review, pre-existing) |
| `tests/test_setup_*.py` (277 tests, `PYTHONPATH=tests`) | OK (32 skipped). Required updating `config/components/effects.json`, `scripts/lib/plan-steps.sh` and `tests/fixtures/setup/catalog-baseline.json` |
| `python3 scripts/reconcile-mcp.py` (exit read directly) | exit 1, same as main: `dependencies` (humanrail pin) and `startup` (31 servers missing modules on this host). Surfaces `catalog`, `docs`, `portability`, `packages`, `meraki-ids` pass. No cisco-iq entry in any failure |
| Real-endpoint smoke | `diagnose --live` with a deliberately bogus key against the real US endpoint returned `AUTH_FAILURE` (HTTP 401); the key was not printed |

## Findings applied from /speckit.analyze
F1: both `~/.openclaw/openclaw.json` and `~/.openclaw/config/openclaw.json` are detected (tested). I1: non-HTTPS refused, plain HTTP only for loopback overrides (tested).

## NOT verified
- The official Cisco IQ guide (`https://iq.cisco.com/apidocs/mcp-server`) returned HTTP 403 to curl and a web-fetch tool. The contract (endpoints, Bearer, user-principal rule, expiry) is from issue #346 and is unconfirmed.
- No live key: acceptance of a valid Bearer key, MCP `initialize`/`tools/list` behaviour on the real server (the client is tested against a mock only), session handling, SSE vs JSON replies, service-account zero-tool behaviour, expiry and permission inheritance.
- Cisco IQ tool names and schemas: unknown; none asserted. The policy allowlist ships empty. No workflow in the skill has been exercised.
- Whether the OpenClaw gateway resolves `${CISCO_IQ_API_KEY}` in `headers` for an entry written at runtime and reloads it; the shape mirrors the existing `meraki-mcp` entry but was not run against a live gateway.
- Per-tool enforcement: the native client has no gate; policy relies on skill instructions and DefenseClaw (not exercised here).
- SC-001 (under 2 minutes hands-on) is a manual claim, not tested.
- `scripts/trace-skill.py cisco-iq` shows `rag-mcp` as its integration (the tracer appears to match the word "coverage"); cosmetic, not investigated.
- Not done: GAIT session log, WordPress milestone post, HUD node beyond the generated `env-map.js` entry, `scripts/build-hud-reference.py` regeneration (it produces about 14k lines of unrelated churn on this tree, so `docs/reference/*` was left untouched).
