# Integrated workflow — one incident, all four processes

Real incidents flow **SA → PA → DA → PPA**. The hand-offs are where undisciplined teams blur cause into
fix into risk and get all three wrong. Watch for them.

## The incident

Monday 09:20. E-commerce checkout failing intermittently for customers; payments API timing out; internal
warehouse app slow; a DC core switch logging errors; the edge firewall HA flapped this morning. Five loud
symptoms across revenue-critical systems. Everyone has a theory.

## Phase 1 — Situation Appraisal (impose order)

Clarify and rank before diagnosing. The pattern — checkout + payments + warehouse app, plus a flapping
core switch and edge firewall — reads as **one infrastructure fault expressing in many apps**, not five
independent problems. Route the two infra concerns (core switch errors; firewall HA flap) to PA as the
likely common cause; **hold** the three app symptoms rather than opening three parallel investigations.
Not chasing the revenue symptom directly is the move a panicked bridge never makes.

## Phase 2 — Problem Analysis (find the cause)

Specify the infra deviation (core-switch errors + HA flap, onset ~06:30).

| Dim | IS | IS-NOT |
|---|---|---|
| WHAT | Intermittent loss + HA heartbeat loss; output drops | No hard link-down; no CRC/input errors; DC-CORE-2 clean |
| WHERE | The DC-CORE-1 ↔ firewall segment | DC-CORE-2 path clean; access layer clean |
| WHEN | Since ~06:30; bursts track morning traffic ramp | Fine over the weekend; fine overnight |
| EXTENT | Worsens as utilization rises; everything on that segment degrades | Redundant path unaffected; not 100% loss |

Change: a weekend maintenance added LAG members between DC-CORE-1 and the firewall pair; onset is the
first business-day ramp after it. Output-drops + heartbeat-loss under load with **zero physical errors** →
logical/forwarding, not a bad optic. **Most probable**: the LAG change left a mismatched member / L2 loop
that intermittently floods the segment under load, starving the HA heartbeat → firewall flaps → apps fail
intermittently. **Verify**: STP/interface counters show flooding + TCN churn correlating with load bursts.
Now the three held app symptoms are explained as one root — without ever being investigated separately.

## Phase 3 — Decision Analysis (choose the fix)

Cause known; choose under active revenue impact (time-boxed, but still MUST/WANT — pressure is exactly
when skipping the method causes a second outage).

- MUSTs: stops the flooding/flap now; no new outage to the redundant path; executable in minutes.
- WANTs: preserves bandwidth gain (5); lowest collateral risk (9); reversible (7).

Alternatives: **A** shut the new LAG members (revert to known-good pre-change topology); **B** reconfigure
LAG hashing live (fails "minutes/low-collateral" MUST — defer to a window); **C** fail all to DC-CORE-2
(bigger blast radius). On the heavily-weighted collateral-risk and reversible WANTs, **A wins** — it ends
the incident instantly and reversibly. The proper LAG reconfiguration (B) is a **separate planned
decision**. Conflating incident fix and permanent fix ("do it properly now" by tuning live) is how teams
extend outages.

## Phase 4 — Potential Problem Analysis (protect the permanent fix)

The permanent fix (re-add bandwidth via a correctly configured LAG) is a planned change → PPA before the
window. Preventive: lab/stage the exact LAG config; verify member consistency; enable one member at a
time. Contingent: trigger on any flooding/TCN churn on enable → shut the member, revert (owner: change
lead). Plus HA-flap and insufficient-bandwidth contingencies with triggers.

## The hand-offs, made explicit

| Transition | Question that changed | What breaks if blurred |
|---|---|---|
| SA → PA | "what do we work on?" → "what caused the infra fault?" | Chasing five app symptoms as five problems; never seeing the one root |
| PA → DA | "what caused it?" → "which fix?" | Applying the first fix before the cause is verified — fixing a symptom |
| DA → PPA | "which fix?" → "how do we protect the permanent fix?" | Re-doing the LAG change with the same lack of staging that caused the incident |

One badly-staged change produced five loud symptoms. The K-T team reaches the root in one investigation,
stops the incident with a reversible known-good action, and protects the permanent fix from repeating the
mistake. The other team opens five tickets, argues firewall-vs-ISP, reboots something, and re-triggers the
outage next weekend.
