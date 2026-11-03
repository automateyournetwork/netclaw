# Feature Specification: R04 — GCP NetClaw member for NetBox and subnet work

**Feature Branch**: `173-gcp-cloud-member`
**Created**: 2026-11-03
**Roadmap**: R04; depends on accepted R03, `specs/172-gcp-hybrid-border/`
**Status**: Implementation, actual qualification and owned retirement complete; pass4 complete, owner accepted; source integration authorized

**Input**: Owner: “proceed with R04 … drive this to 100%”; supplied an existing
NetBox demo endpoint and credential, required “we have netbox skills and MCP use
netclaw member claw”, then delegated autonomous completion. Authoritative brief:
`docs/roadmap/issue-310/briefs/R04-gcp-cloud-member-netbox.md`.

## Clarifications

### Session 2026-11-03

- Q: Which NetBox instance? → A: Owner supplied `https://demo.netbox.dev/` and
  a credential retained privately. Use its existing demo records read-only;
  do not deploy or seed another NetBox, or upload the private CML inventory.
- Q: Which execution path? → A: An actual NetClaw member must use the existing
  NetBox skills and MCP. A standalone HTTP probe is not member qualification.
- Q: Who drives the remaining scope? → A: Owner delegated autonomous R04
  completion after the proposed defaults were presented. Use a separate member
  VM/subnet, both IPAM prefix reads and bounded subnet calculation, hosted inference
  behind the guard, direct registered iN2N, bounded deployment and cleanup.
  Preserve exact plans and evidence; do not repeatedly ask for these permissions.

## User Scenarios & Testing

### User Story 1 — Obtain an approved NetBox device result (Priority: P1)

The configured owner selects the cloud NetClaw member in the authenticated
Border HUD, reviews one exact bounded device read and sees the source-attributed
result. The member uses its installed NetBox skill and MCP behind the guard.

**Why this priority**: Demonstrates real cloud execution while Border coordination
and execution credentials remain separate.

**Independent Test**: A browser approval correlates to a hosted model turn,
existing NetBox MCP invocation, source observation, signed result and durable ACK.

1. Given an enrolled member and an eligible device read, approval permits only
   the reviewed object type, ID/filter, result bound, member and model profile.
2. Given an unknown object type, changed arguments or missing/spent/expired
   approval, the request is refused without a source or provider effect.
3. Given source failure, empty results or changed demo data, the answer reports
   that observed condition and capture time rather than inventing inventory.

### User Story 2 — Read IPAM and independently verify subnet arithmetic (Priority: P1)

The owner separately approves a bounded NetBox prefix read and a bounded subnet
calculation. The result distinguishes documented IPAM intent from calculated facts.

**Why this priority**: Demonstrates that execution placement and hosted inference
are independent, using two existing NetClaw capabilities.

**Independent Test**: A real prefix read agrees with its same-window source;
an actual calculator result agrees with an independent arithmetic implementation.

1. A prefix read uses only approved NetBox IPAM objects and remains read-only.
2. A calculator request pins its exact network and size bounds; invalid or altered
   networks refuse, and no device or NetBox configuration is changed.
3. Each operation has its own approval and evidence; one cannot authorize another.

### User Story 3 — Keep credentials and execution authority isolated (Priority: P1)

The owner can inspect evidence that integration secrets are available only to the
member's credential-handling processes, and no other member can invoke them.

**Why this priority**: A working query is insufficient without the roadmap boundary.

**Independent Test**: Actual process, filesystem, model request, Border artifact,
network and negative-request evidence corroborate the isolated runtime.

1. The NetBox token is absent from Border state, model context, transcripts,
   browser state and exported evidence. Private operator provisioning is distinct
   from the runtime credential boundary; no claim erases the supplied chat input.
2. The model proposes only approved calls; the broker invokes the existing MCP
   with narrowly projected credentials. Write tools and unknown reads refuse
   before reaching NetBox, even if the supplied token has broader permissions.
3. The member dials its enrolled Border outbound and exposes no member/model/MCP
   listener reachable by another member or the public Internet. Provider access
   occurs only through the existing guarded member-side path.

### User Story 4 — Recover member availability without repeating work (Priority: P2)

The owner sees a stopped member as unavailable and sees it reattach after an
owned restart, retaining operation identity and evidence without repeated work.

**Why this priority**: A cloud member has its own lifecycle and failure domain.

**Independent Test**: Actual stop/restart and interrupted-response observations
preserve signed results, ACK state and unchanged provider/source/tool counters.

1. A stopped member becomes unavailable within the configured heartbeat deadline;
   a new request cannot silently queue or execute against an unavailable member.
2. Restart permits status recovery and subsequent newly approved work, never
   automatic replay of spent, interrupted or uncertain operations.
3. Recovery does not reset quotas, approvals, identities or evidence.

### User Story 5 — Qualify and retire a reproducible cloud deployment (Priority: P2)

The maintainer can reproduce the R04 roles, understand added cost and retire all
temporary owned resources after exporting evidence, preserving existing pilots.

**Why this priority**: Completion includes resource hygiene and honest evidence.

**Independent Test**: Exact IaC/state, activation, resource inventories, preserved
artifacts and final absence checks account for every R04 resource.

1. A fresh control-only Border reuses the R03 contract; a separate cloud member
   has a separate subnet and workload identity. Retired R03 plans are not reused.
2. All resources, secret references, exposure, lifetime and cost bounds are
   recorded before execution under this session's R04 delegation.
3. Evidence is exported before teardown; billable residue prevents technical
   completion. R01 and unrelated owner installations remain unchanged.

### Edge Cases

- The demo service can reset or mutate records and revoke credentials. Never
  substitute a cached fixture for current access or weaken authentication.
- Modern NetBox token format may differ from the existing MCP's legacy header;
  compatibility must be fixed in the managed MCP path, not by bypassing it.
- Redirects, arbitrary URLs, response links, proxy environment and oversized or
  secret-bearing responses cannot expand the approved source or result scope.
- Tool discovery is distinct from authenticated source access and actual guarded
  model execution. Existing Thermidor, R01 and R03 results are historical only.
- Shared-VPC placement does not waive strict TLS, enrolled identity or outbound
  membership. No private-path exception is implied by the separate subnet.
- Read refusals are exercised at the broker; no deliberate write is sent to the
  public demo instance to demonstrate that the broker should have blocked it.

## Requirements

### Functional Requirements

- **FR-001**: Reuse R02/R03 owner principal, exact expiring one-use review,
  approval, signed result, durable ACK, spent-claim and GAIT semantics.
- **FR-002**: Execute the actual installed NetBox skill/MCP through an enrolled
  NetClaw cloud member; preserve tool identity and source/runtime pins.
- **FR-003**: Permit only exact bounded device and prefix reads (`dcim.device` / `ipam.prefix` in the installed MCP)
  selected for R04. Refuse every write, unknown type and changed argument.
- **FR-004**: Use the existing bounded subnet skill/tool through the same protected
  member execution path, with independent validation of the result.
- **FR-005**: Pin the hosted model profile and source-compatible guard; only the
  member/guard holds provider credentials. Bound provider turns and tool effects.
- **FR-006**: Confine the NetBox token to the member-side credential boundary;
  disclose it to neither Border nor model, logs, UI, Git or evidence exports.
- **FR-007**: Preserve verified HTTPS and exact source authority. Refuse redirects,
  arbitrary destinations, unbounded pagination and source-controlled execution.
- **FR-008**: Produce finite, source-attributed outputs with capture time, selected
  objects, content digests and explicit failure/empty/changed-source outcomes.
- **FR-009**: Provide real owner HUD review and result recovery for all three
  workload kinds; retain existing authentication, origin and CSRF boundaries.
- **FR-010**: Use a fresh control-only Border and separate member VM/subnet,
  direct registered iN2N and outbound enrollment. Preserve role isolation.
- **FR-011**: Prove member-to-member, public workload/MCP/model and unsupported
  Border peer admission refusals with actual host/network evidence.
- **FR-012**: Report lost availability and reattachment; preserve uncertainty
  without automatic replay or retry storms across actual loss and restart.
- **FR-013**: Reuse workload identity, private startup secret projection, confined
  services, immutable source, bounded traffic/resources and finite expiry.
- **FR-014**: Prepare exact cloud/runtime/DNS plans and receipts under the owner's
  autonomous R04 delegation. Record added monthly and finite-window estimates,
  actual billing visibility, expiry and cleanup. Credit is not a spending target.
- **FR-015**: Export private evidence, retire every owned temporary resource and
  verify no billable residue; preserve R01 and all historical/current-state archives.
- **FR-016**: Preserve source1.18.4/extension1.5.0 and the roadmap release hold.
  No public rollout documentation, release, announcement or R04a/R05 execution.
- **FR-017**: Map all acceptance rows to actual evidence or an explicit unresolved
  status; use independent review and stop for owner acceptance before R04a (then R05).
- **FR-018**: Preserve existing OpenClaw/Hermes, local/optional ngrok paths and
  HUD portfolio behavior; qualify only the actual tested R04 environment.

### Key Entities

- **Member workload profile**: Member identity, installed skill/MCP/tool pins,
  model profile, exact object/network selection and finite effect budget.
- **Source binding**: Verified NetBox origin, private token reference, bounded
  object contracts and observed version; never a browser-supplied destination.
- **Operation evidence**: Principal, approval, attempt/effect counts, source
  capture, result digest, signed receipt, ACK and recovery lineage.
- **Deployment packet**: Fresh owned roles/resources, state, exposure, costs,
  expiry, activation receipts, preservation inventory and teardown outcomes.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Three separately approved live workloads return a correct NetBox
  device read, prefix read and independently verified subnet calculation.
- **SC-002**: Every successful workload proves actual NetClaw skill/MCP execution,
  guarded hosted inference, one approved tool effect, signed result and durable ACK.
- **SC-003**: Every required negative scope/authority case causes zero unauthorized
  effects; runtime inspection finds zero credential disclosures outside its boundary.
- **SC-004**: Actual member loss/restart recovers availability and the same prior
  results with unchanged effect counts and no automatic replay.
- **SC-005**: Actual cloud confinement/topology checks pass and all owned temporary
  resources are retired with zero billable residue; added cost is documented.
- **SC-006**: All acceptance rows have current evidence, independent review and
  qualification limits; human acceptance remains an explicit gate before R04a (then R05).

## Assumptions

- Existing GCP project and Montréal preferences persist. R04 uses fresh names,
  identities, homes and state. Existing R01 is not the R04 Border.
- Source assessment selects existing `claude-sonnet-4-6` instead of the brief's
  Haiku default: all current NetClaw provider/guard/runtime layers pin Sonnet.
  This recorded deviation preserves the established provider boundary; actual
  native Linux/cloud qualification still requires new R04 evidence.
- Read-only public demo records replace the proposed CML-seeded NetBox. No device
  access or ticket creation is required by R04.
- Owner delegation covers bounded R04 provisioning, runtime, workload testing,
  recovery and cleanup. No broader cloud rollout or unrelated operations follow.
- Three of five bounded implementation passes were used through R03. R04 is
  planned as pass4; no automatic Ralph loop or reset of that counter.
