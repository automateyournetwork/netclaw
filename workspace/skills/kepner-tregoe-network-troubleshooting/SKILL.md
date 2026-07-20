---
name: kepner-tregoe-network-troubleshooting
description: >-
  Structured Kepner-Tregoe (K-T) rational-process methodology for network operations. Use this
  whenever diagnosing a network fault, outage, or performance deviation; triaging multiple
  concurrent alarms or an alert storm; choosing between remediation options, designs, or vendors;
  or planning and protecting a network change, migration, or upgrade. Apply it to ANY network
  troubleshooting task — routing/BGP, wireless/RF, firewall/security, SD-WAN/overlay, DNS/DHCP,
  cloud/hybrid connectivity, or performance — even when the request is only "why is X down",
  "figure out what's wrong", or "the network is slow". It exists to stop guess-and-swap
  troubleshooting: it forces you to specify the fault's boundary before hypothesizing, test causes
  against evidence, verify the root cause before changing anything, and separate the fast reversible
  incident fix from the permanent fix. Consult it before making state-changing actions on a network.
license: Apache-2.0
user-invocable: true
---

# Kepner-Tregoe for Network Troubleshooting

## What this skill is for

This skill gives a network-troubleshooting agent a disciplined method so it reaches a **verified root
cause before acting**, instead of pattern-matching to a familiar cause and swapping components. The
entire value is *sequencing and separation*: appraise before diagnosing, specify before theorizing,
verify before fixing, decide before acting, protect before executing.

You will usually have tools that can read network state (telemetry, device configs, routing/ARP/session
tables, logs, packet/flow data, inventory/CMDB). Use those tools to **gather the evidence that fills the
specification** — do not reason from memory when you can observe. The method tells you *which* evidence
matters and *what to conclude from it*.

## Non-negotiable principles

1. **Specify before you hypothesize.** Never name a cause until you have drawn the fault's boundary
   (what IS affected vs. what IS-NOT). The boundary is where the cause hides; skipping it is why
   troubleshooting drifts from symptom to symptom.
2. **The IS-NOT carries the answer.** Recording what is broken eliminates almost nothing. Recording the
   *nearest comparable thing that could be broken but isn't* eliminates whole classes of cause in one line.
3. **Test every candidate cause against the whole specification.** A cause that explains what IS but
   contradicts an IS-NOT is wrong, however plausible. Prefer the cause that fits with the **fewest
   assumptions**.
4. **Verify in the real world before you fix.** A cause proven on paper is a hypothesis until a log line,
   a counter, a table entry, or a controlled test confirms it. Fixing an unverified cause "fixes" a
   symptom and leaves the root.
5. **Separate the incident fix from the permanent fix.** Stop the bleeding with the fastest *reversible*
   known-good action; the proper fix is a separate, planned decision. Conflating them extends outages.
6. **Protect every change before executing it.** Prevention + contingency with explicit triggers.
7. **Do not take state-changing actions without authorization.** Diagnose and recommend freely. Before
   any config change, failover, reboot, or traffic-affecting action, confirm with the human/operator
   unless you have standing authorization for that specific action. Read-only investigation needs no
   confirmation.

## Step 0 — Route to the right process

Ask these in order and stop at the first "yes". Running the wrong process is the most common misuse
(e.g. debating fixes before the cause is known).

| Situation | Process | Reference |
|---|---|---|
| Several things happening at once; unclear priority or whether they're related | **Situation Appraisal** | `references/situation-appraisal.md` |
| A single deviation from expected behavior, cause unknown | **Problem Analysis** | `references/problem-analysis.md` |
| Cause known (or no fault) and you must choose among options | **Decision Analysis** | `references/decision-analysis.md` |
| An action is decided and about to be executed | **Potential Problem Analysis** | `references/potential-problem-analysis.md` |
| An incident already closed; you want the true root + systemic fixes | **Retrospective Problem Analysis** (postmortem) | `references/potential-problem-analysis.md` |

A single incident often flows **SA → PA → DA → PPA**: triage the mess, find the cause, choose the fix,
protect the fix. See `references/integrated-workflow.md` for a full worked end-to-end incident.

## Problem Analysis — the core loop (run this most often)

This is the process you will use most. Full detail and worked examples: `references/problem-analysis.md`.
Execute these steps and **emit the specification as a structured record** (template below).

1. **State the problem.** One object, one defect: "*what* is wrong with *what*." Two defects = two
   problems; split them.
2. **Build the specification (IS / IS-NOT)** across four dimensions. Use your tools to gather each cell.
   For every IS, find the **nearest** comparable case that could show the fault but doesn't.
   - **WHAT** — which object/service; which exact defect (and which defect it is *not*, e.g. resolution
     vs. reachability, drop vs. error, SYN-drop vs. mid-session hang).
   - **WHERE** — site / VLAN / interface / peer / zone / region / path; and which comparable locations
     are clean.
   - **WHEN** — first seen; last known-good; time-of-day/load pattern; and comparable times that are clean.
   - **EXTENT** — how many / how much / what proportion / trend; and how much is unaffected / not spreading.
3. **Distinctions & changes.** For each row: what is different/unique about the IS side vs. the IS-NOT
   side? Within each distinction, **what changed and when?** Changes anchored to the WHEN boundary are
   the strongest leads — but the most recent change is a *candidate*, not a conviction.
4. **Generate possible causes** from distinctions and changes only (not folklore, not the last incident,
   not the component you distrust).
5. **Test each cause** against the full spec: "If this were true, would it produce *everything that IS*
   and *nothing that IS-NOT*, with the fewest assumptions?" Eliminate any cause that contradicts an
   IS-NOT. Rank survivors by assumption count.
6. **Verify the most probable cause** with a targeted, ideally read-only observation before proposing a
   fix. Name the exact command / query / test that confirms it.

If a cause that *should* be right contradicts an IS-NOT, the specification is wrong or incomplete
(a mis-recorded IS-NOT, a blank dimension) — **re-specify, don't re-guess**. If the best cause leaves
exactly one boundary unexplained, suspect a **second, interacting cause** and re-specify that boundary.

### Fast elimination: domain signature library

Before generating causes, check the fault's signature against `references/domain-signatures.md`. It maps
common observable signatures to the cause classes they eliminate or point to, per domain (routing/BGP,
wireless/RF, firewall/security, SD-WAN/overlay, DNS/DHCP, cloud/hybrid, performance). Example: *interface
errors are zero* eliminates physical-layer causes; *auth succeeds but clients drop, band-specific* points
to RF/DFS, not RADIUS. This is Problem Analysis compressed into a lookup — use it to prune fast.

## Output format — the troubleshooting record

Always produce the reasoning as a structured record so a human (or the next agent) inherits the logic,
not just the conclusion. Use this template:

```
PROBLEM: <object> — <defect>

SPECIFICATION
  WHAT   IS: <...>        IS-NOT: <...>
  WHERE  IS: <...>        IS-NOT: <...>
  WHEN   IS: <...>        IS-NOT: <...>
  EXTENT IS: <...>        IS-NOT: <...>

DISTINCTIONS / CHANGES: <what differs about the IS side; what changed and when>

CANDIDATE CAUSES → TEST
  - <cause>: explains IS? explains IS-NOT? assumptions? → <verdict>
  ...

MOST PROBABLE CAUSE: <cause>
VERIFICATION: <exact read-only command/query/test to confirm, and expected result>

INCIDENT FIX (fast, reversible): <action + how to roll back>   [requires authorization]
PERMANENT FIX (planned decision): <route to Decision Analysis if options exist>
```

For Situation Appraisal, Decision Analysis, and Potential Problem Analysis, use the record templates in
`references/worksheets.md`.

## The other three processes (summaries; see references for full method + examples)

- **Situation Appraisal** — triage. List concerns (single & specific), rate each on **Serious / Urgent /
  Growth**, rank, and route each to PA/DA/PPA with an owner. In an alert storm, **collapse alarms sharing
  a time+location signature into their root**, then hunt the one alarm that does *not* fit the pattern —
  it is noise or a second incident. Full method: `references/situation-appraisal.md`.
- **Decision Analysis** — choosing. Define **MUSTs** (mandatory, measurable, pass/fail) and weighted
  **WANTs** (1–10). Screen alternatives against MUSTs (eliminate failures before scoring), score
  survivors on weighted WANTs, then **assess adverse consequences of the leader before committing** — the
  winner is the best score that survives its own risk review. Full method: `references/decision-analysis.md`.
- **Potential Problem Analysis** — protecting a plan. For each vulnerable step: the potential problem, a
  **preventive action** (reduces probability, acts on the cause) and a **contingent action** (reduces
  impact, acts on the effect) with an **observable trigger and a named owner**. Golden rule: **never
  remove the fallback until the replacement is verified.** Full method:
  `references/potential-problem-analysis.md`.

## When NOT to run the full method

A known, trivial fault with an obvious fix (port admin-down, full disk, obviously-expired cert) should be
fixed, not specified. Run the full apparatus when the cause is genuinely unknown, the blast radius is
large, the situation is cluttered, or a wrong move is expensive/hard to reverse. Even then, the *habit* —
"what's the IS-NOT?" and "have I verified this?" — costs nothing and should be reflexive.

## Reference files

- `references/problem-analysis.md` — Full PA method, IS/IS-NOT deep dive, six worked network faults, hard cases.
- `references/situation-appraisal.md` — Full SA method, Serious/Urgent/Growth, on-call and alert-storm examples.
- `references/decision-analysis.md` — Full DA method, MUST/WANT, three worked decisions incl. vendor selection.
- `references/potential-problem-analysis.md` — Full PPA/POA method, change/migration protection, postmortems.
- `references/domain-signatures.md` — Signature→cause lookup tables for seven network domains.
- `references/worksheets.md` — Fill-in record templates for all four processes and a facilitation script.
- `references/integrated-workflow.md` — One incident worked end-to-end through all four processes.
