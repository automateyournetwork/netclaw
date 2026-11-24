# Pass17 — raw counter evidence


One bounded T017/T018 unit; no task checkbox closes (14/30). The graph now retains
catalog-bound raw counter samples independently of strict rate derivation. Exact
unsigned64-bit decimal strings, units, capture intervals and individual provenance
survive missing-pair/unknown-time/incarnation conditions; unavailable values remain
null. The inspector shows both samples separately from derived rate/utilization,
including explicit unknown sample instants and absent observations. No continuity,
identity, capacity or actual sample timestamp is invented.

Python-to-JS validation rejects changed owner/source/intervals, numeric coercion,
overflow and forged derived sample identities, units, instants or deltas. Existing
immutable device/port/link geometry is preserved. Native parser-to-qualified-
identity binding remains open; this is a graph boundary and presentation change.

Files: scripts/genie-worlds/facts.py,viewer/network-graph.mjs,viewer/selection.mjs;
tests/genie-worlds/graph_bridge_test.py,network.test.mjs; contracts/local-network.md.
Actual commands (outputs retained privately under .spec200-local/pass-17/):
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:61/61 pass (python-tests.txt).
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p graph_bridge_test.py -v`:final11/11 pass (bridge-final.txt).
- `NETCLAW_BROWSER_EXECUTABLE='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' NETCLAW_BROWSER_EVIDENCE="$PWD/.spec200-local/pass-17/browser-final" /Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test --test-concurrency=1 tests/genie-worlds/network.test.mjs tests/genie-worlds/selection.test.mjs tests/genie-worlds/core.test.mjs`:18/18 pass,zero skips (node-browser-final.txt).
- `git diff --check`:pass (whitespace.txt).

Initial expected two regression errors retained in before.txt. Initial Node run
had17passes/one browser skip; superseded by actual Chrome18/18 runs. Synthetic
1280SVG and820world screenshots from browser/ visually inspected: counts/provenance
readable, desktop evidence independently scrollable, narrow view stacks evidence.
Actual browser asserts counts in both views, navigation/release/reset, no page errors,
zero external requests and zero provider sessions. browser-final/ retains the final
rerun screenshots and receipt. These are synthetic source evidence, not real counters.

Paid generation/owner acceptance remain pending; device operations remain coordinator-
only. T014 still gates native skill/MCP proof,T029 owner-only,T030 interim audit.
No authority/live packet modification,device/provider call,source commit,branch,
other-checkout edit,publication,ticket or external message. Native GAIT start/end/log
and evidence hashes retained privately. Owner preview remains coordinator-owned
frozen pass12. Source changes require a later coordinator live-manifest review.

Next concrete unit: connect normalize() interface_observations/CDP claims to qualified
inventory bindings and local_graph, refusing unresolved parser aliases. Use observed
capture intervals and retain unknown sample instants/continuity; increasing counts
alone never establish a rate. Broader T020 host/network fault testing is independent.
