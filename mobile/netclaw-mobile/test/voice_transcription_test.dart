import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/voice_transcription.dart';

/// Records every `call()` NCFED method + params — lets the test assert the
/// exact request shape a voice input produces, without a real microphone/STT
/// platform channel (T020: this is not a speech-recognition-accuracy test).
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
  test('a transcribed voice input produces the exact same request shape a typed one would',
      () async {
    final source = _RecordingEdgeRpcSource();
    final askClient = EdgeAskClient(source);
    final voice = VoiceTranscription(
      listenOnce: () async =>
          const VoiceResult.success('check every core router for BGP problems'),
    );

    final result = await voice.recordAndAsk(askClient);

    expect(result, isNotNull);
    final (taskId, text) = result!;
    expect(taskId, 'task-voice-1');
    expect(text, 'check every core router for BGP problems');
    expect(source.calls, hasLength(1));
    expect(source.calls.single.$1, 'n2n/edge/ask');
    // The exact request shape a typed message produces via
    // EdgeAskClient.ask() -- {"text": ...}, nothing voice-specific.
    expect(source.calls.single.$2, {'text': 'check every core router for BGP problems'});
  });

  test('nothing heard never sends an empty (or any) request', () async {
    final source = _RecordingEdgeRpcSource();
    final askClient = EdgeAskClient(source);
    final voice = VoiceTranscription(
      listenOnce: () async => const VoiceResult.failed(
          VoiceFailure.noSpeechDetected, "Didn't hear anything — try again."),
    );

    final result = await voice.recordAndAsk(askClient);

    expect(result, isNull);
    expect(source.calls, isEmpty);
  });

  // Every one of these used to collapse into a bare `null`, so the mic button
  // did nothing at all and the operator had no idea why — reported by a real
  // tester as simply "microphone option isn't working". Each failure mode must
  // now surface a distinct, actionable reason.
  group('failure reporting', () {
    for (final (failure, label) in [
      (VoiceFailure.permissionDenied, 'permission denied'),
      (VoiceFailure.unavailable, 'no recognition engine'),
      (VoiceFailure.noSpeechDetected, 'silence'),
      (VoiceFailure.engineError, 'engine error'),
    ]) {
      test('$label is reported to the caller, and sends nothing', () async {
        final source = _RecordingEdgeRpcSource();
        final askClient = EdgeAskClient(source);
        final voice = VoiceTranscription(
          listenOnce: () async => VoiceResult.failed(failure, 'because $label'),
        );

        final reported = <VoiceResult>[];
        final result =
            await voice.recordAndAsk(askClient, onFailure: reported.add);

        expect(result, isNull);
        expect(source.calls, isEmpty, reason: 'a failed capture must never ask');
        expect(reported, hasLength(1), reason: 'the UI must be told why');
        expect(reported.single.failure, failure);
        expect(reported.single.message, 'because $label');
        expect(reported.single.ok, isFalse);
      });
    }

    test('a caller that passes no onFailure still just gets null, not a throw',
        () async {
      final source = _RecordingEdgeRpcSource();
      final voice = VoiceTranscription(
        listenOnce: () async =>
            const VoiceResult.failed(VoiceFailure.unavailable, 'nope'),
      );
      expect(await voice.recordAndAsk(EdgeAskClient(source)), isNull);
    });
  });

  test('VoiceResult.success reports ok and carries the text', () {
    const r = VoiceResult.success('hello');
    expect(r.ok, isTrue);
    expect(r.text, 'hello');
    expect(r.failure, isNull);
  });
}
