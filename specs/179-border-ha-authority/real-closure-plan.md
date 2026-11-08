# REAL closure work package (owner decision: Option 2, 2026-11-08)

Goal: replace fixture-only evidence with REAL evidence (actual guard + model + native tool, independent
model access-log counter exported BEFORE any container removal) for the nine gap rows and two partials
in `evidence-matrix.md`. Cap: 10 further operations; unknown-producing scenarios last, one per run.
Pre-dispatch refusals proven by status read release the slot (`Budget.refused`); the reservation still counts.

| Row | REAL procedure (summary) | Needs | Approvals | Leaves unknown? |
|---|---|---|---|---|
| Capacity / storage | fill etcd backend to a real NOSPACE alarm, review then approve -> decision refused; heal; alarm cleared | NOSPACE helper from labs/ha/matrix.py | 1 | no (pre-dispatch) |
| Retired node returns | durable retirement of a Border via production authority, reconnect its old key, approve via it -> refused; current cluster records the reason | retire op from matrix.py | 1 | no |
| Minority partition | per-Border etcd/NCFED proxies; isolate the old leader from the majority, majority elects; approve through isolated old leader -> refused; counters unchanged | proxy topology | 1 | no (decision-level) |
| Asymmetric partition | both directed cuts; majority side does distinct work exactly once | proxy topology | 2 | no |
| Three-way partition | all three isolated; refuse everywhere; zero added calls | proxy topology | 1 | no |
| Stale leader (guard level) | SIGSTOP the old leader after dispatch; delayed old claim reaches the real member gate and is refused | held-submit control | 1 | **yes** |
| Clock uncertainty | controlled wall/monotonic discontinuity into the real admission gate; refused before forward/invoke | qualification-only clock input | 1 | **yes** |
| Unknown consensus commit | drop the reply after an actual commit; exact claim recovery, no new forward | reply-drop proxy | 1 | **yes** |
| Lost result / ACK | drop result delivery and ACK independently; original signed result/ACK recovered via survivor | delivery-boundary observer | 2 | no (recovered) |
| Fenced restore | actual owned isolation + new generation from a stale snapshot; real unknown/reservations retained; no speculative execution | restore tooling | 1 | **yes** |
| Topology / trust (partial) | live role/member/external/etcd negatives against the real cluster | existing negatives | 0 | no |

Order inside the cap: no-approval rows -> capacity -> retired -> partitions -> lost result/ACK ->
unknown-producing rows each in their own fresh run (stale guard, clock, unknown commit, restore).
That is 12 approvals for 10 slots: the owner must either raise the cap by 2 or merge/skip rows
(asymmetric second approval and one lost-ACK approval are the first to merge).

Infrastructure lanes (source-only until a cluster window): (A) per-Border proxy topology with
cut/heal/delay and observed byte counters; (B) qualification-only instrumentation (held submit,
clock input, reply-drop, delivery faults) as separate modules that never enter product paths;
(C) cluster driver for capacity + retired rows. Every source change needs a new frozen packet and
fixture gate; machine must be idle during approvals.
