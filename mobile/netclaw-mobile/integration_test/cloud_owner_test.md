# Private native R04a qualification

This test uses the production `CloudOwnerScreen({CloudOwnerStore? store,
OwnerTransport? transport, CloudOwnerClient? initialClient})` and
`CloudOwnerClient(CloudProfile(origin, installationId))`. A separately identified
native harness can depend on `netclaw_mobile` by local path and copy/import this
test. Do not replace the owner's installed app or reuse its app groups.

Run `flutter drive --driver=test_driver/cloud_owner_driver.dart
--target=integration_test/cloud_owner_test.dart -d <selected-device>` with
`NETCLAW_NATIVE_REPORT` set to a fresh absolute report filename in an existing
0700 host directory. Copy the source driver into the isolated native harness's
`test_driver/` directory. The driver exports `binding.reportData` to a 0600 JSON
file through Flutter's test protocol before app teardown, without printing it.
Do not use `flutter test` and rely solely on later Documents extraction: the
actual first iOS simulator prepare passed, but Flutter uninstalled the app at
completion before Documents evidence could be exported. That original prepared
operation must be recovered from authoritative state, never prepared again.

Launch the integration test, then inject `Documents/r04a-qualification.json` into
that app's private data container within five minutes. The test reads at most
64 KiB and deletes the file before any network call. Never supply tickets through
source, `--dart-define`, build assets, logs or a public HTTP fixture. Keep the host
copy and exported evidence private. Bootstrap tickets are single-use; a timeout
never authorizes resending an operation.

First phase config: `phase: "prepare"`, exact `origin`, `installation_id`, fresh
`ticket` if needed, `member_id`, `model_profile_id`, `tool`, and exact `arguments`.
The native UI selects precisely that catalog entry and prepares without approval.
Export `Documents/r04a-evidence-prepare.json`; inspect its complete immutable review
(principal, Border/member identities, provider/model, arguments, limits and expiry).

Only after explicit host-side retirement and new-preparation delegation, prepare
configuration may include `discard_resolved_operation_id` for that exact earlier
operation. If its reference remains on the device, the harness requires the same
ID, `state: refused` with `error_code: owner_denied` (the actual backend denial
spelling), no approval/result, zero attempts, no possible execution and
no reconciliation, then taps the existing native **Remove resolved reference**
button. The exported report records the removed ID. Any unknown state or ID
mismatch fails before preparation. If uninstall already removed the reference,
the host's authoritative denial evidence remains required; the harness does not
claim that it observed or discarded a missing reference.

Second phase config: `phase: "approve"`, same origin/installation,
`operation_id`, `approved_review_digest`, and complete `approved_review` copied
from that inspected evidence. Include a fresh ticket only if sign-in expired.
The test requires exact equality, then taps the native confirmation checkbox and
Approve once. It reads status without replay and exports
`r04a-evidence-approve.json` with the verified result/durable ACK. Never rerun this
phase after an ambiguous decision; use recovery.

Terminate/relaunch the isolated app and run phase `"recover"` with the same
operation/review fields. Existing secure session/reference storage must recover
the original work through GETs only. Export `r04a-evidence-recover.json`; correlate
operation/result/ACK and effect counts with authoritative private Border/member
records. Native test files contain private review/results by design and are not
ordinary application persistence. Export, then retire the qualification app and
its private data after evidence review.

Record SDK, iOS/Android version, bundle identifier and physical device versus
simulator separately. Running this isolated native harness does not establish
the full production multi-bundle/watch package, biometric, camera, Siri or push
qualification. No store upload or app release is implied.
