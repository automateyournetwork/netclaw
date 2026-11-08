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

## Wire recovery follow-up (T021/T034)

wire-recovery-02 on ed94560b passes topology/trust, lost result reply, lost ACK
delivery and paused-leader/unaware-member on fresh voters (4 processes, 7 controlled
callbacks, 0 model/native calls, worker cleanup passed). Voters exported (43 records)
and stopped exit 0. wire-recovery-01's failure stays retained. See fixture-gate.md.
Remaining open: T035-T041, T044-T048 (REAL, client journeys, measurements, closeout).

## REAL packet frozen (T035)

`real-run-01` prepared 2026-11-07 from source commit 9eb65bee (194-file source map,
sha256 407d0405...9295; only spec docs changed since the fixture-source commit
ed94560b). Plan, gate (`real-fixture-gate-01.json`, derived from fixture-gate.md) and
retained R05 runtime template (qwen3:0.6b/ollama arm64 family 4, subnet_summary
native MCP, guard image) are private under the R08 root. Python is the immutable
r04a-owner venv with its manifest. `prepare` made private files only: 0 model calls,
0 native effects, no containers. REAL budget is unspent (0/10 ops, 0/20 inferences,
0/10 effects). The gate is self-generated by the implementing agent from the
fixture evidence listed in it; independent owner review remains part of T048.

## REAL run (T036) and budget state — real-run-07

Source commits dbb9568e (log fix) and 09c55485 (member factory fix). Earlier attempts
real-run-01..06 failed before any operation and spent no budget: Docker 29.9 rejects
json-file `max-size=-1` (fixed to `max-file=1`); plan source maps missed
scripts/*.py, labs/ha/dependencies.json; Docker address pools were exhausted by retired
owned networks (removed, exact owned only); the HA member factory called
`validate_catalog`/`close` on a plain DockerExecutor (fixed + regression test). Each
failure and retirement is retained in its run directory (FAILED.txt, retirement/).

real-run-07: 3 voters, 3 Borders, 1 member (3 authenticated iN2N attachments), qwen3:0.6b
behind the guard, native subnet_calculator. Completed real operations, each exported
with signed result, ACK and `successful_native_workload: true`:
op1 border0, op2 border1, op3 border2, op4 border1 after SIGKILL of the actual leader
(border2, epoch 6). New leader border0 observed ~11s after the kill; op3 stayed
`completed`. Independent model counter (model container POST /v1/chat/completions log):
8 for 4 operations (2 each), matching the journals.

Quorum-loss negative (two voters paused): approve refused, model POSTs unchanged at 8,
existing status readable, `reconcile` refused until heal. **Ordering error:** the refused
approval reserved op5, which the budget now holds as `unknown` with the single slot
retained (it was never dispatched; review is still `review_pending`). The budget refuses
all further reservations (`unresolved_operation_retained`). Budget used: 5/10 operations,
10/20 claimed inferences (actual model POSTs: 8). It is not reset. Remaining REAL rows
that need a new approval (and HUD/Code/Mobile journeys, T038-T040) are blocked pending an
owner decision on how to account for this.

## Owner decision on the retained unknown slot (2026-11-08)

The owner chose continuation: a fresh run (real-run-08) may continue REAL work with
the cumulative R08 cap unchanged at 10 approved operations. real-run-07 used 5 (4
completed + 1 retained unknown, op5 2f13f31b, never dispatched). real-run-08 is limited
by the operator to at most 5 further approvals, so the combined total never exceeds 10
operations / 20 claimed inferences / 10 native effects. real-run-07's unknown slot stays
spent and is not reset. Unknown-producing negatives run last.

## real-run-08: HUD journey, VS Code attempt, second unknown slot

Frozen source 1,018 files (base map + HUD production closure). Same runtime shape as run-07.
Cumulative REAL accounting after run-08: run-07 5 operations (4 settled, 1 unknown) + run-08
2 (1 settled, 1 unknown) = 7 of 10. No cumulative counter was reset.

**HUD (browser, Chrome 156 profile-scoped CA trust, strict TLS)** via leader border2:
original_once complete -> operation c263dbe8 completed, exported with `successful_native_workload:true`
(model access log 2 POSTs, matching the journal). original_result complete (signed result/ACK
verified in the real HUD). Leader SIGKILL (border2): new authority in ~12s (epoch 17). authority
witness at border0 complete. no_quorum (two voters paused) complete. prepare_review + leader SIGKILL
(border1) + stale_review: first stale_review run failed because authority had not yet changed
(retained); rerun after election (epoch 29) complete. Model counter stayed 2 through every
recovery phase. Retained harness failures: attempt 1 of original_once failed before any POST
(driver `getByLabel` exact match on label-wrapped selects; fixed in labs/ha/client_qualification.mjs).
Not exercised: browser same-tab `cold_recovery` (original tab sessionStorage no longer exists).

**VS Code 1.109 (G12)**: attempt 1 failed before any decision (test race, fixed in
extensions/netclaw-vscode/test/editor-ha.cjs). Attempt 2 sent one approval via border1 (leader,
epoch 17) at ~10:45:20; member admission for the model call ended `unknown` (runner latch
`uncertain`, `effect_outcome_unknown`), no model POST, no result. The budget slot is retained
unknown; run-08 was retired without further operations. Likely contributor: concurrent heavy
Xcode/Flutter builds from a parallel agent against the 3-second admission window (not proven;
no explicit error logged). Qualification continues in a fresh run within the remaining 3 operations.

**iOS (G13)**: enrollment blocked on the simulator: the ad-hoc signed harness cannot create its
Keychain key (-34018). Rebuild with entitlements in progress. Product finding: in cluster mode the
HUD route `/api/hud/mobile/enrollment` rejects the Border's `cluster` payload (`invalid_contract`);
enrollment tokens were issued through the Border operator bridge instead.

## real-run-09, closeout and cleanup (T038-T041, T046)

**VS Code 1.109** (run-09, border0 follower after leader border1 SIGKILL, border2 elected epoch 8):
operation fddfce96 completed and settled; original_result, endpoint_recovery (border2),
cold_recovery (same profile), authority, no_quorum (voters 1,2 paused/unpaused) and stale_review
(fresh pending review, authority changed to border0 epoch 73) complete; model POSTs unchanged.
**iOS** (fresh erased simulator, run CA only, entitlement-rebuilt harness): HUD route enrollment in
cluster mode worked (proves the contract fix), operation d728e6b0 completed and settled; select-node
to border0, background/resume, cold terminate/relaunch with preserved key/subject/operation,
no-quorum and stale-review complete; counters unchanged. Two retained test-timing failures were
fixed in `integration_test/cluster_recovery_test.dart` (recovery binary rebuilt).
**Member-kill negative**: member SIGKILL 0.55 s after approve (member row `admitted`, no attempt,
no effect); restart did not replay; budget `unknown` retained; model POSTs stayed 4.
**Full restart**: all voters stopped/started, border0 and member relaunched; both completed
operations remain `acknowledged` with receipt digests identical to the exported packets.
REAL budget total 10/10 (7 settled, 3 unknown); see `evidence-matrix.md` for row status.

**Cleanup (T046).** Only exact owned resources: 68 stopped containers (label netclaw.spec=179, all
exited; `docker inspect` saved in `cleanup-final/containers-before.json`) and 14 owned networks
removed; no owned container, network, listener or R08 process remains; the four unrelated
running containers are untouched. Simulator 'NetClaw R08 Qualification 08' is shut down (kept,
with its run-scoped CA trust). Evidence manifest: `evidence-manifest.json` in the private root,
92,889 files / 6.6 GB hashed (sha256 of the manifest file 644429783060...6d24), excluding public
model blob copies, build outputs, frozen source copies and node_modules.
**Omission:** the model containers' access logs (the independent POST counter source) were
removed with the containers before being exported. Persisted POST counts exist only as the
per-phase `counters/*.json` exports of runs 08 and 09 plus GAIT journals and signed packets; the
run-07 counts (8 POSTs for 4 operations, unchanged under quorum loss) were observed live and are
not backed by a retained log.
**Retirement preservation.** The R05 and R06 retirement jobs ran at their original scheduled
times (launchd `runs = 1`, exit 0; the R05 owner model container stopped at 2026-11-07 14:36
local); nothing in this effort stopped, rescheduled or modified them. Unrelated containers
equinix-explorer-mcp, equinix-mcp, pyats-mcp and gateway5 remained running throughout.
**Not exercised:** HUD same-tab `cold_recovery`; see also the 9 fixture-only matrix rows.


## Final checks on HEAD 7f75b12f (T044)

Reviewed Python + Node 24.19, machine idle: tests/n2n 2048 passed / 5 skipped; installer, setup
and reconcile suites 260 passed / 32 skipped; HUD 539 passed and Vite build ok (HUD closure
inventory unchanged: 705 files, 5,314,095 bytes); editor 211 passed / 3 skipped, tsc ok
(`dist/extension.cjs` sha256 8132a4a0...458a unchanged, build.mjs not run); labs/ha node tests 43
passed; Mobile 525 passed and analyzer clean; inventory, catalog-links, catalog-metadata and
mcp-portability checks exit 0. `scripts/reconcile-mcp.py` exits 1 on this machine and also on a
clean `main` checkout (gitignored local `humanrail-mcp-server` pin finding plus modules missing
from the interpreter), so it is not caused by this branch. Summary:
`t044-final.json` in the session scratchpad.

## Owner decision: Option 2 (2026-11-08)

The owner chose Option 2: a new, explicitly capped REAL work package to close the nine
fixture-only matrix rows and two partials. New cumulative cap for this package: at most 10
further approved operations / 20 claimed inferences / 10 native effects, in addition to the
10 already spent in runs 07-09 (nothing is reset; the three held `unknown` slots stay spent).
Unknown-producing scenarios run last and at most one per run. A pre-dispatch *refusal* may
release the run's active slot only when an independent status read proves no dispatch
(`review_pending`, `attempt_count` 0, `may_have_executed` false) and the independent model
counter is unchanged; anything else remains `unknown`. The reservation always still counts.

## Integration with main and owner decision update (2026-11-08)

`origin/main` (Byrn's PRs #335 convergence setup, #336 hub credential renewal, #337 release 1.19.1
repair) was merged into this branch (`9fbd0e13`) before any further REAL work so the new evidence
matches the integrated source. One conflict (generated catalog hash in `scripts/lib/catalog.sh`)
was resolved by regenerating it with `scripts/build-catalog.py` (`--check` passes). After the merge:
tests/n2n 2062 passed / 5 skipped; inventory, catalog-links, catalog-metadata and mcp-portability
checks exit 0. Overlapping files with this branch were `mcp-servers/protocol-mcp/bgp-daemon-v2.py`,
`config/components/catalog.json`, `scripts/lib/catalog.sh`, `SOUL.md`, `TOOLS.md`.
Naming collision to resolve with maintainers: main now has `specs/179-convergence-setup` and this
branch has `specs/179-border-ha-authority` (same spec number).

Owner decision (supersedes the 10-operation cap in the Option 2 note above): the owner explicitly
said to ignore the budget and run the nine REAL tests. The cumulative cap for this package is
lifted by the owner. Retained controls: one active operation at a time, a fresh per-run budget
ledger, every run's evidence exported before anything is removed, unknowns never reset, and no
deletion of private evidence until acceptance.

## REAL closure rows completed so far (real-run-10)

Capacity/storage: real etcd NOSPACE (quota fill to HTTP 429 "database space exceeded", alarm on all
members), approval refused pre-dispatch (status proven `review_pending`/attempt 0 on all three
Borders; reservation `refused_pre_dispatch`, slot released, still counted), existing completed work
readable, model POSTs unchanged (2 -> 2), heal (delete scratch range, compact, defrag, clear alarm),
recovery operation completed (2 -> 4). Retired node returns: all Borders stopped, lease expired,
`ha-cluster.py drain` + `retire --acquire-authority` of border1 (revocation revision 1), old-key
border1 relaunch refused at process start with `HAError: node_retired` (never opened its operator
port), model POSTs unchanged (4 -> 4). Limitation: no approve was attempted through the retired
node (nothing listening) and the cluster record holds `state: retired` + revocation revision only,
no free-text reason. Model access log saved before container removal (`real-run-10/model-access.log`).
Partition proxies cannot cut NCFED Border-to-Border channels without a production seam (signed
manifest endpoints), so REAL partitions cut each Border's etcd path (`ncfed_cluster_channel_cut:false`).

## Option 2 closure runs (2026-11-08): all 18 rows REAL

Runs (each with its own ledger, model access log saved before removal, evidence exported before
retirement, only exact owned resources removed): run-10 capacity + retired node; run-11 partitions
(minority, both asymmetric orientations, three-way) on a proxied etcd topology; run-13 lost result/ACK
(`result-and-ack-loss`); run-14 live trust negatives with a receiver-side observer; run-15 clock wall-step;
run-16 stale-leader held claim; run-17 unknown consensus commit (recovered + unresolved); run-18 fenced
restore (`voters_dir: old-voters`, stale snapshot revision 14, new generation stayed `recovery_fenced`/
`capacity_frozen`, 0 reservations, 0 model calls). run-12 was aborted before any Border started
(launcher env refusal; fixed, retained). Product/harness fixes found: Budget `refused` state for
evidence-proven pre-dispatch refusals; launcher tolerance of the macOS exec env key; Border trust
observer; `export-unknown` accepting a member killed before its attempt claim (one-line helper, tested).
See `evidence-matrix.md` for per-row evidence and `acceptance.md` for the limits.


## Final state after Option 2 (2026-11-08)

Merged `origin/main` twice (PRs #335-#337, then #338 spec 181 / 1.20.0); conflicts were limited to
generated/catalog hashes and were resolved by regenerating (`scripts/build-catalog.py --check` and
`check-catalog-metadata.py` pass; the merged `n2n-federation` skill hash was recomputed from the file).
Suites on the final merged tree: tests/n2n 2156 passed / 5 skipped; setup/installer/reconcile/
convergence 296 passed / 32 skipped; HUD 544 passed; labs/ha node tests 43 passed; inventory,
catalog-links, catalog-metadata, mcp-portability and catalog `--check` exit 0. Editor (211) and
Mobile (525 + clean analyzer) are unchanged by #338 and keep their earlier green results.
Cleanup: no owned container, network, listener or R08 process remains (the last 24 leftover
operation-sandbox containers and 8 networks were inspect-saved to `cleanup-final2/` and removed by
exact label); unrelated containers untouched. Private evidence is retained, not deleted:
`evidence-manifest-final.json` hashes 98,192 files / 9.4 GB (sha256 cc2282ed96c1...0d40).
