# Spec 148 — Windows / WSL Ubuntu acceptance handoff

**Status:** original Mac-to-WSL handoff, retained for reproduction. WSL continuation
results and remaining gates are in [mac-return-handoff.md](mac-return-handoff.md).
Not release-complete. Read [validation.md](validation.md)
first. Federation remains spec 149. The Mac owner's running HUD was not restarted.

## Transfer the exact implementation

Branch: `148-hermes-hud-integration`. **Implementation commit: db5a1b0f3efdf87e469158337a2d1dfb770be230**.
A subsequent documentation-only commit records this handoff and audit. Transfer the
provided local Git bundle, `/tmp/netclaw-spec148.bundle`, to your Windows machine;
the branch has **not** been pushed. The bundle contains committed repository history,
not ignored `.env`, private homes, credentials, transcripts, local venvs or dependencies.

From Ubuntu on WSL2, store the checkout and private runtime state under the Linux home
filesystem. You can read the bundle from Windows Downloads, but do not keep the runtime
under `/mnt/c`.

```sh
mkdir -p "$HOME/src"
git clone --branch 148-hermes-hud-integration /mnt/c/Users/YOUR_USER/Downloads/netclaw-spec148.bundle "$HOME/src/netclaw-148"
cd "$HOME/src/netclaw-148"
git status --short
git log -2 --oneline
git merge-base --is-ancestor db5a1b0f3efdf87e469158337a2d1dfb770be230 HEAD
```

If using an existing checkout, fetch the bundle into a separate review branch and use a
new worktree; preserve unrelated work. Do not reset or clean the owner's checkout.
Record `git rev-parse HEAD` with every report. The Windows Codex session should read
the constitution, spec, plan, tasks and this handoff, then start its GAIT audit session.

## Prerequisites and deterministic checks

Target: Windows 11, WSL2, Ubuntu 24.04 x86_64. Record actual versions with `wsl --version`
in PowerShell and `uname -a`, `lsb_release -ds`, `node --version`, `python3 --version`,
`uv --version` inside WSL. Use Node 24.19+ below 25 (Mac tested 24.19.0), or 26.1+;
Git, uv, npm and Python 3 must be available. No Docker or production device credentials
are needed for the controlled fixture. Downloading the pinned sources and dependencies
requires internet.

```sh
npm --prefix ui/netclaw-visual ci
python3 scripts/run-contract-tests.py --suite hermes-hud --prepare --strict-capabilities
python3 tests/hermes-hud/run_real_fixture.py --workdir "$HOME/.cache/netclaw-148-fixture"
npm --prefix ui/netclaw-visual test
npm --prefix ui/netclaw-visual run test:canvas
npm --prefix ui/netclaw-visual run test:bundle
bash tests/installer/run-tests.sh
python3 scripts/check-fastmcp-compat.py
python3 scripts/verify-catalog-coverage.py
python3 scripts/verify-inventory-counts.py
python3 scripts/verify-spec-artifacts.py
git diff --check
```

Expected: no failures; the offline suite has one explicit real-agent skip which the
separate required real fixture must pass. Missing prerequisites are not passing evidence.
The real fixture uses a controlled local provider and reviewed real subnet MCP; no paid
provider or owner's home. Keep full logs private; append only sanitized summaries here.

## Isolated installation and actual provider

Use a dedicated test home with a space in its path and a separate selection descriptor.
Have the Hermes CLI available and configure this profile through its normal setup.
Do not copy OpenClaw credentials or overwrite an existing Hermes profile.

```sh
export NETCLAW_RUNTIME=hermes
export HERMES_HOME="$HOME/netclaw-148 acceptance/Hermes Home"
export XDG_CONFIG_HOME="$HOME/netclaw-148 acceptance/config"
mkdir -p "$HERMES_HOME" "$XDG_CONFIG_HOME"
chmod 700 "$HERMES_HOME" "$XDG_CONFIG_HOME"
hermes setup
# Enter provider credentials privately in setup / the selected home's .env.
./scripts/install.sh --runtime hermes --add "subnet-calc hermes-hud"
./scripts/netclaw hud select hermes "$HERMES_HOME"
./scripts/netclaw hud status
```

Ensure the selected home contains the reviewed subnet skill. If the existing installer
has not synchronized it, copy only that public reviewed skill into the **test** profile:

```sh
mkdir -p "$HERMES_HOME/skills/subnet-calculator"
cp workspace/skills/subnet-calculator/SKILL.md "$HERMES_HOME/skills/subnet-calculator/SKILL.md"
```

Use three unused ports if an owner HUD is already running. Defaults are UI 3000, API
3001 and companion 8643; this handoff uses 34000, 34001 and 8644 to avoid collision.

```sh
export HUD_UI_PORT=34000 HUD_PORT=34001 NETCLAW_HERMES_HUD_PORT=8644
./scripts/netclaw hud
```

The launcher starts a dedicated protected Hermes companion, HUD API, and Vite UI.
It does **not** attach the browser to the ordinary Hermes gateway. Leave the launcher
running in this terminal. In another WSL terminal with the same profile selection:

```sh
./scripts/netclaw hud status
"$HERMES_HOME/python-runtimes/hermes-hud-agent/venv/bin/python" \
  tests/hermes-hud/live_acceptance.py --url http://127.0.0.1:34001 \
  --run --output "$HOME/netclaw-148-live-report.json"
```

The explicit `--run` sends five provider turns and may incur provider charges. Expected:
five completed checks, remembered colour, a completed correlated `subnet_calculator`
invocation for `192.0.2.0/28`, and actual model/usage metadata when the provider supplies
it. Review the fourth answer for the correct **14 usable hosts**. Verify the installed
skill is qualified in status. Missing provider counters must remain unknown. Save the
redacted JSON; do not save keys, raw reasoning, full private config or unrelated chats.
If any result is unknown, inspect status instead of rerunning the same work blindly.

## Required host/browser cases

Open **http://localhost:34000/** in a normal Windows browser. The Mac Chrome automation
was blocked before navigation, so a real walkthrough is still required.

| Case | Expected evidence |
|---|---|
| Windows-to-WSL loopback | HUD and API proxy load; browser receives its private installation cookie; no companion key in browser requests/storage |
| Trusted origin | Normal localhost requests work; cross-site Origin and foreign Host requests are denied; no wildcard bind or auth relaxation to make WSL work |
| Chat / local Avatar | Five-turn context survives view changes with zero extra POSTs on switching; actual model attribution; unsupported model/effort controls disabled |
| Canvas | Two branches preserve their respective creation-point context; no later parent/sibling leakage; graph, drafts and quotes survive refresh |
| Unsupported attachments | Submission refuses before admission and preserves the draft; no provider/tool invocation |
| Owned history | Reopen owned conversation; second browser profile cannot read its request/history; raw session IDs and legacy global routes fail |
| Selected installations | Hermes and OpenClaw cookies/storage remain separate; explicit switch rejects stale active-page submissions; old OpenClaw data remains preserved |
| Panels | Hermes metadata only; usage unavailable when absent; no inference from panel reads; federation, hosted Avatar, budget writes and APPLY reject server-side |
| Ports / lifecycle | Each occupied port refuses without killing its owner; Ctrl+C stops only launcher children; fresh shell/custom CWD uses persisted selection |
| Linux permissions | Descriptor/identity/auth/DB regular private files and directories; symlink/shared-readable fixtures fail; no private state under `/mnt/c` |
| Restart / uncertainty | Restart only test-owned HUD/bridge/companion processes; pending nonce survives; status observes without another submit; unknown remains unknown if no evidence |
| Stop / approval | Stop is cooperative, not immediate success; exact once/deny only; stale, bulk and lasting grants reject. If no eligible run can pause, record that path unverified |
| Late result / fresh conversation | Status can recover completed output; acknowledgment of uncertainty enables a fresh conversation without claiming cancellation or replay |
| Provider/auth/source failures | Missing config, rejected credentials, stopped companion and intentionally changed fixture source yield specific failure; no heuristic successful reply |
| Upgrade / rollback | Snapshot synthetic YAML/env/registrations/skills/bindings/browser work; repeat install and HUD upgrade, compare hashes; rollback restores supported old data without v2 downgrade writes |
| Existing OpenClaw | Supported launch, contextual Chat, Canvas, local Avatar, models, panels and Terminal Intent still function on the existing qualified runtime |

Run failure injections only against synthetic test homes/processes. Preserve hashes and
counts, not secret contents. For a new shell, set the same isolated `XDG_CONFIG_HOME`;
unset `NETCLAW_RUNTIME` and `HERMES_HOME` to prove descriptor selection works, then use
the absolute checkout path from another CWD. Restore these variables for explicit setup.

For upgrade, run `scripts/upgrade-hud.sh --check`, then `--apply` in the test selection;
neither should restart the owner gateway. Keep the browser origin unchanged for storage
checks. Finish with Ctrl+C in the test launcher terminal. Do not use broad `pkill` or
remove owner runtime directories.

## Native Windows check (separate from WSL)

In native PowerShell, with a qualified Node installed and the repository accessible,
set `$env:NETCLAW_RUNTIME = 'hermes'` and invoke each of `Start-NetClaw.ps1`,
`Start-NetClaw-Canvas.ps1`, and `Restart-NetClaw-API.ps1`. Each must fail early with
Ubuntu/WSL guidance, without starting/stopping OpenClaw or changing its configuration.
Record process/config baselines first and clear the test environment afterward. Native
Windows Hermes is not supported. Native OpenClaw's existing launch path must still work;
do not infer Windows ACL behavior from POSIX tests.

## Closure

Append host versions, exact commit, commands, PASS/FAIL/UNVERIFIED results, provider/model
identity, tool-policy/source manifest hashes, preservation hashes and sanitized browser
observations to `validation.md`. Fix failures and rerun affected tests. Do not close from
unit results alone. Complete T052, T053 and T055; the Mac live-provider gate remains
unverified unless it is actually run on Mac or the owner explicitly revises that criterion.
Then reconcile main, prepare the minor release via the repository release process,
complete T056, update task/audit records, and report readiness. No automatic push, PR,
merge or publication is authorized by this handoff. Return to Mac for spec 149 as requested.
