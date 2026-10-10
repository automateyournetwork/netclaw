# Hermes HUD qualification tests

These tests distinguish a working protected Hermes agent from a simulated HUD reply.
They never contact network devices. The default suite never uses owner credentials.

## Three separate evidence levels

1. `python3 scripts/run-contract-tests.py --suite hermes-hud --prepare --strict-capabilities`
   runs isolated ledger, admission, guard, recovery, launch and resolver contracts.
   Its real-agent test is intentionally skipped without the three fixture interpreter/source
   variables. A passing offline suite alone does not qualify Hermes execution.
2. `python3 tests/hermes-hud/run_real_fixture.py` installs and runs the **real pinned Hermes
   agent**, a controlled local OpenAI-compatible provider, and the **real installer-patched
   subnet MCP**. It also starts the actual HUD HTTP backend and official MCP client. This
   separate required CI step fails if prerequisites or execution are unavailable.
3. `python3 tests/hermes-hud/live_acceptance.py --url http://127.0.0.1:3001 --run --output /private/path/report.json`
   explicitly performs five turns through the operator's configured provider. Omitting
   `--run` performs status only. Requires `httpx`; use the isolated bridge interpreter.
   This is not part of default tests. Do not include credentials or raw private transcripts
   in reports. An unknown outcome is recorded without replaying it.

Use Node 24.19+ below 25, or 26.1+, `uv`, Git, Python 3, and `npm ci` in
`ui/netclaw-visual` before running the real fixture. `uv` provisions separate Python 3.12
bridge/tool and Python 3.14 agent environments. `--workdir /absolute/test-only/path`
retains the synthetic fixture for inspection and reuse. Never pass an owner's installation
as the fixture work directory. Downloads require internet; inference stays on loopback.

## Provenance and assertions

Hermes is v0.21.6, revision `818c13be1dc4fd28987e1e881a9408224afd4535` from
`https://github.com/NousResearch/hermes-agent`. The compatibility manifest records every
reviewed Python source hash, including constructor, inference, dispatch, API, idempotency
and storage seams. Unsupported or changed sources fail qualification. Dependencies are
constrained in `config/hermes-hud-agent-constraints.txt` and the private bridge manifest.

The subnet source is revision `5178da6f83ebd894fa7331a62e1087ec9550751b` from the
repository recorded in `config/hermes-hud-tool-policy.json`. Only the reviewed original
and installer-patched FastMCP source hashes qualify. The fixture clones into its own
synthetic repository and uses the production `component-launch.py` interpreter records
for bridge and tool. No owner clone is patched. The installed subnet skill must match
the reviewed text hash. Only IPv4 `/24` through `/30` is qualified.

The real fixture asserts five contextual turns, actual correlated tool evidence, eligible
installed skill text, memory-sentinel exclusion, forbidden shell rejection, ownership and
revocation, nonce deduplication, unsupported controls, unchanged owner configuration,
absence of owner native databases, and evidence persistence after native transcript
archiving/compaction. It runs HTTP → official MCP → protected Hermes → real subnet MCP.
The provider fixture is deterministic; this is **not** evidence that a paid provider works.

Related coverage lives in `tests/unit/test_hud_runtime_selection.py`,
`tests/unit/test_hermes_hud_installer.py`, HUD `runtime/recovery.test.js`,
`shared/runtime-client.test.js`, `dashboard/hermes-ui.test.js`, and Canvas branch/session
tests. Browser-component tests use JSDOM; a real-browser walkthrough remains a separate
acceptance gate. See the spec's validation and WSL handoff for results and open cases.

## Real browser fixture (Mac or Windows/WSL)

After preparing a retained real fixture, run
`python3 /absolute/test-only/path/repo/tests/hermes-hud/serve_browser_fixture.py --fixture /absolute/test-only/path`
with the qualified Node on PATH. It starts an isolated controlled-provider installation
on UI 34010 / API 34011 / companion 8645. Stop it with Ctrl+C. The profile is retained
for inspection; it contains synthetic credentials only.

Run `tests/hermes-hud/browser_acceptance.cjs` with Playwright available through
`PLAYWRIGHT_MODULE`, and optionally `BROWSER_EXECUTABLE` pointing to Windows Edge.
Set `HUD_BROWSER_REPORT` to a private report path. Native Windows Node can load the
script and Playwright via the checkout's WSL UNC path. The script accepts only the
dedicated localhost:34010 fixture, never an owner HUD. It tests Chat, local Avatar,
owned history, rejected requests and Canvas branch/storage behavior. Use `--metadata /private/test-metadata.json` when serving, and pass that path as
`HUD_FIXTURE_METADATA` to include actual pending refresh/stop and inference-count checks.
For upgrade/rollback, use a separate owned checkout with `HUD_UPGRADE_REPO` and a known
prior `HUD_ROLLBACK_REF`; the harness refuses to modify its own source checkout.
The real-fixture driver copies the full HUD assets and links its existing development
node_modules; the reviewed patched subnet source is already in that synthetic repository.
Launch the browser server from the fixture copy so exact source paths qualify. For
installation/upgrade testing, use a full isolated Git worktree with its own dependencies.

`run_real_fixture.py` also runs `test_process_integration.py`: actual HUD/private MCP/
companion restarts, dropped admission, configured deadline, stop and failure boundaries.
Offline discovery skips these six integration tests deliberately; run the real driver
separately for their evidence.

`openclaw_browser_acceptance.cjs` is a separate, **live paid-provider** regression. It
requires `NETCLAW_LIVE_ACCEPTANCE=1`, an isolated OpenClaw HUD on 34020/34021 and explicit
operator authorization. It uses fresh owned conversations through the existing gateway;
it never changes the gateway configuration or contacts a device. See the Mac closure
record for the exact tested runtime and scope.

## WSL dependency qualification

Use a current uv with stable Python 3.14. Older uv selected a cached 3.14 alpha on the
acceptance host; native dependencies crashed before startup. The installer now refuses
prerelease interpreters. Preserve an existing unqualified test venv before recreating it.
The explicit companion install includes the pinned Anthropic SDK. Companion execution
disables lazy dependency installs and optional plugin discovery; a preexisting private
`netclaw-hud/hermes/installs` overlay is refused with recovery guidance. Preserve/move
that unexpected overlay only after stopping the affected companion. Do not modify an
owner Hermes environment or copy OpenClaw credentials into the test profile.
