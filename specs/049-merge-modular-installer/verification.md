
## macOS keyboard follow-up — 2026-10-09

- PASS: `/bin/bash` is Apple Bash 3.2.57. Baseline `read -t 0.05`
  reports `invalid timeout specification`; PTY Down cancels the menu.
- Regression proof: execute the arrow-decoding and runtime-cancellation tests
  against temporary copies of HEAD's installer and TUI. Eight arrow subcases
  and two cancellation subcases fail before the patch.
- PASS: `python3 -m unittest discover -s tests/unit -p test_installer_tui.py -v`
  — all 10 tests pass using `/bin/bash` and real pseudo-terminals. Includes
  CSI/application arrows, j/k shortcuts, checklist selection, actual installer
  Hermes selection and q/Escape cancellation, EOF, explicit runtime, and
  non-interactive defaults. No installation steps run.
- PASS: `/bin/bash -n scripts/install.sh scripts/lib/tui.sh`.
- PASS: `python3 scripts/verify-spec-artifacts.py` — 128 specs checked.
- PASS: `python3 scripts/verify-catalog-coverage.py` — zero unexplained gaps.
- PASS: `scripts/reconcile-mcp.py --surface catalog --surface dependencies
  --surface docs --surface meraki-ids --surface packages --surface portability`
  using the app-bundled Python. System Python 3.9 cannot load the existing
  dependency check's union annotations; rerunning with bundled Python resolves
  the initial check failure. No dependency files changed.
- PASS: contract suite inventory and matrix commands; `git diff --check`.
- Pytest is absent from both available Python environments. The focused
  regression suite runs with standard-library unittest and remains collectable
  by the repository's pytest unit suite. The full unit suite was not run.
- Limits: Greg's exact macOS 15.7.9/Terminal session and Linux/modern Bash
  have not been tested. Standalone Escape waits up to one second.
- Local review patch only; no PR, release bump, push, or package installation.

Workaround on unpatched main: `./scripts/install.sh --runtime hermes
--profile recommended` (run as a single command). This bypasses both selection
menus; omitting `--profile recommended` keeps the component menu interactive.

## Python prerequisites/retry follow-up — 2026-10-09

Greg's log confirms missing uv. It uses `/usr/bin/python3` and pip 21.2.4,
consistent with Apple's Python 3.9; Greg's exact version is still pending.
Verified package metadata requires Python >=3.10 for fastmcp 4.0.11 and
mcp 2.3.0. The local `/usr/bin/python3` is 3.9.6 and the new minimum check
rejects it with actionable guidance. No package constraints were loosened.

- Baseline regression proof: previous code incorrectly accepts old installer
  Python, an old explicit base and missing uv; it reuses an old managed runtime.
  Four corresponding checks fail against temporary copies of prior code.
- PASS: 57 tests via isolated pytest 8.4.2 (`/private/tmp/netclaw-installer-tests/bin/python -m pytest ... -q`).
  Test files: test_installer_python_prerequisites.py,
  test_installer_prerequisite_isolation.py, test_installer_python_runtime.py,
  test_installer_tui.py, test_installer_exit_status.py,
  test_installer_constraints.py, test_installer_component_paths.py,
  test_pyats_runtime_recovery.py and test_gait_runtime_recovery.py.
  Includes prerequisite failure, selection-specific uv requirement, explicit
  old runtime refusal, supported runtime reuse, preserved state/records on
  failed retry, and rejection of unmanaged/symlink recovery destinations.
- PASS: actual Python 3.9 stdlib venv retained byte-for-byte for its config and
  sentinel; a new Python 3.12.14 runtime installed an offline fixture wheel
  and recorded the new interpreter. No system or MCP component packages changed.
  An initial smoke test incorrectly used `pip install --version`; it failed
  because pip requires an install requirement. The corrected fixture-wheel
  test exercises real installation and success recording.
- PASS: Bash 3.2 syntax checks for install.sh, install-steps.sh, pip-helper.sh
  and tui.sh; spec artifact checker; declaration reconciliation for catalog,
  dependencies, docs, meraki-ids, packages and portability; `git diff --check`.
- Pytest was installed only in an isolated temporary test environment.
- Limits: Greg's version/full log pending; no full 108-component install,
  real vendor/service discovery, Linux/modern Bash or existing config conflict
  resolution validated. This corrects confirmed prerequisite/retry gaps without
  claiming every reported component failure has been proven resolved.

PR 284 merged as c2cc6d4. Follow-up branch:
`codex/fix-installer-python-prerequisites`, based on that upstream merge.

## Full-log follow-up — 2026-10-09

The supplied version output confirms Python 3.9.6. Read 104 actual logs from
the archive without extracting it; excluded AppleDouble metadata. 42 contain
resolver failures, 11 modern editable-install errors, five no-matching-package
errors and two missing-uv staged failures. Counts describe messages, not a
validated number of failed components. The raw archive and private analysis
are not committed or uploaded to GitHub.

- PASS: 124 tests under isolated Python 3.12.14/pytest 8.4.2, using:

  ```bash
  /private/tmp/netclaw-installer-tests/bin/python -m pytest \
    tests/unit/test_installer_python_prerequisites.py \
    tests/unit/test_installer_python_runtime.py \
    tests/unit/test_installer_prerequisite_isolation.py \
    tests/unit/test_installer_exit_status.py \
    tests/unit/test_installer_constraints.py \
    tests/unit/test_installer_component_paths.py \
    tests/unit/test_installer_tui.py \
    tests/unit/test_installer_mcp_config.py \
    tests/unit/test_installer_log_followups.py \
    tests/unit/test_jev_installer.py \
    tests/unit/test_pyats_runtime_recovery.py \
    tests/unit/test_gait_runtime_recovery.py \
    tests/n2n/test_certs_060.py -q
  ```

  Includes dedicated-runtime preservation, ownership refusal and reuse,
  obsolete-pip/system-pip boundaries, recorded launch binding, installation
  and import failures, certificate runtime/dependency failures, and portable
  gtrace parsing with failed placement. The certificate tests exercise real
  cryptography 46.0.7 and temporary credential/database paths. One existing
  utcnow deprecation warning; no test failures. New tests are collected by
  the existing unit suite; certificate coverage belongs to the n2n suite.
- Regression proof: six new cases fail against temporary copies of the
  previous committed code (source venv recovery, three pip-upgrade boundary
  cases, certificate setup and gtrace). No checkout reset was used.
- PASS: `tests/installer/run-tests.sh`, with the temporary test interpreter
  on PATH and selected as NETCLAW_PY. Memory MCP wheel includes its SQLite
  schema; bgp-intel, gnmi, nautobot and suzieq install into temporary component
  runtimes. Generated registrations launch these four servers and obtain
  tool lists with both legacy and 2026-07-28 protocol versions. No endpoint
  tools are invoked. fwrule: BLOCKED_DEPENDENCY, optional checkout absent.
- PASS: Apple Bash 3.2 syntax, spec artifact checks, catalog/dependency/docs/
  Meraki/package/portability reconciliation, suite inventory/matrix and diff
  whitespace checks. No constraints for other integrations were loosened.
- Limits: no full 108-component installation, live vendor/service discovery,
  Greg's exact Terminal/macOS session, Linux or modern Bash validation.
  Dedicated external integrations are covered with sanitized fixtures, not
  live deployments. Docker, kubectl, Ollama, packet capture, browser setup and
  Linux Computer Use requirements remain operator prerequisites. Existing
  custom launch conflicts still require reconciliation before retiring old
  environments. pip upgrades require package-index availability.

This extends existing draft PR285. Release metadata remains pending maintainer
coordination under CONTRIBUTING.md/docs/RELEASING.md; no release is claimed.

### Spec 144 integration follow-up — 2026-10-09

Integrating main into PR #286 exposed stale standalone/reconciliation fake-Python
fixtures: they rejected the new sys.version_info prerequisite before reaching
intended PEP 668/install-error assertions. Add a successful version-probe response,
retaining the original pip failures and credential-preservation assertions.
Zabbix's source check now recognizes netclaw_component_venv only when that helper
retains netclaw_venv_create delegation and Python validation. This is test-only
compatibility repair for the already-merged installer behavior.


## Platform/component preflight and Zabbix follow-up — 2026-10-09

Based on main aa90e7d after PR285 merged. Spec/research/plan/tasks were extended
before code under the modular installer's existing reliability scope. Spec Kit
slash commands and GAIT tools are unavailable in this session; their checked-in
workflow was followed manually, with this evidence and append-only session audit.

- PASS: 197 focused tests using Python 3.12.14, with its bin directory on PATH:
  `python -m pytest -q tests/unit/test_installer*.py
  tests/unit/test_contract_runtime_preservation.py
  tests/unit/test_standalone_enable_credentials.py
  tests/unit/test_jev_installer.py tests/unit/test_pyats_runtime_recovery.py
  tests/unit/test_gait_runtime_recovery.py`.
  Includes 65 new preflight/cwd cases: Darwin/Linux/unsupported OS, host version
  and architecture normalization, selected and interpreter-native SDK platforms,
  Linux glibc, Python bounds, explicit venv isolation/pip and too-new preservation,
  command selection, optional warnings, Go/CGO/compiler/Apple CLT, Docker daemon,
  vendor-index configuration/no secret disclosure, bounded/no-download probes,
  Python preference/override, disabled picker rows and distinct run logs.
  Ready and blocked --preflight and blocked normal entrypoints assert no runtime
  home/config/environment creation or invocation of package installation.
- PASS: Zabbix cwd regression reaches the previous HEAD installer and fails
  there; the corrected installer passes. Baseline used a temporary script tree,
  with source/config paths present, without resetting the real checkout.
- PASS: Actual `component_install_zabbix` on a temporary copy of tracked vendor
  source/requirements, starting at the repo root, builds a fresh isolated Python
  runtime and installs the local vendored package, FastMCP 4.0.11 and MCP 2.3.0.
  `NETCLAW_PY=<recorded temporary interpreter> bash tests/zabbix/run-tests.sh`
  passes all four static/discovery suites. Real legacy and 2026-07-28 handshakes
  agree on zabbix_api/zabbix_api_docs/zabbix_api_list; manifest 862/5,000 tokens.
  Isolation excludes user/system site packages. No endpoint tools invoked.
  NEEDS_LIVE_CREDENTIALS: Zabbix live trap tests deliberately skipped.
- PASS: `tests/installer/run-tests.sh` with Python 3.12 on PATH/NETCLAW_PY:
  memory wheel schema packaging and fresh bgp-intel/gnmi/nautobot/suzieq installs;
  generated registrations list tools in both protocol modes (10/10/59/5 tools).
  BLOCKED_DEPENDENCY: fwrule optional source checkout absent.
  Both real smoke runs trap-remove their temporary environments; no global pip,
  Homebrew, Go, uv, Docker, Hermes or OpenClaw install occurred on the test Mac.
- PASS: `python scripts/installer-preflight.py --validate-policy` under Python
  3.12 and Apple's Python 3.9.6; 109 unique catalog entries covered by defaults
  and declared overrides. Actual Darwin 26.6.2/arm64/Bash 3.2 preflight reports
  missing Node/npm/npx and Forward Go before install work. Version/architecture
  fixtures additionally cover Greg's macOS 15.7.9 and Linux.
- PASS: spec artifact verification (129 specs), catalog coverage (zero unexplained
  gaps), catalog/dependencies/docs/meraki-ids/packages/portability reconciliation,
  contract suite list/matrix, Apple Bash 3.2 syntax and git diff --check.
  Existing exit-status fixture explicitly substitutes host preflight so it still
  exercises downstream failure propagation; real preflight has separate tests.

Limits: no complete 109-component install, native Linux host execution, exact
Greg Terminal session, live vendor services or real Go/Docker deployment. Policy
covers declared restrictions, not every future package graph. RADKit preflight
checks explicit environment index/local-wheel configuration, not pip config files
or wheel provenance. Go probes prohibit auto-downloads; Docker checks its configured
context read-only. Passing preflight does not establish credential, model, browser,
cluster or endpoint readiness. Interactive logs still do not capture full terminal
transcripts. Existing compatible environments are reused; incompatible ones remain
in place and only successful installations update launch records.

Integration coherence: installer/policy/tests/README/migration docs/spec updated.
No server tool/schema, skill, SOUL/TOOLS, HUD, credentials, catalog identity or MCP
registration interface changes; those integration surfaces are not applicable.
Release metadata is deferred while this follow-up is draft, for a coordinated patch
against current main under CONTRIBUTING.md and docs/RELEASING.md. No release claimed.
