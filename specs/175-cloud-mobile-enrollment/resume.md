# R04b handoff — complete and accepted; stop before R05

Spec175 is complete at **30/30 tasks**. All four QR/enrollment paths, native
refusals, a successful protected data read and cold/background recovery passed.
Reviewed cleanup is complete. On November 5, the owner accepted the completed
scope and instructed packaging, commit/PR/merge/publication and a website draft.
The explicit full stop before R05 remains: do not start R05 or another spec.

Approved release targets are source **1.18.6**, extension **1.6.1** and Mobile
**1.0.4+7**. Packaging and publication outcomes are tracked separately in
[release-verification.md](release-verification.md). This handoff does not claim
those targets are published or that the release artifacts were redeployed to the
pilot. General cloud rollout, user identities, SSO and RBAC remain outside this
qualification.

## Delivered and observed

Actual local HUD, cloud HUD, local VS Code Mobile and cloud VS Code Mobile each
generated a QR consumed by the owned iPhone 17 Pro simulator. Production
`EnrollmentGate` reached `HomeShell` locally and `ProtectedDeviceScreen` for the
cloud. Each enrollment reconnected with the same retained key. Issuing interfaces
displayed consumed status and cleared the QR. Retained enrollment storage contains
no token.

Actual native refusal checks rejected a consumed/expired QR, a wrong domain before
connecting, wrong installation/key fingerprint and unauthorized methods, while
preserving successful enrollment. Source tests separately cover expiry, replay,
concurrent claims, uncertain replies and cross-device references.

The retained pilot serves trusted WSS `/mobile/ws` through the exact route to
loopback 13007. Existing authority, keys, historical results, confinement and
workspace services are preserved. Its original December 1 lifetime remains.
[deployment.md](deployment.md) records the reviewed change and read-only settlement
of its startup-timestamp postcondition failure. Never repeat that spent apply.

The earlier private VSIX is installed in normal VS Code. All 64 runtime/resource
files matched the reviewed package; settings, five NetClaw state databases, five
state files and 17 other extensions were preserved. That installed artifact passed
actual Overview/Mobile checks in an owned editor using a clone of the existing
profile. The original editor/terminal stayed untouched because macOS accessibility
control was unavailable. No normal-window activation is claimed. The test editors
have been retired; the new authorized release targets are tracked separately.

## Successful read and recovery

The first approved operation, `c36dc48c-a9c1-4fc9-b5a3-8b16029af8cb`, returned
HTTP403 with the earlier demo credential. Its signed verified failure, durable ACK,
one attempt and original `cloud-hud` reference remain preserved. Independent
collectors verified one provider call, one inference, one native MCP call and one
HTTP403, with no effects added by cold/background recovery. Preserve that failed
reference and its evidence; do not clear it for reuse. This remains failure
evidence; the precise 403 cause was not established by the bounded receipt.

After the owner supplied a fresh credential, root validated and refreshed only the
exact private broker credential and confirmed its native v2 authentication adapter.
The already enrolled `cloud-vscode` profile prepared the separate operation
`9902abf3-5a4f-46a6-9db1-ca613970551b`. Root independently reviewed its immutable
member/Border/device bindings, NetBox prefix 1 five-field read and Sonnet 4.6 limits
before authorizing one native approval (GAIT f77f9b36). No new QR or enrollment was
needed, and the failed reference was not cleared or reused.

The new operation completed successfully in one attempt. The actual NetBox MCP
returned `10.112.0.0/15`, status `container`, no VRF, and last-updated timestamp
`2020-12-30T20:00:17.126000Z`. The phone displayed the verified signed result and
durable ACK with no delivery pending. Independent member/Border collectors
verified exactly 2 provider dispatches, 2 inference calls, 1 native MCP call and 1
HTTP200. The three historical operation rows were unchanged.

One final cold launch and actual Home/background/resume sequence recovered the
same completed operation, key, result digest and ACK. PID 73667 stayed unchanged
across Home and foreground. Flutter recorded actual paused/resumed events; both
the native framework and isolated XCTest passed. Nine actual simulator screenshots
showed the recovered successful result. Recovery made zero enrollment, prepare,
decision or reconcile requests, and independent collectors confirmed unchanged
effect counts. All four retained enrollment files remained byte-identical.

## Entry points, cleanup and evidence

In the HUD, open **Mobile → Generate QR code**. In VS Code, select
**GCP Border · Montréal → Mobile & edge → Generate QR code**. Scan it in the
existing Mobile registration screen. No host, installation ID or user ticket
needs to be typed. A protected enrollment opens reviewed read-only operations;
legacy Chat, voice, capture, watch and background tasks are unavailable on that
connection.

Reviewed cleanup verified a 411-file export and removed only the new 3 stopped
containers and 1 empty internal network. The original 101-container/50-network
inventory, all four operation rows and all original evidence files were preserved.
The owned simulator is shut down with keys/profiles retained. Disposable local
services and owned test editors are retired; the intended pilot/member and
installed private extension remain. No new cloud resource was created.

Private receipts and screenshots remain under
`~/.local/share/netclaw/roadmap-r04b-20261104/`; successful-read completion is in
its `success-verification-20261105/` directory. The successful and failed operation
records are separate. These files are evidence, not activation or replay payloads.
Do not rerun spent deployment, cleanup or operation claims.
[verification.md](verification.md) records exact receipts, hashes, retained harness
failures and resource counts. GAIT c25645d0 records successful completion, cleanup
and the owner's scoped acceptance/publication instruction, closing T030.

## Qualification limits

Qualification uses macOS, VS Code 1.145.0, Flutter 3.44.8/Dart 3.12.2, Xcode 27.2 and
an iOS 26.5 simulator. The test-only native CPU image decoder and Keychain P256
identity exercise production enrollment/protocol/UI. Physical camera,
SecureEnclave, other mobile platforms and general deployment remain unqualified.
The prior R04a evidence retains its original source and scope. The release work
and website draft do not start R05 or promote general cloud deployment.
