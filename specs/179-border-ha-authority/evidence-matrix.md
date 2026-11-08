# R08 row-to-artifact evidence matrix (T037/T045)

2026-11-08. Private evidence root: `~/.local/share/netclaw/roadmap-r08-20261107/` (all paths
below are relative to it). REAL = the actual guard/model/native profile with its own counters.
FIXTURE = actual authenticated quorum/NCFED transport with controlled effects.
`qualification-matrix.md` says no row may be waived by calling it "applicable", so rows with
no REAL evidence are listed as **gaps**, not as passed.

REAL budget: 10 of 10 approved operations used across real-run-07, -08 and -09: 7 settled
and 3 held `unknown` (run-07 op5, run-08 VS Code attempt, run-09 member-kill). Nothing was
reset. The model access log is the independent counter (2 POSTs per completed operation,
none for an unknown).

## Matrix

| Row | FIXTURE evidence | REAL evidence | Status |
|---|---|---|---|
| Leader loss | core-03; process-fixture-01 (SIGKILL each Border) | run-07 op1-3 then leader border2 SIGKILL: op3 `completed` unchanged, op4 distinct on survivor (`real-run-07/export-op4-leaderloss-border1`, `leader-loss-01/`); run-08 `leader-loss-08/`, `-08b/`; run-09 `leader-loss-09/`, `-09b/` | **REAL pass** |
| Minority partition | matrix-raft-network-01 | none (needs the opaque Raft proxy topology; budget spent) | **Gap: fixture only** |
| Asymmetric partition | matrix-raft-network-01 (both orientations) | none | **Gap: fixture only** |
| Three-way partition | matrix-raft-network-01 | none | **Gap: fixture only** |
| Stale leader / member | wire-recovery-02 paused-leader-unaware-member (real SIGSTOP) | stale-review witnesses with a real pending `attempt_count:0` review across an authority change: HUD (`real-run-08-clients/evidence/browser-08`), VS Code (`real-run-09-clients/evidence/e09`), iOS (`real-run-09-clients/ios/evidence/stale-review.json`); counters unchanged | **Partial**: client refusal is REAL; a delayed old claim at the real guard/effect gate is not |
| Quorum loss | matrix-raft-recovery-02 | run-07 `negatives/quorum-loss`, `quorum-loss-status`: approve refused, model POSTs unchanged at 8, existing status readable, reconcile refused until heal; no_quorum witnesses: HUD (`browser-05`), VS Code (`e06`), iOS (`evidence/no-quorum.json`) | **REAL pass** (iOS fault witness ran ~1 s after the pause: weak) |
| Clock uncertainty | matrix-recovery-01 (+1 s, -1 s, +4 s advance, delayed receipt) | none | **Gap: fixture only** |
| Unknown consensus commit | matrix-recovery-01 | none | **Gap: fixture only** |
| Lost result / ACK | wire-recovery-02 (RPC delivery-boundary faults, successor reconcile) | none | **Gap: fixture only** |
| Member / runner unknown | process-fixture-01 | run-09 `member-kill-09/`: member SIGKILL 0.55 s after approve returned (`admitted`, `attempt_id` null, `effect_claimed` 0), restart does not replay, op stays `dispatch_claimed`, model POSTs stay 4, budget `unknown` retained; run-08 VS Code attempt `export-unknown-vscode` (admission `unknown`, runner latch `uncertain`, `effect_outcome_unknown`) | **REAL pass** (death occurred before the attempt/effect claim; death after an effect claim is fixture-only) |
| Full restart | matrix-raft-recovery-02; process-fixture-01 | run-09 `full-restart-09/`: all 3 voters stopped/started, Border and member relaunched; both completed operations still `acknowledged` with receipt digests identical to the exported packets; unknown unchanged; model POSTs 4 | **REAL pass** (only border0 restarted: border1/border2 had been killed earlier) |
| Retired node returns | matrix-retire-01 | none | **Gap: fixture only** |
| Fenced restore | fenced-restore-fixture-01 | none (real unknown/reservations are retained, but no real restore was run) | **Gap: fixture only** |
| Capacity / storage | matrix-recovery-01, matrix-raft-recovery-02 (actual NOSPACE) | none | **Gap: fixture only** |
| Topology / trust | wire-recovery-02 (cluster mTLS + etcd negatives with receiver events, hello refusals, forbidden methods) | member attached outbound to 3 Borders, authenticated (run-07/08/09 `attachments`); negatives are fixture only | **Partial** |
| HUD | n/a | `real-run-08-clients/evidence/browser-02..08`: original_once (real op c263dbe8, `export-hud-op`), original_result, authority, no_quorum, stale_review; Chrome profile-scoped CA, strict TLS | **REAL pass** except same-tab `cold_recovery` (original tab sessionStorage no longer existed) |
| VS Code G12 | n/a | `real-run-09-clients/evidence/` e01..e09: operation fddfce96 (`export-vscode-op`), original_result, endpoint_recovery, cold_recovery, authority, no_quorum, stale_review; Code 1.109, same original result, zero extra model calls | **REAL pass** |
| Mobile G13 | n/a | `real-run-09-clients/ios/`: HUD-route enrollment in cluster mode, operation d728e6b0 (`export-mobile-op`), select-node to border0, background/resume, cold terminate/relaunch, authority capture, no-quorum, stale-review; recovery binary rebuilt with a test-timing fix | **REAL pass** (authority "witness" is a capture, not a native phase) |

Totals over 18 rows: 7 REAL pass (leader loss, quorum loss, member/runner unknown, full
restart, HUD, VS Code, mobile), 2 partial (stale leader/member, topology/trust), 9 fixture-only
gaps (minority, asymmetric, three-way, clock, unknown commit, lost result/ACK, retired node,
fenced restore, capacity). Under the spec's own rule the 9 gaps and 2 partials are **not
closed**; they need either more REAL budget under a new owner decision or an explicit owner
acceptance of the limitation.

## REAL operation ledger

| Run | Operation | Surface | Outcome | Evidence |
|---|---|---|---|---|
| 07 | 11e23617 | runner via border0 | settled | `real-run-07/export-op1` |
| 07 | ab17e684 | runner via border1 | settled | `export-op2-border1` |
| 07 | 28125f6a | runner via border2 | settled | `export-op3-border2` |
| 07 | f5c5663e | runner via border1 after leader SIGKILL | settled | `export-op4-leaderloss-border1` |
| 07 | 2f13f31b | runner, approval refused under quorum loss | **unknown** (never dispatched) | `negatives/quorum-loss` |
| 08 | c263dbe8 | HUD via border2 | settled | `real-run-08/export-hud-op` |
| 08 | aeb2b0b1 | VS Code via border1 | **unknown** (member admission `unknown`) | `real-run-08/export-unknown-vscode` |
| 09 | fddfce96 | VS Code via border0 | settled | `real-run-09/export-vscode-op` |
| 09 | d728e6b0 | iOS via border2 | settled | `real-run-09/export-mobile-op` |
| 09 | 4e41a309 | runner, member SIGKILL after dispatch | **unknown** (retained, no replay) | `real-run-09/member-kill-09` |

Settled 7, unknown 3, total 10. Earlier attempts (real-run-01..06) failed before any operation
and spent nothing; each directory keeps its `FAILED.txt`.

## Deviations the reviewer should weigh

1. **Ordering errors by the implementing agent.** The run-07 quorum-loss negative ran before
   the positives were done and left an unknown slot that blocked that run. The run-08 VS Code
   attempt ran while a parallel agent was doing heavy Xcode/Flutter builds; its admission
   ended `unknown`. That cause is likely but unproven (no explicit error was logged).
2. **Owner continuation.** After run-07 the owner chose to continue in a fresh run with the
   combined cap held at 10 (`verification.md`). No counter was reset.
3. **Self-attested gate.** `real-fixture-gate-NN.json` was generated by the implementing agent
   from the fixture evidence; this is why T048 needs an independent owner review.
4. **Drivers ran from the repo, not the frozen copy.** The browser/editor drivers are client
   tooling; the runner and all production roles ran from the frozen, hash-checked source.
5. **Harness and product fixes found during REAL work** (all committed with tests where
   applicable): Docker `max-size=-1` log option; HA member factory executor guards; HUD
   mobile-enrollment cluster-mode contract and auth context; HUD driver label locators;
   editor test races; iOS harness Keychain entitlements; recovery test timing.
6. **Unmeasured / unqualified:** pure election time (the measured values include 2 s polling),
   300 ms RTT availability (it refuses beyond the 3 s admission window), host clock steps,
   WAN/regions (R09), physical iPhone/Android, Windows/WSL, other model profiles.
