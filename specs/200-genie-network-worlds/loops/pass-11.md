# Pass11 — focus-loss release recovery

Scope: one bounded T020 recovery unit following coordinator follow-up;T030 interim
notes/audit. Existing200 checkout/branch retained. No complete task claimed.

Changed scripts/genie-worlds/worker.mjs: ordinary release catches transport failure
and enters unknown plus immediate completion. Each attempted key release has a
durable marker; rejected key identity is retained without transport text. The
uncertain send is not replayed. Existing bounded receiver/stop/usage rules stay.
Changed tests/genie-worlds/recovery.test.mjs: four synthetic cases cover rejected
release with/without late terminal, normal release continuing navigation, and
stalled release plus late rejection after cleanup. Updated control contract,
tasks/verification/resume, HANDOFF and daily memory; authority untouched.

Actual commands use:
`NODE=/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node`
with NETCLAW_TEST_TMP in this checkout's private pass11 directory.

- `$NODE --test --test-name-pattern='focus-loss release' tests/genie-worlds/recovery.test.mjs`: two failures before fix (active instead of unknown). The initial teardown registered after fixture cleanup also caused database-closed asynchronous errors; retained release-before.txt. Corrected test cleanup drains inside try/finally.
- `$NODE --test tests/genie-worlds/recovery.test.mjs`:12/12 pass,0skips, no asynchronous errors; recovery-final.txt.
- `NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' $NODE --test --test-concurrency=1 tests/genie-worlds/*.test.mjs`:48/48 pass,0skips, including actual isolated Chrome and owned child SIGSTOP/SIGKILL recovery; node-tests-final.txt.
- `git diff --check`: passed. Spec Kit prerequisites resolve existing200; requirements15/15 and quality39/39 complete. Optional Git hooks skipped as instructed.

Private evidence .spec200-local/pass-11/{release-before.txt,recovery-final.txt,
node-tests-final.txt,manifest.json,gait-start.json,gait-end.json,gait-log.json}.
No UI source change; full browser regression passed but no new visual acceptance
or screenshots claimed. Native GAIT reuses existing root/sticky/branch.

Remaining: T020 recording/upload and broader host/network faults; native collector
binding/normalization/continuity, real local facts, Google live proof, native
NetClaw, owner acceptance.14/30 remains. Device operations coordinator-only;
paid_generation and owner_acceptance pending. No provider/device/credential
operation, owner runtime change, authority edit, source commit or external message.

Exact next step:T018 distinct router/switch forms and close-up labels in the
local3D renderer, preserving geometry endpoints; exercise synthetic overview,
walkthrough visit, key release and reset at1280/820, inspect actual screenshots.
