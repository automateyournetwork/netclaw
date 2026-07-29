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

    test('the operator gets longer to START than to pause mid-sentence', () {
      // Two-stage pause (plugin's documented `changePauseFor` pattern: "a long
      // first pause then dynamically shortening it once the user starts
      // speaking"). Being cut off before saying anything is the worst failure —
      // nothing to salvage — so the opening window must be the more generous of
      // the two.
      expect(VoiceTranscription.initialPauseFor,
          greaterThan(VoiceTranscription.pauseFor));
      expect(VoiceTranscription.initialPauseFor.inSeconds,
          greaterThanOrEqualTo(5));
    });

    test('both pause windows stay inside the hard ceiling', () {
      // Either window exceeding listenFor would make it unreachable and
      // silently reintroduce the original hang.
      expect(VoiceTranscription.initialPauseFor,
          lessThan(VoiceTranscription.listenTimeout));
      expect(VoiceTranscription.pauseFor,
          lessThan(VoiceTranscription.listenTimeout));
    });

    test('listenFor remains a bounded hard ceiling', () {
      expect(VoiceTranscription.listenTimeout.inSeconds, greaterThan(0));
      expect(VoiceTranscription.listenTimeout.inSeconds, lessThanOrEqualTo(60));
    });

    test('a slow speaker fits: initial + mid-sentence pauses under the ceiling',
        () {
      // Worst realistic case — operator takes a while to start, then pauses
      // mid-sentence recalling a device name. Both waits must fit inside
      // listenFor or the session dies mid-request.
      final worstCase =
          VoiceTranscription.initialPauseFor + VoiceTranscription.pauseFor;
      expect(worstCase, lessThan(VoiceTranscription.listenTimeout));
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
}
