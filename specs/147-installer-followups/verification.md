# Verification — investigation on 2026-10-10

## Baseline

Local main fast-forwarded to `b4334bf255cd53aecd2e81f51abe63deea53f1df` and merged into `147-installer-followups` as `cf12ec1`. Includes PR #287's host preflight/Zabbix fixes and PR #288's dotenv fix. No new production installer implementation is claimed here.

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

Implementation and live acceptance remain pending tasks, not passing results.
