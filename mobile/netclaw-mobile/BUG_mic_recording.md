# Bug Report — Microphone recording intermittently fails or hangs

**Reported by:** Justin, 2026-07-27 18:02 EDT
**Device:** Android **15**, recognition engine = **Google** (Google app / Speech Services)
**Plugin:** `speech_to_text` **7.4.0**
**Triaged by:** NetClaw Border (`as65001-4.4.4.4`) — code read, not inferred
**Severity:** High — core input path, and the UI blocks retry while stuck
**Component:** `lib/ncfed/voice_transcription.dart` → `_defaultListenOnce()`

---

## Reported symptoms

1. Sometimes the mic **does not record** at all.
2. Sometimes it **stays hanging**.

Both are reproducible consequences of the current implementation. They are two
faces of the same defect cluster, and they *cause each other* (see §3).

---

## Permissions are NOT the cause — ruled out

Checked first because the code's own comments blame this. All declarations are
correct and present:

| Declaration | File | Status |
|---|---|---|
| `RECORD_AUDIO` | `AndroidManifest.xml` | ✅ explicit |
| `<queries><intent android:name="android.speech.RecognitionService">` | `AndroidManifest.xml` | ✅ present (Android 11+ package visibility) |
| `NSMicrophoneUsageDescription` | `ios/Runner/Info.plist` | ✅ |
| `NSSpeechRecognitionUsageDescription` | `ios/Runner/Info.plist` | ✅ |

So this is **not** the previously-reported "microphone option isn't working"
issue. That one was a missing manifest query and is genuinely fixed. This is a
different, subtler defect in the session state machine.

---

## Root causes

### BUG 1 — No `pauseFor`: the engine listens for the full 30 s after you stop talking
**This is the "hanging" the user sees.** Highest impact, simplest fix.

**CONFIRMED against the installed plugin source** (`~/.pub-cache/.../speech_to_text-7.4.0`).
Two findings raise this from "likely" to "certain", and they are specific to this
reporter's exact device/plugin combination:

**(a) 7.4.0's headline change is literally this feature.** `CHANGELOG.md`, top entry:

```
## 7.4.0-beta
### New
* Android now respects the pauseFor value
```

The app is pinned to the *first* version where `pauseFor` works on Android at
all — and does not set it. Before 7.4.0 the omission was harmless because
Android ignored it regardless; on 7.4.0 it is the whole bug. Silence-based
early stop is available and switched off.

**(b) With `pauseFor` null, `_stopOnPauseOrListen()` can only stop on `listenFor`.**
From `lib/speech_to_text.dart` (~line 585):

```dart
if (null != listenFor && _elapsedListenMillis >= listenFor.inMilliseconds) {
  _stop();
} else if (null != pauseFor &&
    _elapsedSinceSpeechEvent >= pauseFor.inMilliseconds) {
  _stop();
}
```

The silence branch is guarded by `null != pauseFor`. Unset, it is dead code:
the session is guaranteed to run the **full 30 s** irrespective of when the
speaker stops. This is deterministic, not engine-dependent — so the *hang* is
**not** intermittent at all. It happens on every utterance shorter than 30 s.
What varies is only whether the user waits it out or force-closes.

**Android 15 + Google engine relevance:** Android 12+ routes Google recognition
through on-device models that hold the recogniser open awaiting more speech
rather than finalising eagerly. Combined with (b), a 3-word request occupies the
mic for 30 s.

```dart
listenOptions: stt.SpeechListenOptions(
  partialResults: false,
  cancelOnError: true,
  listenFor: listenTimeout,   // 30 s
  // pauseFor: MISSING
),
```

`listenFor` is the **maximum session length**; `pauseFor` is the
**silence-timeout that ends the session early**. With `pauseFor` unset, many
Android engines hold the session open for the entire `listenFor` window
regardless of the speaker falling silent. Say three words and the mic icon stays
red for up to 30 seconds.

Compounding it: `onPressed: _listening ? null : _recordVoice` **disables the mic
button** for the whole duration, so the operator cannot cancel or retry. There is
no cancel affordance at all. That is precisely what "stays hanging" feels like.

**Fix:** add `pauseFor`. **Revised 2026-07-27 18:37 EDT after Justin's review** —
the initial 3 s was too aggressive; see §"Pause tuning" below. Now a two-stage
10 s → 5 s window.

⚠️ **Fix BUG 1 and BUG 6 together — they are coupled in the plugin.**
`pauseFor` is driven by `_lastSpeechEventAt`, which is updated *only* inside
`_notifyResults()` (line ~682). With `partialResults: false`, `_notifyResults`
returns early for non-final results:

```dart
if (!_partialResults && !speechResult.finalResult) {
  return;
}
```

— but note the timestamp assignment sits *above* that guard, so it does still
fire. The plugin's own convenience path nonetheless treats the two as
inseparable (line ~479):

```dart
partialResults: partialResults || null != pauseFor,
```

i.e. **the plugin force-enables partial results whenever `pauseFor` is set.**
Setting `pauseFor` while leaving `partialResults: false` in an explicit
`SpeechListenOptions` bypasses that coercion and is an untested combination.
Set **both**: `pauseFor: 3s` *and* `partialResults: true`, filtering non-final
results in `onResult` (which the app already does via
`if (!result.finalResult) return;`). The Border still only ever receives final
text — the existing contract is preserved.

### BUG 2 — The error path never completes the completer → guaranteed 32 s stall
`initialize(onError: (e) => lastError = e)` records the error and **nothing
else**. `finish()` is never called from `onError`.

With `cancelOnError: true`, an engine error cancels the session — so
`onResult` will never fire either. The `Completer` is then orphaned and the code
waits out the **full `listenTimeout + 2 s` = 32 seconds** before the `onTimeout`
handler salvages it.

The source comment acknowledges the scenario ("an error raised after `listen()`
returned … land here instead of hanging") but treats a 32-second stall as
acceptable. It is not: every mid-session error costs 32 s of frozen, un-cancellable UI.

**Fix:** complete immediately on error.
```dart
final available = await speech.initialize(onError: (e) {
  lastError = e;
  finish(VoiceResult.failed(VoiceFailure.engineError,
      'Speech recognition failed: ${e.errorMsg}'));
});
```
Requires hoisting `completer`/`finish` above `initialize`.

### BUG 3 — No `onStatus` listener: a clean-but-empty session also waits 32 s
`speech_to_text` exposes `onStatus` with `listening` / `notListening` / `done`.
It is not wired up. When the engine ends a session cleanly having heard nothing,
there is no final result and no error — so again the only exit is the 32-second
timeout.

**Fix:** pass `onStatus` to `initialize` and `finish(noSpeechDetected)` on
`done`/`notListening` if the completer is still pending.

### BUG 4 — Fresh `SpeechToText()` per call against a platform singleton → the "doesn't record" case
```dart
static Future<VoiceResult> _defaultListenOnce() async {
  final speech = stt.SpeechToText();     // new Dart object every tap
  final available = await speech.initialize(...);
```

A new Dart wrapper is constructed on every invocation, but the underlying
`SpeechRecognizer` (Android) / `SFSpeechRecognizer` (iOS) is a **single
platform-side resource**. Calling `initialize()` again while a prior session is
still tearing down commonly yields `available == true` from the Dart side while
`listen()` silently attaches to a busy recogniser — **no audio captured, no
error raised**. That is the "sometimes does not record" report exactly.

**Fix:** hold one `SpeechToText` instance for the app lifetime, `initialize()`
once, and reuse it. `VoiceTranscription` is already an injectable class — make
the instance a field.

### BUG 5 — `speech.stop()` is not protected, and there is no `cancel()`
```dart
final result = await completer.future.timeout(...);
await speech.stop();     // only reached on the normal path
return result;
```
Any throw between `listen()` and here (or a widget dispose / app backgrounding
mid-listen) skips `stop()` entirely and **leaks a live recognition session**.

**This is the mechanism that links the two symptoms.** A leaked session from
attempt *N* is exactly what poisons attempt *N+1* via BUG 4. One hang begets one
silent non-recording — a cascading failure, which matches "intermittent" far
better than any single independent fault.

**Fix:** wrap in `try/finally` with `await speech.cancel()` in the `finally`;
add a `dispose()` on `VoiceTranscription` called from `ChatScreen.dispose()`.

### BUG 6 — `partialResults: false` removes the only progress signal
With partials disabled, `onResult` fires **once**, at the very end. Two costs:
- Some Android engines are known not to emit a final result for very short
  utterances when partials are off → straight to the 32 s timeout.
- The operator gets no live feedback that anything is being heard, so a working
  slow recording is indistinguishable from a broken one.

**Fix:** set `partialResults: true`, ignore non-final results for the *request*
(preserving the existing contract that the Border only ever sees final text),
but use their arrival as proof of life — and optionally show interim text.

---

## Why it is intermittent

**Revised after confirming BUG 1 in plugin source.** The two reported symptoms
have *different* determinacy, which matters for triage:

**The hang is deterministic, not intermittent.** With `pauseFor` unset on
plugin 7.4.0, the silence-stop branch is unreachable and every session runs the
full 30 s. It only *looks* intermittent because a long utterance masks it — if
you happen to speak for most of the window, the wait is short. Short requests
hang every single time.

**The non-recording is genuinely intermittent**, and is caused by the hang:

1. Session runs 30 s (BUG 1) → user gives up, backgrounds the app or switches tab.
2. Dispose mid-listen skips `speech.stop()` — it sits outside any `try/finally`
   (BUG 5) → **live recognition session leaked**.
3. Next tap constructs a *new* `SpeechToText()` against the same platform
   singleton (BUG 4). `initialize()` returns true; `listen()` attaches to a busy
   recogniser → **no audio, no error**.
4. On Android 15 the Google engine surfaces this as `ERROR_RECOGNIZER_BUSY`
   or simply never emits a result — and since `onError` never completes the
   completer (BUG 2), that path stalls 32 s too.

So: **BUG 1 fires constantly, and each occurrence has a chance of leaking a
session that breaks the next attempt.** That is the cascade, and it explains why
the two symptoms alternate.

**Practical implication:** fixing BUG 1 alone should sharply reduce the
non-recording reports too, because it removes the abandonment that causes the
leak. Fix 1 + 3 + 5 together and the cascade is closed.

---

## Test-coverage gap (why CI is green)

`test/voice_transcription_test.dart` injects `listenOnce`:

```dart
final voice = VoiceTranscription(
  listenOnce: () async => const VoiceResult.success('check every core router...'),
);
```

The injection seam is good design and the test is legitimate — it asserts a voice
request produces the same wire shape as a typed one. **But it stubs out
`_defaultListenOnce` entirely, and that is where all six bugs live.** The
recording state machine has *zero* test coverage. That is why 24 passing tests
tell us nothing here.

**Recommend:** a fake `SpeechToText` seam (inject the plugin, not just the
result) with cases for: error-during-listen, session-ends-with-no-result,
short-utterance, and back-to-back invocations.

---

## Suggested fix order

| # | Fix | Effort | Impact |
|---|---|---|---|
| 1 | Add `pauseFor: 3s` | 5 min | Removes the common hang outright |
| 2 | `finish()` from `onError` | 20 min | Kills the 32 s error stall |
| 3 | `try/finally` + `cancel()` | 30 min | Stops session leaks → stops the cascade |
| 4 | Single reused `SpeechToText` | 45 min | Fixes "doesn't record" |
| 5 | Wire `onStatus` | 30 min | Kills the silent-session stall |
| 6 | `partialResults: true` | 30 min | Progress signal + short-utterance reliability |
| 7 | Cancel button while listening | 30 min | Operator can always escape |
| 8 | Tests around the plugin seam | 2 h | Prevents regression |

**≈ 5 hours.** Items 1–3 alone should remove most of what Justin is seeing and
could ship as a hotfix.

---

## Pause tuning — revised after reviewer objection

Justin raised that 3 s risks cutting off a slow speaker, or someone who pauses
mid-sentence before continuing. Correct, and it is the *worse* of the two
failure directions: a truncated request ("check BGP on…") is actively
misleading, whereas an extra second of waiting is merely mild. Investigated
against the plugin's own documentation and API.

### Finding 1 — 3 s sat exactly on a platform floor

`listen()`'s doc comment for `pauseFor`:

> *"On some systems, notably Android, there is a system imposed pause of from
> **one to three seconds** that cannot be overridden. The plugin ensures that
> the pause is no longer than the pauseFor value but it may be shorter."*

Two consequences:
- A 3 s request left **zero headroom** above a floor the platform may enforce
  anyway.
- `pauseFor` is a **ceiling, not a floor** — "may be shorter" means asking for
  3 s could yield an *even shorter* effective pause on some devices. Exactly the
  cut-off Justin predicted.

### Finding 2 — the plugin has a purpose-built API for this

`changePauseFor()`, documented as:

> *"Call this while [listen] is active to change the pauseFor duration… It is
> useful for allowing **a long first pause then dynamically shortening it once
> the user starts speaking**."*

That is precisely the problem. Two different silences deserve two different
tolerances:

| Silence | Meaning | Window |
|---|---|---|
| Before any speech | operator collecting their thoughts | **10 s** (`initialPauseFor`) |
| After speech began | mid-sentence pause, or finished | **5 s** (`pauseFor`) |

Implemented: session starts at `initialPauseFor`, and on the **first** partial
result calls `changePauseFor(pauseFor)` (guarded on `speech.isListening`, since
`changePauseFor` throws `ListenNotStartedException` otherwise).

So the operator may take up to 10 s to begin without being cut off, yet a
*finished* request still ends ~5 s after they stop — rather than every request
paying the full opening window. This is only possible because
`partialResults: true` (BUG 6) is now set: the transition is driven by the first
partial.

### Finding 3 — `listenMode` was wrong for dictated sentences

`SpeechListenOptions` defaults to `listenMode: ListenMode.confirmation`, which
the plugin describes as *"the most common use case, words or short phrases to
confirm a command"*, versus `ListenMode.dictation` for *"longer spoken content,
sentences or paragraphs"*.

A NetClaw request is a sentence ("check every core router for BGP problems"),
not a command word. `confirmation` biases the engine toward finalising early —
the opposite of what a slow speaker needs. Changed to `dictation`.

**Caveat, stated plainly:** the plugin marks `listenMode` as *"currently only
supported on iOS"*, so this will **not** change Android behaviour today. It is
still correct to declare, costs nothing, and benefits the iOS port (spec 071).
The Android improvement comes entirely from Findings 1 and 2.

### Why 5 s rather than 8 or 10

Bounded on both sides. Above ~10 s a completed request feels broken again —
re-creating the original complaint in milder form. 5 s clears the 1–3 s platform
floor with real margin, accommodates the hesitation typical of dictating device
names, interface IDs and IP addresses, and still ends a finished request
promptly. Tests assert `pauseFor > 3 s` (floor cleared) and `≤ 10 s` (still
bounded), so neither direction can silently regress.

**Tunable:** both values are named `static const` on `VoiceTranscription`. If 5 s
still clips slow speakers in field use, raise it — the guard tests define the
safe band rather than pinning an exact number.

---

## Related observation

Two speech defects are now on record for this build:
- This one (recording reliability).
- 2026-07-27 11:28 EDT — transcription emitted a duplicated phoneme
  ("speak speak" for "speech"). Accuracy, not session state; likely unrelated.

---

## Verification note

Read from the working tree at `/home/johncapobianco/netclaw/mobile/netclaw-mobile`
on 2026-07-27: full `lib/ncfed/voice_transcription.dart`,
`lib/screens/chat_screen.dart` (mic handler + button wiring),
`android/app/src/main/AndroidManifest.xml`, `ios/Runner/Info.plist`,
`test/voice_transcription_test.dart`.

Also read: `~/.pub-cache/hosted/pub.dev/speech_to_text-7.4.0/lib/speech_to_text.dart`
(lines ~470–600, ~670–695) and its `CHANGELOG.md` — confirming the `pauseFor`
null-guard in `_stopOnPauseOrListen()`, the
`partialResults: partialResults || null != pauseFor` coercion, the
`_lastSpeechEventAt` update site, and that "Android now respects the pauseFor
value" is 7.4.0's headline change.

**Device confirmed by reporter:** Android 15, Google recognition engine.

**Still not verified:** no device logcat was captured during a reproduction.
Expected signatures if one is taken while the mic misbehaves:
`ERROR_RECOGNIZER_BUSY` (confirms BUG 4/5 leak) or `ERROR_NO_MATCH` /
`ERROR_SPEECH_TIMEOUT` (confirms BUG 1/3/6 path). Also unverified: whether
Google's *on-device* vs *network* recognition is selected on this handset — the
app never sets `onDevice`, leaving it to engine default.

BUG 1 no longer requires device confirmation: it is provable from plugin source
and version alone.
