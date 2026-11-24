# Pass27 — collector child capture context

One bounded partial T016 unit.14/30 unchanged; no whole task completed. Read prior
handoff/result and latest coordinator review; private control unchanged. Both
checklists pass (requirements15/15,quality39/39); prerequisite script passed and
optional git hooks skipped. Existing GAIT branch/root/sticky reused. Device listing
deferred under coordinator-only sequencing. No source branch/agent/loop created.

Changed scripts/genie-worlds/collector.py, tests/genie-worlds/collector_test.py,
contracts/collector.md,tasks/verification/resume,loop handoff/progress and memory.
Context support closes the child/raw-preservation ordering gap. Raw persists before
cleanup; parse follows clean cleanup. Durable lifecycle markers retain unknown
cleanup across exception,process exit/hang; affected device retires without replay.
Byte-budget refusal still cleans up; parser loss after clean cleanup is separate.
Existing capture_once compatibility retained. No actual native adapter exposed.

## Actual commands/results

Outputs retained privately in .spec200-local/pass-27/:

- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p collector_test.py -k context -v`: initial3 tests failed before implementation (before.txt); then3/3 passed (context.txt). Two more fault tests were added before final full suite.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:130/130 pass,17.352s (python-all.txt).
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python -m unittest discover -s tests/genie-worlds -p collector_test.py -k context -v`:5/5 pass (native-python.txt); synthetic adapters in installed interpreter, not actual native transport.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7 pass,zero skips (node-core.txt).
- `git diff --check`:pass (whitespace.txt).

No UI change or new browser qualification. Private manifest hashes outputs and
changed source. Native gait_record_turn/gait_log retained locally; no source commit.

## Remaining gates/next step

Qualify native emitted commands with independent synthetic native transport, then
bind frozen preparation/native_session into capture_context inside the child.
Existing native policy and strict endpoint identity remain required; this pass
cannot qualify real transport or device data. T020 host/network/account recovery
also remains actionable. No paid/provider/device call,authority or acceptance
change,source commit,push/publication,other-checkout/existing-home modification,
ticket or external communication. Paid/owner pending;devices coordinator-only.
T014 gates installed MCP/skill,T029 actual owner review,T030 feature handoff.
