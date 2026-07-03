---
name: eve-lab-topology-design
description: Design EVE-NG lab topology and coordinate the design workflow. Use when the user asks for lab design, architecture advice, topology planning, design review, or a build plan, especially when requirements, trade-offs, or validation need to be structured first.
---

# EVE Lab Topology Design

Use this skill as the **entrypoint** for EVE-NG topology design work.

## Core workflow

1. Classify the request: campus, branch/WAN, ISP/SP, data center, or hybrid.
2. If requirements are incomplete, read `{baseDir}/references/discovery-workflow.md` and gather only the missing details.
3. Summarize requirements and assumptions before proposing a design.
4. Present relevant options and trade-offs; recommend one design.
5. Produce both the physical topology and the logical/protocol topology.
6. Before calling the design complete, read `{baseDir}/references/validation-workflow.md` and run the required QA structure.
7. If a `.unl` exists or is built, validate it with `{baseDir}/scripts/validate_unl_topology.py` and the notes in `{baseDir}/references/unl-validator.md`.

## Guardrails

- Never jump into build or config when requirements are vague.
- Work at three layers every time: physical topology, logical/protocol topology, and lab/platform capability.
- State assumptions explicitly.
- Do not include protocols or services unless requested, chosen, or clearly labeled as assumptions.
- Match icons and platform choices to the actual device role.

## When to read references

- Read `{baseDir}/references/discovery-workflow.md` for question flow, defaults, design options, domain guidance, and image selection.
- Read `{baseDir}/references/validation-workflow.md` for output sections, QA gates, build-plan rules, and topology checks.
- Read `{baseDir}/references/unl-validator.md` when you need validator usage, expected outputs, or requirements-file schema.
