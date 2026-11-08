# Spec 179 acceptance packet (T048): AWAITING OWNER REVIEW

Prepared 2026-11-08 by the implementing agent. **No owner review has been recorded.** Do not
treat this document as acceptance. R09 (three-region GCP) must not start until an owner
records a decision below.

## What passed
- Source + fixture: complete authority/admission/ledger/recovery implementation; fixture matrix
  runs (core, Raft network, Raft recovery, retire, process, fenced restore, wire recovery).
- REAL (actual guard + qwen3:0.6b + native subnet tool, independent model-access-log counter):
  3 Borders each carried a signed operation; leader SIGKILL with a distinct post-loss operation;
  quorum-loss refusal; member death after dispatch with no replay; full restart preserving
  completed receipts and the unknown.
- Clients: HUD (Chrome 156), VS Code 1.109 and native iOS each completed a real operation and
  status-only recovery (authority change, no quorum, stale review) with zero extra model calls.
- Final suites: see `verification.md` (T044 section).

## What did not pass or is not claimed
See `evidence-matrix.md`: 7 of 18 rows REAL pass, 2 partial, **9 fixture-only gaps**
(minority/asymmetric/three-way partitions, clock uncertainty, unknown consensus commit, lost
result/ACK, retired node returns, fenced restore, capacity/storage). The spec rule forbids
waiving them. The REAL budget (10 operations) is spent, 3 slots are held `unknown`, and none
was reset.

## Decisions needed from the owner
1. Accept the 9 gap rows + 2 partials as documented limitations for R08 **or** authorize more
   REAL budget and a follow-up run (an unknown slot cannot be reset; a new run needs a new,
   explicit cumulative cap).
2. Accept the self-attested fixture gate (`real-fixture-gate-NN.json`) or require independent
   re-review of the fixture matrix.
3. Decide whether to bump versions (source 1.18.7, editor 1.6.1, Mobile 1.0.4+7 are unchanged
   although HUD/HA source and harness files changed).
4. Confirm R09 may start.

## Owner review record
Reviewer: ____________  Date: ____________  Decision: ACCEPT / ACCEPT WITH LIMITS / REJECT
Notes:

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
