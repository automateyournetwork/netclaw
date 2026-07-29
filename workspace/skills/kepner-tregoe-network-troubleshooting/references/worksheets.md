# Record templates and facilitation

Emit reasoning as structured records so the next agent/human inherits the logic, not just the conclusion.
Fill every field; write "none" where a cell is genuinely empty (an empty IS-NOT is often the point).

## Situation Appraisal record

```
CONCERNS (single & specific):
  C1: <deviation/decision/plan>   S:<H/M/L> U:<H/M/L> G:<H/M/L>  rank:<n>  route:<PA/DA/PPA> owner:<who> action:<now>
  C2: ...
CORRELATION NOTES: <which concerns share a time+location signature = one root; which outlier needs its own check>
```

## Problem Analysis record

```
PROBLEM: <object> — <defect>

SPECIFICATION
  WHAT   IS: <...>   IS-NOT: <...>
  WHERE  IS: <...>   IS-NOT: <...>
  WHEN   IS: <...>   IS-NOT: <...>
  EXTENT IS: <...>   IS-NOT: <...>

DISTINCTIONS/CHANGES: <what differs about the IS side; what changed and when>

CANDIDATE CAUSES → TEST
  - <cause>: IS? <y/n> | IS-NOT? <y/n> | assumptions:<...> → <keep/weak/eliminated>

MOST PROBABLE CAUSE: <cause>
VERIFICATION: <exact read-only command/query/test + expected result>

INCIDENT FIX (fast, reversible): <action + rollback>          [needs authorization before executing]
PERMANENT FIX: <route to Decision Analysis if options exist>
```

## Decision Analysis record

```
DECISION: <choice + scope>

MUSTs (mandatory, measurable): <...>
WANTs (weighted 1-10): <want (wt)> ...

ALTERNATIVES:
  <alt>: MUST screen <PASS/FAIL — which MUST> | weighted-WANT total <n>
  ...
ADVERSE CONSEQUENCES OF LEADER: <problem — P×S — mitigation>
DECISION: <choice> — <why score AND risk review agree>
```

## Potential Problem Analysis record

```
PLAN/CHANGE BEING PROTECTED: <...>

  POTENTIAL PROBLEM: <...>  P/S:<.../...>
    LIKELY CAUSE: <...>
    PREVENTIVE (on cause): <...>
    CONTINGENT (on effect): <...>  TRIGGER: <observable> OWNER: <who>
  ...
POINT OF NO RETURN: <clock/condition by which success must show or rollback executes>
```

## Facilitation script (live incident bridge)

1. **Appraise before diagnosing** (60–90s): list distinct concerns, one line each; rate S/U/G; what's
   rank 1, and is it a cause, a choice, or a symptom of another concern?
2. **Specify before theorizing**: before anyone names a cause — where IS it, where could it but IS-NOT?
   when did it start, when last fine? what's affected, what comparable thing isn't? Put the grid where all
   can see it.
3. **Collect causes, then test**: for each — does it explain the IS *and* the IS-NOT? what are we
   assuming? Eliminate out loud.
4. **Verify before touching anything**: what one read-only test/log confirms this cause? Get it before
   changing state.
5. **Separate incident fix from permanent fix**: fastest reversible action that stops the bleeding; the
   proper fix is a separate planned decision.
6. **Protect the permanent fix**: before scheduling — what could go wrong, what prevents each cause,
   what's the trigger and owner for each contingency?
