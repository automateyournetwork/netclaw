# R11 — Azure multi-region

- **Roadmap item:** 5 — Azure (multi)
- **Depends on:** R10
- **Gate:** human review before R14

## Specify input

Repeat R09 on Azure: three Borders in three Azure regions form a cluster with
three voters; every Azure-stage member attaches to all three; member-to-member
refused; region loss drills pass with no replay.

## Clarify: decisions (recommended default first)

1. Regions. [HUMAN]
2. Same decisions as R09, with measured Azure WAN timings.

## Acceptance evidence

All R09 acceptance rows, re-run on Azure, plus cost and teardown.
