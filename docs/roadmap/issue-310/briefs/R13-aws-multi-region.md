# R13 — AWS multi-region

- **Roadmap item:** 6 — AWS (multi)
- **Depends on:** R12
- **Gate:** human review before R14

## Specify input

Repeat R09 on AWS: three Borders in three AWS regions form a cluster with three
voters; every AWS-stage member attaches to all three; member-to-member refused;
region loss drills pass with no replay.

## Clarify: decisions (recommended default first)

1. Regions. [HUMAN]
2. Same decisions as R09, with measured AWS WAN timings.

## Acceptance evidence

All R09 acceptance rows, re-run on AWS, plus cost and teardown.
