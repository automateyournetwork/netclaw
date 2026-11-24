# Pass07 — private normalized graph bridge

Status:progress. Worked T017/T018 and per-pass T030; no tasks closed (14/30).
Implemented facts.local_graph over resolve_neighbors plus a bounded observation
catalog. Source/hash/parser/device/outcome/interval bindings are checked. Graph
retains typed unresolved remote claims,conflict/expiry/staleness and per-device
read coverage,including missing capture hash and unknown capture. JS validates
and freezes records; shared inspector exposes them in both exact SVG/local3D.
Only resolved links have geometry; discovery cannot supply interface health.

Files: scripts/genie-worlds/facts.py,viewer/network-graph.mjs,viewer/selection.mjs;
tests/genie-worlds/graph_bridge_test.py (new),network.test.mjs. Updated local-network
contract,tasks/verification/resume,HANDOFF and current daily memory. No changes
to control,authority,owner acceptance,paid packet,other checkout or existing homes.

Actual verification (supported owner-specified Node24.19;Python3.12.12):
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:39/39 before final proof validation tightening; python-tests-final.txt.
- Same Python `-p graph_bridge_test.py -v`: final5/5 after tightening; bridge-tests-final.txt. Actual JS localGraph/graphLayout validates Python output and freezes nested discovery.
- `NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" NETCLAW_BROWSER_EVIDENCE="$PWD/.spec200-local/pass-07" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/network.test.mjs tests/genie-worlds/selection.test.mjs tests/genie-worlds/manager.test.mjs`:12/12,zero skips; node-tests-final.txt.
- `git diff --check`:pass;diff-check.txt.

Actual synthetic screenshots inspected: exact1280/820,world1280 and visit close-up.
Readable claims,full interface labels,failed/unknown capture and expandable hashes;
no horizontal overflow. Actual movement/release/blur/Escape/reset,selection,
pan/zoom/fit and inert-label checks pass. Zero external requests/provider sessions.
The Python→JS seam and separate browser fixture are distinct evidence; no native
private pipeline-to-browser end-to-end claim. Block geometry,large/dense port scenes
and near-camera labels remain later refinements. Counters stay unavailable.

Failures preserved: expected missing local_graph in bridge-before.txt; initial
mismatch fixture reused an identical proof (thus not rejected),corrected to a
real hash mismatch; bridge-tests.txt retains failure. Removed accidental inherited
neighbor test duplication before final runs. No failure history rewritten.

Private evidence .spec200-local/pass-07/ contains outputs,screenshots,browser result,
evidence-manifest.json and native gait-start/gait-end/gait-log. Native GAIT existing
root/sticky/branch reused,start19bf9080. Both checklists pass15/15 and39/39;Spec Kit
prerequisite passes. Optional Git hooks omitted by owner request. No device inventory
under coordinator-only restriction;no paid/provider/device/write/cloud operations,
tickets,communications,source commits,push or publication. Paid/owner pending.

Next: synthetic evidence-bound interface-state disagreement and counter-rate graph
fields/overlay using existing counter_rate. Native parser/capture policy and real
collection remain unqualified; device operations belong to coordinator. T014 still
gates MCP/skill/native integration;T029 needs actual owner;T030 remains interim.
