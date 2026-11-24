# Pass08 — state and discovery timing in local views

Status:progress. Worked T017/T018 and interim T030;no complete task closes (14/30).
Added separate state_evidence_id/discovery_evidence_id to the private graph bridge
and closed JS validation. Shared exact SVG/local3D inspector now shows down or
conflicting interface snapshots before/after/overlapping discovery captures,with
microsecond precision and freshness. Both source commands and proofs are visible.
Discovery certainty and geometry remain unchanged. Empty state proof dictionaries
cannot establish health. No inferred comparison for older graphs without pointers.

Files: scripts/genie-worlds/facts.py,viewer/network-graph.mjs,viewer/selection.mjs;
tests/genie-worlds/graph_bridge_test.py,network.test.mjs,selection.test.mjs.
Updated local-network contract,tasks/verification/resume,HANDOFF and daily memory.
No authority/control/acceptance/live-packet,owner-home or other-checkout edits.

Actual checks (Node24.19 and installed native GAIT Python3.12):
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:41/41 before final empty-proof tightening; python-tests-final.txt.
- Same Python command with `-p graph_bridge_test.py -v`:final6/6 after tightening; bridge-tests-final.txt. Includes actual JS validation/selection of Python graph.
- `NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' NETCLAW_TEST_TMP="$PWD/.spec200-local/tests" NETCLAW_BROWSER_EVIDENCE="$PWD/.spec200-local/pass-08" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/network.test.mjs tests/genie-worlds/selection.test.mjs tests/genie-worlds/manager.test.mjs`:13/13,no skips; node-tests-final.txt.
- Supported Node `--check` on selection.mjs and network.test.mjs:pass.
- `git diff --check`:pass;diff-check.txt.

Synthetic screenshots inspected for exact1280/820 and world1280/820. Readable
state/discovery timing and source commands;no horizontal overflow. Actual keyboard
movement,release,blur,Escape,reset,selection,pan/zoom/fit and inert labels pass.
Browser evidence reports zero external requests/provider sessions. These synthetic
checks do not qualify a native pipeline or actual network state. Simple block
geometry,dense-port/near-camera refinement,counters and native parser semantics
remain open. No test failures this pass;initial/final successful outputs retained.

Private .spec200-local/pass-08/ contains actual outputs,screenshots,browser result,
evidence-manifest.json and native gait-start/gait-end/gait-log. Existing native
root/sticky/branch reused;no branch creation. Requirements15/15 and quality39/39
checklists pass;Spec Kit prerequisite passed. Optional Git hooks omitted per owner.
No device inventory under coordinator-only restriction. No paid/device/cloud call,
source commit,push,publication,ticket or external communication. T029 owner and
T030 feature handoff remain open. Authority checked without editing control.

Next: evidence-bound counter results in local_graph/localGraph/shared inspector.
Bind sample/continuity/capacity catalog proofs and retain exact delta,intervals and
unknown reasons;verify with synthetic cross-language/browser tests. Coordinator
owns device gate and exact paid trial. No native or live acceptance claim.
