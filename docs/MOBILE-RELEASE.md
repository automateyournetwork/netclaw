# Mobile release workflow

## Current release — November 5, 2026

Mobile **1.0.4 (7)** is the scoped HUD/VS Code QR enrollment update. The signed
production archive passed all 484 Flutter tests, analysis, five-bundle version and
distribution-signature checks, Apple validation and upload. App Store Connect
processed the exact build as VALID and APP_STORE_ELIGIBLE.

The [public App Store page](https://apps.apple.com/us/app/netclaw/id6800859524)
currently distributes **1.0.2**. Upload, review submission and public availability are
separate states; the [Spec175 release record](../specs/175-cloud-mobile-enrollment/release-verification.md)
records the exact artifact/source hashes. Version **1.0.4 (7)** was submitted
on November 5 and is **WAITING_FOR_REVIEW**, with automatic release after Apple
approval. It is not publicly available yet.

Native simulator acceptance covers actual generated QR images, enrollment,
signed-read results and no-repeat recovery. It does not establish physical
camera/Secure Enclave, Face ID, APNs or Watch-device qualification.

## Historical 1.0.2 upload record — September 2026

Spec 124 validated, signed and uploaded **1.0.2 (4)** to App Store Connect on
2026-09-26 with explicit maintainer authorization. Apple validation and delivery
succeeded without errors. Apple processing is VALID and internal TestFlight is IN_BETA_TESTING.
External TestFlight is READY_FOR_BETA_SUBMISSION. With explicit maintainer
authorization, version 1.0.2 was submitted for public App Review and is
**WAITING_FOR_REVIEW**, with **automatic release after approval**. No human
submission step is pending. At that checkpoint, Apple approval and public availability were not yet
confirmed; the November 5 API observation confirms 1.0.2 is now public. Install 1.0.2 (4) through TestFlight for the outstanding real-device
smoke below. See `specs/124-flagship-audit/evidence/mobile-review.json`.

Apple rejected an earlier 1.0.1 (4) validation because the 1.0.1 train was closed.
The final source and uploaded archive are 1.0.2 (4). Release artifacts are under
`mobile/netclaw-mobile/build/audit124-v102/`; signed packages and private Apple
credentials remain outside Git. See spec 124's `evidence/mobile-upload.json`.

The source version lives in `mobile/netclaw-mobile/pubspec.yaml`. Flutter generates
`FLUTTER_BUILD_NAME` and `FLUTTER_BUILD_NUMBER`; Runner, WatchApp, WatchComplication,
LiveActivityWidget and NetClawWidgetExtension now share those values. Keep all
bundle identifiers and entitlements intact when incrementing a release.

Run the checks serially from `mobile/netclaw-mobile`:

```sh
flutter test
flutter analyze
flutter build ios --release --no-codesign
```

From the repository root, check the actual built bundles and prepare the archive:

```sh
python3 scripts/check-mobile-bundle.py mobile/netclaw-mobile/build/ios/iphoneos/Runner.app
bash scripts/mobile-release-archive.sh
```

The archive script uses the Runner workspace, automatic signing and the root
mobile `ExportOptions.plist` with the `app-store-connect` export method. It rejects
missing/mismatched version metadata or duplicate app/extension identifiers before
export. It does **not** upload or submit. Set `NETCLAW_ARCHIVE_PATH` and
`NETCLAW_EXPORT_PATH` to keep a validation archive separate from release artifacts.

Local prerequisites are Xcode, the intended Apple Developer team, distribution
signing credentials, and profiles covering the iPhone/watch/extensions and their
App Groups, push, Siri and other declared capabilities. Xcode can refresh profiles
with its connected account. Team ID alone does not establish a paid membership
or upload permission. Firebase configuration/APNs credentials remain private,
per-deployment files; never commit them.

Before upload, verify App Store Connect access, select an unused build number,
review the app's privacy disclosures and release notes, and smoke-test enrollment,
reconnect, chat, approval, notifications and watch relay on real devices. The Mac
tests and signed export do not substitute for those device/provider checks.
Upload through the authenticated Apple workflow only when a release is requested;
TestFlight distribution and public review/submission are separate actions.

Previous rollout notes and drafts remain available in `docs/APP-REVIEW-NOTES-DRAFT.md`,
`docs/APP-STORE-LISTING-DRAFT.md` and the mobile `SIDELOAD.md`. Their historical
account/listing claims are not authoritative evidence of today's App Store state.
