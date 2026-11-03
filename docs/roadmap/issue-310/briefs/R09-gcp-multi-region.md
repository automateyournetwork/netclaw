# R09 — GCP multi-region: three meshed Borders

- **Roadmap item:** 4 — multi-region Borders; members meshed with all Borders;
  all Borders meshed
- **Depends on:** R08
- **Gate:** human review before Azure

## Specify input

Three Borders in three GCP regions (Americas, Europe, Asia-Pacific) form one
cluster. All Borders are meshed through cluster links. Every member, on-prem
pyATS, on-prem Ollama, GCP NetBox and GCP Ollama, holds an authenticated outbound
attachment to all three Borders. Member-to-member connections are refused. When a
region is lost, the surviving majority continues, members keep working through
the remaining Borders, and nothing uncertain replays.

User stories:
- P1: All four workloads from R03–R05 run through whichever Border the owner uses.
- P1: Losing any one region keeps service with no replay.
- P2: Status shows every attachment and cluster link with health.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Regions. [HUMAN]
2. Voters: three, one per region.
3. Cloud members: stay in their original region; per-region members are optional.
4. Intra-provider Border links: registered direct/private TCP with the same strict profile; measure latency;
   a VPC-private path is an explicitly configured, separately qualified option.
5. HUD: one endpoint per Border, optionally pooled behind one hostname.
6. eN2N exposure: one designated Border initially.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Mesh | 4 members × 3 Borders = 12 authenticated attachments; 3 cluster links |
| Topology | Member-to-member negative tests from every member |
| Workloads | R03–R05 workloads via each Border |
| Region loss | Each region taken down in turn: service continues, no replay |
| WAN | Measured latency, partition behavior and lease timings |
| Cost | Monthly cost for the three-region stage |
| VS Code integration | Explicit G12 impact/disposition and evidence: GCP regional Border selection and failover retain identity, capability and operation context |
| Mobile integration | Explicit G13 impact/disposition and evidence: Affected regional endpoint selection/reconnection preserves enrollment and existing operations; reasoned no-impact outcome if unaffected |
