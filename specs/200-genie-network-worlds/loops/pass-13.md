# Pass13 — recording/upload failure evidence

One bounded T020 unit, with T030 interim audit. No task closes;14/30 remain complete.
Changed scripts/genie-worlds/{ledger,manager}.mjs,viewer/viewer.mjs and
 tests/genie-worlds/{recording,manager,recovery}.test.mjs. Added closed durable
failure records, stop independent of report/upload waits,3s upload timeout,
no failed-chunk replay and persistent readable failure notice. Actual sink failure
also requests stop; failed artifacts cannot masquerade as recorded media.
Unknown/provider receipt/usage rules are unchanged and directly regression-tested.

Actual commands (supported Node prefix `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node`):
- `--test --test-concurrency=1 tests/genie-worlds/*.test.mjs`:54/54pass,0skip.
- `--test --test-concurrency=1 tests/genie-worlds/manager.test.mjs tests/genie-worlds/recovery.test.mjs`:19/19pass.
- `--test --test-concurrency=1 tests/genie-worlds/recording.test.mjs tests/genie-worlds/browser.test.mjs`:final5/5pass,0skip after final wording.
- `--test tests/genie-worlds/browser.test.mjs`:1/1pass after an earlier normal playback timeout.
- `--test --test-name-pattern='failure: recorder' tests/genie-worlds/recording.test.mjs`:final screenshot capture check (visual-final.txt).
- `--check scripts/genie-worlds/viewer/viewer.mjs`:pass.
- `git diff --check`:pass.
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`:existing200 resolved; requirements15/15,quality39/39. Optional Git hooks skipped.

Browser runs use NETCLAW_BROWSER_EXECUTABLE=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome,
NETCLAW_TEST_TMP=$PWD/.spec200-local/tests and NETCLAW_BROWSER_EVIDENCE=$PWD/.spec200-local/pass-13.
Synthetic constructor/recorder/rejected-upload/stalled-upload tests have no external
requests or page errors; each retains one operation and real fixture terminal.
Backend tests separately retain unknown and terminal-without-usage holds across
provider labels, and actual filesystem failure evidence across ledger reopen.

Initial old-source constructor check timed out. Initial post-fix test incorrectly
matched “no terminal receipt”; tightened to actual terminal state. One normal
playback timeout remains retained; independent rerun/full suite passed. First820
full-page screenshot had duplicated raster content; retained in initial-visual/,
then recaptured viewport after resize/render with single-heading assertion.
No live-provider failure qualification or acceptance is claimed.

Private outputs,synthetic screenshots,hash manifest and native GAIT start/end/log:
.spec200-local/pass-13/. Existing root/sticky/branch reused; no branch creation.
No paid call,device read/write,authority edit,agent/loop,source commit,other-checkout
change,ticket or external communication. T029 remains owner-only;T030 interim.
Source changes stale paid manifests; coordinator owns review. Broader T020 host/
network/account-boundary cases and native/live integration remain open.

Next: implement detailed-profile finite scheduling in collector.py with synthetic
adapter tests (six commands/device,two samples>=10s apart,240s overall,8MiB),
then wire actual normalization caller without inventing continuity or native policy.
Real device operations stay coordinator-only. T014 still gates MCP/skill/native proof.
