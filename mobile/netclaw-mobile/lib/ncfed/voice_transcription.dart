import 'dart:async';

import 'package:speech_to_text/speech_recognition_error.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import 'edge_ask_client.dart';

/// Why a voice request produced nothing. Previously every failure — permission
/// denied, no recognition engine, engine error, silence — collapsed into a bare
/// `null`, so the mic button did nothing at all with no explanation. A real
/// tester reported it simply as "microphone option isn't working", which is the
/// only thing the UI could possibly have conveyed.
enum VoiceFailure {
  /// The plugin could not initialise. Overwhelmingly this is a missing
  /// `android.speech.RecognitionService` query in the manifest (Android 11+
  /// package visibility) or no speech engine installed on the device.
  unavailable,

  /// The operator declined the microphone permission, or it isn't granted.
  permissionDenied,

  /// Initialised and listened, but nothing intelligible was heard.
  noSpeechDetected,

  /// The recognition engine reported an error mid-session.
  engineError,

  /// The operator tapped the mic again to abandon the recording. Not a
  /// failure to report back at them — they know, they did it.
  cancelled,
}

/// Outcome of one voice capture: either transcribed [text], or a [failure]
/// with an operator-facing [message]. Exactly one of the two is set.
class VoiceResult {
  final String? text;
  final VoiceFailure? failure;
  final String? message;

  const VoiceResult.success(this.text)
      : failure = null,
        message = null;
  const VoiceResult.failed(this.failure, this.message) : text = null;

  bool get ok => text != null;
}

/// On-device speech-to-text for voice requests (feature 067, US4, research
/// D7): transcribes before sending, so the wire protocol never differs
/// between a typed and a spoken request — the Border always just sees
/// `{"text": ...}` via `n2n/edge/ask` (contract's client-side-shortcuts
/// section). `listenOnce` is injectable so tests can exercise
/// `recordAndAsk`'s request-shape guarantee without a real microphone/STT
/// platform channel.
class VoiceTranscription {
  /// Hard ceiling on one recording. Reached only if the operator genuinely
  /// talks for this long — [pauseFor] ends a normal request within seconds of
  /// them stopping.
  static const listenTimeout = Duration(seconds: 30);

  /// Silence tolerated **before the operator has said anything**, i.e. how long
  /// they get to collect their thoughts after tapping the mic.
  ///
  /// Deliberately generous. Tapping a mic and being cut off before you have
  /// begun is the worst possible failure — there is nothing to salvage and no
  /// partial text to keep.
  static const initialPauseFor = Duration(seconds: 10);

  /// Silence tolerated **mid-sentence, once speech has started**, before the
  /// session is considered complete.
  ///
  /// This is the fix for the reported "mic stays hanging": `pauseFor` was unset,
  /// and `speech_to_text`'s stop check is guarded on it —
  /// `else if (null != pauseFor && _elapsedSinceSpeechEvent >= ...) _stop()` —
  /// so with it null the branch was unreachable and every session ran the full
  /// [listenTimeout] regardless of when the speaker stopped. 7.4.0 is the first
  /// release whose Android side honours `pauseFor` at all, so on earlier
  /// versions the omission was harmless; here it was the bug.
  ///
  /// **Why 5s and not 3s.** Justin (the original reporter) raised that 3s risks
  /// cutting off a slow speaker or someone pausing mid-sentence — a fair
  /// objection, and a worse failure than a slightly late stop: a truncated
  /// network request ("check BGP on…") is actively misleading, whereas an extra
  /// second of waiting is merely mild. Network operators also dictate content
  /// full of natural pauses — device names, interface IDs, IP addresses — where
  /// people hesitate mid-utterance.
  ///
  /// Also note the plugin's own caveat on this value: *"On some systems, notably
  /// Android, there is a system imposed pause of from one to three seconds that
  /// cannot be overridden."* A 3s request therefore sat right at the floor the
  /// platform might enforce anyway, leaving no headroom. 5s is comfortably
  /// clear of it while still ending a finished request promptly.
  static const pauseFor = Duration(seconds: 5);

  /// One recogniser for the whole process.
  ///
  /// `SpeechToText()` is a thin Dart wrapper over a **single** platform-side
  /// resource (`SpeechRecognizer` on Android, `SFSpeechRecognizer` on iOS).
  /// Constructing a fresh wrapper per tap — as this used to — lets
  /// `initialize()` report success while `listen()` quietly attaches to a
  /// recogniser that is still tearing down from the previous session: no
  /// audio captured and no error raised, which is the reported "sometimes it
  /// just doesn't record". Android surfaces it as `ERROR_RECOGNIZER_BUSY`
  /// when it surfaces anything at all.
  static stt.SpeechToText? _shared;
  static bool _ready = false;

  /// Completion hook for the session in flight; null while idle.
  ///
  /// `onError`/`onStatus` are registered once, at `initialize()` time, and so
  /// outlive any single recording — they have to reach the *current*
  /// completer rather than closing over a stale one.
  static void Function(VoiceResult)? _activeFinish;
  static SpeechRecognitionError? _lastError;

  final Future<VoiceResult> Function() _listenOnce;

  VoiceTranscription({Future<VoiceResult> Function()? listenOnce})
      : _listenOnce = listenOnce ?? _defaultListenOnce;

  /// Abandons the recording in flight, if any. Safe to call when idle.
  Future<void> cancel() async {
    _activeFinish?.call(const VoiceResult.failed(VoiceFailure.cancelled, null));
    final speech = _shared;
    if (speech != null && speech.isListening) await speech.cancel();
  }

  static Future<VoiceResult> _defaultListenOnce() async {
    final speech = _shared ?? stt.SpeechToText();

    if (!_ready) {
      final available = await speech.initialize(
        onError: (e) {
          _lastError = e;
          // Previously this only recorded the error. With `cancelOnError: true`
          // the session is then cancelled, so `onResult` never fires either —
          // leaving the completer orphaned and the UI frozen for the full
          // timeout on *every* mid-session error. Complete immediately.
          _activeFinish?.call(VoiceResult.failed(VoiceFailure.engineError,
              'Speech recognition failed: ${e.errorMsg}'));
        },
        onStatus: (status) {
          // A session can end cleanly having heard nothing: no final result,
          // no error. Without this the only way out was the timeout.
          // `finish` is idempotent, so a real result arriving first wins.
          if (status == stt.SpeechToText.doneStatus) {
            _activeFinish?.call(const VoiceResult.failed(
                VoiceFailure.noSpeechDetected,
                "Didn't catch that — try again."));
          }
        },
      );
      if (!available) {
        // Distinguish "you said no" from "this device can't do it at all" —
        // those need completely different responses from the operator.
        if (!await speech.hasPermission) {
          return const VoiceResult.failed(VoiceFailure.permissionDenied,
              'Microphone permission is needed for voice requests.');
        }
        final why = _lastError?.errorMsg;
        return VoiceResult.failed(
            VoiceFailure.unavailable,
            why != null
                ? 'Speech recognition unavailable: $why'
                : 'Speech recognition is unavailable on this device.');
      }
      _shared = speech;
      _ready = true;
    }

    // Reclaim the recogniser if a previous session was abandoned without
    // being stopped. Cheap when idle, and the difference between a working
    // mic and a silently dead one when not.
    if (speech.isListening) await speech.cancel();

    _lastError = null;
    final completer = Completer<VoiceResult>();
    void finish(VoiceResult r) {
      if (!completer.isCompleted) completer.complete(r);
    }

    _activeFinish = finish;
    var tightened = false;
    try {
      await speech.listen(
        onResult: (result) {
          // First sign of speech: drop from the generous [initialPauseFor] to
          // the mid-sentence [pauseFor]. This is the plugin's documented
          // pattern for exactly this — `changePauseFor` exists to allow "a long
          // first pause then dynamically shortening it once the user starts
          // speaking" — and it is why the operator can take their time starting
          // without every finished request then waiting the full initial
          // window. `isNotListening` would throw, so guard on it.
          if (!tightened && speech.isListening) {
            tightened = true;
            speech.changePauseFor(pauseFor);
          }
          // Partials are enabled below purely to drive `pauseFor` and this
          // transition; the Border still only ever sees final text, exactly as
          // a typed request does.
          if (!result.finalResult) return;
          final words = result.recognizedWords.trim();
          finish(words.isEmpty
              ? const VoiceResult.failed(VoiceFailure.noSpeechDetected,
                  "Didn't catch that — try again.")
              : VoiceResult.success(words));
        },
        listenOptions: stt.SpeechListenOptions(
          // Must be true whenever `pauseFor` is set. The plugin's own
          // convenience path coerces exactly this
          // (`partialResults: partialResults || null != pauseFor`), so an
          // explicit SpeechListenOptions pairing `pauseFor` with
          // `partialResults: false` bypasses that coercion and is an
          // untested combination. Some Android engines also skip the final
          // result entirely for very short utterances with partials off.
          // Partials additionally power the initial->mid-sentence pause
          // transition above.
          partialResults: true,
          cancelOnError: true,
          listenFor: listenTimeout,
          // Starts generous; tightened on first speech (see onResult).
          pauseFor: initialPauseFor,
          // A spoken request is a sentence ("check every core router for BGP
          // problems"), not a keyword or a command word. The default
          // `confirmation` mode tunes the engine for short phrases, which
          // biases it toward finalising early — the opposite of what a slow
          // or pausing speaker needs. iOS-only in this plugin, but correct to
          // declare regardless.
          listenMode: stt.ListenMode.dictation,
        ),
      );

      // Backstop only. `pauseFor` and `onStatus` should both beat this now;
      // it remains so that a wedged engine can never hang the mic forever.
      return await completer.future.timeout(
        listenTimeout + const Duration(seconds: 2),
        onTimeout: () {
          final why = _lastError?.errorMsg;
          return why != null
              ? VoiceResult.failed(
                  VoiceFailure.engineError, 'Speech recognition failed: $why')
              : const VoiceResult.failed(VoiceFailure.noSpeechDetected,
                  "Didn't hear anything — try again.");
        },
      );
    } finally {
      // `stop()` used to sit on the success path only, so any throw here — or
      // a dispose mid-listen — leaked a live session, which then poisoned the
      // *next* recording. That cascade is what made one deterministic hang
      // look like an intermittent fault.
      _activeFinish = null;
      if (speech.isListening) await speech.cancel();
    }
  }

  /// Records, transcribes, and sends the result through the SAME `ask()`
  /// path a typed message uses. Returns the (task_id, transcribed text)
  /// pair on success; on failure calls [onFailure] with the reason and returns
  /// null. An empty request is never sent to the Border.
  Future<(String taskId, String text)?> recordAndAsk(
    EdgeAskClient askClient, {
    void Function(VoiceResult failure)? onFailure,
  }) async {
    final result = await _listenOnce();
    if (!result.ok) {
      onFailure?.call(result);
      return null;
    }
    final text = result.text!;
    final taskId = await askClient.ask(text);
    return (taskId, text);
  }
}
