# Pass28 — native synthetic transport qualification

One bounded partial T016 unit; no task completion (14/30). Read prior result,
required context, current control/coordinator review; prerequisites and checklists
pass (15/15,39/39). Optional git hooks skipped. Existing GAIT/root/sticky reused;
device listing deferred under coordinator-only sequencing. No agent/loop/branch.

Added tests/genie-worlds/offline_native_transport.py and synthetic_terminal.py,
updated collector contract/tasks/verification/resume/loop handoff/progress/memory.
Installed pyATS loader and pinned Unicon plugin now exercise native_session with
a synthetic PTY peer that durably records every received line. Five allowlisted
reads each emit exactly once, with no setup/blank probes. Disable prompt refuses
without commands/enable. Exact selected server validator is compiled independently
without importing the operational server. No real device or SSH request occurs.

## Actual commands/results

Outputs retained in .spec200-local/pass-28/:

- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_native_transport.py /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/live-qualification/run-20261102T155125-625aeb/member-openclaw/netclaw-federation/native-operations/ff22d921-951b-4024-8eaa-b5547417c980/tool/source/pyats_mcp_server.py`: first failed on raw Unicon Connection is_connected property; diagnostic confirmed TypeError. Replaced only harness construction with pyATS loader. Final six cases pass; native-transport-first.txt, native-transport-diagnostic.txt, native-transport-final.txt retained. Existing pkg_resources warning remains.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:130/130 pass,17.617s; python-all.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7 pass,zero skips; node-core.txt.
- `git diff --check`:pass; whitespace.txt.

No UI change/new browser evidence. Private manifest binds outputs/source. Native
gait_record_turn and gait_log saved privately. Control digest is unchanged.
Startup reading was again too broad/truncated; no private control/config was
printed, subsequent reads bounded. Initial wrong source-directory lookup retained
in tool trail and corrected; no runtime file was changed.

## Limits and exact next step

Synthetic PTY proves this installed plugin's command behavior for supplied prompts;
it cannot establish strict SSH identity/authentication or real-device behavior.
Test transport is not permitted by production prepare_device. No adapter marker
or protected-grant change. Compose frozen prepare_device/native_session with
capture_context in collector child, preserving raw-before-cleanup, parse-after-clean
exit, parent deadline/unknown retirement and no retry/fallback. Native SSH and real
collection remain separate coordinator gates. T020 host/network/account recovery
also remains independent useful work.

Paid/owner pending; T014 gates MCP/skill,T029 actual owner,T030 feature handoff.
No provider/device call, authority/acceptance edit, source commit/push/publication,
existing-home/other-checkout change, ticket or external communication.
