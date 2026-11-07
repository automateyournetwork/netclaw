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

The complete fixture gate remains open, particularly actual process and fenced
restore evidence. Unit tests are not substituted for those rows. REAL
OpenClaw/DefenseClaw/Ollama/nativeMCP and browser/Code/iOS qualification remain open.
No region,physical phone,other model/runtime or additional platform is qualified.

## State and preservation

The first3owned voters are stopped after a consistent353record export;their data,
container identities and private network remain preserved pending final cleanup.
No qualification Border/member process remains from those completed runs. The
fresh proxy-fronted Raft fixture03 and its3proxies are now stopped after a
consistent254record export; all process-drill workers exited and their owned
sockets were removed. Never start the prepared fixture02 packet:
its peer SAN contract was superseded before first start. No
global prune,retained runtime upgrade,cloud change or device operation occurred.
R01 pilot and R05/R06 retirement evidence remain preserved. Never rerun spent
core directories or reuse an old activation/enrollment payload.

## Actual Raft and restart follow-up

matrix-raft-network-01 passes all five rows on fixture03: minority, both directed
asymmetric cuts, three-way separation and latency safety. The first four include
independently observed opaque Raft peer cuts as well as quorum-client/NCFED cuts.
Measured row durations are19.985s,20.132s,12.233s and36.248s; these are whole-row
durations, not election-only measurements. The300ms row separately records admitted
and expired probes. It explicitly does not qualify300ms availability or R09.
All owned connections were closed; bounded thread settlement completed.

matrix-raft-recovery-02 passes two-voter loss, actualNOSPACE refusal/healing and
full voter restart with recreated authentication clients. Original completed ACK
and unknown reservations survive; fresh-ID bypass refuses. The restarted node
and member objects in this matrix are not OS-process restart proof; the dedicated
process fixture supplies that separate gate. The preceding recovery-01 invocation
failed at import before initializing any fixture because PYTHONPATH was missing.
Its stderr and corrected explicit import path are retained.

Independent source review reproduced an expired-member-certificate admission on
an already-open attachment. The authoritative fresh prepare/dispatch/admit gates
now recheck validity; historical result and claim recovery remain accessible.
The regression failed before the fix and22 related tests pass. Separate REAL
evidence review is correcting claimed-versus-executed counters and non-settling
unknown exports before any real profile is started.

process-fixture-01 passes actual NCFED cluster mesh, three outbound iN2N member
attachments, follower admission, SIGKILL of each elected Border and the member,
full voter restart, changed process/incarnation identities, unchanged consumed
journals/effect records, spent replay refusal and new-ID reservation refusal.
It produced three controlled callbacks and zero real model/native calls. However,
each restarted Border worker exited1 with TimeoutError during fixture shutdown:
its listener waited before closing accepted channels. The coordinator initially
reported overall success despite those cleanup exit codes. Keep that evidence
qualification limit; corrected source must propagate cleanup failure and prove
graceful shutdown separately. All exact owned worker exits/sockets and the final
six-container stop are independently recorded. No signed REAL result is implied.

## Fenced restore and corrected shutdown

`fenced-restore-fixture-01` completes all actual phases on source d3ed8c3c and
reviewed plan b79584f4671e7a69b8ba546d6ba9e8c278eafe85895b6fa76c1ecddab0b6f5b3.
Its dedicated original generation has exactly one member. Trusted host capture
records all three live voter IDs, three Border processes and the member process.
Operation A completes with controlled signed output and released reservations;
the stale snapshot is revision10. Later operation B consumes model1 and becomes
unknown at revision15; B, its committed claim and current reservations are absent
or obsolete in the stale snapshot. Later evidence is exported separately.

All four original worker processes then exit0 with their exact owned sockets
removed. This supplies actual corrected graceful shutdown proof without erasing
the earlier process-fixture-01 failure. All three original voters are stopped,
disconnected and restart-disabled before the replacement three start. No more
than three R08 voters run concurrently. The offline enrollment signer stays out
of replacement runtimes; node/install/key identities and generation change.

Fresh actual host isolation receipt2c08f0c5-556a-4b25-9197-c41968535cbd authorizes
installation/activation. Inactive campaign refuses recovery_fenced. After status
authority activates,15restored records match expected transformations and fresh
prepare/model/tool admission all refuse recovery_fenced with capacity_frozen.
Missing later evidence is not recreated or claimed recovered. Three controlled
callbacks;zero model/native calls. Replacement voters are exported and stopped
under their separate exact-owned retirement receipt. T025 fixture scope closes;
REAL restore remains T037. T021/T034 still require the independently identified
paused-leader and actual iN2N result/ACK loss/trust follow-up.

## Integrated checks

The coordinator's full federation suite passes1998tests with5existing skips and
104warnings in115.72s. Later setup/role/export/process checks pass110tests and
56subtests. Corrected restore/process integration passes31tests. HUD538tests,
editor211tests with3existing skips, editor TypeScript/build and HUD Vite build
pass. Mobile525tests and analyzer pass. Native binaries and real app journeys
remain separate. Fresh R08 model/guard logging now pins complete non-rotating
Docker logs; private guard ingress logs still require stopped-runner completeness
checks. A reserved inference row is never an actual send counter.
