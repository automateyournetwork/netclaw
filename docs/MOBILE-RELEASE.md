# NetClaw Mobile — Release Checklist

Everything needed to take `mobile/netclaw-mobile` from today's free/Personal-team
debug build to an App Store submission, once a paid Apple Developer Program
account exists. Written as part of spec [099-mobile-prerelease-sweep](../specs/099-mobile-prerelease-sweep/spec.md).

## What's already done (works today, no paid account needed)

- `ios/Runner/PrivacyInfo.xcprivacy` — privacy manifest.
- `ios/Runner/Info.plist` — usage-description strings, `ITSAppUsesNonExemptEncryption`,
  and `UIBackgroundModes` (`remote-notification`, pre-staged but inert until push is signed).
- `ExportOptions.plist` — export configuration template (placeholder `teamID`).
- `scripts/mobile-release-archive.sh` — the archive/export script this checklist ends with.

## Once the paid account is active

1. **Move code signing to the paid team.**
   Xcode → `Runner` target → Signing & Capabilities → Team → select the paid
   team. Repeat for the `WatchApp` target if it's still on the free team.

2. **Enable the Push Notifications capability.**
   Xcode → `Runner` target → Signing & Capabilities → `+ Capability` → Push
   Notifications. Xcode sets `CODE_SIGN_ENTITLEMENTS` in `project.pbxproj` to
   point at `ios/Runner/Runner.entitlements` automatically — **do not** set
   this by hand before this step; a free team build with that entitlement
   wired but unsigned fails to build at all (see `Runner.entitlements`'
   own comment and analyze finding I1 in spec 099's `research.md`).
   Background Modes → "Remote notifications" is already ticked (`Info.plist`
   was pre-staged by this checklist's step above) — nothing to do there.

3. **Drop in Firebase config.**
   Place `GoogleService-Info.plist` into `ios/Runner/` (gitignored, per-deployment,
   never committed). Upload an APNs auth key (`.p8`) to the Firebase project's
   Cloud Messaging settings.

3a. **Register the `WatchComplication` App Group.**
   Confirmed empirically (not just documented): a free/Personal team has **no
   Certificates/Identifiers/App Groups management UI at all** in the Apple
   Developer portal — that section only appears once Program enrollment is
   active. Once it is, go to Certificates, IDs & Profiles → Identifiers → App
   Groups → create `group.ca.automateyournetwork.netclaw.mobile`, then a real-device
   build of `WatchComplication` (Story 8's watch face complication) will
   provision correctly. Until then, real-device installs need `WatchComplication`
   temporarily detached from `WatchApp`'s embed phase (see `research.md` R13) —
   Simulator/CI builds are unaffected either way.

4. **Fill in `ExportOptions.plist`'s `teamID`.**
   Find it at [developer.apple.com/account](https://developer.apple.com/account)
   under Membership.

5. **Run the archive script.**
   ```sh
   ./scripts/mobile-release-archive.sh
   ```
   This refuses to run if `DEVELOPMENT_TEAM` is still the free/Personal team,
   or if `ExportOptions.plist`'s `teamID` is still the placeholder — both
   fail loudly with the exact next step, rather than producing a broken or
   non-distributable archive silently.

6. **Screenshots.**
   No bespoke pipeline — capture directly from a booted Simulator per device
   class App Store Connect requires (`xcrun simctl io <device> screenshot`),
   or from a real device via Xcode's device screenshot tool.

7. **Privacy-policy URL.**
   App Store Connect requires one before submission. **Placeholder — not yet
   set.** Host a privacy policy (even a single static page) and add its URL
   in App Store Connect's App Privacy section before submitting.

8. **Upload and submit.**
   `xcrun altool --upload-app` or Apple's Transporter app, using the `.ipa`
   the archive script produced. Complete the App Store Connect listing
   (description, category, age rating) and submit for review.

## Why this is split this way

Everything in "what's already done" is safe to ship on today's free-team
build — none of it requires signing changes. Everything in "once the paid
account is active" either requires the paid team's signing identity directly
(push, distribution export) or is genuinely blocked on it (screenshots and
the privacy-policy URL could technically be done earlier, but there's no
reason to before an actual submission is imminent). See spec 099's `spec.md`
FR-006/FR-007/FR-008 and `research.md` R6 for the full rationale.
