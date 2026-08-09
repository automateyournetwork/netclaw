# Feature Specification: Mobile Pre-Release Hardening & Expansion Sweep

**Feature Branch**: `099-mobile-prerelease-sweep`
**Created**: 2026-08-06
**Status**: Draft
**Input**: User description: "Pre-release hardening and expansion sweep for the NetClaw mobile app (phone and Apple Watch) ahead of App Store submission. Builds on the existing mobile app delivered across specs 066-073; must not regress existing enrollment, chat, feed, approvals, or capture flows. Scope: (1) fix the stuck notification badge, (2) App Store release readiness split into not-gated and paid-account-gated work, (3) CI enforcement for the mobile app including native watch test coverage, (4) new experience — rich notification actions, Lock Screen widget/Live Activity, a Dashboard/overview home screen surfacing NCFED identity/Border health/stats, and watch complications."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Notification badge always reflects reality (Priority: P1)

A user has the NetClaw app installed on their phone. Messages, approvals, and other unread items arrive over time, some while the app is closed. At any point, the number shown on the app's home-screen icon must match the true number of unread/pending items — including the case where that number is zero.

**Why this priority**: This is a live, user-visible defect reported directly by the developer using the app today. It undermines trust in every other notification-related feature in this spec and is cheap to fix, so it ships first regardless of what else in this spec proceeds.

**Independent Test**: Force the OS badge to a nonzero value (e.g., receive a push while the app is fully closed), then either launch the app fresh or bring it from background to foreground without touching any unread item. The badge must correct itself to the true unread count without any further user action.

**Acceptance Scenarios**:

1. **Given** the app is fully closed and the OS shows a stale badge count, **When** the user launches the app, **Then** the badge is corrected to the true unread count within 5 seconds of launch.
2. **Given** the app is backgrounded with a stale badge count, **When** the user brings the app to the foreground, **Then** the badge is corrected to the true unread count.
3. **Given** the user has read/acknowledged everything, **When** the badge is recomputed (on launch, resume, or any existing recompute trigger), **Then** the badge is cleared to zero and stays at zero until a new unread item arrives.

---

### User Story 2 - App passes automated App Store submission checks (Priority: P2)

The developer wants to be able to run an App Store Connect submission (or a TestFlight build) without it being rejected for a missing privacy manifest, missing usage-description strings, or an undeclared encryption posture — none of which require a paid Apple Developer Program account to fix.

**Why this priority**: These are hard blockers to any App Store Connect upload, independent of the paid-account question, and are the cheapest, most mechanical items to close out.

**Independent Test**: Archive the app for distribution and validate it through App Store Connect's automated checks (or an equivalent local validation step); it must not fail for a missing privacy manifest, missing usage strings, or an undeclared encryption flag.

**Acceptance Scenarios**:

1. **Given** the app requests photo library and/or local-network access anywhere in its flows, **When** the app is built for release, **Then** the corresponding usage-description strings are present and describe the actual use.
2. **Given** the app uses TLS/X.509 for its federation transport, **When** the app is submitted, **Then** its encryption-usage declaration is present and accurate.
3. **Given** the app uses APIs that require a privacy manifest, **When** the app is archived, **Then** a privacy manifest is present and accounts for those APIs.

---

### User Story 3 - Push notifications and store submission work once the paid account is active (Priority: P3)

The developer has committed to upgrading to a paid Apple Developer Program account but has not done so yet. Once they do, push notifications should start working and an actual App Store/TestFlight submission should be possible, without needing to rediscover or re-derive what was deferred.

**Why this priority**: This work is real and necessary but is explicitly blocked on an external dependency (the paid account) that is not yet in place. It is sequenced after P1/P2 so nothing here blocks work that can ship today, but the work itself should be ready to execute the moment the account exists.

**Independent Test**: With a paid account and its signing identity in place, push notification code signing can be enabled and a distribution build can be produced and uploaded to App Store Connect, without further rework of items covered by this story.

**Acceptance Scenarios**:

1. **Given** a paid Apple Developer Program account and distribution signing identity are available, **When** the developer builds for distribution, **Then** push notification entitlements are signed correctly and push notifications are delivered to the device.
2. **Given** the same paid-account prerequisites, **When** the developer archives the app for submission, **Then** a repeatable, documented process produces a build ready for App Store Connect upload (screenshots, export configuration, and privacy-policy URL are accounted for).
3. **Given** the paid account is NOT yet active, **When** the developer builds the app today, **Then** the build still succeeds and runs normally on a free/Personal team, with push simply reporting itself as unavailable (current behavior preserved, not broken by this work).

---

### User Story 4 - Regressions in the mobile app are caught before merge (Priority: P4)

A contributor changes code under the mobile app or its iOS native layer. Before that change can be merged, automated checks must run and catch broken tests, static-analysis violations, or a build failure in either the phone app or the watch app.

**Why this priority**: There is currently no automated gate at all for this codebase; every other story in this spec adds more surface area that could regress silently without one. It's independent of the App Store stories and can proceed in parallel with them.

**Independent Test**: Open a pull request that breaks an existing Dart test, introduces a static-analysis violation, or breaks the iOS/watch build; the check must fail and block merge. Open a clean pull request; the check must pass.

**Acceptance Scenarios**:

1. **Given** a pull request touches the mobile app, **When** the pull request is opened or updated, **Then** the existing Dart test suite and static analysis run automatically and their result is visible on the pull request.
2. **Given** a pull request touches the iOS native layer or the watch app, **When** the pull request is opened or updated, **Then** both the phone app and the watch app target are built automatically and a build failure is visible on the pull request.
3. **Given** the native watch-relay message-passing logic, **When** a contributor changes it, **Then** at least a basic automated test exists that would fail if that logic broke.

---

### User Story 5 - At-a-glance federation status on a Dashboard (Priority: P5)

A user opens the app and, before diving into chat, feed, or approvals, wants to see: is this device actually connected to its Border right now, what is its identity/enrollment standing in the federation, and how much is waiting for attention (unread messages, pending approvals, recent activity).

**Why this priority**: Today the app opens straight into one of four equally-weighted tabs with no overview; this is the single biggest structural UX gap identified in the review, but it's additive (a new pane) rather than corrective, so it follows the fixes and readiness work.

**Independent Test**: Open the app and view the Dashboard pane without navigating anywhere else; it must show current Border connection health, this device's identity/enrollment status, and current unread/pending counts, all without stale or placeholder data.

**Acceptance Scenarios**:

1. **Given** the device is actively connected to its Border, **When** the user opens the Dashboard, **Then** it shows the connection as healthy along with this device's identity and enrollment scope.
2. **Given** the device has lost its connection to the Border, **When** the user opens the Dashboard, **Then** it clearly shows the disconnected/degraded state rather than stale "last known good" data presented as current.
3. **Given** there are unread messages and/or pending approvals, **When** the user opens the Dashboard, **Then** it shows accurate counts for each, and following through from the Dashboard reaches the same detail already available in the Feed/Approvals tabs.

---

### User Story 6 - Approve or deny directly from a notification (Priority: P6)

A user receives a push or local notification about a pending approval. Instead of unlocking the phone and navigating into the app, they act directly on the notification banner.

**Why this priority**: This is the highest-leverage new UX capability identified (matches the pattern of comparable approval-based apps) but depends on notification delivery already working reliably (P1) and is additive rather than corrective.

**Independent Test**: Trigger a pending-approval notification and, without opening the app, tap Approve (or Deny) directly on the notification; the underlying approval must be resolved exactly as if the user had opened the app and acted there.

**Acceptance Scenarios**:

1. **Given** a pending-approval notification is showing, **When** the user taps Approve or Deny on the notification itself, **Then** the approval is resolved accordingly and reflected consistently across phone, watch, and Border.
2. **Given** the action requires biometric confirmation under this app's existing approval security model, **When** the user acts from the notification, **Then** the same confirmation requirement is honored before the approval is resolved — acting from a notification must not weaken the security guarantee of acting from inside the app.
3. **Given** the approval has already expired or been resolved elsewhere (e.g., from another device), **When** the user taps an action on a stale notification, **Then** the app reports the current state rather than silently double-resolving it.

---

### User Story 7 - Pending approval visible without unlocking the phone (Priority: P7)

A user wants to know, at a glance from the Lock Screen, whether there is a pending approval waiting for them, without unlocking the phone.

**Why this priority**: Natural companion to Stories 1 and 6, but lower priority since it's a convenience/glanceability improvement rather than a functional gap.

**Independent Test**: With a pending approval outstanding, view the Lock Screen; a widget or Live Activity must show that a pending approval exists, and it must clear itself once the approval is resolved from any device.

**Acceptance Scenarios**:

1. **Given** a pending approval exists, **When** the user views the Lock Screen, **Then** a widget/Live Activity indicates a pending approval is waiting, without exposing sensitive approval content to anyone who can see the locked screen.
2. **Given** the pending approval is resolved (from phone, watch, or notification action), **When** the user next views the Lock Screen, **Then** the widget/Live Activity reflects the resolved state promptly.

---

### User Story 8 - Pending approval count on the watch face (Priority: P8)

A user wearing the Apple Watch companion app wants a glanceable pending-approval count directly on their watch face, without opening the watch app.

**Why this priority**: Smallest, most isolated addition in this spec; depends on the watch app's existing data already being correct (which it is, per the existing 072 implementation) and is purely additive.

**Independent Test**: With one or more pending approvals outstanding, add the NetClaw complication to a watch face; it must show the current pending count and update as approvals are added or resolved.

**Acceptance Scenarios**:

1. **Given** pending approvals exist, **When** the user views a watch face with the NetClaw complication added, **Then** it displays the current pending-approval count.
2. **Given** all pending approvals are resolved, **When** the user views the complication, **Then** it reflects zero/no pending approvals.

---

### Edge Cases

- What happens to the badge/dashboard/complication counts if the phone and watch briefly disagree because one hasn't synced yet? (Expectation: each surface shows its own best-known state and converges quickly once connectivity is restored; none should show a permanently stuck stale value — this generalizes the P1 fix to every surface added later in this spec.)
- What happens if a user resolves the same pending approval simultaneously from two surfaces (e.g., notification action and watch)? The system must settle on one outcome and reflect it consistently everywhere, not error or double-apply.
- What happens to release-readiness work (Story 2/3) if the developer's paid account application is delayed or rejected? Story 2's items must stand on their own and provide value (a submittable, compliant build shell) even if Story 3 remains blocked indefinitely.
- What happens to the Dashboard (Story 5) when the app has never successfully enrolled with a Border? It must show a clear "not yet enrolled" state rather than an error or blank pane.
- What happens when a CI check (Story 4) is flaky or fails due to environment issues unrelated to the change? Out of scope to solve flakiness itself here, but the check must be clearly attributable (which suite/build failed) so it isn't a black box.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST reconcile its home-screen badge count to the true unread/pending count at every app launch, in addition to any existing reactive recompute triggers.
- **FR-002**: The app MUST reconcile its home-screen badge count to the true unread/pending count every time the app transitions from background to foreground.
- **FR-003**: The app MUST declare a privacy manifest accounting for every API category it uses that requires one.
- **FR-004**: The app MUST present accurate, specific usage-description strings for every protected resource it can request access to (camera, microphone, speech recognition, Face ID, photo library, local network — as applicable to what the app actually does).
- **FR-005**: The app MUST declare its encryption usage posture accurately for App Store submission, consistent with its actual use of TLS/X.509.
- **FR-006**: The release-readiness work that does not require a paid Apple Developer account (FR-003, FR-004, FR-005) MUST be shippable and verifiable independent of whether the paid account exists yet.
- **FR-007**: The push-notification code-signing and distribution-provisioning work MUST be clearly identified as dependent on an active paid Apple Developer Program account, and MUST NOT block or degrade the app's current behavior on a free/Personal team while that account is pending.
- **FR-008**: Once a paid account is active, the system MUST provide a repeatable, documented process for producing a distributable build (including export configuration, a screenshot-generation approach, and a privacy-policy URL reference) suitable for App Store Connect submission.
- **FR-009**: A continuous-integration check MUST run the existing automated Dart test suite and static analysis on every pull request that touches the mobile app.
- **FR-010**: A continuous-integration check MUST build both the phone app and the watch app target on every pull request that touches the mobile app or its iOS native layer, and MUST fail the check if either build fails.
- **FR-011**: The native watch-relay message-passing logic MUST have at least a basic automated test that fails if that logic is broken.
- **FR-012**: The app MUST provide a Dashboard/overview view showing, at minimum: current Border connection health, this device's federation identity/enrollment status, and current unread-message and pending-approval counts, and it MUST be the app's default landing tab, opening before Chat/Feed/Approvals/Settings.
- **FR-013**: The Dashboard MUST distinguish a genuinely healthy/current state from a stale or disconnected one — it must not present last-known-good data as if it were current.
- **FR-014**: The app MUST support resolving a pending approval (approve or deny) directly from a notification action, without requiring the user to open the app.
- **FR-015**: Resolving an approval from a notification action MUST require the same Face ID (biometric) confirmation the in-app approval flow already requires before the approval is resolved — the notification-action path is not a lighter-security shortcut.
- **FR-016**: If a pending approval has already been resolved or has expired by the time a notification action is invoked, the app MUST report the current state to the user rather than silently reapplying or erroring opaquely.
- **FR-017**: The app MUST provide a Lock Screen widget and/or Live Activity that indicates whether a pending approval exists, without exposing sensitive approval content on the locked screen.
- **FR-018**: The Lock Screen indicator MUST update to reflect resolution of the pending approval regardless of which surface (phone, watch, or notification action) resolved it.
- **FR-019**: The watch app MUST provide a complication showing the current pending-approval count, updating as approvals are added or resolved.
- **FR-020**: None of the new work in this spec may regress the existing enrollment, chat, feed, approvals, or capture flows delivered in specs 066-073.

### Key Entities

- **Unread/Pending Count**: The reconciled, authoritative count of unread messages and pending approvals a given surface (phone badge, Dashboard, watch complication, Lock Screen widget) displays; must always be derivable from true underlying state rather than cached/stale.
- **Approval Resolution**: The act of approving or denying a pending approval, regardless of which surface it originates from (in-app, notification action, watch); must resolve consistently and exactly once across all surfaces.
- **Federation Identity/Enrollment Status**: This device's standing within its NCFED federation (Border connection state, member/risk scope, enrollment status) as surfaced on the Dashboard.
- **Release Build Configuration**: The set of signing identity, entitlements, and submission metadata (export configuration, screenshots, privacy-policy URL) that differs between the free/Personal-team build usable today and the paid-account distribution build needed for App Store submission.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The home-screen badge count matches the true unread/pending count within 5 seconds of every app launch and every foreground transition, with zero user-reported instances of a stuck badge after this ships.
- **SC-002**: A release archive of the app passes App Store Connect's automated validation checks for privacy manifest, usage-description strings, and encryption declaration, with zero rejections attributable to those categories.
- **SC-003**: Once a paid account is active, a developer can go from "paid account exists" to "distributable build uploaded to App Store Connect" by following a single documented process, with no rediscovery of deferred configuration.
- **SC-004**: 100% of pull requests touching the mobile app or its iOS native layer show a pass/fail automated check result (tests, analysis, and build) before merge, and a broken build or failing test reliably blocks merge.
- **SC-005**: A user can determine their device's connection health, identity, and unread/pending status within one glance at the Dashboard, without navigating into any other tab.
- **SC-006**: A user can resolve a pending approval entirely from a notification, start to finish (including biometric confirmation), without unlocking into the app's main interface, in under 10 seconds.
- **SC-007**: A user can determine whether a pending approval exists by glancing at either the Lock Screen or the watch face, without opening the phone app.

## Assumptions

- The existing enrollment, chat, feed, approvals, and capture flows from specs 066-073 are stable and are not being redesigned by this spec — this spec only adds a Dashboard as a new pane and touches notification/badge behavior; it does not restructure existing screens.
- "Paid Apple Developer Program account" refers to Apple's standard $99/year individual or organization membership; the developer has stated intent to purchase it but has not yet done so at the time of this spec.
- Screenshot generation for App Store Connect can use a standard simulator/device capture approach; no bespoke marketing-asset pipeline is in scope.
- The Dashboard draws only on federation data already available to the app's existing services (identity, member/risk scope, Border connection state, unread/pending counts) — no new Border-side data surface is assumed necessary unless implementation discovers a genuine gap.
- Watch complications and the Lock Screen widget rely on the existing phone-watch sync (WatchConnectivity) and push/local-notification plumbing already delivered in specs 072-073; no new sync transport is introduced.
- CI enforcement targets the existing ~25 Dart test files and existing static-analysis configuration; this spec does not mandate raising Dart test coverage beyond what already exists, only enforcing what's already written, plus a minimal new native test for the watch-relay logic (FR-011).
