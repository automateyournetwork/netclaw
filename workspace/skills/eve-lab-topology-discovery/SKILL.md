---
name: eve-lab-topology-discovery
description: Gather missing requirements for EVE-NG topology design. Use when the request is vague or incomplete, when you need discovery questions, defaults, trade-off framing, image recommendations, or domain guidance before proposing a topology.
---

# EVE Lab Topology Discovery

Use this skill only for the **requirements and options** phase of topology work.

## Workflow

1. Decide whether the request is vague or already specific.
2. If vague, ask only the missing questions from `{baseDir}/references/question-bank.md`.
3. Offer labeled defaults from `{baseDir}/references/defaults-and-options.md` when the user skips details.
4. Summarize the requirements into a connectivity matrix, required links list, and resilience declaration.
5. If platform/image selection matters, read `{baseDir}/references/domain-and-image-guidance.md`.

## Guardrails

- Never ask more than 5 questions in one turn.
- Group related questions.
- Do not generate a generic topology before topology type and scale are known.
- Label all assumptions explicitly.

## Failure Behavior

- On a tool error (timeout, unreachable host, malformed response), report the failure and its error message directly to the user rather than fabricating or guessing at results.
- All tools here are read-only, so a failed call has no side effects — it's safe to retry once after confirming connectivity, but don't loop indefinitely on repeated failures.
