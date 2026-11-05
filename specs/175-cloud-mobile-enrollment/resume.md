# R04b handoff — native enrollment complete; data-read acceptance open

The owner requested completion of R04b followed by a full stop before R05. Do not
start R05 or another spec, publish this work, or replay any spent deployment or
operation claim. Source1.18.5, extension1.6.0 and Mobile1.0.3+6 are unchanged.

## Delivered and observed

All four requested paths passed in actual applications: local HUD, cloud HUD,
local VS Code Mobile and cloud VS Code Mobile each generated an actual QR consumed
by the owned iPhone17 Pro simulator. The native production enrollment gate reached
HomeShell locally and ProtectedDeviceScreen for the cloud. Each enrollment
reconnected with the same retained key. Issuing interfaces displayed consumed
status and cleared the QR. Tokens are absent from retained enrollment storage.

Actual native refusal checks rejected a consumed/expired QR, a wrong domain before
connecting, wrong installation/key fingerprint and unauthorized methods, while
preserving successful enrollment. Source tests separately cover expiry, replay,
concurrent claims, uncertain replies and cross-device references.

The retained cloud pilot now serves the exact trusted WSS `/mobile/ws` route to
loopback13007. Existing authority, keys, historical results, confinement and
workspace services are preserved. Its original December1 lifetime remains.
See [deployment.md](deployment.md) for the reviewed change and read-only settlement
of its startup-timestamp postcondition failure. Never repeat that apply.

The reviewed private VSIX is installed in normal VS Code. All64 runtime/resource
files match the package; settings, five NetClaw state databases, five state files
and17 other extensions were preserved. The exact installed artifact passed actual
Overview/Mobile checks in an owned editor with a clone of the existing profile.
The original editor/terminal stayed untouched because macOS accessibility control
was unavailable. No permission settings were changed or normal-window activation
claimed. Test editors have been retired.

To generate a code in the HUD, open **Mobile → Generate QR code**. In VS Code,
select **GCP Border · Montréal → Mobile & edge → Generate QR code**. Scan it in
the existing Mobile registration screen. No host, installation ID or user ticket
needs to be typed. The installed private build is for this owner pilot; it has not
been published to Marketplace.

## Remaining acceptance

The one reviewed native operation, `c36dc48c-a9c1-4fc9-b5a3-8b16029af8cb`, was
approved once for the existing member's NetBox prefix1 read. The actual request
returned HTTP403. The phone correctly displayed its signed verified failure and
durable acknowledgment. Independent member/Border collectors verify one provider
call, one inference, one native MCP call, one HTTP403 and unchanged prior history.
This is failure-delivery evidence, not a successful data read.

The broker credential still matches the owner's November4 staged token. The
[public demo](https://demo.netbox.dev/login/) resets nightly at04:00UTC; token invalidation fits the timing but the
bounded response receipt does not establish the precise403 cause. No current
published read-only credential was found. The owner was asked for a current token
in a private local file. Do not create or widen an external token under this
read-only workload scope.

Cold-start and real Home/background/resume recovery passed against the same failed
reference, with identical operation/key/result and unchanged effects. Final native
framework and XCTest receipts pass; earlier harness failures remain excluded. The
failed attempt’s3 stopped containers and1 internal network were removed after
verified export, preserving the101-container/50-network baseline and all original
evidence. Local test services/editors were retired and the owned simulator shut
down with keys/profiles retained. A valid credential would allow
one separately reviewed new read using the already enrolled `cloud-vscode` device
profile, leaving the failed `cloud-hud` reference unchanged. Do not clear the
failed reference to reuse it. Use a separate evidence directory and selected-operation record; do not overwrite
`operation-verification/selected.json` or its failed-operation receipts. Capture a
fresh baseline that includes all three historical operations, refresh only the
exact private broker credential, review the new immutable operation, approve once,
verify success/signatures/ACK, then compare recovery effects and clean its owned
resources. Historical authorities and old credential evidence remain preserved.

## Evidence and limits

Private receipts, screenshots, authority snapshots, exports and tooling are under
`~/.local/share/netclaw/roadmap-r04b-20261104/`. They are evidence, not activation
payloads. [verification.md](verification.md) distinguishes actual observations,
source tests and retained failed attempts. The disposable local services were
stopped after consistent authority export; the intended cloud pilot/member remain
running. The final cleanup inventory is recorded there.

Qualification uses macOS, VS Code1.145.0, Flutter3.44.8/Dart3.12.2, installed
Xcode27.2 and an iOS26.5 simulator. The test-only native CPU image decoder and
Keychain P256 identity exercise the production protocol and UI. Physical camera,
SecureEnclave, other mobile platforms and general deployment remain unqualified.
Human acceptance is separate from technical completion and does not authorize
R05; the explicit full stop remains in force.
