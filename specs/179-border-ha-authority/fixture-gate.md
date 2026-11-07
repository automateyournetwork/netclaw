# R08 fixture gate (T034) — passed for FIXTURE scope

2026-11-07, source ed94560b. Private evidence root
`~/.local/share/netclaw/roadmap-r08-20261107/`. FIXTURE evidence uses actual
authenticated quorum/NCFED transport with controlled effects. It never qualifies
REAL model/native rows (T036/T037) or any client journey (T038-T040).

| Matrix row (fixture column) | Actual evidence |
|---|---|
| Leader loss, old-epoch refusal | core-03, process-fixture-01 (SIGKILL of each elected Border) |
| Minority / asymmetric (both orientations) / three-way partition | matrix-raft-network-01 (opaque Raft peer cuts + quorum-client/NCFED cuts) |
| 300ms latency | matrix-raft-network-01; safely refuses beyond the 3s window, no R09 claim |
| Stale leader / member never saw new epoch | wire-recovery-02 paused-leader-unaware-member (real SIGSTOP/resume, same PID identity, old proofs refused, higher-epoch model2 admitted) |
| Quorum loss, full voter restart | matrix-raft-recovery-02 |
| Clock uncertainty (+1s/-1s/+4s advance, delayed receipt) | matrix-recovery-01 (controlled inputs, not host clock changes) |
| Unknown consensus commit | matrix-recovery-01 |
| Lost result reply / lost ACK delivery | wire-recovery-02 (authenticated RPC delivery-boundary faults; successor reconcile reuses original signed result/ACK; member persists it) |
| Member/runner unknown, process restart | process-fixture-01 |
| Retired node returns | matrix-retire-01 |
| Fenced restore | fenced-restore-fixture-01 |
| Capacity/storage, NOSPACE | matrix-recovery-01, matrix-raft-recovery-02 |
| Topology/trust | wire-recovery-02 topology-trust (fresh/external/unenrolled certs refused at every cluster mTLS and etcd listener with matching receiver verification events; wrong-role and replayed-proof hello refused; forbidden methods refused; member has no listener or etcd credentials) |

wire-recovery-02: 4 actual OS processes, 1 member enrollment, 7 controlled
callbacks, 0 model calls, 0 native calls, owned worker cleanup passed, complete.json
written, voters then exported (43 records, sha256 a4ed644b...481341e) and stopped
exit 0 (`wire-voters-02-retirement`). Earlier failure wire-recovery-01 is retained.

Limits retained: no REAL provider/native path; 300ms availability unqualified;
loss hooks are RPC delivery-boundary faults, not packet loss; clock rows are
controlled inputs. HUD/Code/Mobile rows are REAL-only and remain T038-T040.
