# Pass24 — selected-runtime read and offline-parser boundary

One bounded partial T016 unit; no whole task closes (14/30). Read coordinator
review,pass23 handoff/result,authority/control and Spec Kit artifacts. Prerequisites
pass; requirements15/15 and quality39/39. Optional git hooks skipped per owner.
Existing branch/private GAIT root/sticky reused; device listing deferred under
explicit coordinator-only device sequencing. No authority/acceptance edits.

Changes: scripts/genie-worlds/native_read.py; tests/genie-worlds/native_read_test.py
and offline_native_read.py; collector contract,tasks,verification,resume,HANDOFF,
this pass note and daily memory. Fixed exact command/native read-policy intersection,
source digest/function origin,strict validator result,timeout/posture checks and
one raw execute. Detached offline parsers cannot reach the live device or retry.
This is a source seam only,not an installed collector adapter or proof of connection
setup safety. Frozen testbed/plugin/SSH identity/before-connect checks remain open.
Existing protected show-version-only code is untouched. No UI change.

## Actual commands/results

Outputs retained in .spec200-local/pass-24/:

- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p native_read_test.py -v`:8/8 pass,native-tests.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:107/107 pass,python-all.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7 pass,zero skips,node-core.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_native_read.py /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/live-qualification/run-20261102T155125-625aeb/member-openclaw/netclaw-federation/native-operations/ff22d921-951b-4024-8eaa-b5547417c980/tool/source/pyats_mcp_server.py`:pass,5 policy reads/5 parser classes/3 synthetic captures and offline parsers/zero real device calls,offline-native-final.txt.
- `git diff --check`:pass,whitespace.txt.

First offline harness run failed before capture because extracted native annotations
needed typing.List. Fixed harness; original offline-native.txt retained. Installed
Unicon deprecation warning retained. Initial direct gait_mcp import failed because
its module directory is not on venv sys.path; explicit installed module directory
fixed it. Native start/end,gait_status,gait_log retained privately. No browser check
needed for this Python-only change; no new browser or native-device claim.

## Gates and next step

No actual provider/device call,native connection,configuration,agent/loop/branch,
commit/push/publication,other-checkout change,ticket or external message. Paid/owner
remain pending;devices coordinator-only. T014 still gates MCP/skill integration;
T029 actual owner review;T030 feature handoff. Full T016/T019 remain unqualified.

Next: implement frozen single-device connection factory,validate minimal testbed,
selected source/plugin and strict endpoint/trust BEFORE connect,then qualify exact
emitted commands with synthetic native transport. Reuse this read/parse boundary;
never widen protected execute_once. T020 host/network/account recovery remains
independent. Owner preview stays frozen pass21; no refresh performed.
