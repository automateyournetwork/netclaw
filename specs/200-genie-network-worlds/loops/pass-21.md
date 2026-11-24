# Pass21 — LLDP evidence-to-graph binding

Bounded T017/T018 source unit; no complete task checkbox closes (14/30). Reused
the existing branch, GAIT root and sticky file. Checklists15/15 and39/39 pass;
optional git hooks skipped under explicit owner instructions. Control remains
read-only; paid generation/owner review pending and device operations coordinator-only.

## Work and files

- scripts/genie-worlds/facts.py: lldp_neighbor_graph and shared internal exact
  CDP/LLDP bridge; existing CDP API/limits and behavior retained.
- tests/genie-worlds/lldp_graph_test.py: seven regression cases cover exact geometry,
  JS validation/inspector, immutable input, unknown subtypes/expiry, reciprocal
  unknowns, missing/ambiguous local aliases, remote type mismatch, absent chassis,
  failed/empty/unqualified captures, bounds and forged catalog proof refusal.
- tests/genie-worlds/offline_lldp.py: installed synthetic parser→JSON→graph→JS
  inspector check; empty and duplicate-collapse checks retained, zero execute calls.
- contracts/local-network.md, tasks.md, verification.md, resume.md, HANDOFF.md and
  daily memory updated. No UI change; no new screenshot/browser-visual claim.

## Actual verification

Outputs retained in .spec200-local/pass-21/:

- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p lldp_graph_test.py -v`: seven expected preimplementation AttributeErrors; before.txt retained.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_graph_test.py' -v`:21/21 pass; graph-tests.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:92/92 pass; python-tests.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs tests/genie-worlds/selection.test.mjs`:12/12 pass,zero skips; node-tests.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_lldp.py`:pass,Genie25.2,zero execute calls,JS graph/inspector pass; offline-parser.txt.
- Same installed interpreter running `tests/genie-worlds/offline_cdp.py`:pass,zero execute calls; offline-cdp.txt. Existing installed Unicon deprecation warning retained; runtime unchanged.
- `git diff --check`:pass; whitespace.txt. Source and private evidence hashes in manifest.json.

Native installed gait_mcp was imported with PYTHONDONTWRITEBYTECODE=1 using the
existing private root/sticky. Start/end records and gait_log are retained privately.
No new branch,agent,loop,device/provider operation,source commit,publication,
existing-home modification,other-checkout write,ticket or external communication.

## Limits and next step

Unknown subtypes survive in normalization, not invented as graph identity types.
Native inventory aliases/capture policy, combined detailed collection, unbound
report display and actual collection remain unqualified. Paid and owner gates
remain; T014 still gates native MCP/skill proof, T029 owner-only, T030 feature
handoff-only. Preview remains coordinator-owned frozen pass12. Changed source
requires later coordinator live-manifest review, never a grant edit in this pass.

Next bounded unit: compose CDP/LLDP/counter inputs into one detailed graph while
retaining every failed/unbound record and separate interface-state observations.
Do not concatenate already-rendered graphs or manufacture continuity/expiry.
Broader T020 host/network/account-loss tests remain independent useful work.
