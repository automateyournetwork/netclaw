# R04a — Cloud Border client integration: VS Code and Mobile

- **Roadmap item:** client integration catch-up between R04 and R05
- **Depends on:** accepted R04 and its verified owner/Border/member contracts
- **Gate:** human review of VS Code and Mobile evidence before R05
- **Status:** Spec174 technical qualification and owned retirement complete (16/17); human acceptance pending. See [verification](../../../../specs/174-cloud-client-integration/verification.md). Physical iPhone unqualified; no publication authorized.

## Specify input

The owner reports that VS Code cannot connect to the cloud Border. Reproduce and
diagnose that gap, then bring the existing NetClaw VS Code extension up to date
with the cloud Border contracts delivered through R04. Assess the Mobile app and
its Border-side integration at the same time; implement and verify changes where
those contracts affect mobile behavior. A working browser HUD or backend test
does not establish either client's connectivity or usable workflows.

VS Code and Mobile become two explicit integration objectives for every later
roadmap feature under [G12 and G13](../README.md#global-invariants-every-brief-inherits-these).
Carry them into each feature's spec, plan, tasks and acceptance evidence as work
progresses. R04a establishes this baseline; R20 verifies its continuity rather
than becoming a catch-all for deferred client work.

User stories:
- P1: From actual VS Code, the owner selects the cloud Border, authenticates over
  the supported verified transport and sees the correct connection and identity.
- P1: The owner completes a supported R04 read-only workflow from the extension,
  with the same exact review, approval, member execution, result and audit rules
  as other supported clients. Reconnection recovers existing work without replay.
- P1: A cloud connection preserves existing local profiles and clearly presents
  supported capabilities; local workspace/service controls stay bound to their
  actual installation and never accidentally act on another claw.
- P1: Mobile has an explicit impact decision. Affected enrollment, Ask Border,
  approval, result and reconnection flows work against the selected cloud Border;
  a no-change conclusion identifies the inspected contracts and evidence.
- P2: Each subsequent roadmap brief contains separate VS Code and Mobile tasks
  or reasoned no-change dispositions, plus separate verification rows.

## Clarify: decisions (recommended default first)

1. Reproduce the reported VS Code failure before choosing a fix. Distinguish
   endpoint/configuration discovery, TLS identity, authentication, API/capability
   mismatch and local-only assumptions; do not invent a root cause.
2. Use an explicit remote Border connection profile and existing owner authority
   until R15–R17. Do not infer credentials or authority from a URL or a local home,
   reuse the open R01 lab exception, or expose a broker/gateway/admin endpoint.
3. Inspect actual VS Code and Mobile code plus the selected Border capabilities
   before deciding the supported flow. If client support needs a missing server
   contract, include that narrowly scoped contract and its negative tests here.
4. Qualify the owner's selected VS Code host and affected mobile platform/device;
   list other platform limits explicitly. Keep source/build, emulator/protocol
   and actual application/device evidence distinct.
5. R04 cleanup remains required. Use a fresh, reviewed finite qualification
   deployment if R04 resources are retired; never replay its spent activation,
   enrollment or workload authority. Recheck exact resource/cost scope at kickoff.

## Plan notes

- Start from `extensions/netclaw-vscode/`, `mobile/netclaw-mobile/` and the
  existing HUD/federation/owner API contracts. Inspect the applicable Spec151,
  Spec152, Spec153, Spec155, Spec148/149 and R01–R04 verification limits.
- Cover connection settings, endpoint and identity binding, secure credential
  storage, authenticated requests, capability presentation and actionable errors.
  Review Chat/Canvas, read-only member workflows, workspace/lifecycle/setup and
  mobile enrollment/Ask Border/approval paths for impact; expose only supported,
  authorized capabilities rather than adding an unrestricted remote control API.
- Preserve verified TLS, principal attribution, origin/CSRF protections where
  applicable, exact one-use approvals, uncertain-outcome handling and GAIT.
  Integration/provider secrets remain at the executing member or its guard.
- Prove stale/wrong endpoint identity, expired/revoked authentication, unsupported
  capability and lost-response behavior refuse safely or reconcile existing work.
- Include G12/G13 in each later specify/plan/task/verification cycle. An affected
  client gap is part of that feature's completion scope, not a silent follow-up.
- Allocate the next free spec number at kickoff. Keep existing R01–R20 IDs,
  completed evidence, source/extension versions and roadmap publication hold.
- Reconcile the existing shared bounded-pass allowance across R04a and R05 at
  planning; inserting a milestone does not silently reset or increase that limit.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Reported gap | Actual VS Code reproduction, observed failure, diagnosed cause and before/after result against the selected cloud Border |
| VS Code integration | Real extension connects and authenticates, identifies the intended Border, completes a supported R04 read-only workflow and displays attributable results |
| Mobile integration | Explicit impact map; affected flows pass in the selected actual app/device, or a reasoned no-change decision cites inspected contracts and regression evidence |
| Authority and secrets | Invalid/stale identity and revoked/expired authentication refuse; no authority increase, member secrets in clients or direct model/MCP/admin exposure |
| Recovery | Disconnect, client restart and lost response preserve operation identity, approvals and results without repeating an effect |
| Compatibility | Existing local profiles and selected-runtime behavior preserved; cloud capabilities and unsupported controls are stated accurately |
| Continuing objectives | R05–R20 each carry separate G12/G13 impact, task/disposition and verification rows; no backend-only completion claim |
| Lifecycle and handoff | Qualification versions/platforms and limits recorded; fresh owned resources retired after evidence export; no R04 plan replay or publication |
