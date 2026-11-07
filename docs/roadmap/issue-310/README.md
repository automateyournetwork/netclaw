# NetClaw roadmap: cloud mesh → multi-cloud → multi-user (closes #310)

This folder turns the cloud-first roadmap and issue #310 into 21 ordered feature
briefs for Spec Kit (R01–R20 plus R04a), with a proposed R04b follow-up. VS Code and Mobile integration are
continuing delivery objectives alongside the cloud, federation and user features.
Each brief is the *input* to one feature's
specify → clarify → plan → tasks → analyze → implement cycle; it is not itself a
ratified spec (Constitution XVI).

Baseline: upstream `automateyournetwork/netclaw` at `9ba12ffc` (2026-11-01). The
highest existing spec is `167-production-mode-qualification`, so the first brief
takes the next free number at specify time (168 unless something lands first).

## R07 accepted; source integration authorized — 2026-11-07

[R07/Spec178](../../../specs/178-recovery-gate/verification.md) is accepted31/31,
including the measured operator recovery targets. See its
[completion summary](../../../specs/178-recovery-gate/completion-summary.md),
[runbook](../../../specs/178-recovery-gate/runbook.md) and
[source-integration record](../../../specs/178-recovery-gate/source-integration.md).
The owner requested commit/PR/merge, completed-branch cleanup, return to main and
joint evaluation of R08. R08 implementation is not started. Versions, publication
hold and retained R05/R06/original Border deadlines remain unchanged.

## R06 accepted; source integration authorized — 2026-11-06

[R06/Spec177](../../../specs/177-external-en2n-federation/verification.md) is
complete and accepted35/35. Two independent cloud organizations plus local C
passed all six external federation directions, actual browser/VS Code/iPhone
simulator journeys, scoped refusals and original-result recovery without replay.
See the [short completion write-up](../../../specs/177-external-en2n-federation/completion-summary.md)
and [source-integration record](../../../specs/177-external-en2n-federation/source-integration.md).

The owner authorized commit, PR, merge, completed-branch deletion and return to
main. Existing runtime retention and the roadmap version/publication hold remain.
R06 cleanup is scheduled November8; it has not already happened. See the exact
retirement obligations in the evidence. The next sequence is
[R07 recovery → R08 HA authority → R09 GCP multi-region → R10 Azure](R07-R10-next-steps.md).
This brief does not start those stages; each retains separate VS Code/Mobile
assessment and actual acceptance under G12/G13.

## Historical R05 acceptance and source integration — 2026-11-06

[R05/Spec176](../../../specs/176-ollama-members/verification.md) is complete and
accepted33/33. Fresh NetClaw local ARM64/cloud AMD64 Ollama members, combined
browser, Mac VS Code and native iPhone simulator flows passed, with separate
approvals, native verified facts, signed results/ACKs, confinement and no-repeat
recovery. Thermidor supplied proven patterns/tests; no Thermidor runtime or
Tailscale was deployed. Final disposable cleanup and sealed export are complete;
the intended48-hour delivery remains until November7. Full scheduled cloud
cleanup requires the owner's Mac awake/online with Docker and gcloud/IAP access;
VM STOP alone leaves disk/IP costs. See the evidence and
[clear-session handoff](../../../specs/176-ollama-members/source-integration.md).

The owner authorized commit/PR/merge and return to main. Preserve source1.18.6,
extension1.6.1 and Mobile1.0.4+7; the roadmap publication hold remains. Upstream's
separate `176-convergence-vm-security` and R05's `176-ollama-members` retain their
full paths. Next free spec is expected177, to be rechecked at kickoff.

The next milestones remain unchanged:

| Stage | Scope |
|---|---|
| [R06](briefs/R06-external-en2n-border.md) | Independent external Border, one explicitly exported capability over eN2N/NCFED, bilateral consent and no internal member access |
| [R07](briefs/R07-recovery-gate.md) | Safe restart/outage/revocation/lost-reply/duplicate recovery without replay; required before multi-region work |
| [R08](briefs/R08-border-ha-authority.md) | Exactly one execution authority, stale-leader refusal and no new protected execution without quorum; fixture and real-runtime evidence |
| [R09](briefs/R09-gcp-multi-region.md) | Three-region GCP mesh across Americas/Europe/Asia-Pacific; four members attach to all three; single-region loss preserves service without replay |
| [R10](briefs/R10-azure-single-region.md) | Azure Border, hosted-model NetBox and Ollama workloads with on-prem attachments, isolation, recovery, cost and teardown evidence |

No next-stage implementation or cloud operation is started by this closeout.
Each stage separately assesses and verifies VS Code/Mobile under G12/G13.

## Historical R05 SDD kickoff — 2026-11-05

R04b/Spec175 is accepted30/30; its scoped release is recorded in
[release verification](../../../specs/175-cloud-mobile-enrollment/release-verification.md).
The owner has now started [R05/Spec176](../../../specs/176-ollama-members/spec.md)
on `176-ollama-members`, explicitly requiring reuse of Thermidor's final working
solution, tests and lessons. The branch/spec/plan/contracts/tasks are prepared;
implementation and live acceptance remain open (0/33 tasks). Both VS Code and
Mobile require combined-request integration. No R05 runtime changes or R06/R07
work occurred; existing pilot/lifetime and broader rollout holds remain.
The November4 status below is historical and superseded by this update.

## Historical execution status — 2026-11-04

R01 and [R02/Spec171](../../../specs/171-execution-parity/verification.md) are
complete and accepted. [R03/Spec172](../../../specs/172-gcp-hybrid-border/verification.md)
has completed source, actual GCP/on-prem qualification, independent evidence review
and cleanup:36/36 tasks, accepted by the owner with the post-handoff source-merge
instruction on November3. [R04/Spec173](../../../specs/173-gcp-cloud-member/verification.md)
has completed actual qualification and owned cleanup (33/33), accepted by the
owner with the source-integration instruction. [R04a/Spec174](../../../specs/174-cloud-client-integration/verification.md)
passed isolated Mac VS Code/native iOS simulator reads and recovery, then retired
its24 temporary cloud resources. On November4 the owner reopened R04a: that proof
did not deliver a working connection in his installed VS Code. Persistent GCP
deployment and installed-client delivery are now complete and accepted (22/22).
The normal Overview, Chat, cited RAG/Canvas, advertised panels and protected
NetBox read/result recovery passed on the owner's Mac. The current flow is Name + URL with
no user sign-in; authentication remains later roadmap work. The existing Mobile
scanner needs HUD QR issuance, trusted WSS and protected-operation integration,
documented as proposed [R04b](briefs/R04b-cloud-hud-mobile-enrollment.md). Bounded
Mobile no-login compatibility is source-tested; cloud QR and physical iPhone
execution remain unqualified. After the final check, the owner accepted R04a and
requested source integration plus production VS Code publication; see
[release verification](../../../specs/174-cloud-client-integration/release-verification.md).
Recommended next is the separately scoped R04b QR continuation, then R05. Neither
is started by this integration/publication request.
R03’s four browser-approved reads returned parsed versions with signed results/ACKs;
actual loss/restart recovery caused no repeated device/model execution. All13 R03
cloud resources, DNS and the temporary SSH key are removed; zero owned billable
residues remain. R01's resources and historical evidence are preserved; its retained VM now hosts
the owner-authorized R04a protected runtime, with the old home archived and legacy
applications stopped. Its December1 stop remains unchanged.

The owner authorized the coordinator/three-agent team and at most five bounded
implementation passes. November3 delegation superseded the earlier CAD100/billing
execution hold for isolated R03 completion/cleanup; stated GCP credit is unverified
and not a target. Finite safeguards and exact evidence/cleanup were retained.
Integration preserves upstream source1.18.5 from #325 and both distinct Spec174
directories. The owner-authorized extension1.6.0 production update is a narrow
exception to the earlier Marketplace/version hold. Source release/tag, external
announcements and general cloud rollout remain held throughR20. This release
does not upgrade the retained pilot or other existing runtimes.
R04a uses the fifth bounded pass; no further optional loop is implied. Earlier
assessment and amendment sections below are historical.

## VS Code and Mobile integration amendment — 2026-11-03

The owner reports that VS Code cannot currently connect to the cloud Border.
This is an open client integration gap; backend or browser qualification alone
does not establish that the VS Code extension works with that Border.

Insert [R04a — cloud Border client integration](briefs/R04a-cloud-border-client-integration.md)
after accepted R04 and before R05. R04a catches up VS Code connection and affected
workflows, assesses Mobile against the same cloud contracts, and fixes/qualifies
affected mobile flows. R04 → R04a → R05 replaces the former direct R04 → R05 gate;
existing milestone IDs and completed evidence retain their names. Allocate the
next free Spec Kit number at R04a kickoff, not in this planning amendment.

From R04a onward, every stage has two separate integration obligations: VS Code
(G12) and Mobile (G13). Carry them through specification, design, implementation
tasks and acceptance evidence as the backend evolves. A reviewed no-impact finding
is valid; omission or automatic deferral to R20 is not. This amendment schedules
the work and does not start R04a, extend the active R04 deployment, change its
cleanup obligations, or lift any release/publication hold.

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
1. Read README.md (global invariants G1–G13), the brief, both reference files,
   and the spec.md and verification.md of every spec the brief depends on.
2. Run /speckit.specify with the brief's "Specify input" section. Put the brief
   ID (e.g. "Roadmap: R03") in the spec header.
3. Run /speckit.clarify. Resolve each listed decision with the recommended
   default unless repository evidence contradicts it; record every deviation
   and its reason. Any decision tagged [HUMAN] stops and asks me.
4. For R04a and every later brief, explicitly assess VS Code and Mobile impact
   separately (G12/G13). Put affected client/API/configuration work and its
   verification into this feature's spec, plan and tasks; document the basis for
   each no-impact conclusion. Run /speckit.plan using the brief's plan notes, then /speckit.tasks, then
   /speckit.analyze. Do not implement while analyze reports CRITICAL or HIGH.
5. Run /speckit.implement. Write specs/<NNN>/verification.md mapping every row
   of the brief's "Acceptance evidence" to real evidence (command, excerpt,
   timestamp) or an explicit UNQUALIFIED / FIXTURE-ONLY status. Never relabel
   fixture or historical evidence as live qualification. Include separate
   VS Code and Mobile acceptance rows, with the actual versions, platforms,
   endpoint/identity/authentication paths and qualification limits. Resolve
   affected integration gaps in this stage; do not silently defer them to R20.
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

**G12 VS Code integration as work progresses.** From R04a, every brief must assess
how its endpoint/transport, identity/authentication, API, capability, installation
or workflow changes affect `extensions/netclaw-vscode/`. Include required client
and server changes in the same feature. Verify the affected experience in actual
VS Code against the selected Border, including connection, the relevant workflow,
failure/reconnection and retained results/approvals where applicable. Preserve
local installations and correctly bind remote profiles to their selected Border.
Do not expose private admin/workload services, weaken TLS/authentication or copy
member integration credentials into the client to make connectivity work.

**G13 Mobile integration as work progresses.** From R04a, every brief separately
assesses `mobile/netclaw-mobile/` and its Border-side contracts: enrollment,
verified transport, authentication/identity, Ask Border, approvals, results and
reconnection/background recovery as affected. Implement and qualify necessary
changes in the same feature. If unaffected, record the inspected contract/code
and why existing behavior remains valid. If affected, retain actual mobile-client
evidence for the selected platform/device; emulator or protocol fixtures do not
establish physical-device qualification. Mobile never gains implicit authority
or a direct path to member credentials, models or MCP servers.

For both G12 and G13, every later verification report has an explicit impact
decision, implementation disposition and evidence/qualification row. Unverified
affected paths stay UNQUALIFIED and open; a backend-only pass cannot close them.
Preserve declared platform limits rather than claiming every desktop or phone
platform passed. These two obligations extend G10, including identity, SSO, RBAC,
personal memory and shared knowledge work in R15–R20.

## Sequence

| ID | Feature | Your roadmap item | Depends on |
|---|---|---|---|
| R01 | Direct cloud transport contract and TLS identity fixes | prerequisite | — |
| R02 | Execution parity on NetClaw production mode | prerequisite | — (parallel with R01) |
| R03 | GCP Border with on-prem members (pyATS/SSH, CML) | 1 | R01, R02 |
| R04 | GCP cloud member: NetBox and subnet, hosted model | 2 | R03 |
| R04a | [Cloud Border client integration: VS Code and affected Mobile flows](briefs/R04a-cloud-border-client-integration.md) | client integration gate | R04 |
| R04b (proposed) | [Cloud HUD and existing Mobile QR enrollment](briefs/R04b-cloud-hud-mobile-enrollment.md) | client follow-up | R04a acceptance and scoped plan |
| R05 | Ollama members: cloud IPv6 and on-prem IPv4 | 3 | R04a |
| R06 | External Border over direct eN2N/NCFED | eN2N | R03, R04a |
| R07 | Single-region recovery and tunnel lifecycle gate | gate | R03–R06, including R04a |
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
| R03–R05 | 1 | 0 internal cluster links | M |
| R06 qualification | 3 independent organizations | 3 external eN2N pairs; no HA cluster | Separate organization scope |
| R07 | Single-region recovery topology, chosen in its spec | Preserve qualified relationship types | Requalify affected members |
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
| Actual VS Code cloud Border connectivity and affected client workflows (owner amendment) | R04a, G12, every later brief |
| Mobile cloud-contract impact assessment and affected-flow qualification (owner amendment) | R04a, G13, every later brief |
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
