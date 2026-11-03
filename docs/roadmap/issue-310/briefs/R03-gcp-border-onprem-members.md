# R03 — GCP Border with on-prem members (pyATS/SSH, CML)

- **Roadmap item:** 1 — Border in GCP; on-prem members
- **Depends on:** R01, R02
- **Gate:** human review before R04

Current implementation: [Spec172](../../../../specs/172-gcp-hybrid-border/spec.md).
As of2026-11-03, source, actual cloud activation, four protected reads, recovery
and teardown are complete.35/36 tasks are closed; human acceptance remains the
only gate before R04. No R03 billable resources remain; R01 is preserved.
See [verification](../../../../specs/172-gcp-hybrid-border/verification.md) and
[resume](../../../../specs/172-gcp-hybrid-border/resume.md). This brief's input
questions do not replace the ratified spec or its exact execution gates.

## Specify input

Run a NetClaw Border on a GCP VM in one region, with the HUD reachable through a
reviewed ingress. On-premises members attach outbound over iN2N through the
Border's registered direct TCP endpoint: a pyATS/SSH member that reaches lab devices hosted in
CML, and optionally a CML API member. The owner signs in, reviews and approves a
read; the Border dispatches it; the pyATS member runs `show version` on R1, R2,
SW1 and SW2 with locally held SSH credentials; parsed results return to the
browser. There is no cloud-to-LAN route, no SSH from the cloud, and no public MCP
server.

User stories:
- P1: The Thermidor outcome reproduced: parsed `show version` from four CML
  devices, approved and viewed in the browser.
- P1: The cloud Border holds no device credentials and no provider keys.
- P2: The whole environment is created and torn down from IaC reproducibly.
- P2: HUD exposure is deliberate, documented and restricted at the edge where
  possible.

## Clarify: decisions (recommended default first)

1. IaC: OpenTofu/Terraform under `labs/cloud/gcp/`, built on a provider-neutral
   role contract (Border, cloud member) that Azure and AWS reuse. [HUMAN confirm]
2. HUD ingress: reviewed GCP IAP or an HTTPS load balancer with the existing
   owned-HUD session. This is separate from raw iN2N/NCFED TCP. Optional ngrok
   remains an alternative for NAT-constrained deployments. Record that
   public reachability is an exposure change from Thermidor's private origin. An
   edge OAuth gate may reduce exposure but is never the identity source. [HUMAN]
3. Border model profile: control-only Border with no local model, as in Thermidor.
4. Region and machine type. [HUMAN] Plan records monthly cost.
5. CML: pyATS/SSH against CML-hosted devices is required; a CML API member is P3.
6. Secrets: GCP Secret Manager rendered into a private `.env` at service start via
   the VM's service account.
7. Runtime: OpenClaw qualified; Hermes recorded as unqualified for cloud.

## Plan notes

- Reserve the Border's public address and allow only reviewed iN2N/eN2N TCP
  ports/sources. Admin SSH uses IAP; routing, MCP, gateway and model ports stay private.
- Run Border services as system units with spec165/166 confinement. No ngrok
  agent is required; optional tunnel deployments retain their separate owned unit.
- The pyATS member keeps its testbed, credentials and any device VPN locally.
- Every resource is tagged `roadmap=R03` with an expiry; ship `teardown`.

## Out of scope

Cloud members, Ollama, HA, writes.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Workload | Browser-approved `show version` from R1, R2, SW1, SW2 with parsed output (IOS version recorded) |
| Scope | Unknown device, disallowed command, altered arguments and unapproved write refused |
| Credentials | No SSH credentials, testbed secrets or provider keys on the Border host or in its model context |
| Network | No cloud-to-device route exists; VPC permits only reviewed federation ingress; external scan confirms routing/admin/model/MCP ports are unreachable |
| HUD | Unauthenticated HUD and API calls refused; session, CSRF and origin checks pass |
| IaC | Fresh apply and teardown both succeed; cost estimate versus observed recorded |
