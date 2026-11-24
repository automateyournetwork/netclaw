# Pass20 — bounded offline LLDP extraction

One bounded T017 unit; no checkbox closes (14/30). Replaced lossy LLDP normalization
with bounded count-checked installed IOS-XE parser extraction. Exact chassis/port
identities, protocol, source paths, capture interval and hold time survive. Missing,
unsafe and placeholder identities stay unknown; system-name keys never substitute
for chassis identity. No expiry, subtype, binding, link or health is inferred.

Installed Genie expands interface names and collapses repeated identical nested
neighbor keys. Actual synthetic offline checks verify expansion and count-mismatch
rejection after collapse. This qualifies parser fields, not native capture/policy.

Files: scripts/genie-worlds/facts.py; tests/genie-worlds/{lldp_test.py,
offline_lldp.py,collector_test.py}; contracts/collector.md; tasks/verification/
resume, HANDOFF and daily memory. Requirements15/15 and quality39/39 checklists
pass. Existing branch/audit root/sticky reused; optional commit hooks skipped.

Actual commands/results; outputs under .spec200-local/pass-20/:
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p lldp_test.py -v`: initial8/8 pass, lldp-tests.txt; two later cases included in final suite.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`: final85/85 pass, python-tests-final.txt; earlier83/83 retained.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs tests/genie-worlds/selection.test.mjs`:12/12 pass, zero skips, node-tests.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_lldp.py`: installed Genie25.2 synthetic normal/empty/duplicate-collapse pass, zero execute calls, offline-parser-final.txt.
- `git diff --check`:pass; changed untracked-source whitespace check also passed.

Expected preimplementation four failures/four errors retained in before.txt.
Installed-runtime deprecation warning retained. Initial documentation patch was
rejected for duplicate HANDOFF target operations; corrected without partial edits.
Startup context reads produced excessive/truncated output; use bounded relevant
sections next pass. No UI edit, screenshot or new browser-visual claim.

Remaining: qualified LLDP inventory binding, combined detailed graph assembly and
unbound-report presentation; native adapter/read policy, actual collection/
continuity, live Google, installed NetClaw and owner acceptance. Device operations
coordinator-only; paid/owner pending. T014 gates native MCP/skill; T029 owner-only;
T030 interim memory/audit only until feature handoff.

Private outputs, source/document hashes, native GAIT start/end and full gait_log:
.spec200-local/pass-20/. Control hash unchanged. No device/provider operation,
authority/live-packet edit, source commit, publication, branch/agent/loop,
other-checkout modification, ticket or external communication. Preview stays
coordinator-owned frozen pass12. Later live-source-manifest review remains required.

Next exact step: LLDP→qualified-inventory graph bridge retaining chassis/port types,
unbound local claims and unknown expiry/subtypes; qualify synthetic parser→graph→
JavaScript inspector. Then compose CDP/LLDP/counter assembly and unbound UI reports.
