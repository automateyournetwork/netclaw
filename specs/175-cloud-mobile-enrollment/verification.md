# R04b verification — in progress

Implementation is integrated at9aa2b673. Actual native acceptance is in progress; source tests do not close the remaining end-to-end checks.

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
A full authority/state snapshot remains required immediately before deployment.

Installed Xcode27.2, Flutter3.44.8/Dart3.12.2 and iOS26.5 iPhone17 Pro simulator
are available. Simulator optical camera/mobile_scanner analyzeImage and physical
SecureEnclave are unavailable: separate test-only native decoder/key harness is
planned, with production enrollment UI and protocol shared.

## Acceptance matrix

| Surface/behavior | Local | Cloud |
|---|---|---|
| HUD visible QR generation | Pass: actual browser button and canvas | Pass: actual browser button and canvas |
| Native VS Code Mobile QR generation | Pass: native Code Mobile view | Pass: native Code Mobile view |
| Native simulator actual QR decode/enroll | Pass: both generated images | Pass: both generated images |
| Same-key reconnect/uncertain enrollment | Same-key reconnect pass; uncertainty source tests | Same-key reconnect pass; uncertainty source tests |
| Protected exact review/result/ACK | Scoped fixture pending | Actual read pending |
| Background/process recovery/no effects | Pending | Pending |

Physical iPhone/camera/SecureEnclave and other platforms are unqualified. Existing
R04a evidence retains its original source and scope; it does not qualify R04b.

## Integrated source and first native path

Backend667broader Python tests pass, plus16final native tests;31integrated Node24.19 backend/HUD tests pass. Surfaces31HUD and13extension tests, TypeScript check, extension and169module HUD build pass. Mobile74focused tests and analysis pass; isolated native iOS harness built successfully. Root integrated source commits and built the same169module HUD. Initial root build command used unsupported Vite--root and failed before build; corrected working-directory invocation passed.

Fresh local fixture uses actual FederationService, daemon.handle_http and _start_edge with dedicated localhost TLS credentials trusted only in the owned iOS26.5 simulator. BGP/provider workloads are not started by this fixture. API13305 and native production Vite preview13306 are distinct. The first browser attempt mistakenly targeted APIroot (404), issued no offer, then used actual preview13306.

Actual local HUD button issued one offer on2026-11-04T23:56:43Z. Native simulator decoded actual canvas PNG, connected trustedWSS and server registered memberrisk/r04b-local-hud-20261104 once at23:57:10Z. HUD GETpolling observed consumed, displayed exact member and cleared QR; exactly1POST. Native retained-key/restart report remains pending. Private receipts: local-hud-issued.json/local-hud-after.json, local/border.log and native harness evidence. No cloud/member change or provider/device read has occurred yet.

### November 5 resumed acceptance

The retained `native-local-hud-recovered.json` receipt confirms a trusted WSS
hello using the same enrolled member and device-key fingerprint at
2026-11-05T00:00:21Z. It did not issue or consume a second enrollment token.
The first harness left the successful enrollment screen spinning because its
test callback did not mount the production application gate; production navigation
verification is being completed separately, with the original receipt preserved.

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

The reviewed retained-member update completed successfully on November5. The
same owned LaunchAgent reconnected authenticated and ready; historical operation
rows, model-call rows and826 preserved authority/evidence hashes are unchanged.
The apply made zero workload requests. Its durable claim is spent; never rerun it.
Private receipt: `deployment/member/result.json`. Cloud update is still pending.

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
post-change settlement is pending; the spent apply will not be rerun.

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
