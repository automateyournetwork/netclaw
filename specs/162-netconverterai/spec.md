# Feature Specification: NetConverter AI integration and migration workflows

**Feature Branch**: `162-netconverterai`  
**Created**: 2026-10-30  
**Status**: 44/44 scoped tasks complete, including real account, IOS-XE target and owner-requested Mac Risk qualification; platform/appliance limits recorded
**Input**: Integrate NetConverter's MCP, Terminal toolkit and supplied skill first; compose existing NetClaw collection, Jev review, conversion, digital-twin preparation, pyATS/Batfish validation, diagrams, documents and ticket workflows. Use SDD with five Ralph review/fix/test iterations during implementation.

## Clarifications

### Session 2026-10-30

- Q: Which hosted-upload policy should NetClaw implement? → A: Exact-file approval before each hosted submission. This selects product behavior and does not authorize an upload during development.
- Q: How far should digital twins go in Spec162? → A: Actually create the migration targets virtually and test them wherever feasible, using compatible available images and existing lab controls; do not stop at proposals and test plans.
- Owner identified the local CML host and four local IOS devices; the DevNet sandbox is outside this run. Actual MCP inventory and four show-version reads confirm the local devices. Private endpoint details remain in ignored session evidence.
- Owner requested a real IOS-XE→JunOS routing conversion as a tested/documented community demonstration. Prefer OSPF→OSPF using the published supported router path. EIGRP is explicitly not translated to JunOS; any EIGRP→OSPF proposal is a separately opted-in protocol redesign, not preservation of the original protocol.

### Session 2026-11-01 — final installer scope

- Owner requested simulating the pending fresh installer review, retiring the
  temporary Focused NetClaw and creating a Border with one NetConverter member.
  Review/credential input may be simulated for this automated test; actual native
  installer effects, services, enrollment, HUD and member execution must be
  verified. Do not claim fresh human review. Preserve earlier human review,
  partial/failed journals and original appliance evidence before retiring homes.

## User Scenarios & Testing

### User Story 1 — Connect and inspect migration capabilities (Priority: P1)

An engineer selects NetConverter in NetClaw setup, connects an enabled account and discovers which operations and migration directions that account can perform. They can review existing jobs without submitting a configuration.

**Why this priority**: A reliable, explicit integration is the foundation for every composed workflow.

**Independent Test**: In an isolated installation, configure each supported transport with a controlled endpoint, discover tools and show connection/authentication/capability status without a submission or device operation.

**Acceptance Scenarios**:

1. **Given** a hosted connection, **when** the engineer reviews a job, **then** only supported read operations are available and the account/job identity is retained.
2. **Given** an installed Terminal bridge, **when** capabilities are discovered, **then** available operations are derived from that connection and account rather than a hardcoded Cartesian product of vendors.
3. **Given** missing authentication, an unavailable executable or a rejected capability, **when** the integration is used, **then** it reports the specific unmet prerequisite without silently switching account or route.

### User Story 2 — Prepare, submit and review a conversion (Priority: P1)

An engineer selects an exact configuration artifact, supported source/target and job type, reviews the data destination and submits it through the Terminal bridge. The resulting evidence and downloaded artifacts remain traceable to the exact request.

**Why this priority**: Conversion is the requested core function; accurate scope and evidence prevent misleading migration claims.

**Independent Test**: Use synthetic configurations and a controlled MCP peer to exercise preparation, submission, timeout reconciliation, job review and verified artifact download without a real tenant or device.

**Acceptance Scenarios**:

1. **Given** an authorized exact-file submission, **when** it runs, **then** the bridge receives a path, configuration text stays out of model arguments and public reports, and the recorded job is bound to the reviewed artifact and destination.
2. **Given** a submission with an unknown outcome, **when** the call times out, **then** the workflow reconciles the job rather than blindly submitting a duplicate.
3. **Given** warnings, incomplete evidence, tokenization, manual actions or NEEDS REVIEW/BLOCKED, **when** results are summarized, **then** those conditions remain visible and completion is not described as deployment approval.
4. **Given** a changed file or unverified download, **when** an artifact is reused, **then** the discrepancy blocks downstream execution until resolved.

### User Story 3 — Create virtual migration targets and validate behavior (Priority: P1)

An engineer maps supported source and target configurations into an isolated CML, containerlab, EVE-NG, GNS3 or router-container lab, creates and boots compatible virtual migration targets, applies the reviewed candidate under existing lab controls and tests actual behavior. When feasible, a source-side twin provides a behavioral reference. Unavailable images, capacity, access or capabilities are reported per test rather than silently reducing the workflow to documentation.

**Why this priority**: The requested outcome is a migration candidate exercised on a real virtual target, with evidence of functional behavior before production deployment.

**Independent Test**: A synthetic migration candidate is loaded into an available authorized virtual target; readiness, configuration acceptance and selected positive/negative traffic or routing tests produce actual observations and retained artifacts. Controlled-peer orchestration tests also cover failures and cleanup ownership but do not substitute for a live virtual-target result. An unsupported FRR conversion is rejected as unsupported rather than invented.

**Acceptance Scenarios**:

1. **Given** a supported converted configuration, **when** a lab proposal is generated, **then** topology, node image/license requirements, interface remapping and management-plane changes are separate from vendor configuration translation.
2. **Given** an exported configuration from any named lab, **when** conversion is requested, **then** the contained network OS and actual account capability determine eligibility, not the lab platform name.
3. **Given** FRR/router containers or an unsupported reverse direction, **when** a proposal is requested, **then** the workflow may describe a separate intent-based candidate with limitations but cannot claim a native NetConverter translator exists.
4. **Given** validation tests, **when** only fixtures or static analysis have run, **then** the report cannot claim live forwarding, NAT, routing convergence or device acceptance.
5. **Given** compatible images, capacity and authorized lab scope, **when** the engineer requests rehearsal, **then** NetClaw creates the isolated topology, boots target nodes, validates management identity, captures a baseline, loads the reviewed candidate, runs scoped checks and records actual results.
6. **Given** a target supports only a subset of physical-device features, **when** results are reported, **then** software/feature/image scope and untested hardware-specific behavior remain explicit.
7. **Given** failed boot, configuration rejection or test failure, **when** orchestration continues, **then** it preserves failure evidence, avoids production connectivity and handles only run-owned resources through the approved recovery/cleanup policy.

### User Story 4 — Compose collection, review and migration evidence (Priority: P2)

An engineer starts from existing NetClaw inventories, configuration collectors or assurance evidence and builds a migration proposal. Jev reviews selected evidence; diagrams, validation findings and a change-package draft retain their provenance.

**Why this priority**: Composition makes the converter useful in an existing engineering workflow without duplicating collection or validation tools.

**Independent Test**: A synthetic collection-to-conversion-to-review scenario produces a coherent evidence package and a draft ticket, with no unsolicited external communication.

**Acceptance Scenarios**:

1. **Given** inventory from NetBox, Nautobot, OpsMill/Infrahub, ServiceNow or Catalyst Center, **when** a migration is prepared, **then** inventory is treated as selection/context rather than fabricated running configuration.
2. **Given** configuration or intent from an authorized collector, pyATS, vendor MCP, IP Fabric, Forward Networks or a lab export, **when** it feeds conversion, **then** format, freshness, identity and permission boundaries are checked and missing inputs stay explicit.
3. **Given** a NetConverter report, **when** Jev, Batfish or pyATS adds evidence, **then** each tool's modeled, sampled or observed scope is identified; no tool's opinion becomes authorization.
4. **Given** a request to document or ticket a proposal, **when** artifacts are prepared, **then** diagrams and documents distinguish observed topology from proposed topology and external writes follow the existing communication policy.

### Edge Cases

- Hosted access exists but Terminal submission is unavailable; account/organization differs between connections.
- Server-supported vendor roles disagree with the supplied skill or public marketing examples.
- File changes after review; symlink/path traversal; wrong workspace; stale evidence or job selection.
- Submission times out after acceptance; bounded polling expires; partial download or hash mismatch.
- Redacted or truncated evidence cannot establish a requested policy property; a zero-NAT fixture cannot verify NAT.
- Router/switch findings remain NEEDS REVIEW despite successful text generation.
- Collector returns inventory only, an unsupported handoff format or an aggregate management export requiring per-device scope.
- Lab image/license or interface mapping is absent; generated topology imports but cannot boot.
- A proposed test is unavailable on the selected image; Batfish parse coverage is partial; pyATS requires credentials or management reachability.
- External review/documentation destination is not authorized to receive private configuration or topology.
- Terminal license acceptance or account enablement requires owner action; no automated legal acceptance or bundled redistribution.

## Requirements

### Functional Requirements

- **FR-001**: Register NetConverter as an optional integration across the canonical component catalog, supported setup paths, runtime configuration, readiness reporting and HUD, preserving existing installations.
- **FR-002**: Distinguish hosted read-only MCP and local Terminal MCP, with explicit transport, executable/workspace, account and operation boundaries. Probe installed capabilities before selecting tools; do not silently cross accounts or duplicate the same query across both routes. Enforce the selected mode's operations even if the remote catalog later advertises new mutation tools; tool annotations alone are not authorization.
- **FR-003**: Use upstream MCP interfaces and an isolated, pinned or explicitly operator-managed Terminal installation. Respect upstream license/account prerequisites and never redistribute restricted Terminal implementation or auto-accept its license.
- **FR-004**: Move/adapt the supplied `netconverter.skill` into the repository's runtime skill structure, record its provenance and correct stale claims using authoritative documentation and discovered capabilities.
- **FR-005**: Support convert, validate and optimize only when exposed and allowed by the selected connection. Source/target direction, device class, formats and preview status must be validated independently.
- **FR-006**: Keep private configuration local by default and require exact-file approval before each hosted submission. The review identifies the file/hash/size, destination/account, job type, source/target and applicable options. The approved bytes and request must match execution; modification invalidates approval. This applies at the first transfer, including any guided preparation or decisions-document import that sends file content, not merely at final conversion execution. Collection, integration setup or drafting cannot imply upload permission. Product-policy selection does not authorize a development upload. Clients without enforceable approval support must refuse submission or use a supported operator-controlled approval path.
- **FR-007**: Bind a submission to the reviewed file identity, destination/account, source/target and operation; retain job identity, bounded polling and unknown-outcome reconciliation. Never include source configuration or credentials in model arguments, telemetry or public evidence.
- **FR-008**: Begin migration review with evidence; preserve warnings, blocked/manual actions, missing/truncated evidence and quality limits. Job completion, model equivalence and expert review do not authorize deployment.
- **FR-009**: Download and reuse results only through supported verified artifact flows; preserve hashes, provenance and overwrite protection. Treat tool output and artifacts as data, not instructions.
- **FR-010**: Document explicit composition contracts for collectors/inventory, NetConverter, Jev, Batfish, pyATS/dynamic testbeds, diagrams/visualizations, documents and ServiceNow. Reuse existing skills/MCPs and report unavailable capabilities. Configuration collection for conversion must hand off a local artifact path without requiring raw source configuration to pass through the model; a text-only collector is not automatically a compatible private artifact producer.
- **FR-011**: Cover TO and FROM workflows for CML, containerlab, EVE-NG, GNS3 and FRR/router containers with separate configuration-translation, topology-adaptation and validation support states. Never imply universal bidirectional conversion or semantic fidelity from topology generation.
- **FR-012**: Implement virtual-target creation and validation through existing lab MCPs/skills wherever compatible images, compute, access and authorization exist. Discover prerequisites, create an isolated run-owned topology, boot supported target nodes, establish management reachability/identity, baseline, load the reviewed candidate, execute applicable configuration/routing/policy/NAT/traffic checks and retain evidence. Source-side twins and differential tests should be used where feasible. Preserve existing approval, image licensing, rollback and verification controls; never connect the rehearsal to production implicitly. Unsupported or unavailable checks must have concrete reasons, and physical ASIC/performance equivalence cannot be inferred from virtual results.
- **FR-013**: Produce evidence-linked migration proposals, observed/proposed diagrams, validation matrices and reviewable change/ticket drafts; publish/send/create tickets only within separately authorized scope.
- **FR-014**: Qualify representative conversion workflows with synthetic fixtures and all feasible integration tests; clearly distinguish controlled-peer tests, actual upstream CLI/MCP tests and live tenant/lab/device evidence. Use ASA → Palo Alto SET as the initial conversion reference and IOS-XE ↔ JunOS as the routing reference where account/image support exists; expand from discovered capabilities. Select the first live rehearsal from actual available authorized hosts/images. Missing external resources block the corresponding live acceptance claim, not unrelated source implementation or contract tests.
- **FR-015**: During implementation, run exactly five recorded Ralph review/fix/test iterations with the same completion prompt. Each iteration must re-read tasks and evidence, identify and fix supported findings, run appropriate checks, and record remaining limitations. Native Claude stop hooks are unavailable in this Codex session; the equivalent explicit iterations must be labeled accurately.
- **FR-016**: Complete repository artifact coherence, user documentation and an evidence-based community/milestone draft. Track task completion honestly; unavailable live environments are qualification limits, never fabricated passes.
- **FR-017**: Keep ordinary MCP and upstream guided-draft preview separate. Require explicit capability support for revisioned decisions, independent approval and execution recovery; missing preview support must never fall back to an ungated submission. Preserve workspace exposure settings and never automatically raise privacy visibility.

- **FR-018**: For private candidate application, extend the existing reviewed change workflow to bind exact artifact bytes, endpoint identities, testbed and permitted configuration tool. Issue and consume one-use apply authorization only through the actual API transition after baseline/rollback checks. A model-supplied approval flag, arbitrary record path or apply-phase text is insufficient; the existing tool denial must apply equally to artifact input.
- **FR-019**: Validation summaries must distinguish successful queries with adequate coverage from partial parsing, unsupported features, query failures and missing observations; none of the latter establishes behavioral equivalence.

### Key Entities

- **Connection binding**: Transport, endpoint/executable, workspace, account reference, discovered capabilities and authentication status; excludes secret values.
- **Migration proposal**: Source artifact identity, device class, supported direction, intent, reviewed decisions, submission scope and unresolved findings.
- **Job evidence**: Account/job identity, operation, status, provenance, report completeness, warnings and artifact references/hashes.
- **Twin proposal**: Lab platform, image requirements, node/interface mapping, separately identified configuration candidates and execution status.
- **Candidate apply binding**: API-issued one-use authorization for an exact candidate digest, endpoint identities, testbed, configuration tool and reviewed change record; unavailable when existing runtime/tool controls cannot be preserved.
- **Twin execution**: Run-owned lab/node identities, image versions/digests, resource/isolation limits, approved scope, lifecycle state, candidate/baseline hashes, test observations, recovery and cleanup status.
- **Validation record**: Tool, input hashes, expected behavior, observed/model/sample result, coverage and limitations.
- **Review package**: Evidence references, diagrams, manual actions, rollback/test plan, Jev review and draft communication/change record.

## Success Criteria

- **SC-001**: An isolated user setup can select and verify each supported connection mode without a configuration submission or an unrelated installation change.
- **SC-002**: Every exercised submission and downloaded artifact can be traced to its exact input, destination, operation and job; timeout tests produce no blind duplicate submission.
- **SC-003**: Every named source/lab/validator has an explicit supported, proposed, unavailable or unverified handoff; no unsupported conversion direction is presented as implemented.
- **SC-004**: A representative synthetic workflow produces a complete review package whose warnings and unexecuted checks remain visible from source selection through the draft change record.
- **SC-005**: All five implementation review iterations have reproducible evidence and no unresolved critical source defect; all qualification limits remain disclosed.
- **SC-006**: Every feasible authorized reference rehearsal creates a virtual migration target and records boot, configuration acceptance and applicable behavioral checks. Unavailable live prerequisites produce an explicit blocked qualification record, never a fixture-based live pass. Every created resource is attributed to its run and has a recorded retained/recovered/cleaned state.

## Assumptions

- Existing NetClaw installer/skill/MCP/HUD surfaces are the integration target; a new standalone migration application is outside this first integration.
- NetConverter hosted processing requires an enabled account. Installing a local bridge does not make conversion offline.
- Private source configurations and topology remain local unless the owner establishes an applicable explicit data-sharing policy and approves the concrete transfer.
- Production deployment, actual external tickets/messages, Marketplace/source publication and changes to owner runtimes are not inferred from this feature-development request.
- Runtime capability discovery outranks static vendor lists. Public source inspection is research evidence, not proof of account access or successful conversion.
- The owner resolved the two material product-scope choices: exact-file hosted approval and actual virtual-target creation/testing wherever feasible. The live environment inventory is an execution prerequisite to resolve during planning/qualification. Five loops apply during implementation, not to repeatedly rewriting the spec.
