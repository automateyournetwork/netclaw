# Pass12 — recognizable local forms and visit framing

One bounded T018 quality unit; T030 interim audit. Existing200branch retained.
Changed viewer/world-geometry.mjs,world.mjs,world.html and network.test.mjs:
role-specific chassis/emblems, exact graph ports, face clipping, selected label
bounds, and visit framing. New assertions preserve endpoints/immutability, clip
crossing faces, reject fully hidden faces, and test browser visit framing at both
1280/820. No device/provider data or operations used.

Visual review caught rear-switch camera inside foreground router and a cropped
router visit; both corrected. Initial screenshots retained in private initial-visual/.
Free navigation collision, dense graph readability and native graph acceptance
remain unqualified. Full interface identity/provenance stays outside pixels.

Actual commands:
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/network.test.mjs tests/genie-worlds/selection.test.mjs tests/genie-worlds/manager.test.mjs`, with NETCLAW_TEST_TMP=$PWD/.spec200-local/tests, NETCLAW_BROWSER_EVIDENCE=$PWD/.spec200-local/pass-12 and NETCLAW_BROWSER_EXECUTABLE=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome: final16/16pass,0skip; node-tests-final-fit.txt. Earlier16/16runs did not catch the visually detected framing defect; final run adds explicit bounds.
- Same supported Node `--check scripts/genie-worlds/viewer/world.mjs`:pass.
- `git diff --check`:pass.
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`: existing200resolved; requirements15/15,quality39/39. Optional Git hooks skipped as instructed.

Evidence: .spec200-local/pass-12/{node-tests.txt,node-tests-final.txt,
node-tests-final-fit.txt,local-world-*.png,network-browser-result.json,
manifest.json,gait-start.json,gait-end.json,gait-log.json}. Native GAIT existing
root/sticky/branch reused. No source commit/branch creation/agent/loop/ticket or
external communication. No authority/owner-acceptance change. Control unchanged;
paid/owner pending and device operations coordinator-only. No full task closes.

Updated tasks,verification,resume,local-network contract,HANDOFF and daily memory.
Next: T020 actual synthetic recording/upload fault injection, stop/failure evidence
and durable unknown/usage holds, without repeating fixed pass10/11 recovery cases.
