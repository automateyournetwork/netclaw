# R04 — GCP cloud member: NetBox and subnet, hosted model

- **Roadmap item:** 2 — Border and cloud member in GCP (NetBox; subnet)
- **Depends on:** R03
- **Gate:** human review before R05

## Specify input

Add a cloud execution member in GCP that reads from a NetBox instance through its
own broker-held API token and performs a subnet task, using a hosted model behind
the guard. It attaches to the Border like any member, over iN2N. This shows that
execution placement and inference location are independent of where the Border
runs.

User stories:
- P1: The owner approves a bounded NetBox device read and sees correct results.
- P1: The owner approves a subnet task and the result is independently checked.
- P1: The NetBox token never reaches the Border or the model context.
- P2: Losing the member is reported cleanly, with no retry storm.

## Clarify: decisions (recommended default first)

1. Placement: a separate VM in a separate subnet from the Border, giving a real
   failure domain (Thermidor's NetBox member was a container on the Border's VM).
   [HUMAN: cost]
2. Meaning of "subnet": both a NetBox IPAM prefix read and the bounded subnet
   calculator, read-only. [HUMAN confirm]
3. NetBox instance: containerized NetBox in GCP seeded to match the CML lab, or
   your existing NetBox. [HUMAN]
4. Model: `claude-haiku-4-5-20251001` behind the guard (Thermidor-qualified);
   other models recorded as unqualified.
5. Transport for a member in the same VPC: use the registered direct endpoint like everyone
   else for uniform qualification; a VPC-private path is a later, separately
   qualified option.

## Plan notes

- Reuse the R03 role contract; the cloud member module is the one Azure and AWS
  repeat.
- NetBox write endpoints must be unreachable through the broker's allowed set.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Workload | Approved NetBox device read correct against the source; subnet result independently verified |
| Credentials | NetBox token present only in the member's broker; absent from Border, transcripts and model context |
| Scope | NetBox write calls and unknown object reads refused |
| Topology | Member refuses connections from other members; no listener reachable from outside |
| Failure | Member stopped: Border reports unavailable, no automatic replay; restart reattaches |
| Cost | Added monthly cost recorded |
