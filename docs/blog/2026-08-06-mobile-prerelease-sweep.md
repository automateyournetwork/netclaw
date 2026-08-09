# A Stuck Badge, a Feature We'd Already Built, and a Bug Only a Cold Cache Could Hide

**Draft for review — not published.** Constitution Principle XVII requires John's sign-off first.

*By John Capobianco and Claude · 2026-08-06*

John opened the NetClaw mobile app to a stuck notification badge and a Settings screen insisting push
was unavailable, and asked for a serious sweep of the whole app — phone and watch — before he pays Apple
for the privilege of shipping it. What came back was one real bug, one feature we'd already shipped
without noticing, four new surfaces, and — in the very last hour — a pre-existing defect that would have
made the CI gate we'd just built lie to everyone who trusted it.

## The bug was real; the other complaint wasn't

"Notifications unavailable" turned out to be accurate, not broken: `Runner.entitlements` documents in
its own comment that Push is deliberately unsigned because a free/Personal Apple team can't sign that
capability. The app was telling the truth.

The stuck badge was the real defect. `_recomputeBadge()` only ever ran reactively — on a new message
arriving, or an explicit acknowledge/delete. Nothing called it on cold launch or on foreground-resume, so
a badge left behind by a push delivered while the app was closed had no path back to zero. The fix was
two lines once found: a launch-time call, and a `WidgetsBindingObserver` for `AppLifecycleState.resumed`.
We pulled the observer into its own small class, `BadgeLifecycleObserver`, for a reason that recurred all
day: `_HomeShellState` can't be constructed in a test at all — its `EdgeClient` only exposes real-I/O
static factories — so anything worth testing has to live somewhere a test can actually reach it.

## We almost rebuilt something that already worked

The sweep's spec called for "rich notification actions" — Approve/Deny buttons on the banner itself,
biometric-gated, matching the pattern of Duo-style approval apps. Before writing a line of it, a search
turned up `local_notifications.dart`'s `approval` category, already wired with
`DarwinNotificationActionOption.authenticationRequired`, already routing through the exact same
`confirmAndResolve` function the in-app buttons use, already returning "Already resolved" instead of
double-applying a stale action. Spec 073 had built this. Nobody had told the sweep.

That's the best outcome a spec-driven process can produce here: the plan got rewritten mid-flight to
"verify, don't rebuild," and the six tests we added exist to pin behavior that was already correct, not
to justify new code. Building a parallel path would have been strictly worse — a second place for the
biometric gate to drift out of sync with the first.

## Two new native surfaces, two new lessons about API generations

A Lock Screen Live Activity and a watch complication both needed native extension targets — the exact
kind of Xcode-project surgery that bit us once before, in the watch app itself (spec 072 shipped with an
unset `SUPPORTED_PLATFORMS` and an empty `TargetAttributes` entry that took a manual fix to notice). This
time we wrote the check into the research doc before touching the `.pbxproj`, and verified both new
targets' `TargetAttributes` were populated the moment they were created.

The Live Activity cost us an afternoon in a different way. We picked iOS 16.1 as the floor — Apple's docs
say that's when ActivityKit shipped — and the code compiled right up until `activity.end(_:dismissalPolicy:)`,
which the current SDK only exposes on the `ActivityContent`-wrapped API introduced in 16.2. `request()`
worked at 16.1; `end()` didn't. Bumping one more point release was the whole fix, but it only became
obvious by trying to build, not by reading the changelog.

The watch complication taught a sharper lesson: a WidgetKit extension is a *separate process* from the
watch app. It cannot read `WatchDataStore`'s `@Published` approval count no matter how directly the task
description implied it could — that assumption had to be corrected mid-implementation. The fix is the
standard one, an App Group-shared `UserDefaults` the app writes to and the extension reads from, with
`WidgetCenter.shared.reloadAllTimelines()` called right after every write. App Groups, unlike Push, are
fine on a free team — so this didn't add a fourth thing waiting on John's Apple Developer payment.

## The bug that only a cold cache would show us

Every build all day succeeded — `flutter build ios`, a dozen `xcodebuild` calls across four schemes,
across eight stories. Then, writing the final regression-sweep task, we wiped DerivedData first
specifically to match what a GitHub Actions runner actually sees: nothing cached, ever.

`xcodebuild build -scheme Runner` failed instantly: `firebase-core requires minimum platform version
15.0... but this target supports 13.0`. Flutter's generated `Package.swift` hardcodes an iOS 13.0 floor
whenever `AppFrameworkInfo.plist` doesn't say otherwise — which this project never had. Xcode's package
resolver just doesn't re-check that constraint against an already-resolved graph, so every warm build all
day had been silently coasting past a conflict that was there from the start.

We checked: `git stash` back to the pre-sweep code, wipe DerivedData again, same failure. This predates
everything we built today. It has nothing to do with badges, Live Activities, or watch complications. But
the CI gate this feature exists to add (Story 4 — "catch regressions before merge") would have failed on
its first real pull request, for a reason no contributor touching this app would ever think to look for,
because their local machine would have the same warm cache masking it that ours did all day.

One line fixed it — `MinimumOSVersion` in `AppFrameworkInfo.plist`, which Flutter reads to generate the
real platform floor. But finding it depended entirely on deliberately throwing away a cache that every
other verification step that day had been quietly relying on.

## What we'd tell someone starting the next one

Verify from cold, not from warm. A dozen successful builds against a persistent DerivedData directory
told us nothing about what a fresh CI runner would actually see — and the one time we forced a truly
clean state, on the very last task of the day, it found something eleven hours of green builds had
hidden. If a feature's success criterion is "CI reliably catches this," test that claim the way CI itself
will run it, not the way that's fastest to iterate on locally.
