import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/capture_client.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';

class _RecordingEdgeRpcSource implements EdgeRpcSource {
  final Map<String, EdgeMethodHandler> handlers = {};
  final List<(String method, Map<String, dynamic> params)> calls = [];

  @override
  void on(String method, EdgeMethodHandler handler) {
    handlers[method] = handler;
  }

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return {'task_id': 'task-capture-1'};
  }
}

void main() {
  group('captureAndAsk (US2, phone-initiated)', () {
    test('a successful capture attaches to n2n/edge/ask with the exact shape', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => CaptureResult(contentType: 'image', bytes: [1, 2, 3]),
      );

      final taskId = await client.captureAndAsk('camera.capture', text: 'what is this?');

      expect(taskId, 'task-capture-1');
      expect(source.calls, hasLength(1));
      expect(source.calls.single.$1, 'n2n/edge/ask');
      final params = source.calls.single.$2;
      expect(params['text'], 'what is this?');
      expect(params['attachment'], {
        'content_type': 'image',
        'content': base64Encode([1, 2, 3]),
      });
    });

    test('a bare capture with no text is still sent (FR-005)', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => CaptureResult(contentType: 'image', bytes: [1, 2, 3]),
      );

      final taskId = await client.captureAndAsk('camera.capture');

      expect(taskId, 'task-capture-1');
      expect(source.calls.single.$2['text'], '');
    });

    test('a declined/cancelled capture never calls ask() at all', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => null, // simulated declined permission / cancelled capture
      );

      final taskId = await client.captureAndAsk('camera.capture');

      expect(taskId, isNull);
      expect(source.calls, isEmpty);
    });

    test('a capture exceeding the size cap is refused, never sent (FR-005a)', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final oversized = List<int>.filled(kMaxCaptureBytes + 1, 0);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => CaptureResult(contentType: 'video', bytes: oversized),
      );

      final taskId = await client.captureAndAsk('camera.record_video');

      expect(taskId, isNull);
      expect(source.calls, isEmpty);
    });
  });

  group('n2n/edge/capture handler (US3, Border-requested)', () {
    test('a successful capture returns decision=captured with the exact shape', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => CaptureResult(contentType: 'image', bytes: [4, 5, 6]),
      );
      client.wire(source);

      final result = await source.handlers['n2n/edge/capture']!({'capability': 'camera.capture'});

      expect(result, {
        'decision': 'captured',
        'content_type': 'image',
        'content': base64Encode([4, 5, 6]),
      });
    });

    test('a declined/cancelled capture returns an explicit decline, never empty/hanging', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => null,
      );
      client.wire(source);

      final result = await source.handlers['n2n/edge/capture']!({'capability': 'camera.capture'});

      expect(result['decision'], 'declined');
      expect(result['reason'], isNotEmpty);
    });

    test('an oversized capture is declined server-side too, not just client-side', () async {
      final source = _RecordingEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final oversized = List<int>.filled(kMaxCaptureBytes + 1, 0);
      final client = CaptureClient(
        askClient: askClient,
        capture: (type) async => CaptureResult(contentType: 'audio', bytes: oversized),
      );
      client.wire(source);

      final result = await source.handlers['n2n/edge/capture']!({'capability': 'audio.record'});

      expect(result['decision'], 'declined');
      expect(result['reason'], 'capture_too_large');
    });
  });
}
