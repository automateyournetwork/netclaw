# Pass26 — native connection lifecycle composition

One bounded partial T016 unit.14/30 unchanged; no whole task completed. Prerequisite
script passed,requirements15/15 and quality39/39; optional git hooks skipped.
Latest coordinator review and prior result read; control retained unchanged.
Existing GAIT branch/root/sticky reused; device listing deferred under explicit
coordinator-only sequencing. Startup context output was overly broad/truncated;
subsequent private reads were bounded. No further private values copied to notes.

Changed scripts/genie-worlds/native_session.py and tests/genie-worlds/native_session_test.py;
collector contract,tasks,verification,resume,HANDOFF,this note and daily memory.
The internal context checks source/read policy and frozen connection options
before connect, reserves a new private log, performs one connect/read, yields raw
for preservation before cleanup and attempts one disconnect after partial failures.
Primary failure survives a second cleanup failure with a bounded note. Cleanup
failure after preservation cannot report success. No retries or grant widening.

## Actual commands and retained results

All outputs retained under .spec200-local/pass-26/:

- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p native_session_test.py -v`:8/8 pass,native-session.txt;initial missing-module failure before.txt retained.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:125/125 pass in16.056s,python-all.txt,after final secondary-failure note change.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python -m unittest discover -s tests/genie-worlds -p native_session_test.py -v`:8/8 pass,native-python.txt. This executes synthetic doubles in the installed interpreter; it is NOT native transport qualification.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7 pass,zero skips,node-core.txt.
- `git diff --check`:pass,whitespace.txt.

Tests cover raw preservation ordering,read-policy refusal before I/O,existing/
symlink/hardlink/public log refusal,partial connect failure,execute timeout with
no retry,unsafe post-connect posture,primary preservation plus cleanup failure,
and cleanup failure after preserved raw. No UI change or new browser claim.
Native GAIT start/end/log and private artifact hashes retained in this directory.

## Remaining gates and exact next step

This synchronous internal context has no adapter marker or launcher; it must run
inside the collector-owned child/deadline boundary. Native connect/read/disconnect
can block. Local cleanup is not proof of remote termination. The native logger
reopens the reserved log path; caller must exclusively own its private directory.
Next qualify exact native command emission via synthetic native transport, then
compose child/raw-persistence/deadline retirement. Real endpoint/capture and
four-device identity qualification remain gated. T020 host/network/account tests
are independent useful work. T016 stays open; T030 interim audit only.

Paid/owner pending; devices coordinator-only. T014 still gates native MCP/skill,
T029 requires actual owner review,T030 feature handoff. No actual provider/device
call,branch/agent/loop,source commit,push,publication,other-checkout or existing-home
change,ticket or external communication. Owner preview remains frozen pass21.
