# Pass10 — T020 unknown outcome cleanup

Status:progress. Worked T020 and interim T030;14/30 complete,no checkbox closed.
Read authority/control,current memory,Spec Kit context and coordinator review.
Requirements15/15 and quality39/39 passed. Existing GAIT root/sticky/branch reused;
no branch,agent,loop,Git commit or optional Git hook. Device listing withheld under
explicit coordinator-only device gate;no new device-state claim.

Changes: scripts/genie-worlds/worker.mjs separates durable unknown from local
completion;bounds pending awaits,allows stop/heartbeat past blocked controls,
attempts completion independently of key release,and keeps one receiver available
for a terminal receipt during grace. Grace expiry requests best-effort cancellation
and ends local work without settling usage. Late create cannot submit setup or
change the closed ledger. scripts/genie-worlds/manager.mjs reaps owned unresponsive
children after6500ms before ledger/lock teardown and handles IPC send errors.
Added recovery.test.mjs and actual SIGSTOP/SIGKILL drill in manager.test.mjs.
Updated tasks/verification/resume,HANDOFF and daily memory;no authority edit.

Actual commands/results (supported Node absolute path below):
- `NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/recovery.test.mjs tests/genie-worlds/worker.test.mjs tests/genie-worlds/manager.test.mjs tests/genie-worlds/provider.test.mjs`:19/19 initial affected checks;affected-tests.txt.
- `NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" NETCLAW_BROWSER_EVIDENCE="$PWD/.spec200-local/pass-10" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/*.test.mjs`:42/42,zero failures/skips;node-tests-final.txt. Includes actual isolated Chrome playback/navigation/event/recording/stop and local graph navigation;UI source unchanged.
- `NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/recovery.test.mjs`:8/8 final;recovery-tests-final.txt. Last two cases added after broad suite;no implementation edit after broad pass.
- Supported Node `.spec200-local/pass-10/coordinator-worker-loss-probe.mjs`:copied original reproducer now completes after one completion request,zero provider calls. Original failed coordinator evidence untouched. Its fake ledger does not qualify usage;new real SQLite tests do.
- Supported Node `--check scripts/genie-worlds/worker.mjs` and `--check scripts/genie-worlds/manager.mjs`:pass. `git diff --check`:pass,diff-check.txt. Spec Kit prerequisite command passes.

New tests cover rejected control,stalled key/complete/receive/cancel,stalled setup,
manager heartbeat loss,never-returning creation,late creation,late terminal with
intervening frame and missing usage,alternate-provider admission holds,and real
frozen child reaping. No initial test failure in this pass;coordinator's original
qualified failure remains retained. Browser assets/screenshots are synthetic.
No live proof,private data upload,existing-home change,other-checkout change,
ticket,external message,commit,push,publication or version change.

Private evidence and source hashes: .spec200-local/pass-10/manifest.json.
Native gait_record_turn and gait_log outputs: gait-start.json,gait-end.json,
gait-log.json in that directory. Existing private control SHA256 remains
`db1e8fb2b97f6ccae38c5bc2283b05a38c6396b2b44e8ccc69b7c17e8cbdcf7d`.
Paid and owner acceptance pending;device operations coordinator-only. T020 is
partial:recording/upload failures and broader host/network faults remain. T014
still gates MCP/skill/native acceptance;no live packet or acceptance was edited.

Next bounded unit: T018 distinct router/switch forms and near-camera label checks,
using exact graph/physical interface endpoints;verify overview and actual visit at
1280/820. Alternatively add T020 recording/upload-fault drills if geometry is
blocked. Retain all collector/native and live acceptance limits.
