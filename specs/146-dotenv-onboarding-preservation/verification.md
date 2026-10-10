# Verification — 2026-10-09

## Passing evidence

- `.contract-test-envs/unit/bin/python -m pytest -q tests/unit/test_dotenv_onboarding.py`: **25 passed**. Uses temporary homes/state directories, dummy credentials and stub runtime executables. Covers all FR-001–FR-006 behaviors, including setup before its first question and selected runtime config preservation.
- Actual installed OpenClaw 2026.7.1-2 `loadDotEnv({quiet:true})` in isolated Node subprocesses: provider absent from checkout dotenv; both provider/network keys absent in unrelated cwd; both available there after running the new importer. [Sanitized booleans](loader-evidence.json). No provider/service calls, real dotenv imports, or credential values in evidence.
- `bash -n scripts/install.sh scripts/setup.sh scripts/lib/common.sh scripts/lib/install-steps.sh`: **PASS**.
- `python3 -m py_compile scripts/import-env.py tests/unit/test_dotenv_onboarding.py`: **PASS**.
- `python3 scripts/verify-spec-artifacts.py`: **PASS**, 130 specs, four historical exceptions.
- `python3 scripts/verify-catalog-coverage.py`: **PASS**, zero unexplained gaps.
- `python3 scripts/reconcile-mcp.py --surface catalog --surface dependencies --surface docs --surface meraki-ids --surface packages --surface portability`: **PASS**, all six surfaces.
- `git diff --check`: **PASS**.
- `python3 scripts/run-contract-tests.py --suite unit`: **PASS**, all offline unit contracts, 67.43 seconds. Includes existing installer, environment-writer, CLI and runtime regressions.
- `python3 scripts/prepare-release.py --check`: **PASS**, proposed 1.6.1 metadata. `python3 scripts/test-prepare-release.py`: **6 passed**. No release, tag, PR or push performed.

## Corrections during verification

Python dotenv and Node dotenv differ on unquoted hashes without preceding whitespace. The portability fixture now uses `value # comment`; docs instruct quoting literal hashes. The importer preserves the original assignment syntax rather than rewriting its value. The setup fixture needed the new importer beside its copied setup script; fixed the fixture and confirmed the actual setup handoff.

## Remaining checks and limits

All planned local checks passed. No live user-host diagnosis, provider login, daemon installation/restart, live Hermes credentials or device changes are claimed. Existing runtime configuration presence remains the wizard-skip criterion; a partial upstream config may still require manual onboarding. Repository wrappers outside installation are not migrated to new path semantics by this fix.

Startup device listing was attempted and failed on the existing testbed's unsupported `connections.defaults.arguments` key. MemPalace's configured server file is unavailable. GAIT recorded the session; no network state was inferred and no external tickets/messages were created.
