# Pass25 — frozen native device preparation

One bounded partial T016 unit; no whole task closes (14/30). Prerequisites pass;
requirements15/15 and quality39/39. Latest coordinator review/control retained;
optional git hooks skipped. Existing branch/private GAIT root/sticky reused.
Device listing deferred under the explicit coordinator-only device sequencing.

Changes: scripts/genie-worlds/native_connection.py;
tests/genie-worlds/native_connection_test.py and offline_native_connection.py;
collector contract,tasks,verification,resume,HANDOFF,this note and daily memory.
Frozen minimal JSON/endpoint/trust validation and pinned IOS-XE/IOL native policy
run before pyATS topology load. Scoped ENV credentials,inert names/types,no extra
hooks/classes/connections,loaded identity/platform/freshness/inherited credentials
and rechecked connection options are implemented. Existing protected argument and
show-version execution code is unchanged. No connect/capture/adapter marker exists.

## Actual commands/results

Outputs retained in .spec200-local/pass-25/:

- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p native_connection_test.py -v`:10/10 pass,native-connection-qualified.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:117/117 pass,python-all-final.txt. Final native-object-reference correction was then verified by all10 affected tests and the installed-loader check.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7 pass,zero skips,node-core.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_native_connection.py`:pass,installed25.2 dependency/source checks plus synthetic loader/identity/options,zero socket connects;offline-native-qualified.txt.
- `git diff --check`:pass,whitespace.txt.

The initial regression failed because the module did not exist (before.txt).
Initial installed check exposed pyATS inserting inherited connection Credentials;
these now must match the native testbed credentials while explicit input connection
credentials remain forbidden. Attempted deepcopy of that native object failed;
retaining its native reference fixed the installed check. Both failed outputs and
bounded synthetic diagnostics remain; the installed deprecation warning remains.
No UI change or new browser qualification. Native GAIT/start/end/gait_log retained.

## Gates and next step

Preparation only; source tests do not establish actual connection/no-setup command
behavior. Next implement process-owned connect→single capture→disconnect using
this preparation and native_read.py, with private connection logs and source/read
validation before connect. Qualify exact emitted commands through a synthetic
native transport and preserve unknowns/no retry. Do not expose a real adapter
qualification marker until those checks pass; do not widen protected execute_once.

Paid/owner pending;devices coordinator-only. No actual provider/device call,agent,
loop,branch,commit/push/publication,other-checkout/home change,ticket or external
message. T014 gates MCP/skill,T029 actual owner review,T030 feature handoff.
Owner preview remains coordinator-owned frozen pass21. T020 host/network/account
recovery remains independent useful work. No authority/acceptance record changed.
