# R19 — Shared network knowledge base

- **Roadmap item:** 11 — rest of issue (shared knowledge)
- **Depends on:** R18
- **Gate:** human review before R20

## Specify input

The team shares a persistent knowledge base: topology and relationships, device
inventories and platforms, configuration dependencies, procedures, root causes,
validated solutions and workarounds, standards, and incident history. The agent
can propose that a personal finding is reusable, but publishing requires the
author's explicit confirmation and then review and approval. Every entry carries
its source, author, reviewer, timestamps, affected devices and technologies,
validation status and confidence, and links to anything it supersedes. Search is
semantic, near-duplicates are merged or flagged, and stale entries are marked.

When an entry matches a new problem, the agent explains why it is relevant and
validates the current environment with fresh reads before recommending or
executing anything. Unverified AI conclusions never become authoritative.

User stories:
- P1: Engineer A resolves an intermittent ISE authentication failure, publishes
  the finding, and a reviewer approves it.
- P1: Weeks later Engineer B hits a similar issue; the agent retrieves the entry,
  shows its provenance and runs verification reads before suggesting the fix.
- P2: Outdated entries are superseded and clearly labeled.

## Clarify: decisions (recommended default first)

1. Reviewers: the Approver role from R17.
2. Storage: RAG collections with a typed entry schema, separate from personal
   memory.
3. Freshness: device-linked entries are flagged stale when NetBox or observed
   device versions change.
4. Export over eN2N: off by default; feature 064 knowledge cards can expose
   approved entries only by explicit choice.
5. Deduplication threshold and merge rules.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Lifecycle | Propose, confirm, review, approve, publish, supersede |
| Reuse | ISE scenario end to end, including verification reads before any recommendation |
| Authority | Unapproved entries never presented as authoritative |
| Privacy | Personal memory never published without the author's confirmation |
| Search | Semantic retrieval and deduplication behave as specified |
| Freshness | Stale flags appear when linked device facts change |
