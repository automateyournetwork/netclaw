# Potential Problem Analysis (PPA) — full method

Use PPA on a plan that is **decided and about to be executed** — a maintenance window, cutover,
migration, upgrade. It is the only forward-looking process: what could go wrong, and how do we protect
against it before it does? It turns a runbook from a list of steps into steps + failure modes +
contingencies.

## Prevention vs contingency — the core distinction

- **Preventive action**: reduces the **probability** a cause occurs. Acts **before** the problem, **on the
  cause**. (Take + test-restore a backup before an upgrade.)
- **Contingent action**: reduces the **impact** if the problem occurs anyway. Acts **after** the problem,
  **on the effect**. (Have the tested rollback one command away.)

You need both. Prevention is never perfect; contingency without prevention is planning to fail.

**Every contingency needs an observable trigger and a named owner.** "If BGP hasn't reconverged within 5
min of cutover, execute rollback" is a trigger. "Roll back if it looks bad" is not.

## Six steps

1. Identify vulnerable areas (steps that are new, complex, tightly timed, dependent, or failure-prone).
2. List specific potential problems in those areas.
3. Rate probability × seriousness; focus on high-P or high-S.
4. Identify likely causes of each.
5. Set **preventive** actions (on the causes).
6. Set **contingent** actions (on the effects) with **trigger + owner**.

## Worked example — HA firewall firmware upgrade (abridged)

| Potential problem | P/S | Preventive (on cause) | Contingent + trigger |
|---|---|---|---|
| Config doesn't migrate cleanly | M/H | Read deprecation notes; validate vs upgrade matrix; test migration on a VM clone | Trigger: post-upgrade policy audit shows breakage → restore staged backup, abort. Owner: change lead |
| No clean rollback point | L/H | Full config+system backup, **test-restore** it before the window | Trigger: any need to roll back → restore verified backup / prior partition |
| HA split-brain / both-active | M/H | Follow vendor HA sequence (upgrade passive first, fail over, then primary); verify heartbeat health first | Trigger: duplicate-IP/both-active alarm → force one unit standby; isolate if needed. Owner: on-console |
| Tunnels don't re-establish | M/H | Pre-stage expected phase-1/2 params; partner NOC on standby | Trigger: tunnel down >5 min → apply known-good config; escalate to partner bridge |
| Window overruns | M/M | Time-box phases with go/no-go; rehearse to estimate duration | Trigger: reach **point-of-no-return clock** without green primary → full rollback, reschedule |

The window isn't longer to execute; it's **survivable** because each response is pre-decided, not
improvised at 2 a.m.

## Worked example — cloud/management-plane migration (abridged)

Recurring strongest preventive pattern: **keep the old thing alive and reachable until the new thing is
proven** — batch migration with the old plane retained; a canary site before wider rollout; policy
export+diff before/after adoption; a retained out-of-band management path. Contingencies trigger on: a
device unmanaged > X min (revert that device); migration idle past a set date (escalate); canary traffic
failures (hold rollout, reconcile diff).

## Potential Opportunity Analysis (POA) — the mirror

Apply the same structure to upside: where could the plan go *better* than expected, what would cause that,
and what **promoting** (make it more likely) and **capitalizing** (seize it) actions to take. E.g. canary
automation beats the deploy-time estimate → instrument the canary to *prove* the saving (promoting) +
pre-approve an accelerated rollout and early old-stack retirement (capitalizing). Most teams plan
exhaustively for downside and not at all for upside, so good surprises go unexploited.

## Postmortems as retrospective Problem Analysis

A postmortem is PA after the fact with pressure removed. Specify in IS/IS-NOT terms, then **separate the
trigger from the latent conditions**:

- **Trigger**: the single change/event that set it off (e.g. a fat-fingered command).
- **Latent conditions**: the missing guardrails that let the trigger become an outage.

Corrective actions must target the **latent conditions** (systemic) — those make the next, different
trigger harmless. A postmortem whose only action is "be more careful" found a trigger and no cause.
Prompt set: specification → trigger → latent conditions → detection (why did we learn of it that way?) →
corrective actions (systemic vs local).

## Discipline reminders

- Separate preventive from contingent for every item.
- Every contingency: observable trigger + named owner.
- Prioritize by probability × seriousness.
- Never remove the fallback until the replacement is verified.
