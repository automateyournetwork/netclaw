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
///
/// ## Why this is a multi-segment session, not one `listen()` call
///
/// Android's `SpeechRecognizer` is built for short commands, not dictation. It
/// decides on its own when an utterance is "possibly complete", fires
/// `onEndOfSpeech`, and emits a FINAL result — and the plugin then refuses any
/// further final for that session (`isDuplicateFinal`). Two of the extras that
/// would relax that judgement,
/// `EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS` and
/// `EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS`, are never set by the plugin, so
/// the platform defaults apply and they are short.
///
/// The observable effect, reported from a real device: counting "one, two,
/// three…" out loud, everything from ~10 onwards was silently dropped. The
/// natural gaps between spoken numbers were long enough for the engine to call
/// the utterance finished, and every word after that point went nowhere.
///
/// A single `listen()` therefore *cannot* reliably capture a paused or lengthy
/// request on Android, no matter how the timeouts are tuned. So we stop
/// treating one `listen()` as one recording: when the engine ends a segment
/// early we append its text and immediately listen again, and the recording as
/// a whole ends only when the operator says so, when a genuine silence elapses,
/// or at the hard ceiling. Segments are rejoined in order.
class VoiceTranscription {
  /// Hard ceiling on a single engine segment. **Not** the recording length —
  /// that is [maxSession].
  ///
  /// Only a backstop against a wedged engine, so it is deliberately long: when
  /// a segment hits this limit the engine is stopped and restarted, and that
  /// restart costs [restartSettle] during which speech is not being captured.
  /// A short value would therefore punch a small hole in the audio at regular
  /// intervals through any long dictation. At 4 minutes it is unreachable
  /// before [maxSession] ends the recording anyway, so in practice segments end
  /// because the engine decided to — never because of this number.
  static const listenTimeout = Duration(minutes: 4);

  /// How long the operator may stay silent before the recording is considered
  /// finished. **One** value, applied from the moment listening starts — there
  /// is deliberately no separate, longer "time to start talking" window.
  ///
  /// ## Why a two-stage pause was removed (the reported initial delay)
  ///
  /// This previously started at a generous 10s and was shortened to 5s only
  /// once speech was first detected. That is what produced the reported delay
  /// **before** speaking: on Android `pauseFor` is handed straight to the
  /// engine as `EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS` at
  /// `listen()` time, so a 10s value told the engine that ten seconds of
  /// silence was unremarkable *from the instant the mic opened*. The
  /// `changePauseFor` step meant to tighten it could only run after the first
  /// result — i.e. after the operator had already paid the wait. Intended as
  /// generosity, experienced as a wall at the front of every recording.
  ///
  /// The plugin's own example app — the reference configuration — uses a
  /// single small `pauseFor` (3s) with no staging, which is the pattern
  /// followed here.
  ///
  /// Mid-request pauses are protected by the segment-restart logic instead of
  /// by a long timeout: if the engine gives up while the operator is only
  /// pausing, the text so far is kept and listening resumes.
  ///
  /// **Why 5s and not 3s.** Justin (the original reporter) raised that 3s risks
  /// cutting off a slow speaker or someone pausing mid-sentence — a fair
  /// objection, and a worse failure than a slightly late stop: a truncated
  /// network request ("check BGP on…") is actively misleading, whereas an extra
  /// second of waiting is merely mild. Network operators also dictate content
  /// full of natural pauses — device names, interface IDs, IP addresses — where
  /// people hesitate mid-utterance.
  ///
  /// Also note the plugin's own caveat: *"On some systems, notably Android,
  /// there is a system imposed pause of from one to three seconds that cannot
  /// be overridden."* The example's 3s therefore sits right at the floor the
  /// platform may enforce anyway, leaving no headroom. 5s is comfortably clear
  /// of it while still ending a finished request promptly.
  static const pauseFor = Duration(seconds: 5);

  /// Ceiling on the whole recording, across every segment. Generous, because
  /// segments exist so that a long request survives; this only stops a
  /// recording nobody ever ended.
  static const maxSession = Duration(minutes: 2);

  /// Ask the platform to recognise speech locally rather than in the cloud.
  ///
  /// This is a **privacy commitment, not an optimisation.** The iOS permission
  /// prompt tells the operator "NetClaw Mobile transcribes your voice requests
  /// on-device before sending them", and until this flag was set that was
  /// untrue: with `onDevice` false the platform is free to ship the audio to a
  /// server. Spoken requests here carry hostnames, interface IDs and IP
  /// addresses, so the claim has to hold.
  ///
  /// Requires Android 12+ and a downloaded language pack ("Speech Recognition
  /// and Synthesis from Google"); iOS uses `requiresOnDeviceRecognition`.
  ///
  /// Two independent layers decide this, which is worth knowing when debugging:
  ///
  /// * **Recogniser choice** — the plugin checks
  ///   `isOnDeviceRecognitionAvailable` and, if that fails, constructs the
  ///   ordinary recogniser anyway. Silent, and nothing in its API reports which
  ///   one was chosen.
  /// * **Intent extra** — it also sets `EXTRA_PREFER_OFFLINE`, which makes the
  ///   engine *error* rather than reach for the network when no pack is present.
  ///
  /// So the second layer is what actually enforces the promise, and
  /// [_languageUnavailableErrors] surfaces it to the operator instead of
  /// degrading quietly to the cloud.
  ///
  /// ## Known behavioural differences of the local engine
  ///
  /// * **More aggressive silence cutoff** — local voice-activity detection lacks
  ///   the server's contextual judgement and can end an utterance after ~2-3s of
  ///   quiet, versus longer in cloud mode. It is the main reason the
  ///   segment-restart design in [_Recording] is load-bearing rather than
  ///   belt-and-braces: `pauseFor` alone cannot hold a paused speaker's session
  ///   open, because the only silence extra this plugin exposes is
  ///   `COMPLETE_SILENCE_LENGTH` — `POSSIBLY_COMPLETE_SILENCE_LENGTH` and
  ///   `MINIMUM_LENGTH`, which govern the early cutoff, are not settable from
  ///   Dart at all.
  /// * **No hard stream cap** — unlike the cloud API's 5-minute streaming limit,
  ///   local recognition runs as long as memory allows, so [maxSession] is our
  ///   own bound rather than a platform one.
  /// * **Near-zero latency** — no round trip, so results land as spoken.
  /// * **Weaker on proper nouns** — compressed models struggle with jargon and
  ///   names, which is most of what gets dictated here (`Gi0/0/1`,
  ///   `core-rtr-01`). If accuracy on device names regresses noticeably, this
  ///   flag is the first thing to reconsider — but that must be a deliberate
  ///   decision taken together with the wording of the permission strings, not
  ///   a silent default.
  /// * **Worse in noise** — no server-side acoustic filtering.
  static const preferOnDevice = true;

  /// How long to wait after a deliberate stop for the engine to deliver the
  /// final text of the segment in flight.
  ///
  /// Must exceed the plugin's own `finalTimeout` (default **2000ms**): after
  /// `stop()` it schedules `_notifyFinalTimer` for that long before promoting
  /// the last partial to a final result. Settling sooner races that timer and
  /// silently drops the tail of the request.
  static const settleWindow = Duration(milliseconds: 2600);

  /// Pause between one engine segment ending and the next beginning.
  ///
  /// Android's `SpeechRecognizer` — Google's implementation especially — needs a
  /// moment to tear down before it will accept `startListening` again;
  /// restarting immediately is the classic way to earn `ERROR_RECOGNIZER_BUSY`,
  /// which presents as a mic that looks live and records nothing.
  ///
  /// It also bounds the failure mode where an engine errors instantly on every
  /// attempt: without a gap that becomes a tight restart loop for as long as the
  /// recording lasts. Short enough to be imperceptible mid-sentence.
  static const restartSettle = Duration(milliseconds: 250);

  /// How long to keep an OPEN mic waiting when the operator has said nothing at
  /// all, before giving up with "didn't hear anything".
  ///
  /// This is **not** a delay the operator waits through: the microphone is live
  /// and accepting speech for this entire period, so talking at any point
  /// during it is captured immediately. It only decides when to abandon a
  /// recording that never heard a word. Measured locally and never handed to
  /// the platform — handing a large silence window to the engine is exactly
  /// what created the reported delay before speaking.
  static const noSpeechGiveUp = Duration(seconds: 10);

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

  /// Live handle on the recording in flight; null while idle. Registered once
  /// at `initialize()` time, `onError`/`onStatus` outlive any single segment
  /// and so must reach the *current* recording rather than a stale closure.
  static _Recording? _active;
  static SpeechRecognitionError? _lastError;

  /// Engine errors that mean "this segment found nothing", not "recording
  /// failed". Names as emitted by the plugin's Android layer.
  static const _transientErrors = {
    'error_no_match',
    'error_speech_timeout',
  };

  /// Errors that mean the requested on-device language is not installed.
  ///
  /// `EXTRA_PREFER_OFFLINE` makes the engine fail rather than quietly reach for
  /// the network when no pack is present, so these are the signal that
  /// [preferOnDevice] cannot be honoured on this device/locale.
  ///
  /// Deliberately **not** retried against the cloud. Falling back silently would
  /// break the on-device promise made in the permission prompt at exactly the
  /// moment the operator has no idea it happened; better to say so and let them
  /// choose.
  static const _languageUnavailableErrors = {
    'error_language_unavailable',
    'error_language_not_supported',
  };

  final Future<VoiceResult> Function() _listenOnce;

  VoiceTranscription({Future<VoiceResult> Function()? listenOnce})
      : _listenOnce = listenOnce ?? _defaultListenOnce;

  /// Whether a recording is currently in flight.
  static bool get isRecording => _active != null;

  /// Ends the recording in flight and KEEPS what was said. Safe when idle.
  ///
  /// This is what a "Done" control must call. Distinct from [cancel] — the two
  /// were previously the same button, which meant an operator who finished
  /// speaking and tapped stop silently lost their whole request.
  Future<void> finishNow() async {
    final rec = _active;
    if (rec == null) return;
    rec.stopRequested = true;
    final speech = _shared;
    // `stop()` (not `cancel()`) so the engine still delivers the final text of
    // the segment in flight; `cancel()` documents that it will not.
    if (speech != null && speech.isListening) {
      await speech.stop();
      // Only wait for a trailing final result when one can actually be coming.
      rec.settleSoon();
    } else {
      // Mic already closed (e.g. between segments): nothing further will
      // arrive, so don't make the operator wait out the settle window.
      rec.finishWithTranscript();
    }
  }

  /// Abandons the recording in flight and DISCARDS it. Safe when idle.
  Future<void> cancel() async {
    final rec = _active;
    rec?.stopRequested = true;
    rec?.finish(const VoiceResult.failed(VoiceFailure.cancelled, null));
    final speech = _shared;
    if (speech != null && speech.isListening) await speech.cancel();
  }

  static Future<VoiceResult> _defaultListenOnce() async {
    final speech = _shared ?? stt.SpeechToText();

    if (!_ready) {
      final available = await speech.initialize(
        onError: (e) {
          _lastError = e;
          // Android raises these constantly during ordinary dictation: they
          // fire whenever a segment ends without a confident match, which for
          // someone pausing mid-sentence is routine rather than a fault.
          // Treating them as fatal is what turned "you paused" into "voice
          // request failed", so they only end a segment and we listen again.
          //
          // Checked by NAME, not by `e.permanent`: the plugin's Android side
          // hardcodes `permanent = true` on every error it sends
          // (`sendError()` — `speechError.put("permanent", true)`), so a
          // permanence check is dead code on this platform and would let these
          // kill the recording.
          if (_languageUnavailableErrors.contains(e.errorMsg)) {
            _active?.finish(const VoiceResult.failed(
                VoiceFailure.unavailable,
                'On-device speech needs a language pack. Install it in '
                'Settings → Offline speech recognition, then try again.'));
            return;
          }
          if (_transientErrors.contains(e.errorMsg)) {
            // End the segment HERE rather than waiting for `onStatus(done)`.
            // The Android layer only emits `done` via `notifyListening(false)`,
            // which early-returns when it already believes it is not listening
            // — so after an error `done` may never arrive. Relying on it left
            // the recording stranded with a dead mic and the operator cut off
            // mid-request. `segmentEnded` is idempotent, so the usual case where
            // `done` does follow is harmless. No generation is passed: an error
            // always refers to whatever segment is live when it fires.
            _active?.segmentEnded();
            return;
          }
          _active?.finish(VoiceResult.failed(VoiceFailure.engineError,
              'Speech recognition failed: ${e.errorMsg}'));
        },
        onStatus: (status) {
          // A segment ended. NOT necessarily the recording: on Android this is
          // exactly the premature `onEndOfSpeech` that used to truncate a long
          // request. Hand it to the recording to decide whether to continue.
          if (status == stt.SpeechToText.doneStatus) {
            // `trusted: false` — this callback carries no segment identity, so
            // it may be a straggler from a segment already replaced.
            _active?.segmentEnded(trusted: false);
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

    // Reclaim the recogniser if a previous recording was abandoned without
    // being stopped — e.g. the screen was disposed mid-listen. Cheap when
    // idle, and the difference between a working mic and a silently dead one
    // when not.
    if (speech.isListening) await speech.cancel();

    _lastError = null;
    final rec = _Recording(speech);
    _active = rec;
    try {
      return await rec.run();
    } catch (e) {
      // `listen()` can throw (e.g. ListenFailedException) rather than reporting
      // through onError. Surface it as a normal failure so the caller shows a
      // message; letting it escape would put an unhandled exception on the UI
      // and leave the operator with the silent no-op this all replaced.
      return VoiceResult.failed(
          VoiceFailure.engineError, 'Speech recognition failed: $e');
    } finally {
      _active = null;
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

/// One recording: a sequence of engine segments accumulated into a single
/// transcript.
///
/// Exists because on Android one `listen()` is not one recording (see
/// [VoiceTranscription]'s class comment). All the "when does this end"
/// judgement lives here, on our own clock, rather than being delegated to a
/// platform whose idea of "finished" is tuned for voice commands.
class _Recording {
  /// How many consecutive text-free segments before giving up. Enough to ride
  /// out an isolated engine hiccup, few enough that a dead recogniser reports
  /// back in seconds rather than minutes.
  static const _maxEmptySegments = 8;

  final stt.SpeechToText _speech;

  _Recording(this._speech);

  final _completer = Completer<VoiceResult>();
  final _segments = <String>[];

  /// Text of the segment in flight, superseded on every partial.
  String _current = '';

  final _startedAt = DateTime.now();
  DateTime _lastSpeechAt = DateTime.now();
  bool _heardAnything = false;

  /// True once the end of the current segment is being handled, cleared when a
  /// fresh segment is listening.
  ///
  /// A segment's end can be signalled twice — `onResult(finalResult)` and
  /// `onStatus(done)` — or, on Android, by only one of them:
  ///
  /// * `_onNotifyStatus` drops `done` when `_latestResultType` is still partial,
  ///   so a segment that produced only partials never reports `done`.
  /// * the Android layer's `notifyListening` early-returns when it already
  ///   believes it is not listening, so `done` can be skipped after an error.
  ///
  /// Waiting only on `done` therefore risks never resuming (the operator is cut
  /// off), while acting on both risks restarting twice and tearing down a live
  /// segment. This flag makes whichever signal arrives first the one that acts,
  /// exactly once.
  bool _segmentEnding = false;

  /// Increments every time a new segment starts listening.
  ///
  /// Callbacks are registered once for the whole process, so a late
  /// `onStatus(done)` or error belonging to a segment we have already replaced
  /// can arrive *after* its successor is live. Acting on it would bank an empty
  /// segment and tear down a healthy microphone — cutting the operator off
  /// mid-word, the very fault this class exists to prevent. Callbacks therefore
  /// carry the generation they were issued for and stale ones are ignored.
  int _generation = 0;

  /// Generation whose end is currently being handled, paired with
  /// [_segmentEnding].
  int _endingGeneration = -1;

  /// When the segment currently listening began.
  ///
  /// Used to reject an implausibly early `onStatus(done)`. That callback is
  /// registered once for the whole process and carries no segment identity, so
  /// unlike `onResult` it cannot be generation-checked. A `done` arriving within
  /// [_minSegmentLife] of a segment opening is therefore taken to be a
  /// straggler from the previous one: a real segment must have listened and then
  /// timed out, which takes far longer.
  ///
  /// This is a heuristic, and the only one here. It is safe in the direction
  /// that matters: a wrongly ignored `done` costs nothing, because `onResult`
  /// and the error path both also end segments, and the silence clock still
  /// ends the recording. A wrongly *accepted* one would tear down a live
  /// microphone mid-word.
  DateTime _segmentStartedAt = DateTime.now();

  static const _minSegmentLife = Duration(milliseconds: 600);

  /// Consecutive segments that ended without producing any text.
  ///
  /// Bounds a genuinely broken engine. If `listen()` succeeds but the engine
  /// errors immediately, the cycle is: error → end segment → restart → error.
  /// The silence clock cannot stop that (it is paused while the mic is closed,
  /// and rebased each time a segment opens), so without a counter the only
  /// backstop is [VoiceTranscription.maxSession] — two minutes of churn before
  /// the operator is told anything. A speaker who is merely pausing always
  /// resets this, because their segments produce text.
  int _emptySegments = 0;

  /// True while a restart is in flight, i.e. the microphone is closed.
  ///
  /// The silence clock must not run during this window. A restart costs
  /// [VoiceTranscription.restartSettle] plus however long the platform takes to
  /// hand the mic back, and counting that as the operator being quiet would let
  /// a long or repeated restart end the recording while they are still talking.
  bool _micClosed = false;

  /// Set once the operator has asked to end the recording; suppresses any
  /// further restart so a deliberate stop is never overridden.
  bool stopRequested = false;

  bool _restarting = false;
  Timer? _settle;

  /// Everything heard so far, segments rejoined in order. This is the value
  /// that fixes the reported truncation: text the engine finalised early is
  /// kept and the later words are appended to it, instead of the later words
  /// replacing nothing and vanishing.
  String get transcript =>
      [..._segments, _current].where((s) => s.trim().isNotEmpty).join(' ').trim();

  void finish(VoiceResult r) {
    _settle?.cancel();
    if (!_completer.isCompleted) _completer.complete(r);
  }

  /// Completes with whatever has been heard, or reports silence if nothing was.
  void finishWithTranscript() {
    final words = transcript;
    finish(words.isEmpty
        ? const VoiceResult.failed(
            VoiceFailure.noSpeechDetected, "Didn't catch that — try again.")
        : VoiceResult.success(words));
  }

  /// Wait [VoiceTranscription.settleWindow] for the engine to deliver the final
  /// text of the segment in flight, so a deliberate "Done" never truncates the
  /// last words.
  void settleSoon() {
    _settle?.cancel();
    _settle = Timer(VoiceTranscription.settleWindow, finishWithTranscript);
  }

  Future<VoiceResult> run() async {
    await _listenSegment();

    // Our own clock decides when the recording is over, so neither Android's
    // premature "utterance complete" nor its post-speech delay can end it for
    // us. Polled rather than scheduled because the deadline moves every time
    // the operator speaks.
    final ticker =
        Timer.periodic(const Duration(milliseconds: 250), (_) => _tick());
    try {
      return await _completer.future;
    } finally {
      ticker.cancel();
      _settle?.cancel();
    }
  }

  void _tick() {
    if (_completer.isCompleted) return;
    final now = DateTime.now();

    if (now.difference(_startedAt) >= VoiceTranscription.maxSession) {
      finishWithTranscript();
      return;
    }

    // Never judge silence while the mic is shut for a restart — that is our
    // downtime, not theirs.
    if (_micClosed) return;

    final silence = now.difference(_lastSpeechAt);
    if (_heardAnything) {
      // Spoken, then quiet for the mid-request window: they're done.
      if (silence >= VoiceTranscription.pauseFor) finishWithTranscript();
    } else {
      // Nothing heard yet. The mic is OPEN throughout this window — speech at
      // any moment is captured at once — so it costs the operator no waiting;
      // it only bounds how long a silent recording stays open. Measured here
      // rather than handed to the platform, which is the distinction that
      // removes the reported delay before speaking.
      if (silence >= VoiceTranscription.noSpeechGiveUp) {
        finish(const VoiceResult.failed(
            VoiceFailure.noSpeechDetected, "Didn't hear anything — try again."));
      }
    }
  }

  /// Banks the segment in flight, if any. Idempotent: `onResult(final)` and
  /// `onStatus(done)` both arrive for a normal segment, and double-banking would
  /// duplicate the operator's words in the request.
  void _bankCurrent() {
    final words = _current.trim();
    _current = '';
    if (words.isNotEmpty) {
      _segments.add(words);
      _emptySegments = 0;
    } else {
      _emptySegments++;
    }
  }

  /// The engine ended a segment. Bank its text and, unless the recording is
  /// genuinely over, listen again so the operator can keep talking.
  ///
  /// Idempotent per segment — see [_segmentEnding].
  ///
  /// [generation] is the segment the signal belongs to; omit it only for
  /// signals that genuinely refer to whatever is current.
  void segmentEnded({int? generation, bool trusted = true}) {
    if (_completer.isCompleted) return;
    // Ignore a signal from a segment that has already been replaced.
    if (generation != null && generation != _generation) return;
    // Untrusted signal (`onStatus`, which carries no segment identity) that
    // cannot plausibly belong to the segment now listening — see
    // [_segmentStartedAt]. Errors are trusted: they always refer to the live
    // segment, and delaying them would leave a broken engine spinning.
    if (!trusted &&
        DateTime.now().difference(_segmentStartedAt) < _minSegmentLife) {
      return;
    }
    if (_segmentEnding && _endingGeneration == _generation) return;
    _segmentEnding = true;
    _endingGeneration = _generation;
    _bankCurrent();
    if (stopRequested) {
      finishWithTranscript();
      return;
    }
    // A broken engine, not a pausing speaker — stop churning and say so.
    if (_emptySegments >= _maxEmptySegments) {
      finishWithTranscript();
      return;
    }
    // Deliberately does NOT finish on silence here — that is [_tick]'s job, on
    // our clock. A segment ending is not evidence the operator has finished;
    // on Android it is usually just the engine being impatient.
    _restart();
  }

  Future<void> _restart() async {
    if (_restarting || _completer.isCompleted || stopRequested) return;
    _restarting = true;
    _micClosed = true;
    try {
      if (_speech.isListening) await _speech.cancel();
      // Let the platform recogniser settle before asking it to start again —
      // see [VoiceTranscription.restartSettle].
      await Future<void>.delayed(VoiceTranscription.restartSettle);
      if (_completer.isCompleted || stopRequested) return;
      // Bump BEFORE listening so the new segment's callbacks capture the new
      // generation and any straggler from the old one is recognised as stale.
      _generation++;
      _segmentEnding = false;
      // Don't penalise the operator for the gap we just introduced: treat the
      // reopened mic as a fresh silence baseline.
      _lastSpeechAt = DateTime.now();
      _segmentStartedAt = DateTime.now();
      await _listenSegment();
    } catch (e) {
      // A failed restart is not automatically fatal: if we already have text,
      // returning it beats discarding the request.
      if (!_completer.isCompleted) {
        if (transcript.isNotEmpty) {
          finishWithTranscript();
        } else {
          finish(VoiceResult.failed(
              VoiceFailure.engineError, 'Speech recognition failed: $e'));
        }
      }
    } finally {
      _restarting = false;
      _micClosed = false;
    }
  }

  Future<void> _listenSegment() async {
    // Captured by the callbacks below so a late signal can be recognised as
    // belonging to this segment rather than a successor.
    final generation = _generation;
    await _speech.listen(
      onResult: (result) {
        if (generation != _generation) return; // stale segment
        _lastSpeechAt = DateTime.now();
        final words = result.recognizedWords.trim();
        if (words.isNotEmpty) _heardAnything = true;
        _current = words;
        if (!result.finalResult) return;
        // A final result ends this segment, not necessarily the recording.
        // `onStatus(done)` normally follows and drives continuation via
        // [segmentEnded]; banking here too keeps us correct if it doesn't
        // arrive. [_bankCurrent] is idempotent so the usual both-fire case does
        // not duplicate the text.
        // Act on the final result directly rather than waiting for
        // `onStatus(done)`, which Android does not guarantee (see
        // [_segmentEnding]). Handles the stopping case too: we now have the
        // final text, so there is nothing left to wait for.
        segmentEnded(generation: generation);
      },
      listenOptions: stt.SpeechListenOptions(
        // Required whenever `pauseFor` is set — the plugin's own convenience
        // path coerces exactly this (`partialResults: partialResults || null !=
        // pauseFor`). Also the only proof-of-life the UI can show, and what
        // keeps [_lastSpeechAt] current so our clock doesn't cut off a speaker
        // mid-sentence.
        partialResults: true,
        // Transient errors (ERROR_NO_MATCH / ERROR_SPEECH_TIMEOUT) are routine
        // for a pausing speaker. Cancelling the session on them tore down the
        // recogniser underneath us mid-request; the error handler now ignores
        // non-permanent errors and we let the segment end naturally instead.
        cancelOnError: false,
        listenFor: VoiceTranscription.listenTimeout,
        // The MID-REQUEST value, never the generous opening one. On Android
        // this becomes both EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS
        // and the `onEndOfSpeech` delay, so a large value here is felt directly
        // as dead time after the operator stops talking.
        pauseFor: VoiceTranscription.pauseFor,
        // A spoken request is a sentence ("check every core router for BGP
        // problems"), not a keyword. The default `confirmation` mode tunes the
        // engine for short phrases, biasing it toward finalising early — the
        // opposite of what a slow or pausing speaker needs. iOS-only in this
        // plugin, but correct to declare regardless.
        listenMode: stt.ListenMode.dictation,
        // Keep the operator's voice on the device. See
        // [VoiceTranscription.preferOnDevice] for why this is a privacy
        // requirement here and not merely a preference.
        onDevice: VoiceTranscription.preferOnDevice,
      ),
    );
  }
}
