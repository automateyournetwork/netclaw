# Verification — investigation and implementation on 2026-10-10

## Baseline

Local main fast-forwarded to `b4334bf255cd53aecd2e81f51abe63deea53f1df` and merged into `147-installer-followups` as `cf12ec1`. Includes PR #287's host preflight/Zabbix fixes and PR #288's dotenv fix. Implementation below follows this baseline.

## Existing regressions

Command:

```bash
.contract-test-envs/unit/bin/python -m pytest -q \
  tests/unit/test_installer_preflight.py \
  tests/unit/test_installer_component_paths.py \
  tests/unit/test_installer_python_runtime.py \
  tests/unit/test_installer_mcp_config.py \
  tests/unit/test_n2n_install_preservation.py \
  tests/unit/test_dotenv_onboarding.py
```

**PASS: 113 tests in 11.84 seconds.** Includes Zabbix cwd, independent component paths, Python upper bounds, prerequisite aggregation, runtime records, config preservation and dotenv ordering. Fixtures do not prove a live Forward/CML/Zabbix deployment.

## Remaining defect evidence

- [Node preflight](node-preflight-evidence.json): current evaluator accepts versions incompatible with current upstream OpenClaw's engine range. These results describe the failing baseline, not desired behavior.
- [Registration generator](registration-evidence.json): selected twelve components produce zero native entries, exit 0. Skill-based paths exist for some; no inference that every mechanism is absent.
- [Transport probes](transport-evidence.json): installed OpenClaw 2026.7.1-2 with Node 24.19.0, synthetic servers, isolated temporary HOME/config. Stdio and explicit streamable-http discover the expected fixture tool. URL-only HTTP sends GET and exposes none despite exit 0.

Repeat transport diagnosis with explicit installed binary paths:

```bash
python3 specs/147-installer-followups/reproduce-transports.py \
  --node /absolute/path/to/node \
  --cli /absolute/path/to/openclaw/openclaw.mjs \
  --runtime-label 'the tested OpenClaw version' \
  --output /tmp/netclaw-transport-evidence.json
```

The fixture accepts initialization and discovery only. It starts its own temporary loopback HTTP server; it never calls a model or device and does not alter the installed runtime or gateway.

## Limits

The original log archive is unavailable; six macOS component failures are unnamed. The original CML server, Ollama endpoint, runtime config and precise command/environment are not reproduced. Native CLI probe success is not a gateway agent-turn or model grounding test. No secrets, real provider calls, real package installs, service restarts or device operations occurred.

## Specification checks

- `python3 scripts/verify-spec-artifacts.py`: PASS, 131 specs checked with four legacy exceptions.
- Reproduction helper compilation and `--help`: PASS.
- Final portable reproduction helper rerun: completed all three cases and reproduced the discovery results above.
- `git diff --check`: PASS.

## Implementation verification

- `python3 scripts/run-contract-tests.py --suite unit --json`: PASS, **826 passed / 2 skipped**, 94 isolated test files, 82.10 seconds. Includes the new runtime policy, launcher, readiness and failure-exit cases.
- Reconciliation: catalog, documentation counts, registration portability, package references and dependency policy all PASS.
- FastMCP compatibility: 36 owned servers, zero failures. MCP Tasks adoption: PASS.
- Bash syntax, Python compilation, spec artifacts and `git diff --check`: PASS.
- [Actual component probes](implementation-probes.json): OpenClaw 2026.7.1-2 / Node 24.19.0 on macOS arm64; temporary HOME, runtime config and Python 3.12.12 venv. Native discovery passed for Packet Buddy (12 tools), Subnet Calculator (1), TTS (2) and NetBox (4). NetBox used synthetic loopback credentials; no endpoint call was made.
- Calculator canary: actual `mcp-call --component subnet-calc` returned the expected 192.0.2.0/30 network, /30 mask and two usable hosts. No model generated that result.
- Negative cases cover RPC initialization error, closed/partial stdout, timeout, empty catalogs with exit 0, missing registration/runtime/credentials, and missing/unreachable/non-tool-capable Ollama models.

To reproduce the four-component smoke, use [reproduce-installed-components.py](reproduce-installed-components.py) with `--node-bin /absolute/node/bin --output /tmp/netclaw-components.json`. It explicitly downloads declared test dependencies using uv into a disposable environment; it applies the existing reviewed calculator migration only to temporary source. It does not install or change operator component runtimes. Runtime dotenv settings are part of the fixture, matching installer deployment.

The initial smoke setup intentionally exposed failures when dependencies/patches/settings were absent; readiness flagged them instead of reporting success. After preparing declared source/dependencies and persisting fixture settings, all four passed. This is representative discovery evidence, not a full-catalog fresh-host install or the original CML/pyATS endpoint reproduction.

Release metadata: proposed patch 1.6.2. Live acceptance and arbitrary model answer grounding remain unverified; no tag or published release is implied. PR CI/merge evidence follows below.
