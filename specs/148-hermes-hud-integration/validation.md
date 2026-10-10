# Spec 148 implementation validation

**Date:** 2026-10-10. **Branch:** `148-hermes-hud-integration`.
**Current disposition:** Spec complete for the owner-approved Mac/Ubuntu 26.04 WSL scope; source release 1.7.0 prepared for PR/merge. See [closure.md](closure.md), the portable Mac evidence and [release notes](../../docs/releases/1.7.0.md). Ubuntu 24.04 and native Windows OpenClaw remain unverified outside this qualification. The earlier results below are historical and retain their actual scope.
The exact transferable implementation commit is recorded in [validation-handoff.md](validation-handoff.md).
The original Mac implementation validation below performed no live-provider request.
The subsequent WSL acceptance section records actual Anthropic requests. No owner
gateway restart or device change was performed. These historical acceptance sessions preceded the separately authorized release PR/merge.

## Environment and qualification

Mac host: macOS **26.5.2**, arm64 (the planning matrix's macOS 15 was an anticipated
target, not the machine used). HUD: Node **24.19.0**. Real agent: Python **3.14.6**,
Hermes **v0.21.6**, revision `818c13be1dc4fd28987e1e881a9408224afd4535`.
Bridge and subnet MCP: separate Python **3.12.12** environments; bridge FastMCP
**4.0.11**, MCP **2.3.0**, official Node MCP client **2.3.1**. The agent uses its own
constrained dependencies. No global Python dependency replacement.

The actual subnet MCP source was revision `5178da6f83ebd894fa7331a62e1087ec9550751b`,
patched with the repository's reviewed FastMCP migration inside a synthetic checkout.
Only this qualified read-only calculator and reviewed installed subnet skill are currently
eligible. This is not general Hermes network-tool parity. Federation is spec 149.

## Recorded results

| Check | Result | Evidence and limits |
|---|---|---|
| HUD source unit tests | PASS: 366 tests, zero skipped | `npm test`; includes ownership, selected runtime, browser storage, real React Chat/local Avatar component, late recovery, drafts, Canvas branch context and existing security suites |
| Canvas regression runner | PASS: 27/27 suites | `npm run test:canvas`; includes Terminal Intent, local change control, SSH, topology and observability; no device access |
| Installer/dotenv/runtime regressions | PASS: 219 tests + 25 subtests | Existing installer unit families and new cross-language runtime resolver fixtures |
| Added populated-home tests | PASS: 2 | Repeated selection preserves owner YAML/env/skill/memory; both configuration generators exclude recursive private bridge registration |
| Offline Hermes contract driver | PASS: 18 passed, one real-agent skip; two resolver tests | Strict capabilities, protected guards, ledger/concurrency/recovery, selection/launch; real-agent test deliberately separate |
| Real pinned-agent fixture | PASS | Five contextual turns, real installed MCP/tool/skill, secret sentinel absent, forbidden handler not dispatched, native history compaction preserves evidence, owner files preserved |
| Actual HUD HTTP → MCP integration | PASS | Production component launcher for bridge/tool; ownership/revocation, nonce, installation mismatch, history, local Avatar availability, unsupported model/budget/federation controls |
| Installer smoke | PASS with existing optional gap | Isolated bgp-intel/gnmi/nautobot/suzieq environments and legacy/current MCP discovery: 10/10/59/5 tools; optional fwrule checkout absent, explicitly unverified |
| Production build / Canvas bundle budget | PASS | Four entry points built; Canvas budget 400,000 bytes; existing chunk-size warnings remain |
| npm dependency audit | PASS | Zero reported vulnerabilities at validation time |
| FastMCP compatibility | PASS | 36 owned servers, zero failures |
| Catalog / inventory / spec artifacts | PASS | 111 catalog entries; 237 skills; 176 integrations (124 agent-native + 52 external/private); 132 specs, four existing legacy exceptions |
| MCP declaration reconciliation | PASS | Catalog, dependencies, docs, Meraki IDs, packages and portability |
| Git whitespace check | PASS | `git diff --check` |
| Real browser | UNVERIFIED | Chrome automation rejected isolated localhost navigation with `net::ERR_BLOCKED_BY_CLIENT` before page load. No visual pass inferred from JSDOM |
| Owner provider / Mac owner installation | NEEDS_LIVE_CREDENTIALS | No configured owner Hermes home on this Mac; existing OpenClaw credentials were not copied into Hermes |
| Ubuntu/WSL and Windows browser | UNVERIFIED | Requires the offered Windows/WSL machine; detailed handoff provided |
| Native Windows early refusal | UNVERIFIED on host | Launcher source and resolver tests cover intended refusal; PowerShell not available here |

Local command logs are `/tmp/netclaw148-{unit-final,canvas-final,installer-all,preservation,
contract-final,offline-final,fresh,installer-smoke,bundle,fastmcp}.log`. These are local
diagnostics, not portable acceptance evidence. Reproduce on the transferred commit and
save sanitized results on Windows/WSL. The real fixture lives under a test-only temporary
directory and may be removed after inspection; it contains no owner provider credentials.

## Reproduction on a qualified development host

```sh
npm --prefix ui/netclaw-visual ci
npm --prefix ui/netclaw-visual test
npm --prefix ui/netclaw-visual run test:canvas
npm --prefix ui/netclaw-visual run test:bundle
python3 scripts/run-contract-tests.py --suite hermes-hud --prepare --strict-capabilities
python3 tests/hermes-hud/run_real_fixture.py
bash tests/installer/run-tests.sh
python3 scripts/check-fastmcp-compat.py
python3 scripts/verify-catalog-coverage.py
python3 scripts/verify-inventory-counts.py
python3 scripts/verify-spec-artifacts.py
git diff --check
```

The two new preservation tests are pytest tests: run them with the installer test
environment using `python -m pytest -q tests/unit/test_hermes_hud_installer.py`.
The offline suite intentionally does not substitute for the separate real-agent fixture.

## Final implementation mapping and design refinements

Several planned files were consolidated to reuse existing OpenClaw modules. Hermes
MCP lifecycle, metadata and error handling are in `src/hud-server/runtime/hermes.js`;
owned chat/history routes in `runtime/routes.js`; read-only intent in `runtime/intent.js`.
Existing OpenClaw chat/usage/history behavior remains in the selected server branch.
This replaces the proposed `index`, `openclaw`, `mcp-client`, and `capabilities` wrappers.
Corresponding tests are consolidated in `runtime/recovery.test.js` and the real HTTP
fixture instead of duplicating every proposed test filename.

Browser bootstrap, namespace migration and pending-request reconciliation are shared
in `src/shared/runtime-client.js`. Canvas uses `branch-context.js` for immutable branch
seeds and saves drafts/quotes/attachments with its graph. Chat/local Avatar share the
existing mounted component. Terminal Intent interception occurs before the existing
OpenClaw execution layer; Hermes never enters its APPLY path.

The launcher installs a dedicated pinned agent under `<home>/python-runtimes/hermes-hud-agent`
instead of modifying the owner's Hermes interpreter. Companion provenance is written
to private `<home>/netclaw-hud/launch.json` on explicit launch, containing interpreter,
source, revision, installation and configuration digest. Source hashes are verified on
launch and at execution guard boundaries. It starts fresh owned processes; stale process
records are never trusted or used for killing/reusing processes. Port preflight rejects
conflicts before starting children or generating companion credentials. Health verifies
installation identity, authentication and policy; provider readiness remains unverified
until actual execution. The private credential file is `companion-auth.json`, not dotenv.

Completed request metadata is pruned after 30 days; uncertainty is retained. An owned
uncertain submission missing from the bridge ledger can be acknowledged without
inventing a prior run. Failed preparation before agent submission is reported as a
definite failure. Ambiguous submission never becomes a retry. The audit ledger must
persist an invocation before its tool handler can run.

Generated references now recognize private HUD MCP access and task-wrapped native tools.
The bridge is counted as an integration but is excluded from both agents' registrations.

## Historical acceptance gates before WSL/Mac return

Superseded for completed Mac work by [closure.md](closure.md).

T029 (complete host fault matrix), T034/T039 (full upgrade/rollback), T038 (native Windows),
T052 (real browser), T053 (Mac owner-provider acceptance), T055 (Ubuntu/WSL), and T056
(release preparation) remain open. The WSL handoff carries the remaining
launch/restart/fault/upgrade/rollback/native-Windows cases; partial automated coverage
is not a substitute for those host checks. Any unexercised failure category remains
unverified, even when its handler is implemented. A WSL provider pass does not silently
become a Mac live-provider pass: complete Mac acceptance or obtain an explicit change
to that platform criterion before closure. `VERSION` stays **1.6.2** until acceptance;
the planned minor target **1.7.0** must be reconciled with main at release time.

## Audit and transfer checkpoint

Implementation commit: `db5a1b0f3efdf87e469158337a2d1dfb770be230`. The following handoff commit changes only
validation/task documentation. GAIT branch: `hermes-hud-specification-2026-10-10`;
implementation evidence recorded as `b926b01d`. Daily notes are in the ignored local
`memory/2026-10-10.md`. No tickets or external communications were created.
Completed: 50 of 58 tasks; the eight remaining tasks are explicitly listed above.


## WSL continuation — 2026-10-10

**Disposition: fixes committed; acceptance remains partial.** Use
[the Mac return handoff](mac-return-handoff.md) for remaining gates. Do not interpret a
clean worktree or passing automated suite as completion of T052/T053/T055/T056.

Source was already available locally; at the owner's direction it was used instead of
importing a missing bundle. A separate Linux-filesystem worktree was created at
`/home/johncapobianco/netclaw-148`, on `148-hermes-hud-integration`, from `28cbc67`.
Implementation fixes are commit `9f26dfa`; the Hermes badge correction and expanded
Windows browser coverage are commit `a45225a`. The original `netclaw` checkout on `main`
and its existing stashes were preserved. Its main ref advanced independently during
the session; no checkout/reset/merge or commit on main was performed here.

Actual host: Ubuntu **26.04** x86_64, WSL2 **3.0.1.0**, kernel **6.18.40.1**,
Windows **10.0.26300.9550**, PowerShell **5.1.26100.9549**. The distro is still named
`Ubuntu-22.04`; that label is not its installed version. The requested Ubuntu 24.04
matrix is therefore **not verified** by this run. Isolated tools: Node **24.19.0**,
uv **0.13.0**, agent Python **3.14.6**, bridge/tool Python **3.12.10**. Native Windows
Node **24.11.1** was used only for early Hermes refusal/browser automation; it does
not establish supported native OpenClaw startup.

The owner populated a separate Hermes `.env` with an Anthropic key. The private profile
is `/home/johncapobianco/netclaw-148 acceptance/Hermes Home`; selection is under its
sibling `config` directory. UI/API/companion ports are 34000/34001/8644. Real reviewed
subnet and bridge component installation functions were executed. The complete core
installer was not run against the owner's runtime. No OpenClaw credentials were copied.

### Results and limits

| Check | Result | Actual evidence / boundary |
|---|---|---|
| Live Anthropic | PASS | Five completed turns on committed `9f26dfa`, `anthropic/claude-sonnet-4-6`; remembered violet, correlated subnet tool evidence, 14 usable hosts, actual usage. `evidence/wsl-live-provider.json` |
| Pinned real agent / controlled provider / real MCP | PASS | Five-turn HTTP→MCP→Hermes run, actual companion stop/restart between turns, preserved context/evidence, no lazy dependency overlay. `evidence/wsl-real-agent.txt` |
| Offline strict contract suite | PASS | Separate real-agent test intentionally skipped offline and passed by the real fixture. `evidence/wsl-contracts.txt` |
| HUD unit / Canvas suites | PASS | 366 tests; 27/27 Canvas suites, including existing OpenClaw/Terminal Intent code regressions; these are not live owner acceptance |
| Installer regression tests | PASS | 236 tests + 25 subtests; `python -m pytest -q tests/unit/test_installer_*.py tests/unit/test_hud_*.py tests/unit/test_hermes_hud_installer.py tests/unit/test_dotenv_onboarding.py` |
| Installer smoke | PASS with optional gap | Real isolated bgp-intel/gnmi/nautobot/suzieq install/discovery, both protocol versions, 10/10/59/5 tools. Optional fwrule source absent, unverified |
| Build / inventory | PASS | Production build and 400,000-byte Canvas budget; 37 owned FastMCP servers; 111 catalog entries; 237 skills / 176 integrations; 132 specs with four legacy exceptions |
| Native PowerShell Hermes | PASS refusal only | Three entrypoints reject before actions with Ubuntu/WSL guidance; owner config hash and Node/OpenClaw PID set unchanged |
| Linux private state | PASS sampled host + fault fixtures | Descriptor/installation/auth/ledger/native-state regular files mode 0600; shared-readable DB/directory and symlink DB refused. `evidence/wsl-preservation.json` |
| Upgrade | PASS limited scope | Actual `upgrade-hud.sh --check` and `--apply`; selected profile env/YAML/skills/runtime record hashes unchanged. Full repeated component install, browser rollback and legacy populated upgrade matrix still open |
| Owner preservation | PASS | Original OpenClaw env/config and repository env hashes unchanged; existing gateway/API/UI PIDs 578/745/749 still present. No owner service restart |
| Fresh shell / ports / uncertainty | PASS automated scope | Actual subprocess custom-CWD/descriptor and occupied-three-port tests; ledger nonce/lost-POST/late-result/exact approval tests. Full real-process pending-request browser fault matrix remains open |
| Existing OpenClaw live acceptance | UNVERIFIED | Automated regressions passed and running services preserved; no live contextual Chat/Canvas/Avatar/Terminal walkthrough performed on owner's installation |
| Mac-specific acceptance / release | UNVERIFIED / deferred | T053 still requires actual Mac live provider, upgrade and existing OpenClaw; no version bump or spec closure |

Windows Edge results are stored separately in `evidence/wsl-browser.json`; only its
listed assertions are passing browser evidence. Panels, actual paused approvals,
cooperative stop, late-result/unknown UX, complete installation switch/rollback and
full failure-category walkthroughs remain open where not exercised. Cross-origin/Host
checks are automated server regressions, not a new manual browser security claim.

### Failures found and corrections

- The owner found an incorrect “Gateway unavailable” badge on the live Hermes HUD.
  The UI expected OpenClaw's `online` field, while Hermes reported `ready`. It now uses
  the selected Hermes readiness response and says “Hermes ready”; Windows Edge confirms
  this, and the full 366-test suite/build pass after the fix.
- Windows Edge passed two Canvas branches with distinct quote-point contexts, excluded
  later-parent/sibling messages, and restored graph/draft after refresh. The initial
  browser test selected an earlier quote while expecting later context; the fixture now
  provides distinct answers. Its asynchronous browser polling also returned before IDB
  autosave; explicit bounded polling of actual saved rows corrected the test. No Canvas
  product change was needed. The report includes zero browser page errors.

- Old uv selected Python 3.14.0a6; the real agent exited with signal 11. Updated the
  isolated test tooling and added stable-interpreter enforcement to installation.
- Anthropic was absent from the pinned install. Upstream lazy installation created a
  private overlay that hid the MCP SDK and broke qualified discovery. Install Anthropic
  explicitly, disallow lazy installs, suppress optional plugin discovery for the entire
  companion lifecycle, refuse existing overlays, and require actual qualified discovery.
  Preserve failed test overlays rather than deleting owner state. Final live and controlled
  runs passed after correction. Earlier failures were recorded, never replayed as success.
- Upgrade on an incomplete source tree raised an irrelevant module error. Source/helper
  preflight now precedes runtime inspection; affected upgrade regressions pass.
- Two UI tests assumed fixed startup delays. Bounded observable-readiness waits replace
  those delays; all 366 tests passed. An initial concurrent npm install/test run also failed
  before dependencies finished; the completed-install rerun is the recorded result.

Raw logs and private fixture homes remain under `~/.cache/netclaw-148-*` and the isolated
acceptance directory, outside Git. Committed evidence contains sanitized results only;
no keys, private configuration, raw provider transcripts or owner conversation data.


At handoff, the owner-requested live test HUD remains running on
**http://localhost:34000/** (Anthropic/Claude), separate from the existing OpenClaw HUD
on port 3000. Only the qualified subnet tool is connected: general CML discussion is
possible, but live CML lab queries are **not** qualified by this spec. Private credentials
remain outside Git. The synthetic browser fixture is stopped after validation.

Audit: GAIT branch `spec148-wsl-validation-20261010`, continuation `f67640e0`,
final handoff `fbc15e63`; full inherited log retained privately at
`~/.cache/netclaw-148-evidence/gait-session-log.json`. Daily memory recorded locally.
Startup `pyats_list_devices` failed on an existing testbed schema field
`devices.R1.connections.defaults.arguments`; no network-device operation followed.
This does not establish device state and is not a passing device check.
