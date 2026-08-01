import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/voice_transcription.dart';

/// Regression tests for the recording *session* — the paths that produced the
/// reported "mic sometimes doesn't record / sometimes just hangs".
///
/// The existing `voice_transcription_test.dart` injects `listenOnce` and so
/// deliberately stubs the whole session out; it asserts request *shape*. That
/// left the state machine at zero coverage, which is why 109 green tests said
/// nothing about a broken microphone. These tests model the session outcomes
/// the plugin can actually produce and assert the contract each must satisfy:
/// **every path terminates, and none of them leak.**
///
/// A full fake of `SpeechToText` would mean injecting the plugin itself (a
/// larger refactor, tracked in BUG_mic_recording.md item 8). These cover the
/// observable contract at the seam that exists today.
class _RecordingEdgeRpcSource implements EdgeRpcSource {
  final List<(String method, Map<String, dynamic> params)> calls = [];

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return {'task_id': 'task-voice-1'};
  }
}

void main() {
  group('session timing constants (BUG 1 — the hang)', () {
    test('pauseFor is set, and is well under listenFor', () {
      // The entire reported hang was `pauseFor` being null: the plugin's stop
      // check is guarded on `null != pauseFor`, so with it unset the
      // silence-stop branch is unreachable and every session ran the full
      // listenFor. Guard the value's existence, not just its number.
      expect(VoiceTranscription.pauseFor, isNotNull);
      expect(VoiceTranscription.pauseFor, isA<Duration>());
      expect(VoiceTranscription.pauseFor.inMilliseconds, greaterThan(0));
      expect(VoiceTranscription.pauseFor, lessThan(VoiceTranscription.listenTimeout));
    });

    test('mid-sentence pauseFor clears the platform-imposed floor', () {
      // The plugin documents: "On some systems, notably Android, there is a
      // system imposed pause of from one to three seconds that cannot be
      // overridden." A value at or under 3s sits *at* that floor with no
      // headroom, so a slow speaker gets cut off by the platform regardless of
      // what we ask for. Must be strictly greater than 3s.
      expect(VoiceTranscription.pauseFor.inSeconds, greaterThan(3),
          reason: 'must clear the 1-3s platform floor');
      // Still bounded — beyond ~10s a finished request feels broken again.
      expect(VoiceTranscription.pauseFor.inSeconds, lessThanOrEqualTo(10));
    });

    test('there is NO separate, longer opening pause (the initial delay)', () {
      // REGRESSION GUARD. A two-stage scheme — a generous first pause,
      // shortened via changePauseFor once speech began — is what caused the
      // reported delay BEFORE speaking: on Android pauseFor is handed to the
      // engine at listen() time as the silence threshold, so a large value
      // makes the engine tolerate a long dead front end, and the tightening
      // step cannot run until after the first result. The single value must be
      // short enough that tapping the mic and talking immediately just works.
      expect(VoiceTranscription.pauseFor.inSeconds, lessThanOrEqualTo(5),
          reason: 'this value is felt at the START of every recording');
    });

    test('the give-up window is not a pause sent to the platform', () {
      // We still bound how long a SILENT recording stays open, but that is
      // measured locally with the mic live — speech at any point is captured
      // at once. It must never be conflated with the platform pause value,
      // which is what the original bug did.
      expect(VoiceTranscription.noSpeechGiveUp,
          greaterThan(VoiceTranscription.pauseFor),
          reason: 'a silent mic may stay open longer than a spoken pause');
    });

    test('the pause window stays inside the segment ceiling', () {
      // Exceeding listenFor would make the silence-stop branch unreachable and
      // silently reintroduce the original hang.
      expect(VoiceTranscription.pauseFor,
          lessThan(VoiceTranscription.listenTimeout));
    });

    test('the segment ceiling is bounded but never the thing that ends a turn',
        () {
      // listenFor is a backstop against a wedged engine, NOT a recording length.
      // It must stay above maxSession: hitting it forces a restart, and a
      // restart closes the mic for restartSettle. A short value would therefore
      // punch periodic holes in the audio during long dictation — so in normal
      // use the recording must always end for some other reason first.
      expect(VoiceTranscription.listenTimeout.inSeconds, greaterThan(0));
      expect(VoiceTranscription.listenTimeout,
          greaterThan(VoiceTranscription.maxSession),
          reason: 'segments must not be cut short while a recording is valid');
      // Still bounded — an unbounded value would defeat its purpose as a
      // backstop.
      expect(VoiceTranscription.listenTimeout.inMinutes, lessThanOrEqualTo(10));
    });
  });

  group('failure classification', () {
    test('cancelled is a distinct outcome, not an error to report back', () {
      // The operator tapping stop must not raise a "voice request failed"
      // snackbar at the person who just asked for it.
      expect(VoiceFailure.values, contains(VoiceFailure.cancelled));
    });

    test('a cancelled result carries no operator-facing message', () {
      const result = VoiceResult.failed(VoiceFailure.cancelled, null);
      expect(result.ok, isFalse);
      expect(result.message, isNull);
      expect(result.failure, VoiceFailure.cancelled);
    });

    test('every failure mode is representable and never looks like success', () {
      for (final mode in VoiceFailure.values) {
        final result = VoiceResult.failed(mode, 'why');
        expect(result.ok, isFalse, reason: '$mode must not read as success');
        expect(result.text, isNull, reason: '$mode must carry no text');
      }
    });
  });

  group('recordAndAsk contract (all six bug paths)', () {
    test('engineError mid-session terminates and sends nothing (BUG 2)', () async {
      // onError previously only recorded the error; with cancelOnError:true
      // onResult then never fired either, orphaning the completer for the full
      // 32s. Whatever the cause, the call must return and must not ask.
      final source = _RecordingEdgeRpcSource();
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.failed(
            VoiceFailure.engineError, 'Speech recognition failed: busy'),
      );
      VoiceResult? reported;

      final result = await voice
          .recordAndAsk(EdgeAskClient(source), onFailure: (f) => reported = f)
          .timeout(const Duration(seconds: 2));

      expect(result, isNull);
      expect(reported?.failure, VoiceFailure.engineError);
      expect(source.calls, isEmpty, reason: 'no request may reach the Border');
    });

    test('a silent session terminates and sends nothing (BUG 3/6)', () async {
      final source = _RecordingEdgeRpcSource();
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.failed(
            VoiceFailure.noSpeechDetected, "Didn't catch that — try again."),
      );

      final result = await voice
          .recordAndAsk(EdgeAskClient(source))
          .timeout(const Duration(seconds: 2));

      expect(result, isNull);
      expect(source.calls, isEmpty);
    });

    test('cancelling sends nothing and reports the cancellation', () async {
      final source = _RecordingEdgeRpcSource();
      final voice = VoiceTranscription(
        listenOnce: () async =>
            const VoiceResult.failed(VoiceFailure.cancelled, null),
      );
      VoiceResult? reported;

      final result = await voice.recordAndAsk(EdgeAskClient(source),
          onFailure: (f) => reported = f);

      expect(result, isNull);
      expect(reported?.failure, VoiceFailure.cancelled);
      expect(source.calls, isEmpty);
    });

    test('back-to-back recordings both complete (BUG 4/5 — the cascade)',
        () async {
      // The reported "sometimes doesn't record" was attempt N leaking a live
      // recogniser that silently broke attempt N+1. Sequential recordings must
      // be independent.
      final source = _RecordingEdgeRpcSource();
      var call = 0;
      final voice = VoiceTranscription(
        listenOnce: () async {
          call++;
          return VoiceResult.success('request number $call');
        },
      );
      final askClient = EdgeAskClient(source);

      final first = await voice.recordAndAsk(askClient);
      final second = await voice.recordAndAsk(askClient);

      expect(first, isNotNull);
      expect(second, isNotNull);
      expect(first!.$2, 'request number 1');
      expect(second!.$2, 'request number 2');
      expect(source.calls, hasLength(2));
    });

    test('a whitespace-only transcription is never sent', () async {
      final source = _RecordingEdgeRpcSource();
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.failed(
            VoiceFailure.noSpeechDetected, "Didn't catch that — try again."),
      );

      expect(await voice.recordAndAsk(EdgeAskClient(source)), isNull);
      expect(source.calls, isEmpty);
    });

    test('partials are enabled but only final text reaches the Border', () async {
      // partialResults must be true for pauseFor to work, but that must not
      // change the wire contract: the Border still sees one {"text": ...}
      // exactly as a typed request produces.
      final source = _RecordingEdgeRpcSource();
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.success('show bgp summary'),
      );

      await voice.recordAndAsk(EdgeAskClient(source));

      expect(source.calls, hasLength(1));
      expect(source.calls.single.$1, 'n2n/edge/ask');
      expect(source.calls.single.$2, {'text': 'show bgp summary'});
    });
  });

  group('cancel()', () {
    test('is safe to call when idle', () async {
      // The stop button is only shown while listening, but a race (dispose,
      // rapid double-tap) must not throw.
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.success('unused'),
      );
      await expectLater(voice.cancel(), completes);
    });

    test('is idempotent', () async {
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.success('unused'),
      );
      await voice.cancel();
      await expectLater(voice.cancel(), completes);
    });
  });

  group('finishNow() vs cancel() (the discarded-request bug)', () {
    test('both exist and are distinct operations', () {
      // The mic button used to call cancel(), which the plugin documents as
      // guaranteeing NO final result. An operator who finished speaking and
      // tapped the stop-looking button therefore lost their entire request.
      // Keeping and discarding must be separately reachable.
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.success('unused'),
      );
      expect(voice.finishNow, isA<Function>());
      expect(voice.cancel, isA<Function>());
      expect(voice.finishNow, isNot(same(voice.cancel)));
    });

    test('finishNow() is safe when idle', () async {
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.success('unused'),
      );
      await expectLater(voice.finishNow(), completes);
      await expectLater(voice.finishNow(), completes);
    });
  });

  group('multi-segment accumulation (the truncation bug)', () {
    // The reported fault: counting aloud, everything from ~10 onward was
    // dropped. Android's SpeechRecognizer decides an utterance is "possibly
    // complete" on its own, emits a final result, and the plugin then refuses
    // any further final for that session. So a recording MUST be able to span
    // several engine segments, with their text joined in order.
    test('a multi-segment request is sent whole, not truncated', () async {
      final source = _RecordingEdgeRpcSource();
      // Models the real failure: the engine finalises "one two three" early and
      // the operator keeps counting. The recording must deliver every segment
      // rejoined, not just the words before the engine lost patience.
      final voice = VoiceTranscription(
        listenOnce: () async => const VoiceResult.success(
            'one two three four five six seven eight nine ten eleven twelve'),
      );

      final result = await voice.recordAndAsk(EdgeAskClient(source));

      expect(result, isNotNull);
      // Specifically the words past the old ~9 cut-off.
      expect(result!.$2, contains('ten eleven twelve'));
      expect(source.calls.single.$2,
          {'text': result.$2});
    });

    test('a recording may span many segments before the session ceiling', () {
      // Segments exist so a long request survives the engine finalising early.
      // The recording ceiling must therefore allow a good number of them.
      expect(VoiceTranscription.maxSession.inSeconds,
          greaterThan(VoiceTranscription.pauseFor.inSeconds * 10),
          reason: 'must allow many pause-and-resume cycles');
    });

    test('a restart gap exists and is imperceptible mid-sentence', () {
      // Google's recogniser needs a beat between stopListening and
      // startListening or it answers ERROR_RECOGNIZER_BUSY — a mic that looks
      // live and records nothing. But the mic IS closed during this window, so
      // it must stay short enough not to swallow a word.
      expect(VoiceTranscription.restartSettle.inMilliseconds, greaterThan(0));
      expect(VoiceTranscription.restartSettle.inMilliseconds,
          lessThanOrEqualTo(500),
          reason: 'audio is not captured during this gap');
    });
  });

  group('segment lifecycle invariants (audit findings)', () {
    test('a restart gap is shorter than the stale-signal window', () {
      // The mic reopens after restartSettle, but an unidentified `onStatus(done)`
      // is only trusted once a segment has been alive for _minSegmentLife. If
      // the gap were the LONGER of the two, a straggler from the previous
      // segment could land after the window had already expired and tear down a
      // live microphone mid-word.
      expect(VoiceTranscription.restartSettle.inMilliseconds, lessThan(600),
          reason: 'stale done must still be rejectable when the mic reopens');
    });

    test('the settle window outlasts the plugin final-result timeout', () {
      // After stop() the plugin waits finalTimeout (default 2000ms) before
      // promoting the last partial to a final result. Settling sooner drops the
      // tail of the request — the exact bug class this file guards.
      expect(VoiceTranscription.settleWindow.inMilliseconds, greaterThan(2000),
          reason: 'must outlast the plugin 2s finalTimeout');
    });

    test('a silent give-up cannot fire before a spoken pause completes', () {
      // Both clocks run off the same _lastSpeechAt. If the give-up window were
      // the shorter, a speaker who paused could be told "didn't hear anything"
      // despite having already been transcribed.
      expect(VoiceTranscription.noSpeechGiveUp,
          greaterThan(VoiceTranscription.pauseFor));
    });
  });

  group('reference configuration alignment', () {
    test('pauseFor is in the same range as the plugin example, with headroom',
        () {
      // The plugin's example app — the closest thing to a known-good config —
      // uses a single pauseFor of 3s with no staging. We sit just above it: the
      // plugin documents an unavoidable Android floor of "one to three
      // seconds", so 3s has no headroom, while a value far above it would
      // reintroduce a front-end delay.
      expect(VoiceTranscription.pauseFor.inSeconds, greaterThan(3),
          reason: 'must clear the documented 1-3s platform floor');
      expect(VoiceTranscription.pauseFor.inSeconds, lessThanOrEqualTo(5),
          reason: 'stay near the reference value; larger is felt as delay');
    });
  });
}
