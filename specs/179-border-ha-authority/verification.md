# R08 verification — implementation in progress

R08 is not yet complete. No REAL model/native effect or native client HA acceptance
has occurred. The48task plan and every qualification-matrix row remain required.
Source1.18.7/editor1.6.1/Mobile1.0.4+7 and the roadmap release hold are unchanged.

## Evidence established

- SDD spec,clarification,plan,contracts,tasks and cross-artifact analysis precede
  implementation. Analysis has zero critical/high findings at that checkpoint.
- Three actual private etcd3.6.16 voters use distinct peer/client CAs,mTLS,RBAC,
  bounded memory/CPU/storage and loopback administrative ports. Exact IDs and
  command journals are private under roadmap-r08-20261107/etcd-fixture-01.
- core-03 passes7fixture rows using actual etcd and NCFED cluster sockets:
  three-node mesh,one follower-forwarded admission,leader replacement,old-leader
  refusal,unknown reservation,single-voter continuation and two-voter refusal.
  Replacement measured15.007s. Two controlled callbacks;zero model/native calls.
- Actual socket tests separately cover strict mutual TLS,NCFED proof/method
  isolation and one member's three outbound authenticated iN2N attachments.
- Source/controlled tests cover fresh single-use admission,clock discontinuity,
  delayed receipts,unknown dispatch,member/runner reservations,device revocation
  CAS races,original result/successor ACK,lifecycle and fenced restore.
- Integrated targeted Python batch:235passed,12existing datetime warnings.
  HUD/editor lane:538HUD tests passed;211editor tests passed,3existing skips;
  focused owner35passed,TypeScript and builds pass. See clients-notes.md for
  commands,initial pre-build harness failures and exact qualification limits.
- Full federation suite before the final transport changes:1904passed,5skipped,
  104warnings in114.39s using the existing R04a Python3.12 environment read-only.
  The first environment lacked chromadb:1775passed,5skipped and5RAG failures before
  maxfail stopped that run. No dependency or retained environment was modified.
- Integrated late-admission/ownedTLS/role/MCP regression batch:134passed. Native
  MCP admission now occurs after startup/schema discovery and is rechecked at
  the synchronous bounded pipe write; actual OS-pipe saturation is covered.
- Mobile source:524tests pass,analyzer clean and the production verifier compiles
  for both iOS simulator architectures. Whole-app compilation requires the absent
  ignored GoogleService-Info.plist. No native simulator acceptance is claimed.

## Retained failures and limits

core-01 refused a manifest path mismatch before execution. core-02 failed cluster
transport because the application URI-SAN certificate did not establish TLS DNS
identity. The corrected fixture has a separate transport CA/DNS-SAN certificate
with each enrolled application key preserved. Both failed packets remain private.

matrix-network-01 passed minority and asymmetric-request rows,then recorded an
asymmetric-response assertion. Both denied admission probes remained unknown with
zero callbacks. Investigation reproduced a fixture election-wait defect:the
helper excluded an isolated observer but could still return that old leader from
a healthy observer before lease expiry. Its shutdown also waited for open proxy
connections before closing them. The exact owned process was terminated after
the failure remained stuck;termination.json preserves that action. Corrected
drivers must rerun this row in a new evidence directory. This failure is retained,
not converted into a passing row by diagnosis.

Review also found delayed model/helper and MCP handoff risks. MCP now uses the
official SDK stream seam with a bounded synchronous atomic pipe handoff. The
trusted Docker helper now independently checks its READY-relative monotonic/wall
budget immediately before its single nonblocking HTTP send to the unchanged
DefenseClaw gateway. It subtracts250ms and refuses partial/blocked sends without
retry. Integrated model/MCP/role/Ollama regression138passed;these controlled
helper tests do not establish REAL model execution. HA mcp-call.json explicitly
records prepared intent;its presence is not an actual native-call counter.

matrix-network-02 passed all4partition rows and cleaned up normally. Its strict
combined300ms delay row failed with admission_expired and zero added callbacks.
Ten sequential quorum round trips plus cluster transit exceed the3s window.
Keep this failure and safety window;separate latency-safety measurements must
state admitted versus bounded-refusal outcomes. No300ms service-availability or
R09 WAN-readiness claim is made.

matrix-recovery-01 exercised9passing safety rows:stale receipt,three clock cases,
unknown consensus reply,lost result,lost ACK,record capacity and actualNOSPACE.
Its NOSPACE cleanup failed on a zero-valued memberID omitted by protobufJSON.
The coordinator observed exactly the injected alarm,deactivated memberID0 once
and verified GET returned no alarms. All receipts remain beside the failure.

matrix-restart-retire-01 actually stopped/restarted all3owned voters and retained
the quorum snapshot and old/new OS PIDs. Recreating node objects while retaining
EtcdStore authentication tokens caused etcd_access_refused;the row remains failed.
Corrected fixture source reconstructs clients as a real process restart would.
matrix-retire-01 then passed durable retirement and old-key return refusal.

Isolated Chrome156 profile preparation passes ordinary certificate validation:
the fresh public testCA is visible in that profile's Trusted Certificates;
matching DNS succeeds,wrong hostname returns ERR_CERT_COMMON_NAME_INVALID and
unknownCA returns ERR_CERT_AUTHORITY_INVALID. No certificate-error flags or host
trust-store changes. This validates client test setup,not HUD HA acceptance.

The current fixture has not yet established the full partition/restart/storage/
retirement/restore matrix. Unit tests are not substituted for those rows. REAL
OpenClaw/DefenseClaw/Ollama/nativeMCP and browser/Code/iOS qualification remain open.
No region,physical phone,other model/runtime or additional platform is qualified.

## State and preservation

The first3owned voters are stopped after a consistent353record export;their data,
container identities and private network remain preserved pending final cleanup.
No qualification Border/member process remains from those completed runs. A new
proxy-fronted Raft fixture is being prepared with fresh keys/IDs;do not start an
older prepared packet after its pinned source or certificate contract changes. No
global prune,retained runtime upgrade,cloud change or device operation occurred.
R01 pilot and R05/R06 retirement evidence remain preserved. Never rerun spent
core directories or reuse an old activation/enrollment payload.
