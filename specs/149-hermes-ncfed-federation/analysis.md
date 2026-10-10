# Specification analysis: Hermes NCFED federation

Initial read-only analysis performed after plan and all44 tasks existed. Mobile expansion was separately analyzed after the updated53-task plan existed. Owner authorization covers subsequent remediation and proceeding to implementation. Corrections below were applied only after the analysis pass; this report is its retained record.

| ID | Category | Severity | Location | Finding and correction |
|---|---|---|---|---|
| A1 | Underspecification | High | contracts/runtime-execution.md | Specify bounded per-effect permit lifetime, exactly-once admission key/digest, issuer authentication, ownership of returned handles and failure/restart behavior; added explicit rules and T005/T030 tests. |
| A2 | Ambiguity | Medium | contracts/capability-card.md | Compiled compatibility version does not prove selected installed version; require source/executable provenance or null and bounded observation. |
| A3 | Inconsistency | High | tasks.md T040 | Preparing a handoff cannot complete host acceptance; task now explicitly remains unchecked until execution. |

Final pass: all three findings resolved in artifacts; zero unresolved critical/high findings, zero constitution conflicts, zero unmapped tasks, zero unresolved product decisions. Runtime implementation and live acceptance are not yet verified.

## Coverage

| Requirement | Tasks |
|---|---|
| FR-001 | T003,T009–012 |
| FR-002 | T003,T009–012,T020–021 |
| FR-003 | T018–023,T038–041 |
| FR-004 | T018–023 |
| FR-005 | T013–017,T038 |
| FR-006 | T024–027,T038 |
| FR-007 | T014,T034–036,T039 |
| FR-008 | T017,T027,T035–036 |
| FR-009 | T005,T015,T023–031 |
| FR-010 | T005–007,T015,T023,T030–031 |
| FR-011 | T005,T007,T028–031 |
| FR-012 | T028–031 |
| FR-013 | T007,T022,T030–031 |
| FR-014 | T021–023,T030–031,T040 |
| FR-015 | T004–007,T024–026,T030 |
| FR-016 | T004,T015,T032–035 |
| FR-017 | T004,T008,T032–033 |
| FR-018 | T005,T008,T013,T032 |
| FR-019 | T004–005,T015,T031,T039 |
| FR-020 | T003,T011–012,T019–021,T037 |
| FR-021 | T036–037,T041 |
| FR-022 | T039–044 |
| FR-023 | T003,T017,T027,T035–036 |
| SC-001 | T013,T018–023,T038–039 |
| SC-002 | T038–041 |
| SC-003 | T024–027,T038–041 |
| SC-004 | T028–031 |
| SC-005 | T032–033,T038–039 |
| SC-006 | T034–036,T039,T041 |
| SC-007 | T004–005,T015,T039 |
| SC-008 | T037,T041 |
| SC-009 | T039–044 |
| SC-010 | T003,T017,T027,T035–036 |

Initial metrics:23 functional requirements +10 buildable success criteria;44tasks;33/33coverage (100%). Setup/foundation/polish tasks map to cross-cutting evidence, safety and coherence. Requirements checklist16/16 complete. Proceed to implementation under existing owner authorization.

## Mobile expansion analysis (2026-10-10)

Read-only source/artifact comparison after the owner expansion found the following required corrections. Remediation follows under the same explicit authorization; these findings do not certify implementation.

| ID | Severity | Finding | Required remediation / verification |
|---|---|---|---|
| A4 | High | Adding execution context alone cannot enable mobile: protected scoped profiles reject operator and broker accepts only HUD ledgers. | T047 extends both as one change, using backend-issued device scope and existing permit; external receiver profiles remain unable to orchestrate. |
| A5 | High | Mobile persists only after Ask acknowledgment; a lost receipt strands executed work. | T048–049 persist client request first and query owner-bound original admission through existing task methods; never resubmit uncertain work. |
| A6 | High | A reused member label after re-enrollment could inherit old conversation/task ownership if only member_id is used. | Bind new mobile context and recovery to the enrolled key fingerprint/generation as well as installation/device; add cross-generation negatives in T046/T051. |
| A7 | High | New backend states become generic unknown→pending in Chat, reconciler, Siri/watch and Live Activity. | T049–051 update all projections, preserve evidence-only recovery, distinguish cancellation request/confirmation and add explicit legacy explanation/minimum version. |
| A8 | High | Existing attachment-to-text-file path is not typed multimodal support and exceeds protected bounds. | T046/T050 reject/advertise unavailable before Hermes admission, preserve OpenClaw tests and label no media parity. |
| A9 | Medium | Gateway Hermes branch ignores voice composition and member deadline is shorter than mobile outer deadline. | T047 uses explicit interaction-origin composition before body hash; respects configured outer deadline and bounds child work. |
| A10 | Medium | Existing mobile integration test logs rather than fails on missing result; available iOS tools do not establish physical-device/Android coverage. | T052 requires actual matched execution/result; T053 records simulator/build/signing separately and unrun Android/physical-device tests. |

All seven corrections are now represented in plan/contracts/tasks. Zero unresolved scope decisions or constitution conflicts. The original federation implementation continues alongside this extension; acceptance and build tasks remain open.

| Added requirement | Tasks |
|---|---|
| FR-024 | T046–048,T052 |
| FR-025 | T046–052 |
| FR-026 | T046–047,T049,T051–052 |
| FR-027 | T048–051,T053 |
| FR-028 | T046,T050–053 |
| FR-029 | T051–053 |
| SC-011 | T046–049,T052 |
| SC-012 | T048–052 |
| SC-013 | T051–053 |

Expanded metrics:29functional requirements +13success criteria;53tasks;42/42requirements mapped. No unresolved high/critical artifact findings after the documented remediation. Implementation verification remains pending for the added scope.

A11 — Owner explicitly superseded the earlier upload prohibition with an App Store Connect push request. T054 covers signed archive, validation, upload and processing evidence. Public release remains outside scope. Dashboard type is covered by T050, with unknown metadata retained. Distribution completion must not imply physical-device qualification.

A12 — Public article, both PR links and source 1.8.0 explicitly authorized by latest owner steering; T055 added. Content must not claim full Hermes/mobile/tool parity or unrun physical-device/WSL acceptance. Existing five infographics require captions consistent with actual qualification.

## Final implementation analysis

A read-only cross-artifact/code/evidence pass identified and then rechecked these
corrections under the owner's existing implementation authorization:

| ID | Severity | Finding / disposition |
|---|---|---|
| A13 | High | Companion restart could expose a persisted upstream queued receipt with no worker. Federation startup marks unknown; nonterminal status cannot erase uncertainty. Real kill/restart/no-replay test passes. |
| A14 | High | OpenClaw WS lookup ignored custom selected config. Fixed; six-process four-pair internal and bidirectional mixed external acceptance passes. |
| A15 | Medium | Watch manual status retained provisional admission IDs. Resolve persisted admission and rebound alias without replay; Flutter regression passes. Final mobile build is1.0.3(6), superseding uploaded build5. |
| A16 | Medium | Disabled federation/dead companion could still look ready. Daemon distinguishes running mesh from enabled, owned live federation; HUD requires matching installation/harness. Selected CLI tests cover the disabled case. |
| A17 | Medium | Plan/tasks retained old publication/upload exclusions and53-task count after owner changes. Updated to55tasks; explicit App Store Connect and website authorization retained, public App Review/release excluded. |
| A18 | Qualification pending | No fresh Linux/WSL host/control acceptance or physical mobile/Android run. T040 remains open, handoff is runnable, production Hermes control fails closed; docs/article must not imply those passes. |

Coverage:29functional requirements +13success criteria,42/42mapped;55tasks.
T054 maps to FR029/SC013 and the explicit distribution instruction; T055 maps to
FR022/SC009 plus the explicit public-release-docs instruction. No unmapped task,
new constitutional conflict or unresolved product decision. Code/contract defects
A13–A17 are resolved with tests; A18 remains an acceptance limitation, not a pass.
The final publication/evidence tasks close only after public verification. This
report does not mark T040 complete or convert prior spec148 WSL/browser evidence
into spec149 evidence.

A19 — Final actual daemon CLI test found `start` restarting an already running owned daemon and readiness appearing before authenticated companion startup finished. `start` is now idempotent; explicit `restart` performs the stop/start. Readiness becomes true only after the authenticated companion health check. Both real lifecycle tests and17focused follow-up checks pass. No broad process kill or foreign-listener replacement was introduced.
