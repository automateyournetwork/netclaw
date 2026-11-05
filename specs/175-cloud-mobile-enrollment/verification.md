# R04b verification — scoped acceptance complete

All 30 tasks are complete. All four actual QR/enrollment paths, native refusal
checks, a successful protected data read and cold/background recovery passed.
The owner accepted the completed stage on November 5 and authorized its scoped
packaging, commit/PR/merge/publication and a website draft. R05 remains stopped.

The successful read is a separately reviewed operation using a fresh owner-provided
credential; the earlier signed HTTP403 failure remains intact. Reviewed cleanup
restored the original resource inventory and preserved all four operation records.
Release targets are source 1.18.6, extension 1.6.1 and Mobile 1.0.4+7. Packaging and
publication outcomes are tracked separately in
[release-verification.md](release-verification.md); this record does not claim they
are published. General cloud rollout and broader platform qualification remain held.

## Startup and baseline

Clean main209cba6f matches fetched upstream; no open PR at kickoff. Spec175 and
three separate worktrees created. GAIT branch r04b-cloud-mobile-qr-20261104
explicitly checked out and verified. Startup default pyATS unavailable (HTTP
runtime missing); MemPalace unavailable (module missing). No device query or
runtime install was substituted. GAIT uses the existing local gait_mcp interpreter.

Actual read-only GCP IAP observation succeeded: retained protected federation,
HUD, normal workspace gateway/HUD and Caddy remain running; historical R01 apps
remain stopped. Current role/HUD/source-manifest/Caddy hashes and listener inventory
are private at ~/.local/share/netclaw/roadmap-r04b-20261104/cloud-readonly-baseline.json.
No configuration, enrollment, workload or cloud resource was changed by this probe.
The full authority/state snapshot was subsequently captured in the reviewed
deployment packet.

Installed Xcode 27.2, Flutter 3.44.8/Dart 3.12.2 and iOS 26.5 iPhone 17 Pro simulator
are available. Simulator optical camera/mobile_scanner analyzeImage and physical
SecureEnclave are unavailable. The qualification used a separate test-only native
decoder/key harness with the production enrollment UI and protocol shared.

## Acceptance matrix

| Surface/behavior | Local | Cloud |
|---|---|---|
| HUD visible QR generation | Pass: actual browser button and canvas | Pass: actual browser button and canvas |
| Native VS Code Mobile QR generation | Pass: native Code Mobile view | Pass: native Code Mobile view |
| Native simulator actual QR decode/enroll | Pass: both generated images | Pass: both generated images |
| Same-key reconnect/uncertain enrollment | Same-key reconnect pass; uncertainty source tests | Same-key reconnect pass; uncertainty source tests |
| Protected exact review/result/ACK | Source fixtures pass | Actual successful prefix 1 read, signed result and durable ACK; earlier403 failure retained |
| Background/process recovery/no effects | Same-key cold reconnect pass | Actual cold launch and Home/resume pass for failed and successful references; unchanged effects |

Physical iPhone/camera/SecureEnclave and other platforms are unqualified. Existing
R04a evidence retains its original source and scope; it does not qualify R04b.

## Integrated source and first native path

Backend667broader Python tests pass, plus16final native tests;31integrated Node24.19 backend/HUD tests pass. Surfaces31HUD and 13extension tests, TypeScript check, extension and 169module HUD build pass. Mobile74focused tests and analysis pass; isolated native iOS harness built successfully. Root integrated source commits and built the same169module HUD. Initial root build command used unsupported Vite--root and failed before build; corrected working-directory invocation passed.

Fresh local fixture uses actual FederationService, daemon.handle_http and _start_edge with dedicated localhost TLS credentials trusted only in the owned iOS 26.5 simulator. BGP/provider workloads are not started by this fixture. API13305 and native production Vite preview13306 are distinct. The first browser attempt mistakenly targeted APIroot (404), issued no offer, then used actual preview13306.

Actual local HUD button issued one offer on2026-11-04T23:56:43Z. Native simulator decoded actual canvas PNG, connected trustedWSS and server registered memberrisk/r04b-local-hud-20261104 once at23:57:10Z. HUD GETpolling observed consumed, displayed exact member and cleared QR; exactly1POST. Retained-key/restart proof was completed in the resumed acceptance below. Private receipts: local-hud-issued.json/local-hud-after.json, local/border.log and native harness evidence. At that checkpoint, no cloud/member change or provider/device read had occurred.

### November 5 resumed acceptance

The retained `native-local-hud-recovered.json` receipt confirms a trusted WSS
hello using the same enrolled member and device-key fingerprint at
2026-11-05T00:00:21Z. It did not issue or consume a second enrollment token.
The first harness left the successful enrollment screen spinning because its
test callback did not mount the production application gate; production navigation
verification was completed separately below, with the original receipt preserved.

After the host session interruption, the disposable local services were stopped.
Their recorded process identifiers were not reused. The same local home and SQLite
authority were resumed on the original loopback ports, with new private process
receipts and logs. The installation-bound enrollment-info read returned available;
the first unbound diagnostic read correctly returned `installation_changed`.
The original local enrollment remains intact. The owner requested completion of
this stage followed by a full stop before R05; no next-stage work is authorized.

The resumed native local-HUD recovery now also traverses the production
`EnrollmentGate` into `HomeShell`, retaining the original member/key and using
hello only. Receipt: `native-local-hud-production-gate.json` at
2026-11-05T12:34:42Z. Sixteen focused Mobile onboarding/protected/heartbeat tests
passed after the harness navigation correction.

Host restart also left the retained member supervisor waiting for Docker. The
read-only deployment check refused stale daemon receipts, and no update claim was
created. Docker Desktop was started to let the existing owned LaunchAgent recover
its retained service before fresh preconditions; this is not a new enrollment or
workload approval.

Actual native VS Code 1.145.0 Mobile generation also passed: one observed Generate
click at12:36:19Z, actual canvas PNG decoded on the simulator, trusted WSS
registration at12:36:54Z, production Gate → HomeShell and same-key reconnect.
Native Check status then displayed Device enrolled and cleared the QR. The image
hash, issuer nonce and enrolled member are correlated in private
`surfaces/native-editor/local-vscode-acceptance.json`; transport POST count is not
separately claimed for the editor. The isolated test editor required a shorter
owned profile path after the installed Code version changed; the original profile
and failed pre-launch path remain preserved.

The reviewed retained-member update completed successfully on November 5. The
same owned LaunchAgent reconnected authenticated and ready; historical operation
rows, model-call rows and826 preserved authority/evidence hashes are unchanged.
The apply made zero workload requests. Its durable claim is spent; never rerun it.
Private receipt: `deployment/member/result.json`. Cloud qualification followed.

Native local refusal receipt `native-local-refusals.json` verifies the actual
previously consumed QR (also expired by this test) was refused with RPC -32021,
`enrollment_refused`, HTTP-style status400 and matching `not_enrolled` admission
proof. Only the probe's pending state was cleared. A QR payload mutation changing
only the host was rejected before any dial. The successful enrollment bytes stayed
unchanged. This does not independently distinguish expiry from spent-token refusal;
isolated source tests cover each condition.

The cloud stage and preflight passed. The one-use apply installed the candidate,
started owner federation/HUD and restarted the exact Caddy service, then stopped
at its final strict risk-row comparison. Read-only inspection found only
`risk.updated_at` changed during startup; all other risk fields and both historical
operation rows match. Services are running and public trusted HTTPS enrollment
info returns200 for the same installation and `/mobile/ws`. Independent full
post-change settlement followed below; the spent apply was not rerun.

Independent cloud settlement passed at12:45:00Z. It verified13 preserved authority
and key files; both historical operation rows and existing member authority;
all1,006 source files,26 HUD assets and9 installed replacements; preserved old
source/bytecode/dist and consistent database backup; unchanged nftables and
workspace/gateway/egress service identities; loopback-only13007; and actual trusted
HTTPS enrollment readiness. Only the three intended service PIDs changed.
`risk.updated_at` alone changed from2026-11-04T17:08:34Z to
2026-11-05T12:42:59Z. The original failed postcondition remains in evidence;
`deployment/cloud-settlement.json` is the successful read-only settlement, with
zero workload requests and no repeated apply.

Actual cloud HUD generation passed: one observed Generate click and one HTTP POST,
actual canvas image decoded by the native simulator, one device registration at
12:45:50Z over trusted WSS443/mobile/ws, production Gate → ProtectedDeviceScreen,
authenticated catalog and same-key hello reconnect. The HUD polled consumed and
cleared the QR. No operation was prepared or approved in this enrollment test.
Private receipts: `cloud-hud-issued.json`, `cloud-hud-after.json`,
`native-cloud-hud.json` and correlated logs.

Actual cloud VS Code generation passed at12:47:19Z, with native enrollment at
12:47:26Z. Its actual canvas PNG hash matches the native decode receipt. The app
reached ProtectedDeviceScreen and authenticated catalog, then reconnected with the
same key. Native VS Code Check status displayed Device enrolled and cleared the QR.
This completes all four positive local/cloud × HUD/editor paths. Receipt:
`surfaces/native-editor/cloud-vscode-acceptance.json` and `native-cloud-vscode.json`.

Native cloud binding/scope probes passed: wrong installation and wrong declared
key fingerprint each returned -32023; unavailable revoke and an unknown method
returned -32601. The successful enrollment file remained byte-identical and valid
same-key hello recovered afterward. No operation request was made. Receipt:
`native-cloud-binding-refusals.json`. Earlier local HomeShell startup left an iOS
notification permission alert on the shared qualification simulator; the Flutter
integration assertions passed beneath it. The alert was dismissed before the
visible screen qualification below; the original alert screenshot is retained and
is not counted as a visible protected-screen result.

Private extension package was built from clean committed source `fba7f6fe` using
qualified Node24.19. Root independently verified its SHA256
`c6dfb221109f2079e5f028cff408b997b46db924c283605dc506028089b0b208` and all 64
packaged runtime/resource files against the source build, including Mobile. The
existing installed1.5.0 archive is preserved. Normal installation and profile
preservation subsequently passed: all 64 packaged files matched, with settings,
five NetClaw state databases, five state files and 17 other extensions preserved.
The installed artifact passed actual Overview/Mobile checks in an owned editor
using a clone of the existing profile. The original editor/terminal stayed
untouched because macOS accessibility control was unavailable; normal-window
activation is not claimed. This private package was not Marketplace publication.
The later scoped release authorization is recorded separately below.

The native alert was dismissed through one isolated XCTest UI test, with the
original alert capture retained. Four actual simulator screenshots then showed
production Mobile operations and its complete immutable review with unchecked
confirmation/disabled approval. Root independently recomputed the review digest
and matched the frozen Border/member, device principal, exact prefix 1 read and
Sonnet 4.6 limits (GAIT6439693c).

Native approval was submitted once at12:56:26Z for operation
`c36dc48c-a9c1-4fc9-b5a3-8b16029af8cb`, revision1, review digest
`a6229e769f3bebeea70bd9355df3cbaf5509d8d60ec6e270e3550ccd1d999817`.
The actual NetBox read returned HTTP403. The phone displayed the signed verified
failure, one attempt and durable ACK, with delivery no longer pending. Receipt
`native-cloud-approved.json` and seven actual result screenshots retain this
failure. Result digest: `7a6aa420422dbe49f0d9f90d2a617e1cc2f28e8e77bcbc885aea09187dcb162e`.
This qualifies truthful failure delivery, not a successful data read. The
same-reference recovery below preserved it; the later successful operation was
separately reviewed and approved. The failed operation was never replayed or
silently replaced.

### Failed-operation recovery and initial retirement

Final native recovery passed the Flutter framework and isolated XCTest checks at
13:13:55Z. It cold-loaded the same retained enrollment/reference, then recorded
actual inactive → hidden → paused → hidden → inactive → resumed lifecycle events.
The process remained PID43198 across Home/background and foreground. Seven fresh
actual simulator screenshots show the retained failed result. Root compared the
entire operation and enrollment objects against the pre-recovery native receipt:
identical. `native-cloud-recovered-verified.json` explicitly records
`framework_passed:true`; `native-lifecycle-process-verified.json` binds the process.
Earlier XCTest accessibility/teardown and duplicate screenshot filename failures
are retained. A receipt emitted during a failed harness run was renamed
`native-cloud-recovered-harness-failed.json` and excluded. The driver now exports
success evidence only after the framework passes; no failed run is counted.

Independent member and Border recovered collectors passed. Approval/result/ACK,
GAIT references and actor, exact review, old2 operation rows and current effect
counts are unchanged:1 provider dispatch,1 inference, 1 native MCP call, 1 HTTP403.
No recovery preparation, decision or reconcile request was made by the final
native recovery flow. At this checkpoint the successful-data-read gate remained
open. The subsequent successful read closes that gate without relabeling this
failed result.

Root reviewed cleanup packet
`1f0116afcf4c535269d51adc308f678bd0d3a3904bf86cfc7f8a256c507303db`, exported409
operation files plus consistent database snapshots and correlated receipts, then
removed only the exact 3 newly owned stopped containers and 1 internal network.
Post-checks restored the original101 container IDs and50 network IDs, preserved
their states, all3 operation rows, guard credential and all409 original evidence
files. Private receipt: `operation-verification/failure-cleanup-result.json`.
The local fixture's3 processes and both owned test editors were retired. The
owned simulator was shut down with its keys/profiles retained for the then-pending
credential-dependent check; other simulator states were preserved. No cloud
resource was created, and no cloud teardown was needed. The intended pilot/member,
private installed extension, original editor and December 1 lifetime remain.

Retained non-running qualification data is deliberate: private evidence exports,
source/config backups, owned editor profiles, local fixture home and simulator
state. Cloud qualification device registration/operation records remain as audit
history. At that checkpoint no active QR or background workload remained, and
no publication, R05 or next-spec work had occurred.


## Successful read, recovery and final closure — November 5

The owner supplied a fresh NetBox credential and authorized completion of the
remaining read. Root validated and refreshed only the exact private broker
credential. Its native v2 authentication adapter was confirmed without a service
change. The credential value is absent from this record and the client evidence.
All three historical operations, including the403 failure above, were captured
before the new request. The original failed `cloud-hud` reference was retained;
the already enrolled `cloud-vscode` profile supplied the separate new reference.
No QR was issued and no device was reenrolled.

Actual native preparation produced operation
`9902abf3-5a4f-46a6-9db1-ca613970551b`, revision 1, with review digest
`850514e3e81c652e8268283010ea9c19576fbd28c3219e6cf9a41010c31f5b50`.
Four actual simulator screenshots showed the complete review and unchecked
confirmation. Root independently verified the frozen Border/member, the new
device principal, NetBox `ipam.prefix` object 1 with exactly
`id,prefix,status,vrf,last_updated`, and Sonnet 4.6 limits before authorizing one
native Approve once (GAIT f77f9b36).

The request completed successfully with one attempt. Actual native NetBox MCP
output was prefix `10.112.0.0/15`, status `container`, no VRF, and
`last_updated=2020-12-30T20:00:17.126000Z`. The phone displayed the completed state,
verified signed result, durable ACK and no pending ACK delivery. Result digest:
`732e85402231afa589adf5d14bac20254a4695f61efc411435d3740803eff6de`.
Independent member and Border collectors verified exactly 2 provider dispatches,
2 inference calls, 1 native MCP call and 1 HTTP200. All three historical operation
rows were unchanged. Nine actual simulator screenshots show the successful
result and its evidence. `native-approved.json` records `framework_passed:true`;
its completed/succeeded outcome is checked separately from framework success.

After completed baselines were captured, one final cold launch and real
Home/background/resume sequence recovered that same successful reference. The
native process remained PID 73667 across Home and foreground, and the framework
recorded inactive → hidden → paused → hidden → inactive → resumed. The retained
key, operation, one attempt, result digest, signatures and ACK remained identical.
The recovery emitted zero enrollment, prepare, decision or reconcile requests;
only authenticated hello/catalog/status reads occurred. Both the Flutter framework
and isolated XCTest passed on the first successful-read recovery sequence. Nine
fresh actual screenshots showed the recovered completed result. Independent
recovered collectors confirmed the same 2 provider/2 inference/1 MCP/1 HTTP counts
and unchanged historical rows. All four retained enrollment files remained
byte-identical, including the failed `cloud-hud` profile.

The fresh receipts are under private
`~/.local/share/netclaw/roadmap-r04b-20261104/success-verification-20261105/`:
`native-prepare.json`, `native-approved.json`, `completed.json`,
`border-completed.json`, `native-recovered.json`, `native-lifecycle-process.json`,
`native-final-summary.json`, `recovered.json` and `border-recovered.json`, with
correlated native logs, XCTest results and screenshots. No source change or new
platform qualification was introduced by this credential-dependent completion.
The earlier failed-operation receipts and harness diagnostics remain separate.

Root reviewed cleanup packet
`2bb608499f130b260e192d88f1915d0c898fdeeed58998cdddd5fd0d872f6405`, verified a 411-file
export, then removed only the exact 3 newly owned stopped containers and 1 empty
internal network. The original 101-container/50-network inventory was restored;
all four operation rows and their evidence files were unchanged. Receipt:
`success-verification-20261105/cleanup-completed.json`. The owned simulator was
shut down again with keys/profiles retained. The intended pilot/member, installed
private extension, original editor and December 1 lifetime remain preserved.
No new cloud resource or general cloud deployment was introduced.

The owner's November 5 instruction to package, commit/PR/merge and publish the
completed scoped work, plus prepare a website draft, is explicit stage acceptance
and closes T030. GAIT c25645d0 records the successful read, recovery, cleanup and
that authorization. T026 and all 30 tasks are complete. Release execution is
tracked in [release-verification.md](release-verification.md); this scoped
acceptance does not start R05, waive physical-device/platform limits, or qualify
users/SSO/RBAC and general cloud rollout. The owner's full stop before R05 remains.


Root release-preparation checks at `6a8a0a2f` additionally passed the full HUD
suite (499/499) and VS Code suite (194 passed,3 platform skips,0 failed). Those
skips remain qualification limits. These checks do not assert publication or
redeployment of the frozen live pilot evidence.
