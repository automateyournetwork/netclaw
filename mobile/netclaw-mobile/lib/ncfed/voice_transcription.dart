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
  /// How long to wait for a final result before giving up. Without a bound the
  /// completer could wait forever if the engine ended its session without ever
  /// firing `finalResult` — the mic button would hang with no way out.
  static const listenTimeout = Duration(seconds: 30);

  final Future<VoiceResult> Function() _listenOnce;

  VoiceTranscription({Future<VoiceResult> Function()? listenOnce})
      : _listenOnce = listenOnce ?? _defaultListenOnce;

  static Future<VoiceResult> _defaultListenOnce() async {
    final speech = stt.SpeechToText();
    SpeechRecognitionError? lastError;

    final available = await speech.initialize(onError: (e) => lastError = e);
    if (!available) {
      // Distinguish "you said no" from "this device can't do it at all" —
      // those need completely different responses from the operator.
      if (!await speech.hasPermission) {
        return const VoiceResult.failed(VoiceFailure.permissionDenied,
            'Microphone permission is needed for voice requests.');
      }
      final why = lastError?.errorMsg;
      return VoiceResult.failed(
          VoiceFailure.unavailable,
          why != null
              ? 'Speech recognition unavailable: $why'
              : 'Speech recognition is unavailable on this device.');
    }

    final completer = Completer<VoiceResult>();
    void finish(VoiceResult r) {
      if (!completer.isCompleted) completer.complete(r);
    }

    await speech.listen(
      onResult: (result) {
        if (!result.finalResult) return;
        final words = result.recognizedWords.trim();
        finish(words.isEmpty
            ? const VoiceResult.failed(
                VoiceFailure.noSpeechDetected, "Didn't catch that — try again.")
            : VoiceResult.success(words));
      },
      listenOptions: stt.SpeechListenOptions(
        partialResults: false,
        cancelOnError: true,
        listenFor: listenTimeout,
      ),
    );

    // The engine can also end its session without ever producing a final
    // result (pure silence, or an error raised after listen() returned).
    // Both land here instead of hanging.
    final result = await completer.future.timeout(
      listenTimeout + const Duration(seconds: 2),
      onTimeout: () {
        final why = lastError?.errorMsg;
        return why != null
            ? VoiceResult.failed(
                VoiceFailure.engineError, 'Speech recognition failed: $why')
            : const VoiceResult.failed(VoiceFailure.noSpeechDetected,
                "Didn't hear anything — try again.");
      },
    );
    await speech.stop();
    return result;
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
