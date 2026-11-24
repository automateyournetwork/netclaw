# Pass09 — evidence-bound counters in both local views

Status:progress. Worked T017/T018 and interim T030;no full task closes (14/30).
Implemented optional bounded counter requests in facts.local_graph invoking the
existing counter_rate helper. Catalog capture/source/parser/hash/owner binding,
strict JS validation,exact decimal delta,paired intervals and separate unknown
reasons survive into both inspectors. Includes sourced directional utilization,
capacity conflicts and stale/future counter ages. Fixed tall inspector stretching
the scene using independent desktop scrolling;selection resets panel scroll.
Narrow layout retains full evidence. Native normalization/policy/continuity are
still unqualified;source binding does not prove real readings or resets absent.

Files: scripts/genie-worlds/facts.py;viewer/network-graph.mjs,selection.mjs,
network.css,world.html;tests/genie-worlds/graph_bridge_test.py,network.test.mjs,
selection.test.mjs. Updated local-network contract,tasks/verification/resume,
HANDOFF and daily memory. Authority/control/acceptance/live packet unchanged.

Actual commands/results (all outputs retained in .spec200-local/pass-09/):
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:44/44 final;python-tests-final.txt. Earlier50/50 included six inherited duplicate tests,subsequently removed.
- Same Python command with `-p graph_bridge_test.py -v`:15/15 intermediate;bridge-tests.txt. Initial15 missing-parameter errors before implementation retained in bridge-before.txt.
- `NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" NETCLAW_BROWSER_EVIDENCE="$PWD/.spec200-local/pass-09" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/network.test.mjs tests/genie-worlds/selection.test.mjs tests/genie-worlds/manager.test.mjs`:14/14,no skips;node-tests-final.txt.
- Supported Node `--test tests/genie-worlds/selection.test.mjs`:5/5 after adding final reset/zero/conflict/future-age assertions;selection-tests-final.txt.
- Supported Node `--check tests/genie-worlds/network.test.mjs` and `--check scripts/genie-worlds/viewer/network-graph.mjs`:pass.
- `git diff --check`:pass;diff-check.txt. Spec Kit prerequisite and requirements15/15,quality39/39 checklists pass;optional Git hooks omitted per owner.

Synthetic screenshots at1280/820 plus actual visit inspected. Actual keyboard
navigation/release/blur/Escape/reset,selection,pan/zoom/fit and inert labels pass;
zero external requests/provider sessions. Generic block shapes/near-camera and
dense-port quality remain open. One screenshot after opening raw details showed
the panel scrolled to the bottom;selection now resets scroll and final screenshot
capture returns to panel top. No acceptance inferred from screenshot appearance.

Native GAIT reused existing private root/sticky/branch;gait-start.json,gait-end.json
and gait-log.json retain audit. Evidence manifest contains output/source hashes.
No device inventory under coordinator gate;no paid/device/cloud operation,owner
runtime modification,other-checkout edit,source commit,push,ticket or external
communication. Paid allowance and owner review remain pending. No authority edits.

Next: distinct router/switch3D forms with exact graph/port preservation,overview
and visit screenshot/navigation checks. Native binding and T020 fault cases remain
independent useful work;MCP/skill await actual T014;T029 requires owner acceptance.
