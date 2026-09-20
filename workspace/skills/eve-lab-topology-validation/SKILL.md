---
name: eve-lab-topology-validation
description: Validate EVE-NG topology designs and enforce final delivery structure. Use when reviewing a design, checking build readiness, producing the final design output, building an implementation plan, or running topology QA before implementation.
---

# EVE Lab Topology Validation

Use this skill for the **final QA and delivery** phase of topology work.

## Workflow

1. Run the decision gate in `{baseDir}/references/decision-gate.md`.
2. Produce the required output sections from `{baseDir}/references/output-structure.md`.
3. Run the topology checks in `{baseDir}/references/checklists.md`.
4. If the design will be implemented, use the ordered build plan from `{baseDir}/references/build-and-config-rules.md`.

## Guardrails

- Do not approve build work while unresolved gate items remain.
- State PASS, WARN, or FAIL directly.
- Put unresolved items in the final risks/open-questions section; do not silently skip them.

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
