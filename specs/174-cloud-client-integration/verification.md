# R04a verification

R04a technical implementation, actual Mac VS Code/native iOS simulator qualification and owned retirement are complete:16/17 tasks. Human evidence acceptance (T017) remains required before R05. R04 remains accepted/merged/retired.

## Actual pre-fix reproduction (T003)

On source44cfe290, isolated actual VS Code1.109.0 activated the unchanged extension. The real `netclaw.addConnection` command accepted a friendly name and HTTPS address through native input UI, then displayed the host-local URL rejection. No profile was saved and no network connection was attempted. A reserved `.invalid` origin was deliberately sufficient because validation occurs before networking. Private receipt and screenshot: `roadmap-r04a-20261103/reproduction/`.

The initially selected installed editor1.108.0 refused extension engine^1.109; this separate compatibility failure is retained in editor.log. The supported cached editor is isolated; the owner's installed editor was not upgraded. CUA is unavailable in this session; actual native input automation used the existing Playwright/editor-harness approach.

## Source verification

- Python3.12: protected capability/handler consistency plus existing edge enrollment:7 passed. Protected Edge now advertises no legacy text/voice/media/recovery support, matching its refused Ask handler; local enrollment remains unchanged.
- Node24.19: existing protected production ingress/server, owner authorization and reference recovery suites:30 passed. No server route/authority broadening.

## VS Code source and review

Final product216b04d6 (integrated83a3943c), harnessa4a3f818 (integrated12034464): TypeScript check/build passed on Node24.19. Full extension suite169 tests:166 passed,3 existing optional skips,0 failed. Actual disposable local lifecycle/setup regression6/6 passed. Final focused cloud suite20/20 passed. Independent final review confirmed all11 integrated extension files match the qualified lane byte-for-byte.

The reviewed implementation separates cloud-owner authority from local management/MCP, validates exact canonical review digest, retains non-secret nonce/operation/decision references and suppresses late output on close/profile change. Independent review caught and resolved a definite-unsubmitted refusal dead end and missing local expiry guard. Explicit discard is restricted to the exact nonce with definite pre-submission proof; unknown/404 never permits discard. Expiry is checked before native offer, decision marker and transport.

## Mobile source and build

Mobile commit410d2690 (integrated as51ce4ae1):459 Flutter tests passed (442 existing plus17 cloud security/recovery/widget tests), analyzer clean. Flutter3.44.8/Dart3.12.2. Durable decision markers prevent another approval after a lost reply/restart; lifecycle-generation checks prevent late storage completions from restoring private state after suspension.

Final independent review found that definite-notSubmitted proof was memory-only: after restart, an unsubmitted nonce could remain stuck behind a404. Correctionc0b0c034 (integratedc3204ec2) durably stores only exact nonce-bound proof, skips the nonexistent status request and requires explicit discard. Unknown/404 never creates proof. All20 focused Mobile tests and analyzer pass, including three added restart/background/unknown404 regressions; independent code review passes. This narrow error-path fix is separately source-qualified. The actual successful native workload/restart evidence remains bound to earlier410d2690/51ce4ae1; it was not replayed on the final fix.

An isolated native harness imports the actual production cloud screen/client through a local package dependency. Xcode27.2/iOS SDK27.2 built and code-signature verification passed for `ca.automateyournetwork.r04aClientQualification`, deployment target16.2. The first generated-project build failed on its obsolete13.0 deployment target; correction is confined to the private harness. The existing Mobile app, its Watch bundles and App Groups were not modified on the device.

Physical install was refused because the paired iPhone was locked (CoreDeviceError10003). Physical execution remains unqualified. Qualification continued on the actual native iOS26.5 iPhone17Pro simulator with the separately identified app; no provider ticket was embedded in source, build assets or launch arguments.

## Available native targets

Actual `xcrun devicectl list devices` found a paired iPhone14,5 running iOS27.0.1, but its locked state prevented installation. Simulator execution below is actual native-app evidence, distinct from physical-device qualification. Android, physical iOS, Watch, Windows/Linux editors and general deployment remain unqualified by R04a.

## Fresh cloud setup

Reviewed fresh foundation plan e04d1bfb13be99af15a3292bd0328a836c926661173a9b7f180485f7b46d9ac6 applied once:18 creates. After actual host quota/rate/expiry proofs, activation plan a2f5bc9cfab5ee399168485dc6e3bea30a1ebcb688b5797bf65cfce3d2699316 applied once:6 new firewall rules,18 no-op resources. The fixed stop remains2026-11-04T12:12:52Z; cleanup follows evidence rather than waiting for expiry.

Fresh R04a DNS was created once with TTL600, verified through the provider and both authoritative nameservers; the current R01 record remained identical. The fresh operator secret received exactly numerical version1 and was verified byte-for-byte privately. No credential values were emitted. Current private receipts live under `roadmap-r04a-20261103/cloud-plan/`.

The server was frozen at4a3ed4e38ac76b4227d354ef9fc8ed15dd5ae2ce. Later client commits do not imply server redeployment. Fresh Border/member installation IDs were e459926a-609a-4f69-96a6-f13f12e1c191 and1b5e05bd-7701-4f69-a768-29c5a5d7d01f. GCP reassigned two former R04 numeric addresses to new instances; no old VM, key, authority, enrollment or state was reused. Host quota/rate/expiry, metadata denial, private-port confinement and pinned Docker checks passed before client execution.

## Actual client reads and recovery

Both clients used the existing NetClaw NetBox skill/native MCP through the fresh OpenClaw2026.7.1-2 member and guarded Sonnet4.6. Each approved operation produced one native MCP call, two inference calls, a verified signed result and durable ACK. No device configuration or NetBox mutation was requested.

| Client | Exact operation | Workload | Result digest | Recovery |
|---|---|---|---|---|
| Mac VS Code1.109.0 | `0dfa4818-6350-4920-85bc-bd43c47f5994` | `dcim.device`, ID1 | `1ec40ea94f27efccbd2709a84104cff3a0ca69da865c1d19eaa6f85f6aa70006` | Actual editor process restart; same reference/result/attempt, no prepare, decision or reconcile |
| Native iOS26.5 simulator | `f4c0b670-43de-4c0d-9c2a-cacb62dca323` | `ipam.prefix`, ID1 | `b83b8bcaca2ed96cd508f4f434ab4b4bedfecfca3c32d42c36e193df2d1dad25` | Actual app termination/restart; four GET requests, identical reference/result/attempt |

The editor displayed the complete immutable review in a scrollable read-only document, followed by a compact native decision. Mobile rendered the production cloud-owner screen, required its exact-review checkbox and submitted one decision. Each result has attempt_count1, verified=true, durable_ack=true and ack_delivery_pending=false. The member's signed execution intervals were103,604ms (editor) and95,569ms (Mobile). Signed receipts mark provider token usage unavailable; exact provider request counts come from the separate guard evidence, not estimated token usage.

Private editor evidence: `editor/lane-verification.json`, successful `editor/profile/result-1793753411403.json` and restarted `result-1793753452739.json`, with native screenshots. Mobile evidence: `native-evidence/prepare-v3.json`, `approve-v3.json`, `recover-v3.json` and `recovery-comparison.json`. Approval/recovery receipt SHA256 values are bbce3e2883bb3ad08d8af6427d99dd562b57993d24aed1389bb7eaf88caeeb3a and4fb955670be2ab3330ac24954239e97251e1b9d68b5805b4a3732738c77862b4. These remain local private evidence, not replayable inputs.

Independent Mobile receipt `native-evidence/mobile-lane-verification.json` (SHAe2e5a7c79fd1b36ae8e5f4c0f6d2feeecf85a57f1812c3c35e1f4b63a3be9aa3) rechecks full review equality/digest, source/harness hashes, same-result recovery and separately qualified final correction. Retained v2/v3 reports restore the existing secure owner session; the first native preparation passed but its report was lost with Documents. The retained receipts therefore prove native authenticated workflow and secure-session restoration, not a separately retained fresh-ticket UI transcript.

## Retained failures and qualifications

- Native editor automation first failed on DOM whitespace before approval. The next actual review exposed a viewport-overflow issue; the product now uses a complete scrollable review plus compact confirmation. Both failures remain preserved.
- GET status reads the Border ledger; the first approved editor wait stopped at member_admitted. Explicit reconciliation of that same operation fetched its existing receipt and ACK. The harness now invokes native reconciliation before waiting; neither approval nor execution was repeated.
- A successful first Mobile preparation used `flutter test`, which removed the app Documents evidence on exit. The private driver now exports through host reportData before teardown. A subsequent review expired before approval while the driver/reconciliation procedure was corrected. Its driver was stopped before configuration injection.
- Three original unapproved reviews remain `refused/owner_denied`: f45e233b-7240-4c6f-b0f3-34279ba64c96,325526a9-c5c8-4f18-8cdf-e97cf2baf0b2 andebf07265-5cca-4706-9bc6-29f905c00935. Each was inspected with no approval, attempt or effect before a normal owner denial. No database mutation, unknown-operation removal or approved-operation replay occurred. Mobile exercised explicit removal of the exact resolved reference before its final preparation.
- Fresh setup retains the initial capability-bootstrap refusal, OS Login alias mismatch, masked Docker-check failure and read-only SQLite diagnostic failure. Corrected actual proofs passed; failed receipts were not relabeled successful.
- Lost-response, wrong identity/TLS, expired/revoked authorization, stale review and lifecycle-generation behavior have source/protocol tests. Actual client process restarts establish the narrower successful-operation recovery evidence above; they do not establish every physical-device/network-fault combination.

## Startup and limits

`pyats_list_devices` initialization failed because the configured pyATS HTTP runtime was unavailable. No device was accessed and no runtime upgrade was attempted. GAIT branch/checkout/kickoff succeeded. Source1.18.4, extension1.5.0 and Mobile1.0.3+6 unchanged. This is the fifth bounded optional pass; no further optional loop. R05 awaits human evidence acceptance; entire-roadmap release/publication hold remains.

## Frozen export and retirement

Independent local cryptographic verification passed both signed approval/result/ACK chains, exact member/principal/profile/native tool bindings and actual Border/member GAIT commits. It accounts for all five authorities: two successes and three owner-denied reviews with no effect. Totals are four provider requests, four inference calls, two native MCP calls and two NetBox GETs. Final paired effect hashes remain identical after both native client restarts. Report `cloud-plan/final-independent-verification.json`, SHA04aa91782a62b24d0e38c984d4f3982e62b6ea0524929cfade9b54270fa7802b. This reads retained native evidence; no extra demo query or arithmetic qualification is implied.

The frozen export contains315 copied files/4,916,404 bytes. Root independently checked every file hash and the exact saved-plan/module/state/tool preconditions before delegating cleanup. Manifest `cloud-plan/final-export-manifest.json`, SHA4abd94a67060fd6fb7b2f0292a7dc29ff55855dc1e7cca8e835884bf6b66693c; review `final-export-review.json`, SHA28c03ed3c38f3ec221ef55c5272cba99c51cd97ce327c8280d88fc28f775fcfa. Selected integration-value scans passed raw files, decompressed snapshot entries, SQLite cells and decoded Git objects. Private keys, integration secret files and temporary session/ticket files are excluded. This is evidence-only export, not a restorable deployment bundle; no claim covers unselected runtime files.

The exact24-delete plan0634ade9b4849125a3d8fe2e2674d4bacab0623b2b9ca2a6d4be96b0428630a6 completed once, exit0, with empty authoritative state. Actual inventories across12 cloud categories found zero owned residues. The exact temporary OS Login key is removed; other keys are unchanged. Owned DNS retirement passed provider deletion/absence and both authoritative nameservers. The isolated simulator app was terminated/uninstalled and its formerly shutdown simulator returned to shutdown; the original physical Mobile app was untouched.

R01's eight checked Compute resources, private state, known-host file, DNS, trusted HTTPS and three shared budgets remain unchanged. Existing R01 costs remain. Historical R01 service-account/secret coverage is presence-only with preserved state, not a full before/after metadata or direct secret-IAM comparison. Cloud closure receipt `cloud-plan/cloud-lane-closure.json`, SHA972c54e941f41497752b4deef21aa211ce9f2a8be80d69fa430b89588ba41f6f, binds all12 final receipts; root checked each referenced hash and the empty state. The315 original frozen-export hashes remain unchanged.

## Handoff

All required technical work is complete for the recorded Mac/editor and iOS simulator scope. The only unchecked task is human evidence acceptance before R05; no acceptance is inferred from technical completion. Final daily memory is local in `memory/2026-11-03.md`; session audit uses GAIT branch `roadmap-r04a-client-integration-20261103`, with the complete final log saved privately as `final-gait-log.json`. No MemPalace tool was available; no long-term-memory write is claimed. Source commits and lane provenance are additionally preserved in the verified private Git bundle. No release, publication, existing-runtime upgrade or R05 work occurred.
