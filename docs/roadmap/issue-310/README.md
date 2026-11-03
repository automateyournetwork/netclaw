# NetClaw roadmap: cloud mesh → multi-cloud → multi-user (closes #310)

This folder turns the cloud-first roadmap and issue #310 into 20 ordered feature
briefs for Spec Kit. Each brief is the *input* to one feature's
specify → clarify → plan → tasks → analyze → implement cycle; it is not itself a
ratified spec (Constitution XVI).

Baseline: upstream `automateyournetwork/netclaw` at `9ba12ffc` (2026-11-01). The
highest existing spec is `167-production-mode-qualification`, so the first brief
takes the next free number at specify time (168 unless something lands first).

## Current execution status — 2026-11-03

R01 and [R02/Spec171](../../../specs/171-execution-parity/verification.md) are
complete and accepted. [R03/Spec172](../../../specs/172-gcp-hybrid-border/verification.md)
has completed source, actual GCP/on-prem qualification, independent evidence review
and cleanup:36/36 tasks, accepted by the owner with the post-handoff source-merge
instruction on November3. R04 has not started.
Four browser-approved reads returned parsed versions with signed results/ACKs;
actual loss/restart recovery caused no repeated device/model execution. All13 R03
cloud resources, DNS and the temporary SSH key are removed; zero owned billable
residues remain. R01's existing running pilot remains preserved.

The owner authorized the coordinator/three-agent team and at most five bounded
implementation passes. November3 delegation superseded the earlier CAD100/billing
execution hold for isolated R03 completion/cleanup; stated GCP credit is unverified
and not a target. Finite safeguards and exact evidence/cleanup were retained.
Integration preserves upstream source1.18.4 from #321 and extension1.5.0 without
a roadmap version bump. The entire-roadmap release/public rollout hold remains. R04/R05 have not started. Earlier assessment sections below are historical.

## Roadmap source integration and release hold — 2026-11-02

The owner authorized committing, pushing and merging the completed R01 source into
main, with a short maintainer summary. This supersedes R01's earlier source-merge
hold only. The issue310 roadmap work remains unreleased until the entire roadmap
is complete, including user identities, SSO and RBAC (R15–R17) and closure (R20).
Do not bump a version, create a release/tag, publish a package/Marketplace build,
publish a blog/changelog/announcement, or promote general cloud deployment for
this work. R01 transport proof is not authorization to deploy a cloud Border
without user controls. Keep technical specs/evidence for maintainers; rollout
copy is deferred under specs/168-ngrok-transport-contract/deferred-docs/ and absent
from the public README, setup wizard and general installation guides. Existing
owner pilot authorization is a bounded exception, not a user deployment recipe.
R01 integrated on upstream 1.18.1 without a version increment. Subsequent upstream
fixes #317/spec169 and #318/spec170 advance source to 1.18.3; extension 1.5.0 is
unchanged. These maintenance fixes do not release or qualify the cloud roadmap.
Next roadmap brief is R02 execution parity, expected next available spec 171
(recheck at kickoff; 169 and 170 are occupied by those upstream fixes);
it is not started by this integration request. No R02 cloud/device operation is
authorized here. Keep the original R01 directory name despite the parallel
upstream168-openclaw-2026-10-compat feature; cite R01/full path to distinguish them.

## Upstream reconciliation and parallel-work assessment — 2026-11-02

[PR317](https://github.com/automateyournetwork/netclaw/pull/317) records useful
member timeout errors; cancellation, time budgets and uncertain-outcome handling
are unchanged. [PR318](https://github.com/automateyournetwork/netclaw/pull/318)
restores DNS-provider credential delivery to the lego child process and skips its
random renewal delay. Both are merged; source 1.18.3 includes R01. The combined
source passed 888 federation tests with 5 existing skips, and its tested tree
matches merge a8d7e348. Provider coverage and unattended-renewal limits remain
in spec170 verification; this review made no live certificate or runtime changes.
The R01 cloud HUD uses Caddy for HTTPS, so lego qualification does not qualify
that separate certificate lifecycle. R01 stays spec168; R02 has not started.

R02–R05 remain ordered by their acceptance gates: execution parity → GCP Border
with on-prem pyATS → GCP NetBox/subnet member → cloud/local Ollama members. The
R01 open Sonnet lab is transport and demonstration evidence; it does not satisfy
R03's authenticated HUD, control-only Border or member-held credential criteria.
User/SSO/RBAC work stays in R15–R17; R03 uses the existing owner session boundary.

Parallel agents can divide one ratified feature after its contracts are agreed:

- Coordinator: parity matrix, shared approval/result/principal contracts,
  integration and gate review.
- Execution agent: approval consumption, broker/guard enforcement and durable
  result handling under those contracts.
- HUD agent: exact owner review and approval/result presentation.
- Verification agent: independent refusal, lost-reply and no-replay tests,
  credential-isolation checks and evidence review.

Use separate worktrees and explicit file ownership; one coordinator integrates
shared federation code. Later-brief feasibility research can overlap if separately
requested, but implementation and live qualification do not bypass the R02→R03,
R03→R04 or R04→R05 human gates. The owner has asked for this assessment, not started
R02–R05 or delegated new cloud, model or device operations. No parallel agents
were launched for this review. The release hold above remains unchanged.

## Owner decisions — 2026-11-01

Opening assessment and questions are complete. R01 is spec
[168-ngrok-transport-contract](../../../specs/168-ngrok-transport-contract/spec.md).
Work still proceeds one brief at a time; no later feature is ratified by this index.

- Initial cloud placement: GCP Montréal; initial trial 30 days. Exact project,
  billing identity, credentials and remaining credits belong in private deployment
  configuration. The owner's approximately $1,000 credit identifies the intended
  account; it is neither an assigned spending cap nor a spending target.
- Owner deployment DNS base: `lobsternet.automateyournetwork.com`; choose unique
  provider/region/instance names without deriving application identities from them.
  Reusable examples use `example.com`, and no default selects the owner's account.
- Three new local members: pyATS/SSH to CML-hosted devices; separate CML API;
  local Ollama IPv4 subnet calculator. pyATS and CML use latest Sonnet, resolved
  to an explicit model ID and qualified with their actual runtime and guard.
  Cloud Border remains control-only. Ollama execution qualification remains R05.
- Reusability includes install and migration local↔cloud and cloud↔cloud with
  each operator's credentials. Specify stable identity versus endpoint placement,
  move versus clone, private state/secret handling, fenced cutover, rollback and
  per-provider qualification. R01 covers transport address migration; later briefs
  qualify runtime/state relocation. A fixture never qualifies a cloud migration.
- With these three local members and two cloud members per provider, the current
  eventual example is 9 members × 9 Borders = 81 attachments. The 90-attachment
  example below remains the original illustrative four-local-member case.

### Direct-cloud transport amendment — 2026-11-01

The owner explicitly approved a full pivot from mandatory ngrok to native cloud
connectivity. Cloud Borders use provider-reserved addresses with separate iN2N
and eN2N/NCFED TCP ports, application-terminated TLS and reviewed narrow ingress.
Home members still dial outbound. ngrok remains optional for NAT-constrained
Borders; neither a paid plan nor ngrok live acceptance blocks direct-cloud R01.
Existing ngrok work is preserved. Spec/branch paths retain their historical name.
Home/NAT ngrok remains a supported option, alongside private on-premises and
air-gapped Border/member topologies without ngrok. Cloud-friendly members may
move to cloud; local SSH/internal-system members remain on premises and dial out.
Offline artifact/model provisioning must be qualified separately. Hybrid,
multi-region and multi-cloud stay in the roadmap; no completed qualification is
implied by this transport choice.
This amendment supersedes contrary transport wording in the original briefs and
historical references; it does not ratify or begin a later brief. Exact cloud,
account, spend and publication approval boundaries remain unchanged.

Both reference files are staged. The Thermidor file is a dated design reference;
its private-repository relative links intentionally do not resolve in this tree.

## Setup

Copy this folder to `docs/roadmap/issue-310/` in the NetClaw repo, then add:

- `reference/thermidor-ngrok-handoff.md` — the Thermidor "Cloud Border and member
  architecture with an ngrok alternative" handoff (2026-11-01). Its relative links
  point into the private Thermidor repo and will not resolve here. Treat it as a
  design and evidence reference, never as code to import.
- `reference/issue-310.md` — the issue body plus the byrn-baker and owner comments.

## Driver prompt for the coding harness

```text
You are executing the roadmap in docs/roadmap/issue-310/. Work on exactly one
brief at a time, in the order of the Sequence table in README.md.

For the current brief:
1. Read README.md (global invariants G1–G11), the brief, both reference files,
   and the spec.md and verification.md of every spec the brief depends on.
2. Run /speckit.specify with the brief's "Specify input" section. Put the brief
   ID (e.g. "Roadmap: R03") in the spec header.
3. Run /speckit.clarify. Resolve each listed decision with the recommended
   default unless repository evidence contradicts it; record every deviation
   and its reason. Any decision tagged [HUMAN] stops and asks me.
4. Run /speckit.plan using the brief's plan notes, then /speckit.tasks, then
   /speckit.analyze. Do not implement while analyze reports CRITICAL or HIGH.
5. Run /speckit.implement. Write specs/<NNN>/verification.md mapping every row
   of the brief's "Acceptance evidence" to real evidence (command, excerpt,
   timestamp) or an explicit UNQUALIFIED / FIXTURE-ONLY status. Never relabel
   fixture or historical evidence as live qualification.
6. Run the Artifact Coherence Checklist (Constitution XI). Draft, but do not
   publish, the milestone blog post (XIV, XVII).
7. Stop and report: spec number, branch, PR, verification summary, open risks,
   and any invariant you could not meet. Wait for me to say "next".

Never do any of the following yourself; prepare the exact commands and ask me:
`tofu/terraform apply` or destroy, any command that creates, changes or deletes
cloud resources or incurs spend, ngrok account or endpoint changes, IdP app
registrations, and any device operation outside the brief's approved read set.
```

## Global invariants (every brief inherits these)

**G1 Topology.** Members attach outbound over iN2N to every eligible Border in
their cluster. Border-to-Border is allowed: internal cluster links within the
organization, eN2N/NCFED with independently administered organizations.
Member-to-member is never allowed. No member exposes a listener another member
can reach, and members refuse any peer that is not an enrolled Border. Every
topology brief proves this with negative tests.

**G2 Transport.** Native cloud TCP is primary: stable provider addresses with
separate iN2N and eN2N ports. ngrok TCP reservations remain an optional deployment
choice for NAT-constrained Borders. The HUD needs its own reviewed ingress.
TLS terminates only in NetClaw; no provider/ngrok TLS termination, PROXY headers
or payload transformation. TLS1.3 minimum on remote paths, no cleartext or
loopback exception and no weaker fallback. Routing address, verified TLS name
and enrolled application identity remain separate. Preserve NCFED identification
before TLS and document its metadata; no application payload before TLS.

**G3 Exposure.** Ollama, MCP servers, brokers, the OpenClaw gateway and etcd never
receive a public endpoint unless a brief specifies one with its own protection
(etcd only from R08, with mTLS and RBAC).

**G4 Credentials.** Integration credentials (device SSH, NetBox token, provider
API keys) live only at the executing member or its guard. Borders hold scoped
delegation authority, not integration secrets. ngrok tokens are transport-only
and never an identity. Secrets follow Constitution XIII: cloud secret managers
render into a private `.env` at service start through workload identity.

**G5 Execution.** The model proposes; the broker validates exact approved
arguments; the member enforces. Approvals are exact, scoped, expiring and
one-use. Uncertain outcomes become reconciliation work and are never replayed
automatically. From R08: no quorum means no new protected execution.

**G6 Principal.** From R02 every request carries a principal. Until R15 the only
principal is the owner. Nothing may hard-code "the owner" in a way R15 has to
unpick.

**G7 Evidence.** Thermidor and Tailscale results are a baseline only. Each brief
produces its own positive, negative and recovery evidence. TCP reachability is
recorded separately from authenticated admission. Fixture or synthetic results
are labeled as such.

**G8 Constitution.** Safety-first (observe before change), GAIT audit for every
action, ServiceNow CR for production changes, artifact coherence (XI) and
backwards compatibility (XV): the cloudflared transport (spec 108), direct LAN
iN2N, single-user installs and the Hermes runtime keep working or get a
documented migration.

**G9 Cloud hygiene.** Every cloud resource is created from IaC and tagged with its
brief ID and an expiry date. Each cloud brief ships a teardown script, a cost
estimate in plan.md, a budget alert, workload identity (no static cloud keys on
hosts), and reviewed ingress limited to the selected iN2N/eN2N ports and source ranges
for direct cloud TCP. Optional ngrok deployments need no service ingress. Admin
access uses the provider's identity-aware path; no public routing/admin/workload API.
The owner-approved R01 lab publishes the full HUD over reviewed DNS/HTTPS ingress,
including Chat, Canvas and RAG, without login. The owner also authorized Anthropic
Sonnet and a scoped on-prem subnet-calculator demonstration. Raw configuration,
credentials, routing/admin and device-write APIs remain private. This does not
bring R15 users, R16 SSO or R17 RBAC forward or qualify later workloads.

**G10 Portfolio.** Do not regress HUD Chat and Canvas, gateway, skills/MCPs, Zoom,
Mobile or VS Code. Record qualified / retained / unqualified status per platform
and transport in each verification.md.

**G11 Read-only until RBAC.** R03–R14 run read-only workloads: show commands,
NetBox reads, subnet calculations. Device or system writes arrive only with
R17's authority, approval and audit model.

## Sequence

| ID | Feature | Your roadmap item | Depends on |
|---|---|---|---|
| R01 | Direct cloud transport contract and TLS identity fixes | prerequisite | — |
| R02 | Execution parity on NetClaw production mode | prerequisite | — (parallel with R01) |
| R03 | GCP Border with on-prem members (pyATS/SSH, CML) | 1 | R01, R02 |
| R04 | GCP cloud member: NetBox and subnet, hosted model | 2 | R03 |
| R05 | Ollama members: cloud IPv6 and on-prem IPv4 | 3 | R04 |
| R06 | External Border over direct eN2N/NCFED | eN2N | R03 |
| R07 | Single-region recovery and tunnel lifecycle gate | gate | R03–R06 |
| R08 | Border HA authority and protected quorum transport | prerequisite for 4 | R07 |
| R09 | GCP multi-region: three meshed Borders | 4 | R08 |
| R10 | Azure single region | 5 | R09 |
| R11 | Azure multi-region | 5 | R10 |
| R12 | AWS single region | 6 | R09 (may run beside R10) |
| R13 | AWS multi-region | 6 | R12 |
| R14 | Multi-cloud: nine Borders, three providers | 7 | R11, R13 |
| R15 | Multi-user foundation | 8 | R14 |
| R16 | Bring-your-own SSO | 9 | R15 |
| R17 | RBAC, delegated authority, approvals and audit | 10 | R16 |
| R18 | Personal conversations and memory | 11 | R17 |
| R19 | Shared network knowledge base | 11 | R18 |
| R20 | Issue #310 closure: isolation suite and UX | 11 | R19 |

R15 does not depend on provider specifics and could start after R09 if you want
overlap, but it must be qualified on the nine-Border mesh. Multi-user stays
feature-flagged off in releases until R17 lands, so no release ships multi-user
without authorization and audit (byrn-baker's phase-one point).

## Topology arithmetic

| Stage | Borders | Border pairs | Member attachments |
|---|---|---|---|
| R03–R07 | 1 | 0 (+1 external eN2N peer) | M |
| R09, R11, R13 | 3 per provider | 3 | M × 3 |
| R14 | 9 | 36 | M × 9 |

With four local members and two cloud members per provider (10 members), R14
has 90 member attachments. Counting one iN2N and one cluster endpoint per Border,
a few eN2N endpoints and etcd client/peer paths for the voters, expect roughly
30–40 distinct service endpoints plus HUD ingress. Multiple direct TCP ports may
share a provider-reserved IP; endpoint count is not public-IP count. Verify each
selected provider's quotas/costs. Optional ngrok deployment would need its own
TCP reservation/endpoint entitlement; it is no longer a mesh-wide dependency.

## Where this differs from the Thermidor program

Thermidor planned ten Borders including an on-prem Mac Border; this roadmap has
nine cloud Borders and keeps on-prem as members only (a Mac makes a poor voter
because of sleep and residential connectivity). Thermidor's global operations
globe is not included; spec 121 (federated topology viz) is the natural place to
add it. Each new provider is qualified as its own three-Border cluster and then
joined into one global cluster at R14, because consensus clusters are rebuilt by
joining nodes, not merged in place. Finally, the work happens inside NetClaw, so
Thermidor's execution controls are mapped onto NetClaw's existing production mode
(R02) rather than imported as a separate product.

## Issue #310 traceability

| Requirement (issue or comment) | Brief |
|---|---|
| Entra ID via OIDC; extensible to other providers; BYO (owner comment) | R16 |
| Google, GitHub and generic OIDC providers | R16 |
| Server-side identity; isolated, persistent, resumable sessions; Chat and Canvas | R15 |
| No reliance on browser storage or client-supplied session IDs | R15 |
| Shared agent with per-user runtime state, files, terminals, background tasks | R15 |
| Personal memory: retrieve, inspect, correct, delete | R18 |
| Shared KB: publish with confirmation, review, provenance, freshness, dedup, search | R19 |
| Validate current environment before reusing a past solution | R19 |
| RBAC from IdP groups, enforced server-side for MCP, SSH, API, workflows | R17 |
| Approval requirements for high-impact operations | R17 |
| Audit: who, devices, tools, commands, approvals, outcome; secrets excluded | R15 (attribution), R17 (full) |
| Carry user authority through every delegation (byrn-baker) | R17 |
| Integration credentials stay at the executing member (byrn-baker) | G4, R02 |
| Classify remote claws: iN2N internal, eN2N independent (byrn-baker) | G1, R06, R08 |
| Border access never implies administrator access (byrn-baker) | R15, R17 |
| Authorization and audit in phase one, not later (byrn-baker) | R15 flag rule, R17 |
| Security considerations list (WebSocket, cross-user retrieval, indirect tool access, retention) | R15, R17, R18, R20 |
| UX: sign-in, current user, personal vs shared, role-aware visibility | R15–R20 |
| Answers to the maintainers' questions; closing the issue | R20 |

## Glossary

**Border** — the organization's coordination and policy boundary: owner service,
enrolled members, approvals, dispatch, results, approved external exports. It
need not run inference. **Member** — an independently identified execution
installation with scoped runtime, model profile and tools. **iN2N** — an enrolled
member's channel to its own organization's Border. **Cluster link** — an
authenticated Border-to-Border channel inside one organization, carrying HA
membership and bounded control state (new in R08). **eN2N / NCFED** — federation
between independently administered organizations' Borders, with bilateral consent
and restricted exports; no vote and no member access. **Principal** — the
authenticated identity a request runs on behalf of.
