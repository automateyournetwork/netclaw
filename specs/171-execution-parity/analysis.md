# R02 independent contract analysis

2026-11-02. Independent reviewer: r02_runtime_design. Strict read-only review of
spec, plan, tasks, contracts and constitution before implementation.

Initial result: 1 CRITICAL, 2 HIGH and 3 MEDIUM findings. Coordinator corrected
all six; independent focused recheck returned PASS, with no remaining findings
at those severities. Requirement coverage: all 16 functional requirements and
7 success criteria mapped across 36 tasks. This is design review, not runtime
qualification or final security acceptance.

| Finding | Correction | Recheck |
|---|---|---|
| C1: bearer in JSON conflicts with constitution | Private .env credential; metadata-only descriptor with file validation | PASS |
| I1: principal-only and session authority interfaces conflict | One server-derived auth_context on every operation; locked claims and read checks | PASS |
| I2: marker-only and wrapped effect gate conflict | Gate wraps actual invocation once and retains real evidence | PASS |
| I3: native tool name hides execute-once adapter | Explicit protected adapter, schema, revision and one-attempt semantics | PASS |
| U1: output cannot fit same-size envelope | 1 MiB envelope, 512 KiB output, 64 KiB arguments, explicit overflow failure | PASS |
| I4: CLI ownership conflict | Backend owns owner authority/CLI; coordinator owns runtime activation/setup | PASS |

Implementation gate opened after the independent recheck. Final implementation,
security and actual-evidence review remains T035; human acceptance remains T036.

## Final implementation and evidence review — 2026-11-02

Independent source/security review: r02_protocol. Independent native receipt,
cryptography, command transcript, GAIT and recovery review: r02_runtime_design.
HUD/artifact/containment and actual isolated-network review: r02_hud.

Final result: **PASS for T035**, after two bounded implementation passes. Source
`8c178ff8` and actual run `run-20261102T155125-625aeb` retain original complete
reports; no fixture result substitutes for the two actual provider/device reads.

Material implementation findings were resolved and independently rechecked:

| Finding | Correction and evidence |
|---|---|
| Supplied runtime revisions did not prove actual input bindings | Recompute and enforce image/guard/source/tool/native input digests before forwarding/effect; drift tests pass. |
| Official SDK retries could exceed facade-only dispatch accounting | Durable inner provider deduplication; actual guard→stub retries/unknown restart tests and final real dispatch counts pass. |
| Raw MCP values could be coerced or extra fields ignored by SDK | Validate exact raw call before SDK parsing;17 actual production HTTP/MCP refusal cases with synthetic external seams, zero effects. |
| Initial image policy permissions and token-field translation failed native startup/forwarding | Correct non-root public assets and bounded token normalization; failed operations retained, final native execution passes. |
| Unicon automatically sent an unreviewed mode-discovery command despite empty initialization lists | Fixed internal no-learning/no-reconnect policy and exact IOS-XE/IOL native dependency pins; already-enable requirement; actual native mock plus fresh full SSH transcripts show exactly the approved command. |

Final independent actual verification passes approval/result/ACK signatures,
enrollment keys, exact single-command raw/parsed evidence, two provider calls and
one tool per operation, GAIT principal/correlation, lost replies, full restart
with unchanged evidence and owned cleanup. Separate image egress probes passed
with explicit positive controls.86 Border/model/provider-body artifacts contain
none of the actual credential bytes. Original inventories are unchanged.

Qualification limits in verification.md and parity-matrix.md are part of this
verdict. This is not cloud, arbitrary provider/plugin/platform, device-write,
SSO/RBAC or untrusted-host qualification. The owner subsequently accepted T036
on 2026-11-02; exact cloud-resource review and later roadmap gates remain.
