# Requirements quality checklist: Genie network worlds

**Purpose**: Author/reviewer design gate before task generation; tests the written
requirements, not implementation. **Created/reviewed**:2026-11-22.
**Feature**: [spec.md](../spec.md). **Depth**: rigorous for privacy/lifecycle/spend.
All checked items mean requirement quality passed, never live acceptance.

## Completeness and scope

- [x] CHK001 Is the operator benefit of a spatial walkthrough explained without promising network simulation? [Clarity, Spec Clarifications; FR-005]
- [x] CHK002 Are specification/planning, direct proof, native integration and feature completion distinct milestones? [Consistency, Spec Clarifications; FR-026; SC-010]
- [x] CHK003 Is the skill/MCP role distinguished from provider execution and media streaming? [Completeness, FR-013; Plan Summary]
- [x] CHK004 Are preservation of198, reservation199 and later roadmap ordering explicit? [Coverage, FR-011]
- [x] CHK005 Are separate HUD, VS Code and Mobile impact decisions documented? [Coverage, FR-012; Plan Product impact]
- [x] CHK006 Is standalone proof versus full artifact coherence explicitly scoped rather than silently waived? [Consistency, Plan Constitution Check/Complexity Tracking]

## Facts and private data

- [x] CHK007 Are observation provenance, timestamps, parser outcomes and source identity required for every measured fact? [Completeness, FR-003/015; SC-003]
- [x] CHK008 Are inventory, controller state and actual device observations distinguished? [Clarity, FR-001/015; SC-001]
- [x] CHK009 Are unknown, stale, empty, raw-only, timeout and conflicting data meanings distinct? [Coverage, FR-014/016]
- [x] CHK010 Are observed, one-sided, corroborated, unknown and fictional links distinguished without inference from shared addressing? [Clarity, FR-015; Data model Link]
- [x] CHK011 Are collection scope, concurrency, byte limits and deadlines quantified? [Measurability, FR-014]
- [x] CHK012 Is independently synthetic input required rather than relying on renamed private topology? [Consistency, FR-004/017; SC-004]
- [x] CHK013 Are image metadata, recordings and hosted-agent context included in the privacy boundary? [Coverage, FR-017/019/025; Plan Architecture]
- [x] CHK014 Are untrusted device strings kept from becoming instructions, paths or executable content? [Coverage, FR-019; Plan Observation pipeline]

## Lifecycle, credentials and cost

- [x] CHK015 Are credential presence, subscription, API entitlement and actual generation evidence separate? [Clarity, FR-018; Edge Cases]
- [x] CHK016 Is exact input/model/event/allowance review bound to later execution and invalidated by changes? [Completeness, FR-018; Data model ReviewGrant]
- [x] CHK017 Are local budget estimates distinguished from service caps, actual usage and billed cost? [Clarity, FR-022; Plan Session lifecycle]
- [x] CHK018 Are maximum-exposure reservation and missing-price/bound failures addressed? [Coverage, FR-022; Plan Session lifecycle]
- [x] CHK019 Are browser, MCP, manager, worker, host and upstream connection losses distinguished? [Coverage, FR-020/021; Plan Session lifecycle]
- [x] CHK020 Are duplicate/concurrent requests and creation with a lost ID covered without blind replay? [Coverage, FR-020; Data model State machine]
- [x] CHK021 Is a completion request explicitly distinct from a provider terminal receipt? [Clarity, FR-021; SC-009]
- [x] CHK022 Is missing usage distinct from confirmed terminal state and zero cost? [Consistency, FR-022; Data model UsageRecord]
- [x] CHK023 Are unknown-outcome holds retained across identifiers, credentials and restarts, with reconciliation boundaries? [Completeness, FR-020/022; Data model Admission]
- [x] CHK024 Are deadline and heartbeat defaults quantified, including failure before first frame? [Measurability, Plan Session lifecycle; Quickstart step4]

## Experience and acceptance

- [x] CHK025 Are facts, roles, legend, timestamps and fiction labels readable outside generated pixels? [Completeness, FR-023]
- [x] CHK026 Are keyboard controls, focus, stopping and non-color/non-audio information specified? [Coverage, FR-023]
- [x] CHK027 Is actual generated navigation required with a measurable duration? [Measurability, FR-008; SC-002/008]
- [x] CHK028 Are event intent, send and observed visible outcome distinct, with timestamps and explicit failed/unassessed outcomes? [Clarity, FR-024; SC-008]
- [x] CHK029 Are recognizability and structure/link drift assessed at fixed checkpoints without assuming unseen content? [Measurability, SC-007/008]
- [x] CHK030 Are previews, prepared prompts and documentation excluded as substitutes for a generated world? [Consistency, FR-010; Acceptance decisions]
- [x] CHK031 Are recording failure, insufficient navigation time, provider error and absent receipt treated as incomplete/failed evidence? [Coverage, FR-025; SC-009; Quickstart step4]
- [x] CHK032 Are GO,NO_GO,BLOCKED_LIVE and owner-approved scope amendments distinct while original failures stay visible? [Clarity, Acceptance decisions]
- [x] CHK033 Is actual native NetClaw skill/MCP execution required beyond tool discovery or direct API proof? [Completeness, FR-026; SC-010]
- [x] CHK034 Are retention, evidence bounds and unknown-session preservation stated? [Coverage, FR-025; Data model Evidence]
- [x] CHK035 Are missing credentials a live gate rather than a reason to leave planning unfinished? [Consistency, Spec Clarifications/Assumptions; Quickstart step3]

## Review record

35/35 written-requirement checks passed. No requirement clarification placeholder
remains. Implementation and live acceptance are entirely separate; see
[verification.md](../verification.md). No task completion percentage is inferred.

### Owner refinement review

- [x] CHK036 Realistic and fantasy worlds require actual Google sessions; local renderer substitution is excluded. Authoritative facts stay separate and visual drift is assessed (FR-023a;direction-correction.md).
- [x] CHK037 CDP/LLDP identity,one-sided/conflicting/stale links and controller wiring have distinct provenance (FR-015).
- [x] CHK038 Counter continuity,sampling interval,capacity and unknown-rate rules are explicit (FR-023b).
- [x] CHK039 Detailed collection remains finite and cannot enable discovery or polling (FR-014a).

39/39 written-requirement quality checks reviewed;this is not live acceptance.

### Routed-lab expansion review

- [x] CHK040 Is explicit lab change authorization separate from read-only collector and hosted export authority? [Spec routed CML evidence; routed-lab qualification]
- [x] CHK041 Are physical discovery, OSPF/iBGP adjacencies, route installation, VLAN/STP and endpoint reachability separate evidence types? [Data model routed-lab extension]
- [x] CHK042 Are management preservation, stopped hosts, persistence, actual rollback and API uncertainty retained? [Routed-lab qualification]
- [x] CHK043 Does the complete command catalog distinguish planned product coverage from actually executed bounded manifests? [Collection commands; Plan routed-lab preparation]

43/43 written-requirement quality checks reviewed. These checks establish written
requirements, not product implementation, generated-world acceptance or host health.

### Release integration review — 2026-11-23

- [x] CHK044 Does the owner's accepted recorded-illustration scope preserve historical strict visual/event failures without claiming exact topology? [Spec owner acceptance amendment; SC-007/008]
- [x] CHK045 Is the member owned and routed by the existing Border while Google termination and credentials remain backend-owned? [FR-026; native-review.md]

45/45 written-requirement quality checks reviewed. Actual integration is 25/30;
see integration-closeout.md for the five open tasks.
