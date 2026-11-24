# Pass19 — normalized CDP graph assembly

One bounded T017/T018 unit; no checkbox closes (14/30). Added
facts.cdp_neighbor_graph with full catalog validation, exact local interface_name
aliases and typed remote cdp_device_id/port_id identities. No cross-type fallback.
Unmatched, ambiguous or incomplete local identities retain normalized provenance
outside geometry; remote unresolved claims remain in graph discovery. Reciprocal
claims with unknown expiry cannot corroborate; no current interface health inferred.
Read failures, empty tables and unqualified parser shapes stay distinguishable.

Files: scripts/genie-worlds/facts.py;
tests/genie-worlds/{cdp_graph_test.py,offline_cdp.py};
contracts/local-network.md; tasks/verification/resume, HANDOFF and daily memory.
Checklists passed (15/15 requirements,39/39 quality); optional commit hooks skipped
as instructed. No branch, agent or nested loop created. Existing audit branch reused.

Actual commands/results; full outputs under .spec200-local/pass-19/:
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p cdp_graph_test.py -v`:6/6 pass, cdp-graph.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:75/75 pass, python-tests.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs tests/genie-worlds/selection.test.mjs`:12/12 pass, zero skips, node-tests.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_cdp.py`:installed Genie25.2 parsed synthetic CDP through JSON→exact graph→JavaScript validator/shared inspector, zero execute calls; offline-parser.txt.
- `git diff --check`:pass; untracked source whitespace checked separately, whitespace.txt.

Six expected preimplementation missing-function errors are retained in before.txt.
Installed runtime's existing deprecation warning remains in offline-parser.txt.
Initial startup context reads were overbroad/truncated; use bounded relevant local
reads in future passes. No private observation was needed for this implementation.
No UI source change or new screenshot/browser-visual claim. JavaScript validation
and shared selection ran against synthetic input, including actual parser output.

Remaining limits: this is a CDP-only graph assembler, separate from the existing
counter-only assembler. No combined collection, LLDP typed binding, unbound-report
viewer presentation or native alias/capture qualification. Native read-policy,
actual collection, Google trial, installed NetClaw MCP/skill and human review
remain open. T030 has interim memory/audit only, not feature handoff acceptance.

Private outputs, source/document hashes and native GAIT start/end/log are retained
in .spec200-local/pass-19/manifest.json and gait-*.json. Control checksum unchanged.
No device/provider operation (devices coordinator-only), authority/live packet edit,
source commit, publication, other-checkout change, ticket or external message.
Owner preview remains coordinator-owned frozen pass12. Source changes require later
coordinator review of the live source manifest before any paid action.

Next exact step: qualify installed LLDP detail extraction with synthetic offline
text and source paths; preserve exact chassis/port types and reject unsafe identity
text instead of truncating it. Then compose the detailed collection graph and
present unbound reports. T020 host/network/account-loss coverage is independent.
