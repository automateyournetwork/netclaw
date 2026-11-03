# Feature Specification: R03 — authenticated GCP Border with on-prem members

**Feature Branch**: `172-gcp-hybrid-border`  
**Created**: 2026-11-02  
**Status**: Complete and owner accepted for source integration (36/36 tasks)

**Input**: Owner: “drive R03 to 100%”. Authoritative brief: `docs/roadmap/issue-310/briefs/R03-gcp-border-onprem-members.md`. R02 accepted at `96cbdf0f`.

## User Scenarios & Testing

### User Story 1 — Approve four on-prem reads from the cloud (P1)

The configured owner opens the named cloud HTTPS HUD, signs in with a short-lived
administrator-issued ticket, reviews each exact device read, and receives parsed
`show version` results for R1, R2, SW1 and SW2. Members initiate outbound iN2N;
the cloud Border neither reaches the LAN nor executes a model or tool.

**Independent test**: Four real browser approvals correlate to four sole-command
SSH transcripts, observed software versions, signed receipts and durable ACKs.

1. Given an authenticated owner and enrolled member, preparing a read displays
   its exact member, device, arguments, model, expiry and immutable pins.
2. Approving one review authorizes exactly one `show version` on that device.
   Other devices still require separate reviews and approvals.
3. Browser reload, session renewal, transport loss and service restart recover
   retained references and status without additional provider/tool effects.
4. Unknown devices, substituted profiles, altered arguments, writes and missing,
   expired or foreign approvals fail without model/tool/device effects.

### User Story 2 — Keep authority and credentials in their proper locations (P1)

The owner can verify that only authenticated operational views are public and
that device/provider credentials remain on-prem. The cloud is control-only.

**Independent test**: Actual named HTTPS browser, ingress/route scan, runtime/IAM
inspection and negative requests demonstrate the stated boundary.

1. Anonymous visitors receive only sign-in assets and minimal installation
   metadata; member/catalog/operation/result APIs require the owner session.
2. Wrong Host/Origin, CSRF, forged proxy identity, duplicate headers/cookies,
   expired/reused tickets, revoked sessions and legacy execution routes refuse.
3. The Border has no device or provider keys, local inference/tool executor,
   Docker daemon, public MCP or cloud-to-LAN route. IAM cannot read R01 secrets.
4. Admin access uses IAP. Public exposure is the reviewed HTTPS hostname and
   direct iN2N TCP endpoint; eN2N remains dormant/private for this brief.

### User Story 3 — Reproduce and retire a bounded cloud lab (P2)

The maintainer reviews a complete infrastructure/runtime packet, creates a fresh
isolated deployment, verifies it, and tears it down without changing R01.

**Independent test**: Saved-plan apply, actual service/browser/workload receipts,
and reviewed teardown with a final resource/state inventory.

1. Plans name every resource, exposure, secret reference, service, cost, expiry
   and recovery action before an exact execution delegation is requested.
2. Resource and activation contracts separate provider-neutral roles from GCP
   details. Selected homes, state and credentials never fall back to R01/ambient.
3. Teardown retains private evidence but removes all reviewed R03 billable
   resources; leftover resources/costs, if any, remain explicit and block closure.

### Edge Cases

- A saved IOS-XE/IOL label is not live qualification. Each endpoint requires
  authenticated host-key provenance and an exact native command transcript.
- A switch in an unexpected initial state refuses; no implicit enable, discovery,
  configuration, fallback inventory or reconnect is permitted.
- Concurrent device operations cannot exchange testbeds, credentials or profiles.
- An unknown effect remains spent. No restart, reconcile, new browser session or
  recovery path may turn uncertainty into permission to execute again.
- Public sign-in assets are deliberately reachable; operational data is private.
- Price estimates/alerts are not an enforceable hard cap. The owner's November3
  execution-and-cleanup delegation supersedes the earlier unresolved billing
  ceiling gate. Stated credit is not a verified balance or spending target;
  finite resources/traffic/lifetime and removal of billable residues remain required.

## Requirements

### Functional Requirements

- **FR-001**: Reuse R02's owner authority, exact signed review/approval/result/ACK,
  strict iN2N enrollment, durable spent claims and mandatory audit semantics.
- **FR-002**: Support four separately approved `pyats_run_show_command` calls for
  R1/R2/SW1/SW2, each with complete exact arguments, one effect and at most two
  guarded member-side inference/provider calls. Never broaden a signed limit.
- **FR-003**: Select an immutable local device runtime by the full approved model
  and tool profile. Reject ambiguous duplicates. Each child sees one frozen device
  inventory, strict host-key file and only its scoped credential projection.
- **FR-004**: Preserve R02's pinned native IOS-XE/IOL adapter and zero-discovery,
  zero-setup-command policy; qualify every actual device before claiming parity.
- **FR-005**: Serve production-built protected HUD assets and the existing owner
  APIs on one exact HTTPS origin, without Vite, legacy routes or arbitrary proxy.
- **FR-006**: Enforce Secure HttpOnly SameSite=Strict installation-specific cookies,
  exact authority/Origin, CSRF, bounded requests and login attempts, revocation,
  post-I/O authorization and no browser-controlled principal.
- **FR-007**: Retain bounded installation-scoped operation references for all four
  results; restore by status-only reads. Display verified parsed evidence and
  honest unknown/ACK states. Cross-browser discovery/history is out of scope;
  an explicit retained operation ID remains recoverable by its owner.
- **FR-008**: Start a control-only Border through a strict role contract and
  environment allowlist. Reject local member executor/catalog and provider/device
  secret fields. Do not start a gateway/model/guard/tool or install Docker there.
- **FR-009**: Run dedicated non-root confined system services with immutable source,
  narrowly writable owned paths, resource bounds and private startup secrets from
  a least-privilege VM service account. Role-aware posture reports local inference
  controls as not applicable only after verifying the control-only contract.
- **FR-010**: Use an isolated GCP VPC/VM/address/state and new named HTTPS endpoint;
  admin SSH only through IAP, federation only on reviewed ports/sources. Keep
  routing/admin/model/MCP and dormant eN2N listeners inaccessible publicly.
- **FR-011**: Preserve all R01 resources/homes/secrets and R02 records, including
  unknown outcomes; never replay old activation plans or secret payloads.
- **FR-012**: Supply reproducible IaC, activation and teardown under exact review;
  label owned resources by roadmap/expiry and record observed cost visibility.
- **FR-013**: Follow the owner's November3 execution-and-cleanup delegation in
  activation-delegation.md, which supersedes the earlier CAD100/month execution
  gate. Record exact costs/visibility limits, bounded duration and residual charges;
  retain finite safeguards and remove owned billable residues after evidence export.
- **FR-014**: Preserve the issue310 release hold: no version/tag/package/Marketplace,
  public deployment instructions, blog/changelog or cloud rollout promotion.
- **FR-015**: End R03 with independent evidence and human acceptance before R04.

### Key Entities

- **Role contract**: selected installation/home, control-only Border or member,
  source/runtime pins, allowed listener/environment/service/state references.
- **Device profile**: exact approved tool/model identity, endpoint/inventory/source
  hashes and private one-device runtime references; never browser-supplied paths.
- **Operation reference**: installation, nonce and operation ID; no credential,
  ticket, approval token, raw result or review persisted in browser storage.
- **Cloud packet**: exact saved plan, hashes, resource/cost/expiry/teardown manifest
  and separate activation delegation; private state remains authoritative.

## Success Criteria

- **SC-001**: Four browser-approved reads return actual parsed versions, each with
  one native `show version`, zero setup commands, signed receipt and durable ACK.
- **SC-002**: Negative authority/scope/ingress cases cause zero extra effects;
  actual loss and owned restart retain the same operation identities/counters.
- **SC-003**: Actual DNS/trusted HTTPS and owner controls pass through the deployed
  ingress; external observations show only reviewed ports reachable.
- **SC-004**: Cloud inspection finds zero device/provider credentials or local
  inference/tool executor and no route to lab endpoints; on-prem outbound
  federation reconnects using unchanged enrollment keys.
- **SC-005**: Fresh reviewed apply and teardown succeed, costs/visibility and all
  residual resources are recorded, and R01/private inventories remain unchanged.
- **SC-006**: Every task has evidence or an explicit unresolved gate; 100% is
  reported only when implementation, live qualification and acceptance are done.

## Decisions and Assumptions

- Owner's existing preferences select Montréal, a named public HTTPS URL with
  the R02 configured-owner session, and OpenTofu/provider-neutral roles. Dedicated
  Caddy on an isolated e2-small avoids a load balancer's standing cost. Exact plan
  approval still precedes resources/DNS/activation; these are design defaults.
- Qualified and now retired hostname: `r03-gcp-montreal.lobsternet.automateyournetwork.com`.
  Owner identities/SSO/RBAC remain R15–R17; this is one configured owner.
- Cloud installation metadata is OpenClaw; no cloud inference is qualified.
  Hermes cloud remains unqualified. Preserve on-prem OpenClaw/Hermes support;
  the required four-device live acceptance uses OpenClaw. Additional Hermes live
  evidence is optional and must not be claimed without execution receipts.
- CML API member, cloud members, Ollama, HA, multi-cloud, writes and batch approval
  are outside R03. Existing optional ngrok support remains unchanged.
- Cloud qualification is a finite window of at most 48 hours with
  automatic VM stop and reviewed teardown. This does not alone guarantee the
  final billed amount; actual cost visibility and remaining exposure require review.
- Two of the owner's maximum five implementation passes were used by R02.
  R03 starts pass 3 only after contract/task consistency review.
