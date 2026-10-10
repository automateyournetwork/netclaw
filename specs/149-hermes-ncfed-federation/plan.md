# Implementation Plan: Hermes NCFED federation

**Branch**: `149-hermes-ncfed-federation` | **Date**: 2026-10-10 | **Spec**: [spec.md](spec.md)

## Summary

Make the selected Hermes installation usable as Border and scoped member over the existing NCFED network. Preserve the OpenClaw execution adapter, add a protected Hermes adapter, and make installation/lifecycle/inventory/HUD paths agree on the selected installation. Extend the capability card with harness identity. Qualify core federation operations and the existing harmless subnet tool/skill first; do not interpret installed MCP registrations as authority.

The owner explicitly authorized plan → tasks → analyze → implement, including routine corrections, without another clarification round. Analysis remains an independent read-only pass; remediation follows that pass under this authorization.

## Technical Context

**Mobile addition**: existing Flutter/Dart application (`mobile/netclaw-mobile`, baseline1.0.2+4), existing Android/iOS enrollment and NCFED edge methods. Verify installed SDK/build tooling before recording a platform claim. New complete outcome handling targets1.0.3+6; retain legacy server projections.
**Language/Version**: existing Python federation and scripts (isolated Python 3.12); pinned Hermes companion Python 3.14; JavaScript ESM/Express/React HUD on Node >=24.19 <25 or >=26.1.
**Primary Dependencies**: existing FastMCP 4.0.11/MCP SDK 2.3.0; Hermes v0.21.6 source818c13be1dc4fd28987e1e881a9408224afd4535; existing HTTPX, SQLite, NCFED secured channels and official Node MCP client2.3.1.
**Storage**: additive federation.db migrations; selected-home private runtime manifests; distinct netclaw-hud and netclaw-federation conversation/evidence databases; existing GAIT audit.
**Testing**: pytest/unittest federation and installer contracts, existing real pinned-Hermes controlled-provider fixtures, Node HUD tests/build, browser acceptance where available, multi-node transport integration and process faults.
**Target Platform**: macOS development/testing; Linux/Ubuntu WSL execution with actual control probes. Native Windows Hermes remains unsupported. Production containment must be verified per host and refused when unavailable.
**Project Type**: runtime integration across an existing Python daemon/MCP tool surface, CLI/installer and web HUD and existing Flutter mobile app.
**Performance Goals**: status reads perform no inference; preserve current configurable execution deadlines (default skill300s, chat300s), bounded private MCP admission10s and status polling1s. No unbounded retry or duplicate admission. Integration tests use smaller explicit deadlines.
**Constraints**: no owner credential/config fallback; no peer-controlled executables; no blanket tool qualification; no automatic uncertain replay; no production-write permission from federation; keep original owner services untouched during validation.
**Scale/Scope**: four internal runtime pairs, two external pair types in both directions; one Border with multiple scoped members; protected companion retains bounded admission (four active requests per installation namespace).

## Constitution Check

Pre-design and post-design gates PASS subject to the implementation checks below. Safety/read-before-write/ITSM: qualify harmless calls and refuse unqualified writes; no device change is required to prove core journeys. MCP-native: agent tools and private runtime access use official MCP lifecycle; NCFED and its local control service remain the existing federation transport, not a replacement tool protocol. Audit: correlated GAIT and durable execution evidence. Least privilege: scoped member homes, per-request receiver profiles, no external-to-operator privilege promotion. Compatibility: additive cards/state, missing harness unknown, existing OpenClaw adapter retained. Coherence: existing components are extended, so update their manifests/installers/docs/HUD and inventory where changed; no fictitious new integration count. Milestone blog draft stays local pending separate publication authorization. No constitutional amendment is needed.

## Architecture and decisions

1. **Installation context**: reusable `bgp/federation/runtime.py` resolves the shared runtime-selection contract before any identity/state/provider work; supplies home/config/env/skills/base directory and safe harness metadata. Persistent installation ownership fences custom homes; explicit N2N_BASE_DIR remains supported with an ownership record. OpenClaw legacy defaults remain.
2. **Protected execution**: retain `gateway.run_agent_turn` public shape but accept trusted execution context from authenticated ingress. Hermes calls a private stdio federation bridge with the official Python MCP client. Bridge/ledger/companion reuse spec148 code with an explicit federation namespace; HUD eight-tool contract remains unchanged. Explicit daemon/member startup owns a separate long-lived companion, private key, source/interpreter and port. Status never starts inference or services. Missing/unsupported Hermes never falls back to OpenClaw.
3. **Receiver authority**: persist context before admission (installation, origin/requester, target, task, body digest, grant/approval, profile, deadline). Capture it on the protected agent before upstream worker-thread handoff. Intersect local qualified tools with the authorized target and member scope. Initial skill closure is subnet-calculator; peer chat is conversational and has no operational tools. Incoming federation runs never receive n2n orchestration, native shell, history, shared memory, plugin, fallback-provider or native delegation tools.
4. **Current authorization**: a private loopback execution broker owned by the federation service issues opaque bounded permits, checks the actual live service/grant/member state at each protected effect, and fails closed if unavailable. Tokens are injected by trusted code, never model arguments. Request/body/tool-call fingerprints prevent permit reuse for a different effect. Private broker discovery carries installation identity; no guessed endpoint or cross-installation service use.
5. **HUD operator orchestration**: qualify only n2n inventory/health, capability routing, peer chat, named invocation/delegation and owned status/result retrieval. Existing n2n-mcp remains the MCP surface, but protected calls use an official MCP client with a per-call scoped environment/permit and the installation-bound broker. Trust, consent, grants, approvals, membership administration and replication mutation remain unavailable to this agent profile. Initial invocation targets are qualified subnet tool/skill; route cannot select an unqualified target. Operator actions through existing authenticated HUD controls retain their own rules. Scope-owned task/chat references prevent reads into unrelated conversations.
6. **NCFED policy and task lifecycle**: carry origin through internal delegation; fix empty member scope to deny and external skill/chat session key collisions. Consume exact approvals transactionally after current-grant/deadline checks. Persist dispatch boundary and outbound request intent before effects; deduplicate authenticated owner/request/body on receiver. Lost response, restart or cancelled waiter after dispatch is outcome_unknown unless execution provides stronger evidence. Recover known handles read-only; no automatic replay. Preserve uncertain/active evidence and unknown usage rather than writing measured zero.
7. **Discovery**: selected runtime supplies configured registrations/model/skills. Expose qualification separately from configured inventory. Add bounded harness type/version/source/observed_at/status projection to internal inventories and external Border cards. Preserve original card version counter and deployment runtime_kind. External card never lists private member topology.
8. **Lifecycle**: share selection across CLI, daemon, provisioner and managed service paths. Hermes members get private allowlisted configuration, installed qualified skill context and fresh least-privilege environment. Use installation-scoped locks/PIDs/unit names, actual recorded interpreters, and exact owned process cleanup. Refuse unsupported production controls. Explicit start may create private runtime state; discovery/status does not. Upgrade preserves populated state and old defaults.
9. **HUD**: allow selected-daemon federation routes only when installation identity/readiness matches. Keep Terminal Intent, writes, hosted Avatar and other unqualified spec148 restrictions independent. Render runtime/harness next to model/tools, with unavailable/unknown/stale states and safe labels.

## Project Structure

```text
specs/149-hermes-ncfed-federation/{spec,baseline,research,plan,data-model,quickstart,tasks,analysis,verification}.md
specs/149-hermes-ncfed-federation/contracts/{runtime-execution,capability-card,lifecycle-hud}.md
mcp-servers/protocol-mcp/bgp/federation/{runtime,execution,hermes_runtime}.py
mcp-servers/protocol-mcp/bgp/federation/{gateway,invocation,service,chat,tasks,authorization,inventory,member_inventory,controls,manager,negotiate}.py
mcp-servers/hermes-hud-mcp/{federation_server,federation_tools,bridge,ledger,policy,protected_agent,hermes_api}.py
mcp-servers/n2n-mcp/server.py
scripts/{runtime-selection,peering-launch,in2n-member-home,in2n-member,in2n-services,in2n-profiles,in2n-migrate}.py
scripts/{netclaw,peering-setup.sh,lib/install-steps.sh,lib/runtime-install.sh}
ui/netclaw-visual/{server.js,src/dashboard,src/hud-server,runtime-client,src/orgchart}
tests/{n2n,hermes-hud,unit}/
```

Use the existing package and component layouts; private bridge operations are not advertised as agent tools. Exact additional helper files may be split by cohesion during implementation without changing the contracts.

## Implementation sequence and verification

Foundation: shared selection/harness, durable context/outcomes, scoped execution broker and namespace isolation. Then selected launch, member provision/execution, internal/external call paths, HUD orchestration/display, and failure/preservation integration. Tests first for security/lifecycle contracts. Run focused suites after each dependent change, then the complete federation/Hermes/HUD/installer checks and repository coherence checks. Re-run only when changes justify it.

Acceptance requires actual pinned Hermes execution and real MCP tool invocation over real local NCFED connections in controlled-provider tests. A scripted provider is labeled controlled; it is not live hosted-provider qualification. The current host cannot stand in for a Windows/WSL or native-Linux host: record actual host/control evidence and outstanding handoff work honestly. No task is complete merely because a fixture returned a plausible result. See [quickstart.md](quickstart.md) for release gates.

## Mobile scope extension (owner authorized 2026-10-10)

Add US8/FR024–029/SC011–013 without replacing the original federation work. Authenticated pinned-key edge ingress creates an operator scope in the federation ledger, distinct from HUD operator and external receiver scopes. Bind requester/device and pinned-key generation, installation, conversation, request/body, task, interaction origin and explicit mobile outer deadline. A re-enrolled label cannot inherit old device context/results; child work is bounded by remaining parent time. Do not accept origin/profile authority from request text. Generalize the operator broker to explicitly validate either HUD admissions or authenticated mobile admissions and retain per-device/conversation handle ownership. Revocation stops new effects; a temporary reconnect does not change ownership or replay a run.

Preserve `n2n/edge/ask`, progress/result notifications, task status/result/cancel and enrollment. Add optional request/conversation IDs and outcome-capability metadata; legacy requests remain accepted. New mobile clients persist an admission reference before sending, reconcile a lost acknowledgment through owner-bound existing task queries, and never retry an uncertain submission. Older clients receive canonical outcome metadata plus an existing-state fallback with a clear message when they cannot represent unknown/interrupted/cancellation-requested states. Cancellation acknowledgment is not confirmation of cessation.

Keep interaction origin (`voice`) separate from trust origin (`operator`). Apply the existing voice composition instruction inside the protected prompt before body fingerprinting. All mobile-origin tools use the same bounded operator subset and current grant/member checks; no enrollment/admin/approval mutations are enabled on the model.

Photo/video: initial disposition is explicitly unavailable on Hermes because the protected companion's text-only admission and audited tool profile have no qualified media pipeline. Reject before task creation/inference, advertise `attachments:false`, and gate the updated mobile UI. Preserve existing OpenClaw attachment behavior and test its regressions. This is text/voice/delegation compatibility, not full media parity.

Mobile changes span `lib/ncfed/edge_ask_client.dart`, conversation store/reconciler, headless Siri/watch handling, Chat and Dashboard UI and tests. Produce Android APK and/or iOS simulator/device build with actual tool availability recorded; do not represent an unsigned simulator bundle as a signed distributable or physical-device test. Minimum app version and artifact paths belong in verification/mobile compatibility docs. The original upload exclusion was superseded by the owner update below; public App Review/release remains excluded.

Read-only mobile build research observed Flutter3.44.8/Dart3.12.2, Xcode26.6(17F113), macOS26.5.2 and iOS/watchOS26.5 simulator runtimes. Android SDK/JDK were not found. The available toolchain produced a signed iOS device archive with Watch and extensions; record Android/physical-device execution unverified unless subsequently performed. No OS-floor increase is planned.

## Authorized mobile distribution update

Include Border type on Dashboard summary, bump all shared bundle versions, and after verification produce and validate the signed archive, upload to App Store Connect, and observe processing. No public App Review submission/release. Upload credentials remain local and artifacts stay outside Git.

The owner additionally authorizes source 1.8.0, README/release history, spec149 PR creation and publication of the five-image Hermes article to the existing .com site. Preserve the website’s already-published uncommitted AONE work; stage only this task’s release delta and verify public article, NetClaw collection and Latest.
