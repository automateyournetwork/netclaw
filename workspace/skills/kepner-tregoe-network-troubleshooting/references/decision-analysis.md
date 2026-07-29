# Decision Analysis (DA) — full method

Use DA to choose among alternatives — a fix (once the cause is verified), a design, a remediation path, a
vendor. Do **not** run DA before PA when the cause is unknown: choosing a fix for an unverified cause is
deciding what to do about an undiagnosed problem.

## Six steps

1. **State the decision** — one sentence: the choice + scope.
2. **Objectives → MUSTs and WANTs**.
   - **MUST**: mandatory, pass/fail, **measurable**. Any option failing a MUST is out, regardless of merit.
     Test: if you'd still consider an option that fails it, it's not a MUST — it's a WANT.
   - **WANT**: desirable, **weighted 1–10** by importance.
3. **Generate alternatives** — include "do nothing" and sensible hybrids.
4. **Screen against MUSTs** — eliminate failures now, before any scoring, on objective bars.
5. **Score survivors on weighted WANTs** — score each 1–10 per WANT, ×weight, sum → ranked shortlist
   (not yet the answer).
6. **Assess adverse consequences, then choose** — for top contenders list what could go wrong, rate
   probability × severity, and let the risk review (not the raw score alone) drive the call. The winner
   is the **best score that survives its own risk assessment**.

Weight WANTs **before** scoring, never after (setting weights once you see scores back-fits the answer).

## Worked example 1 — Remediating a weak IPsec tunnel (cause known)

Decision: replace IKEv1/AES-128/SHA-1 site-to-site tunnel with a policy-compliant one, acceptable risk.

- **MUSTs**: result is IKEv2 + AES-256/SHA-256; interops with partner device; ≤30-min change; no new HW.
- **WANTs**: minimize downtime (9); low coordination-failure risk (8); minimal ongoing complexity (6);
  fast to schedule (5).

MUST screen: "SASE overlay" fails (partner not onboarded, weeks) and "do nothing" fails (compliance) —
both eliminated before scoring. Survivors: **A** in-place proposal upgrade vs **B** parallel new tunnel
then migrate. Weighted WANTs: **B wins 203 vs 188** — it scores higher on the heavily-weighted downtime
and coordination-risk WANTs because a parallel build validates the new tunnel *before* cutover and keeps
the old tunnel as a fallback. Adverse-consequence review of B (selector overlap, partner delay, forgotten
teardown) — all mitigable and non-service-affecting. **Choose B.** Score and risk review agree.

## Worked example 2 — Access-layer refresh (design choice)

MUSTs: central cloud management across all sites; multigig access; within FY budget. Top WANTs: low
per-site deploy effort (9); zero-touch provisioning quality (8); 5-yr cost incl. licensing (8); roadmap
fit for automation (6). A naive "cheapest per port" comparison picks the wrong box; the MUSTs remove any
option lacking cloud mgmt/multigig, then the weighted WANTs push toward lowest deploy effort + 5-yr
licensed cost. The winner is usually the cheapest to **operate at fleet scale**, not the cheapest to buy.

## Worked example 3 — SD-WAN / SASE platform selection (high-stakes, hard to reverse)

Decision: standardize one SASE platform across 60 sites over 5 years, within budget, deployable by the
existing team.

- **MUSTs**: integrated SASE (SD-WAN+SWG+ZTNA+FWaaS) from one policy plane; central cloud orchestration
  for all 60 sites; meets data-residency/compliance in all regions; interops during migration; in budget.
- **WANTs**: operational simplicity / single pane (9); 5-yr TCO incl. licensing & bandwidth (9); support
  & local presence (7); API/automation & NetOps integration (7); deployment speed (6); roadmap/viability (5).

MUST screen eliminates best-of-breed two-vendor (fails single-plane) and incumbent add-on (no cloud
ZTNA/SWG) — **if** you won't eliminate the two-vendor option, then "single plane" was never a real MUST
and belongs in WANTs; the method forces that honesty. Survivors V1/V4 score close (322 vs 310). **A close
score means the adverse-consequence step decides, not the total.** V1's top risk (lock-in pricing) is
mitigable contractually (price protection + data-portability terms) → **choose V1 contingent on those
terms.** A feature-count spreadsheet would pick the most checkboxes; the method picks the option cheapest
and safest to operate for 5 years.

## Discipline reminders

- No DA before a verified cause when the cause was the question.
- Keep MUSTs few, mandatory, measurable — soft MUSTs wrongly eliminate good options.
- Weight before scoring.
- Never skip the adverse-consequence step — a top score with an unassessed catastrophic downside is how
  good scores produce bad outcomes.
