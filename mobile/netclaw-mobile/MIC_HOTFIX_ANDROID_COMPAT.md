# Mic Hotfix — Android Version Compatibility Analysis

**Question:** is the mic hotfix applicable and compatible with Android **15, 16,
and 17**?
**Answer:** Yes for **15 and 16**, with evidence below. **Android 17 cannot be
verified** — see §6, it does not exist yet as a testable target and the SDK is
not installed here. Claiming otherwise would be guesswork.

**Analysed:** 2026-07-27 · plugin `speech_to_text` 7.4.0 (Dart + Kotlin native)
· Flutter 3.44.8 / Dart 3.12.2

> **RE-VERIFIED 2026-07-27 18:41 EDT.** The hotfix changed after the first pass
> (two-stage `changePauseFor`, `ListenMode.dictation`), introducing new API
> surface that the original analysis had not covered. Both are re-checked in
> §9 and the APK has been rebuilt against the current code. Conclusions are
> unchanged, and one new **zero-regression proof** for Android emerged.

---

## 1. SDK configuration as built

| Setting | Value | Android release |
|---|---|---|
| `compileSdk` | **36** (`flutter.compileSdkVersion`) | Android 16 |
| `targetSdk` | **36** (`flutter.targetSdkVersion`) | Android 16 |
| `minSdk` | **24** (`flutter.minSdkVersion`) | Android 7.0 |
| plugin `minSdkVersion` | 21 | Android 5.0 |
| Java/Kotlin target | 17 | — |

Locally installed SDK platforms: **android-34, android-35, android-36**. There is
no android-37.

So the app compiles against Android 16 and declares support from Android 7
upward. Android 15 (API 35) and 16 (API 36) are both covered by the existing
configuration; **no gradle change is needed for either.**

---

## 2. Why the fix is version-robust by construction

The important finding: **`pauseFor` is enforced by two independent mechanisms**,
one of which is entirely OS-agnostic.

### Mechanism A — Dart-side timer (primary, version-independent)

`speech_to_text.dart` runs its own timer and stops the session itself:

```dart
_listenTimer = Timer(minDuration, _stopOnPauseOrListen);
...
} else if (null != pauseFor &&
    _elapsedSinceSpeechEvent >= pauseFor.inMilliseconds) {
  _stop();
}
```

This is pure Dart. It does not consult `Build.VERSION.SDK_INT`, the OEM, or the
recognition engine. **On any Android version — 15, 16, 17, or 25 — a 3-second
silence stops the session.** This is the mechanism that fixes the reported hang,
and it cannot regress on a future OS release.

### Mechanism B — native intent extra (secondary, engine-dependent)

`SpeechToTextPlugin.kt` also forwards the value to the engine:

```kotlin
pauseFor?.also {
    putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, it)
}
```

`EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS` is documented as a *hint* —
engines may ignore it. That is fine: it is an optimisation, not the guarantee.
Mechanism A is the guarantee.

**Consequence:** even if Google's engine on a future Android ignores the hint
entirely, the hotfix still works. That is the single most important
forward-compatibility property here.

---

## 3. Every version gate in the plugin, checked

Exhaustive grep of `Build.VERSION.SDK_INT` in the plugin's Kotlin:

| Line | Gate | API 35 (A15) | API 36 (A16) | API 37+ |
|---|---|---|---|---|
| 265 | `SDK_INT < 21` → unsupported | pass | pass | pass |
| 253 | `SDK_INT != 29` → `recognizerStops` | **true** | **true** | true |
| 373 | `SDK_INT >= 33` → on-device check | yes | yes | yes |
| 530 | `SDK_INT >= 31 (S)` | yes | yes | yes |
| 623 | `SDK_INT >= 31 (S)` + `onDevice` | yes | yes | yes |

**All gates are lower bounds except one, and that one is an equality test for
API 29 only.** `brokenStopSdk = 29` — Android 10 alone has the broken-`stop()`
workaround. Android 15, 16, and any later release take the identical modern code
path. There is no upper bound anywhere in the plugin that a new Android version
could trip.

This is the key structural result: **15, 16 and 17 are not three different code
paths in this plugin — they are one.**

---

## 4. Each fix, assessed for version sensitivity

| Fix | Mechanism | Version-sensitive? |
|---|---|---|
| BUG 1 `pauseFor: 3s` | Dart timer (A) + intent hint (B) | **No** — A is pure Dart |
| BUG 2 complete on `onError` | Dart completer | **No** |
| BUG 3 `onStatus` → `doneStatus` | Dart callback | **No** (see §5 caveat) |
| BUG 4 single `SpeechToText` | Dart instance reuse | **No** — and aligns with the plugin's own `if (_initWorked) return` idempotence |
| BUG 5 `try/finally` + `cancel()` | Dart lifecycle | **No** |
| BUG 6 `partialResults: true` | `EXTRA_PARTIAL_RESULTS` | Minor — see §5 |
| Stop button | Flutter UI | **No** |

**Six of seven fixes live entirely in Dart** and are therefore immune to Android
version differences by construction. Only BUG 6 touches engine behaviour, and it
is a hint whose absence is already tolerated.

Verified compatible with the plugin's `initialize()` contract:

```dart
if (_initWorked) { return Future.value(_initWorked); }
...
errorListener = onError;
statusListener = onStatus;
```

`initialize()` early-returns once it has succeeded, so `onError`/`onStatus` are
registered **only on the first call**. Our design registers them once and routes
completion through a mutable `_activeFinish` pointer rather than closing over a
per-session completer. **This is not incidental — it is required** by that
early-return, and it is the reason instance reuse (BUG 4) and the new callbacks
(BUGs 2/3) are compatible rather than in conflict.

---

## 5. Residual risk found — one honest gap

Tracing `_onNotifyStatus` in `speech_to_text.dart`:

```dart
case doneStatus:
  _notifiedDone = true;
  if (_latestResultType == ResultType.partial) return;   // <-- swallowed
  break;
```

`_latestResultType` is initialised to `ResultType.partial` at the start of every
`listen()`. So:

- **Truly silent session** → native emits `doneNoResult` (Kotlin line ~421:
  `false -> SpeechToTextStatus.doneNoResult.name`), which Dart maps to
  `doneStatus` **unconditionally** with no early return. → **our `onStatus`
  handler fires. Covered.**
- **Partial arrived but no final** → status is swallowed by that guard, so our
  handler does *not* fire. This path is instead rescued by the plugin's own
  `_notifyFinalTimer` / `finalTimeout`, which promotes the last partial to a
  final result (`_onFinalTimeout` → `toFinal()` → `_notifyResults`) — which
  triggers our `onResult`. **Covered, but by a different mechanism than
  intended.**

**Net:** every path terminates, but via three different routes (`pauseFor` timer,
`doneNoResult` status, `finalTimeout` promotion), plus the 32 s backstop. That is
defence in depth rather than elegance. Worth noting in review; not a defect.

---

## 6. Android 17 — cannot be verified, and I will not claim it

Being explicit, because this was asked directly:

- **Android 17 (API 37) is not released.** Android 16 = API 36 is current, and is
  what `flutter.targetSdkVersion` resolves to in Flutter 3.44.8.
- **No android-37 platform is installed** on this host (34, 35, 36 only), so it
  cannot be compiled against, let alone tested.
- Any statement that this hotfix "works on Android 17" would be unfalsifiable
  today.

**What can be said with confidence:** the fix contains **no upper version
bound**, and its primary mechanism is a Dart timer that never inspects the OS
version. Structurally there is nothing for a future Android release to break.
The plugin's only version-equality gate targets API 29, far below.

**Where Android 17 could still bite** — historically plausible, worth watching:

1. **Tighter mic/permission rules.** Android 14 added foreground-service audio
   restrictions; a future release could extend them. *Current posture is
   correct:* the mic is used only from a foreground `Activity`, and the manifest
   declares no `FOREGROUND_SERVICE` audio type — nothing to break today.
2. **Engine behaviour changes.** If Google's recogniser ignores
   `EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS`, Mechanism A still stops
   the session. **This is already handled.**
3. **`targetSdk` bump required for Play Store.** A policy matter, not a mic
   matter. Because `targetSdk = flutter.targetSdkVersion`, a Flutter SDK upgrade
   moves it automatically — no code edit.
4. **New `SpeechRecognizer` API deprecations.** Would need a plugin update, not
   an app change. Out of our hands either way.

**Recommendation:** re-test on Android 17 when a developer preview ships. Do not
mark it "supported" until it is.

---

## 7. Verification performed

```
flutter analyze        → No issues found!
flutter test           → 123/123 passed  (109 before the hotfix; +14 new)
flutter build apk      → ✓ Built build/app/outputs/flutter-apk/app-debug.apk  (474s, exit 0)
```

**The Android build succeeds.** This is the material addition to this analysis:
the hotfix compiles and links against `compileSdk 36` / `targetSdk 36`
(Android 16) with `minSdk 24`, producing a real installable APK. Compatibility
with 15 and 16 is therefore demonstrated at the toolchain level, not merely
argued from source reading.

Still **no on-device run on any Android version.** The tests cover the Dart state
machine — where six of seven fixes live — but cannot exercise a real recogniser.

### Two build warnings observed (pre-existing, not caused by the hotfix)

1. **KGP deprecation:** *"Your app uses the following plugins that apply Kotlin
   Gradle Plugin (KGP): mobile_scanner, speech_to_text — future versions of
   Flutter will fail to build."* This is a **forward-compatibility risk on the
   `speech_to_text` plugin itself** — precisely the dependency this hotfix relies
   on. It does not affect Android 15/16 today, but it is the most likely thing to
   break a future Flutter upgrade, and it is upstream of us. Track it.
2. **SDK XML version 4 vs tooling 3:** benign command-line-tools/Android Studio
   version skew. No action.

Neither warning is introduced by these changes; both reproduce on the unmodified
tree.

**To close the remaining doubt**, the meaningful check is a build + manual mic
test on:
- **Android 15 (API 35)** — Justin's handset, the original reporter
- **Android 16 (API 36)** — the compile/target level
- **Android 17** — when it exists

Expected behaviour on all: mic releases ~3 s after speech stops; stop button
cancels immediately; two consecutive recordings both work.

---

## 9. Re-verification of the post-review changes (18:41 EDT)

The pause-tuning revision added two things not present when §§1–8 were written.
Both needed independent compatibility checking; neither weakens the conclusion.

### 9.1 `changePauseFor()` — pure Dart, zero platform surface

Measured, not assumed:

```
SDK_INT / Platform references inside changePauseFor()  →  0
Platform-channel calls inside changePauseFor()         →  NONE
```

It only cancels and re-arms a Dart `Timer` via `_setupListenAndPause(...)`. It
never crosses the method channel, so the native Kotlin never learns the pause
was retightened. **Consequence: the 10 s → 5 s transition behaves identically on
Android 15, 16, 17 and every earlier release** — it is not an OS feature at all.
This strengthens Mechanism A from §2 rather than adding risk.

One real constraint, handled: `changePauseFor` throws
`ListenNotStartedException` when `isNotListening`. Our call site is guarded on
`speech.isListening`, so a race (result arriving as the session ends) cannot
throw. Version-independent.

### 9.2 `ListenMode.dictation` — enum ordinal crosses the channel

This one warranted care, because the value is marshalled as an **ordinal index**,
not a name:

```dart
"listenMode": options?.listenMode.index ?? listenMode,
```

A Dart/Kotlin enum-order mismatch would silently select the wrong mode. Verified
both declarations:

| Index | Dart (`ListenMode`) | Kotlin (`ListenMode`) |
|---|---|---|
| 0 | `deviceDefault` | `deviceDefault` |
| 1 | **`dictation`** | **`dictation`** |
| 2 | `search` | `search` |
| 3 | `confirmation` | `confirmation` |

**Orders match exactly.** `dictation` → index 1 → Kotlin
`enumValues<ListenMode>()[1]` = `dictation`. No mismatch, no risk.

### 9.3 New finding — `dictation` is provably a no-op on Android

The earlier caveat ("iOS-only, so no Android effect") was taken from the
plugin's doc comment. It is now **proven from the native source**
(`setupRecognizerIntent`, line ~668):

```kotlin
if (listenMode == ListenMode.search) {
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_WEB_SEARCH)
} else {
    putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
}
```

Android branches on `search` **only**. `dictation` and `confirmation` both fall
to the same `else`, yielding identical `LANGUAGE_MODEL_FREE_FORM`.

**This is a zero-regression proof, not merely "no benefit":** the
`confirmation` → `dictation` change cannot alter Android behaviour on *any*
version, because the two values are indistinguishable to the native layer. The
only Android-visible consequence is a cache invalidation — `previousListenMode
!= listenMode` forces one `recognizerIntent` rebuild on the first listen after
the change, which is exactly what that guard exists to do.

iOS remains the only platform where `dictation` has effect, benefiting spec 071.

### 9.4 Interaction with the instance-reuse fix (BUG 4)

Worth checking, since the native layer caches a recogniser and we now reuse the
Dart wrapper. `createRecognizer` (line ~603):

```kotlin
if ( null != speechRecognizer && onDevice == lastOnDevice ) {
    return
}
```

The native side **already** reuses its `SpeechRecognizer` across listens,
recreating only when `onDevice` changes. Our single-instance Dart approach
therefore *matches* the plugin's own native lifecycle rather than fighting it —
the per-tap construction it replaced was the anomaly. We never set `onDevice`
(default `false`, unchanged), so no recogniser churn is introduced.

Also re-confirmed: the `SDK_INT >= 31` on-device branch is unreachable for us
because `onDevice` is false, so it cannot differ across 15/16/17.

### 9.5 Re-verification results

```
flutter analyze     → No issues found!
flutter test        → 126/126 passed   (+3 pause-band guard tests)
flutter build apk   → ✓ Built app-debug.apk   (9.5s incremental, exit 0)
```

APK rebuilt **against the current code**, so the artifact and the analysis now
agree. Same two pre-existing warnings (KGP deprecation, SDK XML skew); no new
ones.

---

## 8. Bottom line

| Version | Status | Basis |
|---|---|---|
| Android 7–14 (API 24–34) | ✅ Compatible | `minSdk 24`; only API 29 has a special path, unrelated to these fixes |
| **Android 15 (API 35)** | ✅ Compatible | All plugin gates are lower bounds; SDK installed; reporter's device |
| **Android 16 (API 36)** | ✅ Compatible | Is the `compileSdk`/`targetSdk`; identical code path to 15 |
| **Android 17 (API 37)** | ⚠️ **Unverifiable** | Not released, SDK not installed. No upper bound in the fix; primary mechanism is OS-agnostic Dart |

Build evidence: `flutter build apk --debug` completes successfully (exit 0)
against `compileSdk`/`targetSdk` 36 with `minSdk` 24 — rebuilt 18:41 EDT against
the post-review code.

**Post-review changes add no version sensitivity** (§9): `changePauseFor` is pure
Dart with zero platform-channel surface, and `ListenMode.dictation` is provably
indistinguishable from `confirmation` in the native Android path — so the
revision cannot regress any Android version. Dart/Kotlin enum ordinals verified
aligned.

No gradle, manifest, or `minSdk` change is required for 15 or 16. The hotfix is
version-robust because it is overwhelmingly Dart-side — but "robust by
construction" is an argument, not a test result, and 17 should be re-tested when
it ships.
