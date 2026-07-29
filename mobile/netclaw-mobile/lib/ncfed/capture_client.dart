import 'dart:convert';

import 'edge_ask_client.dart';
import 'edge_client.dart';

/// Mirrors `bgp/constants.py`'s `NCFED_MAX_MESSAGE` (16 MiB) — the ceiling
/// FR-005a requires every capture to comfortably fit under, enforced here
/// at capture time, never discovered at send time (research D4). Capped
/// more conservatively (half the wire bound) to leave headroom for the
/// rest of the JSON-RPC envelope and base64's ~33% size inflation.
const int kMaxCaptureBytes = 8 * 1024 * 1024;

class CaptureResult {
  final String contentType; // 'image' | 'video' | 'audio'
  final List<int> bytes;

  const CaptureResult({required this.contentType, required this.bytes});
}

/// What actually drives a capture — injected so `CaptureClient` is testable
/// without real camera/microphone hardware (mirrors `VoiceTranscription`'s
/// `listenOnce` pattern). Returns `null` on a declined permission or a
/// cancelled capture — never a partial/empty result (FR-005's acceptance
/// scenarios 3-4).
typedef CaptureFn = Future<CaptureResult?> Function(String captureType);

/// Bidirectional capture (feature 068, US2/US3). Phone-initiated captures
/// attach to `n2n/edge/ask` (research D3, no new wire method); Border-
/// requested captures register a handler for `n2n/edge/capture` (contract
/// §2), invoking the SAME underlying `CaptureFn`.
class CaptureClient {
  final EdgeAskClient askClient;
  final CaptureFn capture;

  CaptureClient({required this.askClient, required this.capture});

  /// Registers the Border-requested capture handler (US3). Call once, after
  /// enrollment.
  void wire(EdgeMethodSource client) {
    client.on('n2n/edge/capture', (params) async {
      final captureType = params['capability'] as String? ?? 'camera.capture';
      final result = await capture(captureType);
      if (result == null) {
        return {'decision': 'declined', 'reason': 'permission_denied_or_cancelled'};
      }
      if (result.bytes.length > kMaxCaptureBytes) {
        // Enforced here too, not just at the UI layer -- FR-005a is a hard
        // requirement, not merely a UI nicety.
        return {'decision': 'declined', 'reason': 'capture_too_large'};
      }
      return {
        'decision': 'captured',
        'content_type': result.contentType,
        'content': base64Encode(result.bytes),
      };
    });
  }

  /// Phone-initiated capture (US2): captures, then sends it attached to an
  /// `n2n/edge/ask` request — `text` may be empty for a bare capture with
  /// no accompanying question (FR-005). Returns the task_id, or `null` if
  /// the capture was declined/cancelled (no request is ever sent for that
  /// case) or exceeded the size cap. [onCaptured] fires right after a
  /// successful (under-the-cap) capture, before sending — lets a caller
  /// (e.g. the chat UI) keep the raw bytes for local display without this
  /// method needing to change its return type.
  Future<String?> captureAndAsk(
    String captureType, {
    String text = '',
    void Function(CaptureResult result)? onCaptured,
  }) async {
    final result = await capture(captureType);
    if (result == null) return null;
    if (result.bytes.length > kMaxCaptureBytes) return null;
    onCaptured?.call(result);
    return askClient.ask(text, attachment: {
      'content_type': result.contentType,
      'content': base64Encode(result.bytes),
    });
  }
}
