# Pass14 — detailed collector scheduling

One bounded T016 source unit with T017 coverage guard and T030 interim audit.
Changed scripts/genie-worlds/{collector,facts}.py,tests/genie-worlds/collector_test.py
and contracts/collector.md. Updated verification,resume,tasks,memory and HANDOFF.
No checkbox closes;14/30 complete. No native adapter/read-policy qualification.

## Pass14 — explicit detailed capture scheduling

Added an explicit detailed profile to collector.py: six fixed reads per device,
maximum24 across four devices, two concurrent children,30s/read,240s overall and
shared8MiB raw budget. Initial profile remains default with180s ceiling. Second
show interfaces sample starts at least10s after the first child's capture/parse
completion; waiting occupies no child and the overall deadline still applies.
Request/observation records retain profile,command_index and sample_index.
Capture-once,unknown-device retirement and no retry behavior are unchanged.

facts.normalize accepts the detailed envelope but does not guess native CDP or
interface parser schemas. Observed additional payloads produce explicit unknown
normalization_unqualified facts; failed/empty/raw-only coverage remains distinct.
No neighbor,rate or continuity proof is manufactured. Native adapter/extraction,
identity binding and collector-to-graph assembly remain unqualified.

Actual checks: Python3.12 full discovery48/48pass; supported Node core7/7pass;
whitespace check passed. Four new tests cover exact24reads/actual>=10s timing,
parser failure without recapture,deadline during the gap,closed limits and unknown
normalization (the timing and parser case shares one test). Initial preimplementation
run failed with3expected unsupported-profile errors and is retained; intermediate
47/47passed before strengthening interval/unknown assertions. No UI change or
new browser qualification is claimed. Evidence:.spec200-local/pass-14/ contains
collector-before.txt,python-tests.txt,python-tests-final.txt,node-core.txt,
whitespace.txt,manifest.json and native GAIT receipts/log. Source/control hashes
are retained privately. No task closes;14/30. T030 is interim audit only.

No device operation under coordinator-only gate;paid generation and owner acceptance
remain pending. Authority/acceptance records and existing homes untouched. No
branch,agent,loop,source commit,push,publication,other-checkout change,ticket or
external communication. Next unit: qualify native offline parser field extraction
from synthetic IOS-XE CDP/show-interfaces fixtures and bind it to the existing
identity/counter/graph contracts. Preserve unknown continuity and no device calls.

Actual commands and outcomes:
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p collector_test.py -v`:before implementation15tests,3expected errors; retained collector-before.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:final48/48pass (initial47/47 before stronger coverage).
- `NETCLAW_TEST_TMP=$PWD/.spec200-local/tests /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7pass,0skip.
- `git diff --check`:pass.
- `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`:existing200resolved; requirements15/15,quality39/39. Optional Git hooks omitted per owner.

Native GAIT reuses existing private root/sticky/branch with installed gait_mcp and
PYTHONDONTWRITEBYTECODE=1; start/end and gait_log retained under pass14. No fresh
inventory under coordinator device gate. Startup context reads were overbroad and
truncated; next pass should bound output and parse private references locally.
