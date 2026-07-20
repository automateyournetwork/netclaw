# Situation Appraisal (SA) — full method

Use SA when the situation is cluttered — many concerns at once, unclear priorities, unclear whether
things are related. It is triage: run it *before* you know whether you face a cause problem, a decision,
or a risk. Do not deep-dive one alarm while others grow.

## Four steps

1. **List concerns** — enumerate everything needing attention: deviations, decisions, plans to protect,
   unexplained observations, half-finished changes. Don't filter yet.
2. **Separate & clarify** — break compound concerns into single, specific ones. A concern is clarified
   when you can name the exact deviation or exact choice. "Site is down" is not a concern; the specific
   deviations that make you say so are.
3. **Set priority** — rate each on three independent dimensions and rank.
4. **Plan next steps & route** — for each concern decide the process (PA/DA/PPA), the owner, and the
   immediate action. Some need only an interim fix; some full analysis; some can wait. Every concern
   exits SA with a named route and owner.

## Priority dimensions — Serious / Urgent / Growth

Rate each separately (High/Med/Low); "importance" is three questions that pull differently.

| Dimension | Question | Network read |
|---|---|---|
| **Seriousness** | Current impact if we do nothing now? | Users, revenue, SLA, security exposure, blast radius |
| **Urgency** | How much time before we must act? | Hard deadline — expiring cert, closing window, market open, compliance cutoff |
| **Growth** | Is it getting worse, how fast? | Memory leak, filling partition, spreading MAC-flap, widening BGP flap |

Concerns High on two or three rise to the top. A **High-Growth** item earns an early containment action
even at low current seriousness — it's tomorrow's High-Seriousness incident.

## Alert-storm correlation

When dozens of alarms fire at once, the key SA skill is separating **correlated symptoms** from
**independent concerns**:

- **Collapse** alarms sharing a common time signature *and* a common location into their single root.
  (All device/BGP/server-down alarms in the same rack rows, same 14:07 onset, same power phase → ONE
  concern: the power event. The rest are its symptoms — don't dispatch them separately.)
- Then **hunt the outlier**: the one alarm that does *not* fit the pattern (different location/time). It
  is either noise or a **second, independent incident hiding in the storm** — verify it on its own. A
  second incident masked by a storm is how a bad afternoon becomes a bad week.

## Worked example — 2 a.m. on-call shift

Five signals arrive. Clarify, then rank, then route.

| Concern (clarified) | S | U | G | Rank / route |
|---|---|---|---|---|
| C1 FortiGate HQ CPU 95%+ for 20 min | H | H | H | 1 → PA (likely common cause of C2/C3) |
| C2 Finance VLAN can't reach ERP (other apps fine) | H | M | L | 2 → PA, but hold — may be symptom of C1 |
| C5 Syslog partition 88%, +3%/h | M | M | H | 3 → obvious cause → extend/rotate NOW (kills a high-growth item) |
| C3 Branch-7 WAN flapping (SD-WAN failed to LTE) | M | L | M | 4 → service protected; defer PA |
| C4 Portal cert expires in 34 h | H | L | None | 5 → PPA at day shift; add T-7d alarm |

C1 wins (High×3, plausible common root). C5 outranks C3 on Growth (self-inflicts a monitoring blackout in
4 h). C4 has the highest consequence but 34 h runway and zero growth → correctly last tonight. Result:
three of five concerns resolved or safely parked without any deep investigation — the point of triage.

## Common traps

- Treating the loudest/reddest alarm as highest priority (alert severity is a static threshold, not live
  blast radius) — re-rank by S/U/G.
- Failing to separate — "site down" hides three faults with three owners.
- Analyzing before triaging — appraise the whole board first, deep-dive second.
- Ignoring Growth — the trivial-but-doubling item ambushes the next shift.
- No explicit routing — a concern with no route and owner gets forgotten.
