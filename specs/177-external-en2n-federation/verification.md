# R06 Verification

Status: **35/35 tasks complete** for final technical qualification and the approved retained-delivery scope.
See the final actual qualification section and parity-matrix.md. Earlier checkpoints
are historical and do not override the final evidence.

## Scope and source

Owner requested existing eN2N cloud parity, full SDD through100%, three independent
organizations/full triangle, two separate cloud resource sets in the existing
GCP project and local third organization. Branch177-external-en2n-federation,
baseline6cdfde1e5834725907ed9e4b14f44f22e45013a4.

The owner approved fresh ordinary full Borders through the concrete activation
packet; no profile or activation approval remains pending. Ordinary outcomes are
not protected-operation/member-ACK qualification. Existing R01/R04a/R05 runtime
and cleanup obligations remain outside this new installation scope.

## SDD analysis

35 sequential tasks;16FR+6SC mapped,22/22coverage; no unresolved template markers
or missing mandatory artifacts. Read-only semantic analysis identified two HIGH
contract underspecifications: unnamed ordinary-client capability and unnamed
external-agent selection. Resolved in contracts/client-surface.md and
contracts/cloud-federation.md before implementation. Recheck found no remaining
critical/high source-design findings. Exact actual activation remains a later
concrete plan gate, not a source-design placeholder.

## Baseline evidence

| Check | Observed result |
|---|---|
| Isolated Python n2n core/auth/registry |22passed,1.07s;2existing datetime warnings |
| Core/auth/registry plus secured federation/protected role |47passed,1.28s;4existing datetime warnings |
| Spec/task structure |35sequential IDs,22requirements covered, no unresolved template markers |
| Git whitespace |Pass |
| GCP read-only inventory |Five categories succeeded;2instances/3networks/3addresses/12firewalls/4serviceaccounts; no R06 matches |
| Existing VMs |Observed R01 and R05 running; no runtime changes |
| Startup pyATS |Initialize failed: configured HTTP runtime missing; no device contacted |
| MemPalace |Initialize failed: module absent; file memory/GAIT used |
| GAIT |Branch/checkout/status confirmed; kickoff6e5ae481 |

Commands:

```sh
.contract-test-envs/n2n/bin/python -m pytest -q tests/n2n/test_secured_federation_060.py tests/n2n/test_en2n_regression.py tests/n2n/test_en2n_auth_baseline_060.py tests/n2n/test_endpoint_registry_168.py tests/n2n/test_protected_role_172.py
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
git diff --check
```

Private evidence root: `~/.local/share/netclaw/roadmap-r06-20261106/`.
Inventory receipts are under research/cloud-inventory. This five-category scan
is not a complete residue assessment. Source tests are not cloud or native-client
execution evidence.

## Historical pre-activation checkpoint

The following source milestones preceded actual acceptance. The final section
records their completed cloud/native qualification and retained lifecycle. No
release, publication, device configuration, ticket or external message occurred.


## Selected-runtime correction

New selected-tool tests reproduced4failures before implementation: modern/legacy selected registrations were ignored, foreign fallback executed, and timeout behavior could not reach the intended selected child. After correction, selected configuration, reserved home selectors, canonical component binding and owned process reaping pass. Optional external agent selection tests reproduced5failures before implementation; configured valid profile now selected only for external gateway turns, missing/invalid/operator-equal profiles refuse before RPC, unset preserves legacy behavior. Final focused27tests passed2.21s. Native policy-function validation is recorded below; actual deployed gateway qualification remains open. These are source fixtures, not cloud qualification.


## Triangle, native tool and recovery source evidence

Strict loopback TLS triangle uses independent CA/certificate/application identities. Local C listener is closed before local→A, local→B and A→B connections; all six bidirectional RPC directions pass. Closing C/A preserves C/B and A/B. No service transport correction required (T007). This is local socket evidence, not cloud firewall/DNS qualification.

Six-direction workflows pass inventory, two-turn isolated chat, actual hash-checked installed subnet MCP process execution and asynchronous task submission/retrieval. Model chat/skill responses are deterministic fixtures, not provider qualification. Native subnet uses a private copy of the existing reviewed installer patch; initial raw vendor source failed against MCP2.3 because its historical FastMCP import is unpatched. No vendor/owner runtime was modified. The workflow exposed a canonical component-launch relative-path gap; exact declared wrapper registration now resolves through the installation-owned component helper.

Lost-channel retrieval previously dropped source/trust and token usage. Corrected cache projection retains them and enforces outbound peer/task ownership. Remote response fields cannot overwrite local source/trust. Dispatched ordinary gateway workers retain outcome_unknown on response loss; same request resolves to the original task and is not rerun. Native gateway transport no longer transparently retries after loss, including clean WebSocket closure. This supersedes the retry expectation in Spec116 for this implementation.

Source runs:11triangle/agent tests passed0.24s; six-workflow native-MCP matrix passed6.55s;42combined runtime/triangle/workflow/recovery tests passed11.40s;27provenance/workflow/gateway/task tests passed9.50s before structured-result cases were added. All initial failures remain described above; no live cloud/provider claim.

## Native external-agent policy and result attribution

Installed OpenClaw2026.7.1-2/Node24.19.0 schema and actual native global/agent/final-MCP policy functions validated offline. Initial no-read profile and amended narrow skill-read profile both pass: main can use only selected outbound n2n tools; external can use read plus subnet MCP, with workspaceOnly and a dedicated skill workspace. Native agent names normalize lowercase; selector now rejects uppercase, operator equality and normalized duplicates. Session keys bind agent:external to an opaque SHA256 of the original context; bare keys would route to main and fail native validation.

Private native-source hashes, validation script, candidate config and results: research/native-policy/ and skill-read/ under the R06 evidence root. The amended policy allows reading only the intended skill context subject to native path/skill-root checks; actual deployed skill snapshot/native read/MCP evidence remains required in T025/T028. Static native function validation does not prove prompt containment or actual runtime behavior.

Bounded external provenance joins native authenticated agent run/toolCallId events (locally generated run ID) to local outbound request/task receipts. No inference from model prose, no arbitrary peer result fields as authority. Malformed/truncated/unmatched events omit attribution. Records persist with parent task ownership, status/result and edge push. Native MCP JSON output is explicitly selectable with NETCLAW_FEDERATION_JSON=1. Mobile parsing/rendering is implemented and tested as recorded below. Source rows now expire with their retained parent task.


## Client source integration

Explicit ordinary mode validates a fresh private role/installation binding, pinned workspace/assets, fixed daemon URL and exact HTTPS origin. Protected profiles cannot enter ordinary mode; protected route/schema tests remain unchanged. Peer chat is available only in ordinary cloud mode with peer feature, exact installation/origin and bounded payload; backend310s→edge320s→editor330s deadlines leave room for existing daemon300s and never retry. Projection restores skill/version/freshness/chat/in-flight/approval display fields without publication of control routes. VS Code discovery accepts exact ordinary capability or complete protected capability; mixed capability is refused, changes close connection, protected actions are unavailable for ordinary.

Ordinary Mobile retains the existing native WSS endpoint/QR/legacy conversation mode; it does not adopt protected operations or a new scanner. Cloud edge uses exact HTTPS issuance origin and fixed loopback enrollment adapter without protected auth_context. Separate ordinary cloud QR tests assert domain/8443/root-path; existing protected issuance/refusal tests remain. No Python endpoint change was needed. Native source records now persist in Mobile conversation, reconnect recovery and live-activity/watch intake; UI displays explicit external/untrusted peer references. Older answers never infer attribution from text.

Focused results:67federation/identity/boundary tests pass5.83s (four existing datetime warnings);24HUD edge/remote/protected tests pass0.82s;39editor owner/remote tests pass0.23s;22Mobile persistence/recovery tests pass. Full editor208tests:205pass/3existing skipped,35.61s. Full Flutter497pass20s. Federation69focused tests pass29.30s. Full HUD initial517/518: one existing Avatar button timing assertion failed while all suites ran concurrently; isolated reproduction passed, and clean full rerun passed518/518 in5.90s. Initial two editor message assertions failed after more specific refusals; wording now preserves existing expectations and all39pass. TypeScript noEmit and extension build passed. HUD Vite build passed1.52s with its existing large-chunk warning. Flutter analyzer passed with no issues, including the new native harness phases.

GAIT progress665eddb0. Cloud definitions/actual execution/client journeys remain open; these checks do not qualify deployed source.


## Broad regression and cloud preparation checkpoint

Full federation plus native gateway client and R06 host/plan suite:
**1758passed,5skipped,94warnings in101.84s**. Environment:
`~/.local/share/netclaw/roadmap-r04a-owner-20261104/local-member/venv/bin/python`.
No owner runtime was started or changed. Initial broader run in the smaller R05
venv had1724passes/18failures/5skips:17replication failures from absent ChromaDB,
and one source-integrity failure from the changed n2n MCP source hash. The reviewed
hash was added to the existing Hermes tool policy;33affected tests passed8.45s
with existing ChromaDB, then the entire suite passed in that environment.

Gateway reconnect now joins the old reader before replacing shared pending state;
a stale reader cannot fail a new connection's requests. Retention removes native
external-source records when their parent is removed. Focused recovery/provenance
18tests passed0.52s. No automatic gateway retry is restored.

Hermes HUD compatibility:30tests,24pass/6existing skips with qualified Node24.19.
The first invocation inherited an unsupported Node and three port-refusal
subcases failed at the earlier Node-version gate; the qualified-Node rerun passed.
No live Hermes/provider acceptance is inferred.

Catalog generation parity, metadata112components/239skills, coverage126registered
servers/52external integrations, and Comms77entries pass. Broad public-link check
found168verified/0dead/2needs-review; no catalog URL was changed. These transient
link results are not deployment prerequisites or a claim all upstreams are live.

New cloud source:16host/secret/plan tests pass, including immutable plan/source,
one-use unknown apply, verified export, role secret isolation, finite egress,
IAP export preservation and separate signer/gateway/edge users. OpenTofu1.13.2 /
Google8.9.0 init/validate passed. The actual saved foundation plan has16creates,
zero updates/deletes/imports. The activation preview has34creates; inspection
verified separate networks, no project role/peering, own-secret IAM references,
Shielded/no-forward VMs, private client ingress and fixedSTOP. The preview is
not executable: host guards and current-state delta review precede activation.

Fresh Linux AMD64 dependency build uses current HUD lockfile, existing pinned
Node24.19/Caddy2.11.7/Python3.12/FastMCP/MCP dependencies and OpenClaw2026.7.1-2.
Actual Linux HUD and federation module imports pass with pyOpenSSL26.4.0 and
cryptography50.0.2. Linux Caddy adapt/validate passes. Both fresh native gateway
candidate configurations pass installed native schema/effective policy checks.
The current971-file source archive is `source-package-v2`; the earlier970-file
archive is preserved but superseded for preparation. No private home or credential
is in either source archive. Hashes and exact scope are in deployment-review.md.

Fresh DNS GETs returned empty records for both proposed R06 names and the existing
R01 record unchanged. Fresh CAD pricing confirms10.95for the proposed48h cloud
base costs, excluding the explicitly listed additional usage. Existing budgets
are observed only. No R06 cloud/DNS/provider operation has occurred.

Mobile native harness preparation adds `external-ask` (production Send once,
required native source attribution) and `external-recover` (retained IDs, original
result GET and unchanged source). It reuses the real QR PNG decoder and existing
production enrollment screen, in a separate simulator bundle. Analyzer passes;
these phases have not yet run against cloud. Physical camera/Secure Enclave,
actual VS Code/browser, provider and native federation acceptance remain open.

The owner was asked to review the complete concrete packet through the pending
asynchronous question. No answer, elapsed time or prepared plan supplies approval.
T025's actual final runtime bindings/secret/certificate preparation, T026 approval,
T027–T032 live qualification/lifecycle and final reconciliation remain open.


## Actual activation and retained bootstrap failures — November6

The owner approved the complete packet (“yes go go go go go”; “get it to100%
yes ?”), recorded in GAIT7a196046 and829e6198. No repeated approval is required
for that scope. T026 is closed; actual acceptance remains open. Foundation-v1
failed before provider startup because an evidence-mode normalization had removed
the Google provider binary executable bit. Its exact reviewed hash was restored,
zero effects verified, and a fresh equivalent foundation-v2 plan applied once.
Never replay the spent v1 attempt. v2 SHA256:
`4ffdbef6959f488d142f390b0d1f00f08c87200d2f84dfd8e90b76d499dd5d51`.

Both independent Montréal foundations exist with fixed Nov8 15:19:35Z expiry.
Actual host baselines found clean R06 paths/UIDs, Ubuntu24.04.5, Python3.12 and
installed nftables/iproute2; no package downgrade was needed. Public runtimes,
fresh separate signer/gateway/edge identities and services were installed. Native
TLS/MCP imports, Node24.19 and Caddy2.11.7 passed on both actual hosts.

Live preparation found current OpenClaw `toolFilter.include` was omitted from
federation inventory. Added explicit-name support with conflict/wildcard refusal;
20 focused inventory/runtime/workflow tests pass. Source package v3 was installed
and all971 source hashes verified. Both cloud certificates subsequently issued
with distinct P256 keys. Earlier ACME orders remain failed: inherited wrong
recursive resolvers, then a secondary-validation NXDOMAIN during the observed
600-second negative cache interval. The corrected bounded multi-resolver hold
completed both orders; no failed order was silently retried or called successful.

A real host-network restart activated the closed guard before application quota
activation. The closed policy preserved IAP responses but omitted host metadata,
blocking OS Login and the guest agent. Serial output establishes the failure.
Correction preserves only host administration metadata/DNS/NTP, excludes the
three application UIDs, retains signer/edge metadata denial and application
service metadata confinement, quota/no-reset and fixed expiry.16 cloud-control
tests pass. Recovery uses the two owned VMs and one temporary20GiB rescue boot
disk; original boot disks and private identities are preserved and repaired
offline, with phase claims and exact hashes. Recovery is **in progress**, not
qualified. No provider/federation request or application ingress has started.

Current package v4: archive
`f24cb426646cddfa9544f1a15828ad0a358c9bfc995efafe0e840a4799f4a161`;
manifest `85d86263bdb4e5d0a58adc53fa0defdfba1833f495b94f7d21321f8a17db9ecd`.
The offline guard correction is the only v3→v4 source delta. Private evidence is
under `activation-baseline/`, `certificates/`, `host-recovery/` and
`runtime-bindings/` in the R06 root. Existing R01/R04a/R05 and their deadlines
remain outside every mutation. Full six-direction/native-client/lifecycle
acceptance still determines100%.


## Live activation and first matrix checkpoint — 2026-11-06 17:30Z

The original two VM boots, IDs, disks, addresses, service accounts, SSH host
keys and fixed expiry were restored and verified after the documented offline
host-guard repair. All28 original authority files on each host remained unchanged.
The temporary20GiB repair disk was removed and its absence verified by Compute
404; `host-recovery/rescue-retired.json` retains the exact resource identity.
Current public source packagev4 is971files, archive
`f24cb426646cddfa9544f1a15828ad0a358c9bfc995efafe0e840a4799f4a161`;
manifest `85d86263bdb4e5d0a58adc53fa0defdfba1833f495b94f7d21321f8a17db9ecd`.
All source hashes were verified on both hosts. Closed application-UID metadata
refusal and host OS Login/metadata access passed before one-use guard activation.

The reviewed runtime delta applied18creates with16noops (no update/replacement),
plan `51f9a71b2ab2927ff4421ad213e8029a39543e880ff66dedef07ded93de1e08f`.
Each gateway projected its own exact numeric Secret Manager version1; expected
payload, installation, UID10022 and0600 file checks passed. Both sets of gateway,
federation, workspace, HUD and Caddy services are active. Fresh local C runs in
its own signer/gateway homes. Both cloud HTTPS runtime endpoints validate with
normal trust and report ordinary external federation capabilities.

All three physical strict TLS links are established: C→A, C→B, A→B. Each
organization reports its other two peers federated/channel-up, with successful
possession proof and bilateral consent learned on the actual channel. No remote
consent record was synthesized. All six directions returned actual native subnet
MCP results for192.0.2.0/26. All six two-turn Sonnet chats returned their own
conversation marker with exact peer source and remote-untrusted attribution.
First C→A and A→C asynchronous skills completed, each using the native subnet
MCP for198.51.100.0/27; remaining skill directions and client/refusal/recovery
qualification are still pending. Evidence is in private `live-triangle/`,
`live-matrix/` and `activation-baseline/` receipts.

Native OpenClaw records nonzero Anthropic token usage but zero monetary cost.
Zero is not evidence of free provider usage. The operator harness now also sums
all measured input/output/cache tokens at a conservative USD20/million and stops
additional submissions atUSD10; missing token usage stops dispatch. This exceeds
the published Sonnet4.6 category prices, including the optional1.1geography
multiplier ([Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing),
checked November6). It is an estimate, not a billing receipt. The60-submission,
no-replay and fixed-expiry limits remain. Earlier claims/results are retained.

Fresh R06 iPhone17Pro/iOS26.5 simulator and independent bundle were created;
the native qualification build succeeded. No earlier owner simulator app/profile
was replaced. Actual Mobile enrollment and external Ask Border remain pending.

## Final actual qualification — 2026-11-06

This section supersedes the preparation statuses above. The full delegated R06
scope is technically qualified. All six directions passed actual strict TLS,
independent identity/consent, inventory, two-turn contextual Sonnet chat, native
subnet tool and asynchronous skill/original-result retrieval. See
[parity-matrix.md](parity-matrix.md) for original task IDs and exact scope.

### Deployment and preserved boundaries

Cloud A/B are fresh Ubuntu24.04 AMD64 ordinary Borders in distinct VPCs/subnets,
service accounts, secret projections, private homes, databases and certificate
identities within the existing GCP project. A installation is
`a76e44e4-b135-4f8d-86e0-187bb565ce09`, B
`71fcf47c-812e-4df1-8b21-0e466aa86b5a`, local C
`a49c13e1-015c-4f65-ab91-bf1198222a47`. Three connections, C→A/C→B/A→B, carry all
six application directions. C has no public inbound listener. Actual host UID,
metadata denial, secret isolation, finite network guard, exact ingress, trusted
HTTPS/WSS, runtime and original-identity checks passed. Existing R01/R04a/R05
resources and R05 scheduled authority were preserved.

Live source is the frozen v4 package, archive SHA256
`f24cb426646cddfa9544f1a15828ad0a358c9bfc995efafe0e840a4799f4a161`, manifest
`85d86263bdb4e5d0a58adc53fa0defdfba1833f495b94f7d21321f8a17db9ecd`.
Native runtime: OpenClaw2026.7.1-2, Sonnet4.6, Node24.19, Python3.12. Later exact
host corrections are separately recorded: metadata-compatible guard
`a82f075230d7302e6979d693eb9d0a994d4cc067ef6d691405d9c13cf7b40cff`, native CLI
launcher `34b317a26d5f1d475f649cc6f194be178a8f28034df59c550120c8f410a747d0`, workspace
unit initially `9118c71be05e07833d3db323d3862cc7095bc0cc7e7fef6475b6a7ffa618e47e`.
The final history correction below records its superseding unit and module hashes.
The final repository includes those renderer corrections and the later Mobile
cold-load fix. This is not a claim that every final repository byte was redeployed
to the cloud; the exact tested runtime closures remain authoritative.

The browser exposed a missing native CLI launcher, then a384MiB workspace-cgroup
OOM when native settings/catalog commands overlapped. The pinned launcher and
1024MiB workspace limit with256MiB Node heap corrected these actual failures.
Only workspace services restarted; federation identity, gateway requests, quotas
and authority were preserved. Native gateway status subsequently reported online,
reachable and chat completions enabled. Earlier503 and OOM witnesses remain.

### Actual refusal and recovery

Actual denied cases cover ungranted member/secret/transit tool names; disabled
peer chat; revoked tool grant; strict wrong configured application pin; wrong
claimed hello identity (connection closed before admission); external wire calls
to internal member/admin/enrollment methods; another peer's chat and task;
withdrawn bilateral consent; and exhausted receiver budget. Budget qualification
lowered only B's configured limit12→1 over its already consumed durable counters,
then restored12. The counters were never reset. Both actual B process restarts
preserved authority and results. Other peer pairs exchanged inventory while C/B
consent was withdrawn. Final health reports all six directed relationships up.

`live-cloud-refusals/summary.json` verifies native transcript bytes unchanged
across budget/consent refusals. Earlier `live-refusals/` deliberately hid a skill
advertisement while its independent explicit execution grant remained active.
The harness wrongly expected this authorized call to be denied. It executed one
permitted workspace skill read and asked for a missing CIDR, with no subnet call.
Visibility was restored; this is retained as an incorrect test assumption, not a
security refusal or an unauthorized execution. Hiding advertisement does not
revoke a separate grant. Grant revocation itself was actually denied.

Original loss task `1accd9ca-61ff-45d6-b063-bac5434c69a5` was admitted once; the
local caller process stopped before completion. B completed the original task.
The restarted caller retrieved that same result. Native evidence has exactly one
subnet MCP call for203.0.113.64/28 (plus one permitted skill-file read). No task
was resubmitted. Private probe failures—selected-HOME import path, an assertion
expecting an error rather than the correct ownership-safe `unknown` response,
and expecting an RPC error rather than strict authentication closure—remain
recorded. Each stopped local signer was restored using its original authority.

Across the final workload checkpoint, correlated native evidence counts16subnet
MCP executions,3permitted workspace reads and38provider responses. Browser/editor/
Mobile native n2n toolCallIds join actual receiver request IDs and GAIT records;
model prose is not the source of attribution. Native reported cost is zero despite
nonzero tokens; conservative all-token accounting is USD3.47652 with no missing
usage, not an invoice claim. No device command was issued.

### Actual clients and cold recovery

- Browser Chrome: actual cloud peer view, Ask A→B via native n2n/subnet, original
  answer display and browser-process restart recovery. Recovery submitted zero
  new chats. The ordinary main Chat's answer remains model prose; authenticated
  native MCP source/trust evidence is independently correlated, not inferred from
  the model's wording. A screenshot taken before feed readiness showed a temporary
  Gateway unavailable label; direct live status established actual readiness.
- VS Code1.145.0: owned development profile, native connection discovery, peer
  inventory and chat, native main Ask A→B, answer display and editor restart
  recovery with zero resubmission. Real inventory/reply fields exposed missing
  presenter mappings; those are corrected and regression-tested. A stale frame
  locator failed after one successful early peer chat; its original transcript
  was reconciled before a distinct new marked journey. The original was not replayed.
- iPhone17Pro/iOS26.5 simulator: actual cloud HUD QR image, CoreImage CPU decode,
  production enrollment and trusted WSS, independent Keychain P256 identity, native
  Ask A→C, original answer and structured external-source display. Original task
  `68d95b5f-ede4-4929-8799-cbeedee86d00`, request
  `22d2ced5d81071d5d00d2669d7dc5074b2072f8ac524d5d8`, and remote request
  `b16fd3a1-b70e-4c11-9b26-86e6665a4137` remain unchanged. App termination/relaunch,
  same-key reconnect and original-result fetch passed without another Ask.

The final simulator reboot check reproduced an existing concurrent history-load
race: `_loaded` was set before disk I/O finished, so a second awaiting caller
could observe an empty list. ConversationStore now shares the in-flight Future,
marks loaded only after success and permits recovery after a failed read. Two
new regressions cover concurrent readers/admission and failed-read recovery.
All499Flutter tests, analyzer and actual rebuilt native recovery passed. Final
`mobile-visual-v5-report.json` is framework-passed/same-key with the original turn;
`mobile-final-0.png` was inspected and shows answer plus external-untrusted source.
Earlier permission-dialog, missing harness asset, exact-label assertion and
screenshot-handshake/container-path failures are retained. They were repaired
without replaying the original Ask or changing production permission handling.
Physical camera, physical Secure Enclave and hardware push delivery are not qualified.

### Final browser history correction

A final read-only probe reopened the provisional closeout: initial history listing
returned `sourceAvailable=false` after20.25s, while the concurrent model catalog
completed after24.20s. Direct native reads and the original transcript remained
intact. The CPU-limited host needed more than the default20s native CLI startup
allowance. Only `sessions.list` and `chat.history` now accept an explicitly configured,
bounded60s history allowance; defaults and unrelated operations stay unchanged.
The saved-history proxy has130s for its two possible bounded native reads. There
is no automatic chat, task or provider retry.

Both cloud workspace/HUD processes were restarted with captured baselines and
exact file receipts; federation/gateway identities, quotas and original requests
were preserved. Final workspace unit SHA256 is
`4ae6904e372265328c92ce66327259efaac655100d35c9185348a2c7a2b8e85e`;
`chat-runtime.js` is `e901bbe2c2ba9aa5c089af8cee1e3d83e9d7b06a267654cf63a986cf6b206e4d`;
`remote-hud.js` is `a1a3d83db67924912ff01139f76c453cc48f62280b4e9c7e579648462393c12f`.
These are exact amendments to the frozen v4 cloud package.

`browser-final-visual-v5.json` and its inspected screenshot show the original
192.0.2.64/27 answer, source peer, Gateway available and successful saved-history
recovery with zero new chat submissions. Initial dashboard polling can exhaust
the existing four-request proxy bound and return429; a manual **Refresh chats**
recovers the read after that burst. The v4 harness stopped on that initial refusal;
the v5 journey used the existing refresh control. This bounded-busy behavior is
retained, not represented as every concurrent read succeeding. Earlier diagnostic
harnesses did not record non-JSON/unfinished error bodies; later instrumentation
retains the429 witness. No admission cap was widened.

A subsequent controlled cold workspace restart ran model discovery and saved
history concurrently: both returned200/available in33.10s and33.34s, beyond the
old20s limit and within the new bound. The original history ID was present.
Federation and gateway PIDs did not change; `cold-read-results.json` retains the
actual responses. Native transcript hashes remained identical in all three
organizations, with38provider responses total. Final source checks are520HUD tests, including new
method/deadline-composition regressions, and22cloud/retirement tests. Private
`history-recovery/` retains baselines, exact changes, timing, resource checks and
no-repeat evidence. GAIT05686d98 explicitly reopened the earlier provisional
closeout before this correction.

### Retention, exported evidence and exact cleanup

The owner-approved setup is retained within its fixed48h window. Current private
export contains verified cloud A/B/local C home archives:283/248/234files, with
consistent SQLite backups and hashes, plus current cloud inventory and evidence.
Snapshot manifest SHA256:
`484684af71ce8625ddba84e3ed987f318e4a647bc9cb0e107c90dc1088f0ddf3`.
This snapshot was deliberately taken while services remained available; a new
quiescent export is mandatory before scheduled deletion.

Fresh current-state teardown plan has exactly34managed deletions, no foreign
resource/update/import, SHA256
`4f03feb371bcc3df640adf0c8f6d0a5b3177d891be07a0faddd540c575a588c0`.
The one-use private controller seals source/plan/state/helper/ownership inputs,
refuses early or missed execution, exports first, and never retries an unknown
claim. `labs/cloud/gcp/r06/retire.py` has meaningful scope/time/export/no-replay
regressions. Actual snapshot/export verification, saved-plan check and launchd
registration passed. Initial export attempts retained an identity-list tuple/JSON
comparison error and an oversized immutable staging archive timeout; the final
export includes authoritative homes/configuration and separately preserved public
artifact closures, rather than re-copying installation staging packages.

`com.netclaw.r06-retire-48h` is installed, loaded and not running at handoff:

- **Nov8 15:09:35Z (10:09:35 Toronto):** stop owned runtime processes and export.
- **Nov8 15:14:35Z:** apply the exact saved teardown, remove only the two owned DNS
  records and temporary OS Login key, inspect actual residues and preservation.
- **Nov8 15:19:35Z:** independent GCE STOP and host-network expiry fallback.

Current intentional retained inventory is2VMs,2boot disks,2static IPs,2VPCs,
2subnets,20firewalls,2service accounts and2secrets, with secret IAM in the34-resource
state. No owned snapshot/image/forwarding-rule residue was observed. Future
retirement is **scheduled, not already executed**; no zero-billable-residue claim
is made for this retained setup. Mac cleanup needs the Mac awake/online; missed or
unknown outcomes retain receipts and require reconciliation. VM STOP alone can
leave disk/IP charges. R05's Nov7 19:36:25Z/19:41:25Z jobs and original Border's
December1 lifetime are unchanged. Rescue disk removal was separately verified.

### Final source coherence and qualification limits

Full federation/native gateway/cloud baseline:1758passes/5existing skips.
Final cloud/retirement suite:22passes. Full HUD520passes; final editor206passes/
3existing skips; Flutter499passes and analyzer clean. Existing TypeScript,
production HUD/editor builds and Hermes compatibility24passes/6existing skips
remain recorded above. Catalog generation parity,112components/239skills,
126registered servers/52external integrations, and77Comms entries pass. No new
MCP server, skill/catalog count, public cloud installer surface or version is added.

FR001–004 map to actual identity/host/triangle receipts; FR005–010 to matrix,
refusals, preserved counters, native agent policy and original-loss recovery;
FR011–012 to the three actual clients; FR013–014 to correlated ledgers/GAIT,
source pins and finite retained lifecycle; FR015–016 to compatibility/coherence
and full SDD. SC001/002 are the six-direction matrix, SC003 the refusal/effect
records, SC004 actual clients, SC005 original-result recovery, SC006 preserved
owner resources and honest bounded closure. All required evidence is retained;
fixtures remain labeled separately from actual provider/cloud/native execution.

Source1.18.6, extension1.6.1 and Mobile1.0.4+7 remain unchanged. This scope does not
qualify live cloud Hermes, other providers/platforms, physical Mobile hardware,
production multi-user identities/SSO/RBAC or HA. No commit/push/merge, release,
publication, external announcement or R07 work is part of this closure.

Final GAIT qualified closeout: `b6d4926a`. The final read-only health snapshot
confirms all six directed channels up, no in-flight tasks, and unchanged native
transcript hashes. Cleanup validation and loaded launchd registration were
rechecked after the history correction; no cleanup was executed at handoff.

## Accepted source integration

The owner accepted this35/35handoff and authorized commit, PR, merge, completed
branch deletion and return to main on2026-11-06. The earlier no-source-integration
statement describes technical closure before that instruction. Publication and
R07 execution remain held. See source-integration.md for the tracked candidate,
CI outcomes and release boundary. The new cloud-r06 test family is registered
in tests/contract-suites.json as part of T033 source coherence.

The first source-integration CI run exposed an installed-clone assumption in the
R06 offline test helper (7failures,1734passes,5existing skips). Tests now include
the exact hash-verified upstream subnet source/license fixture and apply the same
installer migration in a private temporary tree. Focused10tests pass without
network/installed clones or skipped acceptance. See source-integration.md for
clean-checkout and final CI evidence; deployed source/identity/effects are unchanged.

The exact fixture correction passed the full clean-checkout federation suite:
1741passed,5existing skips,94existing warnings in101.55s. No installed subnet
checkout was present. The final PR head retains all seven originally failing
cases; none is skipped or replaced with a fake calculator.
