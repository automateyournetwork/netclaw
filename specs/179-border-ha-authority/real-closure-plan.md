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
| Fenced restore | actual owned isolation + new generation from a stale snapshot; real unknown/reservations retained; no speculative execution | restore tooling | 2 reservations: A positive, then B unknown-producing (B last) | **yes** |
| Topology / trust (partial) | live role/member/external/etcd negatives against the real cluster | existing negatives | 0 | no |

Order inside the cap: no-approval rows -> capacity -> retired -> partitions -> lost result/ACK ->
unknown-producing rows each in their own fresh run (stale guard, clock, unknown commit, restore).
That is 12 approvals for 10 slots: the owner must either raise the cap by 2 or merge/skip rows
(asymmetric second approval and one lost-ACK approval are the first to merge).

Infrastructure lanes (source-only until a cluster window), now committed: (A) per-Border proxy topology with
cut/heal/delay and observed byte counters (`labs/ha/real_proxies.py`, `labs/ha/REAL-PARTITIONS.md`); (B) qualification-only
instrumentation (held submit, clock input, reply-drop, delivery faults) as separate modules that never enter product paths
(`labs/ha/real_instrument.py`, `labs/ha/real_role_launcher.py`, `labs/ha/REAL-INSTRUMENTATION.md`); (C) cluster driver for
capacity + retired rows; (D) default-off fenced-restore driver (`labs/ha/real_restore.py`, `labs/ha/REAL-FENCED-RESTORE.md`),
supported by the optional plan `voters_dir` indirection in `labs/ha/real_runtime.py` (absent = unchanged). Every source change
needs a new frozen packet and fixture gate; machine must be idle during approvals.

## ⚠ R09 RELEASE GATE: client builds MUST be updated for multi-region HA Borders

Owner instruction (2026-11-08): at the R09 checkpoint (three-region / multi-region deployment of
these HA Borders) the **VS Code extension, the Mobile app and the HUD/Border source builds WILL need
a published update**. This is a hard gate, not a nice-to-have. Until those builds ship, do not
announce, enable or document multi-region HA as available to end users.

What must be true before R09 is called released (verify each; none is done by R08):
1. **VS Code extension** (source version now 1.6.1, `extensions/netclaw-vscode`): a build that includes
   the cluster-aware paths proven in R08 (signed-manifest pinning, native endpoint replacement,
   retained-reference recovery, no-quorum/stale-review states) AND the multi-region additions R09
   defines (region-aware endpoint lists, failover UX). Bump the version, build, publish through the
   owner-approved channel, and check the marketplace-installed version against source.
2. **Mobile app** (source 1.0.4+7, `mobile/netclaw-mobile`): same, including enrollment against a
   multi-region cluster descriptor, `select-node` across regions, and background/cold recovery. Needs
   an owner-approved TestFlight/App Store submission; App Store review time is outside our control.
3. **HUD / Border source** (main is at 1.19.1 after PRs #335-#337; this branch's HUD fixes include the
   cluster-mode mobile-enrollment contract fix): ship the refreshed HUD build with the Border release
   so every Border serves the fixed enrollment route.
4. Re-run the client journeys of `evidence-matrix.md` (HUD, VS Code, iOS) against the **published**
   builds on the multi-region topology, not against repo checkouts.
5. Owner approval for every outward-facing release step; nothing is published, pushed live or
   announced by an agent without it.

Known R08 facts to carry into R09: no extension or app product code changed in R08 except the HUD
enrollment fix; the shipped client versions were not verified against source during R08; R08 used a
single-host loopback topology (no WAN, no regions, no public DNS/TLS).
