# Pass18 — normalized counter graph assembly

One bounded T017/T018 unit; no checkbox closes (14/30). interface_counter_graph
validates inventory/catalog proofs, normalizes interface parser fields and binds
exact device-scoped interface_name aliases into the graph/shared inspector. Slots
are explicit and unique; reordered input cannot swap samples. Unmatched/ambiguous
names and missing slots remain in a private report. Missing fields have no invented
path; invalid present fields retain sourced unknowns. Failed reads retain coverage.
No timestamp, incarnation, continuity, capacity, alias or combined health inferred.

Files: scripts/genie-worlds/facts.py;
tests/genie-worlds/{normalized_graph_test.py,offline_interfaces.py};
contracts/local-network.md; tasks/verification/resume, HANDOFF and daily memory.
Checklists passed (15/15 requirements,39/39 quality); optional commit hooks skipped
as instructed. No branch, agent or nested loop created.

Actual commands/results; full outputs under .spec200-local/pass-18/:
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:69/69 pass, python-tests.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs tests/genie-worlds/selection.test.mjs`:12/12 pass, zero skips, node-tests.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_interfaces.py`:actual installed Genie25.2 parsed two synthetic captures through JSON, bound eight counter entries, passed JavaScript graph/inspector, zero execute calls; offline-parser-final.txt.
- `git diff --check`:pass; additional untracked-source whitespace checks retained in whitespace.txt.

Initial preimplementation run retained six expected missing-function errors in
before.txt. It also collected five imported tests redundantly; module import fixed
that harness issue. Final eight new tests are unique. Installed runtime's existing
deprecation warning retained. An attempted documentation patch was rejected for
multiple operations on HANDOFF; corrected with a single rewrite. No UI source
change or new screenshot/browser-visual qualification; actual JavaScript graph
validation/selection ran through subprocesses with synthetic input only.

Remaining limits: interface-only assembly, not native collector/CDP/LLDP/state
assembly. Unbound report not yet presented by viewer. Native identity/read-policy,
actual collection, Google trial, installed NetClaw MCP/skill and human review remain
open. T029 owner-only;T030 interim audit stays open. Paid/owner pending;device work
coordinator-only. Control/authority/acceptance/live packets and owner homes untouched.
No source commit,publication,other-checkout edit,ticket or external message.

Native GAIT reuses private root/sticky/branch; start/end/log and manifest hashes in
pass-18. Next: bind normalized CDP claims through exact qualified local interface
and typed remote identity records; preserve unbound local claims, unknown expiry
and coverage. Keep parser state fields separate; never infer aliases or continuity.
Broader T020 host/network faults remain independent work.
