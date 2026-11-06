# R04b private native QR qualification

Use a **separate simulator bundle** with a path dependency on this Mobile package,
not the owner's installed application or key namespace. Import/copy
`mobile_qr_test.dart` and `test_driver/mobile_qr_driver.dart`. The harness registers
`integration_test/native/R04bSimulatorPlugin.swift` and compiles the unchanged
production `ios/Runner/X509SelfSigned.swift`. Do not register the qualification
plugin in production.

The harness uses Apple's Core Image CPU QR detector on the **actual generated
HUD/VS Code QR PNG**, then passes its barcode result through production
`EnrollmentScreen`'s scanner callback, enrollment flow, device client and durable
store. This is actual image decoding and native UI/protocol execution. It does
not qualify physical camera capture. Installed mobile_scanner7.4.0 explicitly
refuses image analysis on iOS Simulator; its camera path is unchanged.
Apple documents the detector's still-image QR semantics at
https://developer.apple.com/documentation/coreimage/cidetectortypeqrcode.

The qualification plugin uses simulator Keychain P256 keys and the same
production certificate/SPKI/signature format. It exposes no private-key export.
Production iOS keeps Secure Enclave keys; physical hardware protection is not
inferred from simulator evidence. Public fingerprint is SHA256(SPKI DER).

Run `flutter drive --keep-app-running` with the checked-in driver and
`NETCLAW_NATIVE_REPORT` naming a fresh file in a private0700 host directory.
After the app starts, copy the actual PNG into its Documents directory and
atomically place `Documents/r04b-qualification.json`. The harness reads/deletes
this private configuration before networking. Never pass token data through
source, dart-defines, logs or build assets. Export reports before cleanup.

Common configuration: `phase`, `profile` (bounded lowercase scenario name),
`installation_id`. Enrollment adds `member_id` and `image_file` (PNG basename).
Use distinct profiles/member IDs for local HUD/local editor/cloud HUD/cloud editor
so earlier enrollment records are retained. This directory separation is a
qualification harness facility; production has one active enrollment. The
simulator retains the same key across these enrollments; each server registration
and protected principal remains scoped to its installation and generation.

Phases:

- `enroll`: real native PNG decode and production enrollment UI, persisted key,
  protected catalog when supported, actual same-key reconnect. No operation prepare.
- `prepare`: retained device reconnect, exact `member_id`, `model_profile_id`,
  `tool` and `arguments` selection in the native UI, complete immutable review.
  The host must inspect the exported review before proceeding.
- `approve`: requires exact `operation_id`, `review_digest` and complete `review`
  matching host inspection. Native checkbox and Approve once; bounded explicit
  reconciliation of that same operation until signed result/durable ACK.
  Never repeat after an ambiguous outcome.
- `recover`: same exact operation/review after a real host-driven app restart;
  initialization/status only, no preparation, decision or reconciliation.

All phases also close/reconnect using the retained identity and compare the key.
Actual OS background/process events and backend effect counts need independently
correlated receipts. A widget lifecycle callback alone is not OS evidence.
Trusted WSS is mandatory. A local test CA may be trusted only in the owned simulator;
never disable certificate verification or change host/production trust. Local
legacy and cloud protected behavior retain distinct evidence.

R06 adds `external-ask` and `external-recover` for an independently enrolled
ordinary cloud Border. Use a fresh R06 simulator bundle, the same PNG decoder and
production enrollment flow, then keep that profile and key. `external-ask` requires
an exact bounded `prompt` and `expected_peer`; it taps the production Chat Send
button once and exports `external_turn` only after completion, server-derived
source attribution and the visible External sources section. An existing identical
prompt or an uncertain result refuses; inspect and recover the original request.

After a real host-driven app termination/relaunch, `external-recover` requires
`expected_turn` copied from the private first report and the same `expected_peer`.
It checks the retained request/task IDs, answer and attribution, and fetches only
the original task result. It never submits again. Correlate both reports with the
Border's original task and outbound/provider records; simulator image decoding and
Keychain use retain the physical camera/Secure Enclave qualification limits above.

The separate harness must also bundle the production `assets/illustrations/`
and `assets/icon/` directories under the same asset names. Ordinary Home renders
these before Chat. Resolve the owned simulator's native notification permission
prompt before waiting for Home navigation; do not suppress a production permission
dialog in application code. If a display assertion fails after completion, export
the existing private conversation record and use it as `expected_turn` for recovery.
Never send the original prompt a second time to repair a test harness failure.
