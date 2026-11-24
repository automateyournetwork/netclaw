# Pass16 — offline interface extraction

One bounded T017 unit; no task checkbox closes (14/30).

Changed scripts/genie-worlds/facts.py; added tests/genie-worlds/interfaces_test.py
and offline_interfaces.py. Contract,task progress,verification,resume,HANDOFF and
daily memory updated. No UI change and no browser rerun claimed.

The normalizer preserves independent parser state fields and exact64-bit decimal
counters with source paths and capture intervals. Missing/invalid values remain
unknown; unsupported shapes/unsafe names are not qualified;256rows/read bound.
Genie name expansion and line-protocol-derived oper_status are explicit limits.
No inventory alias,sample time,width,incarnation,continuity,rate,utilization or
capacity is invented. Native graph binding and capture policy are still open.

Actual commands and outcomes (full output in .spec200-local/pass-16/):
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/gait_mcp/venv/bin/python -m unittest discover -s tests/genie-worlds -p '*_test.py' -v`:59/59pass,python-tests.txt.
- `/Users/john.capobianco/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node --test tests/genie-worlds/core.test.mjs`:7/7pass,node-core.txt.
- `PYTHONDONTWRITEBYTECODE=1 /Users/john.capobianco/.local/share/netclaw/roadmap-r02-r05-20261102/.pyats-runtime-generation-nujn4zpi/bin/python tests/genie-worlds/offline_interfaces.py`:pass,Genie25.2,zero execute calls,offline-parser-result.txt.
- `git diff --check`:pass,whitespace.txt.

Five preimplementation regressions retained in interfaces-before.txt. Installed
Unicon deprecation warning retained; no runtime changed. Native GAIT root/sticky/
branch reused, start/end and gait_log retained privately. Control hash preserved.
No device/provider call,source commit,branch,agent/loop,other checkout,authority
change,ticket or external communication. T030 is interim audit only.

Next bounded unit: integrate normalized evidence with qualified inventory bindings
and resolver/local_graph. Preserve unresolved aliases/expiry and null timing/
continuity; no native collection until coordinator device gate releases. T020
broader host/network/account-loss tests remain independent useful work. T013/014
paid allowance pending;T022/023 gated on T014;T029 owner-only;T030 feature handoff.
