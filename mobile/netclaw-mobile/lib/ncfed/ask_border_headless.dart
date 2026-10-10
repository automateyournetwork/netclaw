import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:path_provider/path_provider.dart';

import 'conversation_store.dart';
import 'edge_ask_client.dart';
import 'edge_client.dart';
import 'headless_connect.dart';
import 'local_notifications.dart';

const _channel = MethodChannel('ca.automateyournetwork.netclaw/ask_border');

/// How long [runAskBorder] waits, before ever acknowledging, for a real
/// answer it can hand straight to Siri to speak aloud -- true two-way voice
/// for anything the agent answers reasonably quickly.
///
/// Re-tuned in spec 117 (Pass 3) against spec 116's (Pass 2) real measured
/// Border latency after its fixed per-turn startup toll was eliminated: a
/// cold first-in-session turn now lands around 9s, and every turn after
/// that under 4s (specs/116-border-turn-latency/PASS3-HANDOFF.md). The
/// previous value of 18s was tuned against a ~38s-always baseline that no
/// longer applies (specs/117-siri-voice-tuning/research.md R1) -- 12s
/// gives the cold case a real margin while staying well under Siri's own
/// observed real-world patience for a spoken App Intent response (on-device
/// testing showed it can abandon the request and fall back to a web search
/// well before 30s if nothing has been said yet).
const askBorderFastWindow = Duration(seconds: 12);

/// How long [runAskBorder] keeps listening for a fast-arriving `ask_result`
/// after the acknowledgment has already been reported (because [
/// askBorderFastWindow] elapsed first), hoping to post the real-answer
/// notification before this headless process is reclaimed (spec 111 FR-004,
/// research.md R8). A slower answer is left `pending` --
/// `lib/ncfed/turn_reconciler.dart`'s `reconcileStaleTurns` finishes it on a
/// later reconnect, exactly as it already does for any other stranded ask.
const askBorderPostAckWindow = Duration(seconds: 20);

/// Entry point for the headless `FlutterEngine` `AskBorderIntent.swift`
/// spins up (spec 111, research.md R1). Mirrors `background_refresh.dart`'s
/// shape: no widget tree, reconnects via the same persisted enrollment a
/// cold foreground launch would, and reports back over [_channel] — except
/// here the channel carries a real request (the question) inbound, not just
/// a completion signal outbound.
@pragma('vm:entry-point')
Future<void> askBorderMain() async {
  WidgetsFlutterBinding.ensureInitialized();
  _channel.setMethodCallHandler((call) async {
    if (call.method != 'submit') return null;
    final question = (call.arguments as Map)['question'] as String;
    final dir = await getApplicationDocumentsDirectory();

    final EdgeClient client;
    try {
      client = await connectHeadless(directory: dir);
    } on NotEnrolledError {
      throw PlatformException(code: 'not_enrolled');
    } on ConnectTimeoutError {
      throw PlatformException(code: 'timeout');
    }

    final store = ConversationStore(dir);
    await store.load();
    try {
      return await runAskBorder(
        question,
        rpc: client,
        store: store,
        close: client.close,
        notify: ({required identifier, required preview, required badgeCount}) async {
          final notifications = LocalNotifications();
          await notifications.initialize(onResponse: (_) {});
          await notifications.postChatNotification(
              identifier: identifier, preview: preview, badgeCount: badgeCount);
        },
        onFinished: () => _channel.invokeMethod<void>('finished'),
      );
    } catch (e) {
      await client.close();
      throw PlatformException(code: 'failed', message: '$e');
    }
  });
}

/// Strips the Border's lightweight markdown (bold/italic emphasis, `#`
/// headers, `-`/`*` list markers) from [text] so it reads as natural speech
/// when handed to Siri as spoken `IntentDialog` content (spec 115 FR-005,
/// research.md R5). Only ever applied to the string [runAskBorder] returns
/// on its fast-voice path -- never to the value persisted via
/// `store.updateState`, which stays exactly as the Border composed it for
/// display in the app's own Chat screen.
String stripMarkdownForSpeech(String text) {
  var result = text
      // Headers: leading '#'s followed by a space, at line start.
      .replaceAll(RegExp(r'^#{1,6}\s+', multiLine: true), '')
      // Bold/italic emphasis markers -- content is kept, markers dropped.
      .replaceAllMapped(RegExp(r'\*\*(.+?)\*\*'), (m) => m.group(1)!)
      .replaceAllMapped(RegExp(r'\*(.+?)\*'), (m) => m.group(1)!)
      // List-item markers at line start ('- ' or '* '), content kept.
      .replaceAll(RegExp(r'^[-*]\s+', multiLine: true), '');
  // Collapse any blank lines the marker removal left behind.
  result = result.replaceAll(RegExp(r'\n{3,}'), '\n\n').trim();
  return result;
}

/// `null` if [state] isn't one of the three terminal states.
String? _terminalStateString(TaskState state) => state.needsAttention ? state.wireName : null;

/// The testable core of [askBorderMain]: given an already-connected [rpc],
/// submits [question] and persists it into [store] as a pending turn with
/// `origin: 'siri'` (FR-005/FR-011). Two-phase result:
///
/// 1. Waits up to [fastWindow] for a terminal `ask_result` it can hand
///    straight back as the return value -- Siri speaks this verbatim, so an
///    answer that arrives in time gets a real two-way voice exchange, not
///    just an acknowledgment.
/// 2. If nothing terminal arrives in [fastWindow], falls back to today's
///    behavior: returns a plain acknowledgment (FR-003) and keeps listening
///    in the background for up to [postAckWindow] more, notifying if the
///    answer lands late (FR-004, research.md R8) or leaving it `pending` for
///    `reconcileStaleTurns` otherwise.
Future<String> runAskBorder(
  String question, {
  required EdgeRpcSource rpc,
  required ConversationStore store,
  required Future<void> Function() close,
  required Future<void> Function({
    required String identifier,
    required String preview,
    required int badgeCount,
  }) notify,
  required void Function() onFinished,
  Duration fastWindow = askBorderFastWindow,
  Duration postAckWindow = askBorderPostAckWindow,
}) async {
  final askClient = EdgeAskClient(rpc, store: store);
  final String taskId;
  try {
    // This is the sole Siri-specific caller of EdgeAskClient.ask() in the
    // codebase (AskBorderIntent.swift's headless entry point) -- always
    // marks its requests origin: 'voice' (spec 117 FR-002) so the Border
    // composes a short, plain-spoken answer instead of the Chat screen's
    // default structured style.
    taskId = await askClient.ask(question, origin: 'voice', localOrigin: 'siri');
  } catch (e) {
    onFinished();
    rethrow;
  }
  await store.addPending(taskId, question, origin: 'siri');
  if (taskId.startsWith('request-')) {
    await close();
    onFinished();
    return TaskState.outcomeUnknown.explanation;
  }

  try {
    final update = await askClient.updates
        .firstWhere((u) => u.taskId == taskId && u.state.needsAttention)
        .timeout(fastWindow);
    final stateString = _terminalStateString(update.state);
    if (stateString != null) {
      final answer = update.outputText ?? update.state.explanation;
      await store.updateState(taskId, stateString, answerText: answer);
      await close();
      onFinished();
      if (answer.isEmpty) return "NetClaw answered, but didn't say anything.";
      final spoken = stripMarkdownForSpeech(answer);
      return spoken.isEmpty ? "NetClaw answered, but didn't say anything." : spoken;
    }
    // Still working when fastWindow elapsed -- fall through to phase 2.
  } on TimeoutException {
    // Nothing yet after fastWindow -- fall through to phase 2.
  }

  unawaited(_awaitResultAndNotify(
    askClient: askClient,
    store: store,
    taskId: taskId,
    close: close,
    notify: notify,
    window: postAckWindow,
    onFinished: onFinished,
  ));

  return "Sent to NetClaw. I'll let you know when it answers.";
}

Future<void> _awaitResultAndNotify({
  required EdgeAskClient askClient,
  required ConversationStore store,
  required String taskId,
  required Future<void> Function() close,
  required Future<void> Function({
    required String identifier,
    required String preview,
    required int badgeCount,
  }) notify,
  required Duration window,
  required void Function() onFinished,
}) async {
  try {
    final update = await askClient.updates
        .firstWhere((u) => u.taskId == taskId && u.state.needsAttention)
        .timeout(window);
    if (!update.state.needsAttention) {
      return; // still working when the stream closed early — leave it pending
    }
    final answer = update.outputText ?? update.state.explanation;
    await store.updateState(
      taskId,
      update.state.wireName,
      answerText: answer,
    );
    await notify(
      identifier: taskId,
      preview: answer.isEmpty ? 'NetClaw answered your question.' : answer,
      badgeCount: store.unreadCount,
    );
  } on TimeoutException {
    // Left 'pending' -- reconcileStaleTurns finishes this later (research.md R8).
  } finally {
    await close();
    onFinished();
  }
}
