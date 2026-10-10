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
