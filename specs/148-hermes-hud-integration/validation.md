# Spec 148 implementation validation

**Date:** 2026-10-10. **Branch:** `148-hermes-hud-integration`.
**Disposition:** implementation available for acceptance; spec and release remain open.
The exact transferable implementation commit is recorded in [validation-handoff.md](validation-handoff.md).
No deployment, owner gateway restart, live-provider request, device operation, push or
publication was performed. The owner's existing port 3000 process was left running.

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

## Open acceptance gates

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
