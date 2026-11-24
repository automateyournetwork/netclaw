# Pass15 — bounded offline CDP extraction

One coherent T017 source unit; no task checkbox closes (14/30).
Changed scripts/genie-worlds/facts.py and added tests/genie-worlds/cdp_test.py.
Updated collector contract,tasks,verification,resume,HANDOFF and daily memory.


## Pass15 — offline CDP extraction

T017 progresses with bounded IOS-XE Genie CDP-detail extraction in facts.py.
Exact device/port claims, field source paths, capture intervals and reported
hold-time are retained; unsafe or missing identities stay unknown without lossy
matching. No identity binding, expiry, link, rate or continuity is invented.
Unsupported/mismatched shapes stay normalization_unqualified; explicit reported
zero differs from failed collection. The256claim bound refuses excess.

Actual installed Genie25.2 parser processed independent synthetic CDP text with
zero execute calls, then normalization/path assertions passed. Private script
and result: .spec200-local/pass-15/offline-parser.py and offline-parser-result.txt.
The installed parser emits integer index keys; persisted JSON uses strings;
source paths use canonical string components. This qualifies the tested parser
shape only, not device access, capture policy, identity aliases or native graphs.
Existing installed-runtime deprecation warning is retained; no runtime changed.

Actual commands/results (full output retained under .spec200-local/pass-15/):
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:54/54pass,python-tests.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7pass,node-core.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python .spec200-local/pass-15/offline-parser.py`:pass,zero device calls.
- `git diff --check`:pass,whitespace.txt.
Initial six-case preimplementation regression run failed as expected and is
retained in cdp-before.txt. No UI change; no new browser qualification claimed.

No checkbox closes:14/30. T016native capture/identity,T017interface extraction
and graph binding,T019actual collection remain open. Paid generation and owner
acceptance pending; device operations coordinator-only. T029owner-only,T030
interim notes/audit only. Native GAIT/start/end/log and manifest in pass-15.
Next: offline installed show-interfaces parser on synthetic text into exact
counter fields and intervals; preserve unknown sample instant/incarnation/
continuity, then bind qualified claims to resolver/graph APIs.

No source commit,push,branch,agent,loop,publication,other-checkout write,
authority/owner-acceptance modification,device operation or paid request.
Startup inventory connector is unavailable and device gate belongs to coordinator;
no native device listing was attempted. Existing GAIT root/sticky/branch reused.
Context reads initially exceeded output limits; later focused reads supplied
needed task/contracts/source details. No private observations were printed.
