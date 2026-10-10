import 'dart:async';
import 'dart:math';

import 'conversation_store.dart';

import 'edge_client.dart';

enum TaskState { pending, working, completed, failed, cancelled, outcomeUnknown, interrupted, cancellationRequested, unknown }

TaskState parseTaskState(String? s) => switch (s) {
  'completed' => TaskState.completed,
  'failed' => TaskState.failed,
  'cancelled' => TaskState.cancelled,
  'working' => TaskState.working,
  'submitted' || 'pending' => TaskState.pending,
  'outcome_unknown' => TaskState.outcomeUnknown,
  'interrupted' => TaskState.interrupted,
  'cancellation_requested' => TaskState.cancellationRequested,
  _ => TaskState.unknown,
};

extension TaskStatePresentation on TaskState {
  String get wireName => switch (this) {
    TaskState.outcomeUnknown || TaskState.unknown => 'outcome_unknown',
    TaskState.cancellationRequested => 'cancellation_requested',
    _ => name,
  };
  bool get needsAttention => this != TaskState.pending && this != TaskState.working;
  String get explanation => switch (this) {
    TaskState.outcomeUnknown || TaskState.unknown => 'Outcome unknown. Work may have run. Check status; do not resend.',
    TaskState.interrupted => 'Interrupted before execution. This request did not run.',
    TaskState.cancellationRequested => 'Cancellation requested; stopping has not been confirmed.',
    TaskState.cancelled => 'Cancellation confirmed.',
    TaskState.failed => 'Request failed.',
    _ => '',
  };
}

class TaskUpdate {
  final String taskId;
  final TaskState state;
  final String? outputText;
  final int? tokensUsed;
  final bool cancellationRequested;
  final bool cancellationConfirmed;

  /// Set only by an `n2n/edge/task_progress` notification — a still-alive turn
  /// reporting in. Never persisted; purely a live hint for the UI.
  final String? progressDetail;

  const TaskUpdate({
    required this.taskId,
    required this.state,
    this.outputText,
    this.tokensUsed,
    this.cancellationRequested = false,
    this.cancellationConfirmed = false,
    this.progressDetail,
  });

  factory TaskUpdate.fromAskResult(Map<String, dynamic> params) => TaskUpdate(
        taskId: params['task_id'] as String,
        state: params['cancel_requested'] == true && ['working', 'submitted', 'pending'].contains(params['state'])
            ? TaskState.cancellationRequested : parseTaskState((params['outcome_state'] ?? params['state']) as String?),
        cancellationRequested: params['cancel_requested'] == true,
        cancellationConfirmed: params['cancellation_confirmed'] == true || params['state'] == 'cancelled',
        // A failed task carries its reason under `error`, not `output_text`
        // (TaskManager.run stores {"error": ...} on exception). Reading only
        // output_text dropped every failure explanation on the floor, so a
        // timeout showed as a bare "Failed" with no text at all.
        outputText: (params['output_text'] ?? params['error']) as String?,
        tokensUsed: params['tokens_used'] as int?,
      );

  factory TaskUpdate.fromProgress(Map<String, dynamic> params) => TaskUpdate(
        taskId: params['task_id'] as String,
        state: TaskState.working,
        progressDetail: params['detail'] as String?,
      );
}

/// Phone-to-Border command channel (feature 067). Wraps `EdgeClient`'s
/// call()/on() to expose the n2n/edge/ask / ask_result / tasks/status /
/// tasks/cancel wire surface
/// (contracts/edge-ask-command-channel.md).
class EdgeAskClient {
  final EdgeRpcSource client;
  final _updates = StreamController<TaskUpdate>.broadcast();

  ConversationStore? store;

  EdgeAskClient(this.client, {this.store}) {
    client.on('n2n/edge/ask_result', (params) {
      _updates.add(TaskUpdate.fromAskResult(params));
      return <String, dynamic>{};
    });
    // Best-effort liveness for a long turn. A Border that never sends this
    // (older build) simply produces no progress updates — nothing breaks.
    client.on('n2n/edge/task_progress', (params) {
      _updates.add(TaskUpdate.fromProgress(params));
      return <String, dynamic>{};
    });
  }

  /// Fires once per task whenever the Border pushes a finished answer
  /// (best-effort — a disconnected phone should also poll `status()` on
  /// reconnect for a task it submitted but never heard back on).
  Stream<TaskUpdate> get updates => _updates.stream;

  /// `attachment` (feature 068, US2, research D3): an optional
  /// `{content_type, content}` capture riding the SAME request — `text` may
  /// be empty when the capture stands alone (FR-005).
  ///
  /// `origin` (spec 117, FR-002/contracts/edge-ask-origin-field.md): an
  /// optional marker, currently only ever sent as `'voice'` by Siri's
  /// headless entry point (`ask_border_headless.dart`), so the Border can
  /// forward it to `run_agent_turn(origin=...)` (spec 116) and compose a
  /// short, plain-spoken answer. Absent for the app's own Chat screen --
  /// identical wire shape to today, same optional-field pattern as
  /// `attachment`.
  ///
  /// Per contract (edge-ask-command-channel.md), the Border acks
  /// `n2n/edge/ask` immediately and never blocks on the answer -- but a
  /// base64-encoded photo/video attachment can be several MB, and just
  /// transferring that much data over the wire (especially on a slower
  /// connection) can plausibly exceed the plain-text default's 30s budget
  /// well before the Border even gets to acking it. A longer timeout only
  /// when an attachment is present avoids inflating the fast, common
  /// text-only case.
  Map<String, dynamic> get border => client is EdgeClient ? (client as EdgeClient).border : const {};
  bool get attachmentsUnavailable => (border['capabilities'] as Map?)?['attachments'] == false;
  String? get ownerGeneration => client is EdgeClient ? (client as EdgeClient).enrollFingerprint : null;

  Future<String> ask(String text, {Map<String, dynamic>? attachment, String? origin, String localOrigin = 'phone'}) async {
    if (attachment != null && attachmentsUnavailable) {
      throw EdgeClientException('unsupported_attachment', 'Photo and video Ask Border requests are unavailable on this Hermes Border.');
    }
    final requestId = List.generate(24, (_) => Random.secure().nextInt(256).toRadixString(16).padLeft(2, '0')).join();
    final localId = 'request-$requestId';
    await store?.prepareAdmission(localId, requestId, text, origin: localOrigin, ownerGeneration: ownerGeneration);
    try {
      final result = await client.call('n2n/edge/ask', {
        'text': text, 'attachment': ?attachment, 'origin': ?origin,
        'request_id': requestId, 'conversation_id': 'mobile',
        'client_capabilities': ['task_outcomes_v1', 'request_recovery'],
      }, timeout: attachment == null ? const Duration(seconds: 30) : const Duration(seconds: 120));
      final taskId = result['task_id'] as String;
      await store?.bindAdmission(requestId, taskId);
      return taskId;
    } catch (error) {
      // A transport failure cannot prove that the Border did not admit work.
      // Persist the request receipt BEFORE sending; reconciliation only reads.
      final definite = error is EdgeClientException && int.tryParse(error.code) != null;
      await store?.updateState(localId, definite ? 'failed' : 'outcome_unknown', answerText: definite ? '$error' : TaskState.outcomeUnknown.explanation);
      if (!definite && store != null) return localId;
      rethrow;
    }
  }

  Future<bool> cancel(String taskId) async {
    await store?.updateState(taskId, 'cancellation_requested', answerText: TaskState.cancellationRequested.explanation);
    try {
      final result = await client.call('n2n/tasks/cancel', {'task_id': taskId});
      final confirmed = result['cancellation_confirmed'] == true || result['cancelled'] == true;
      await store?.updateState(taskId, confirmed ? 'cancelled' : 'cancellation_requested', answerText: confirmed ? TaskState.cancelled.explanation : TaskState.cancellationRequested.explanation);
      _updates.add(TaskUpdate(taskId: taskId, state: confirmed ? TaskState.cancelled : TaskState.cancellationRequested, cancellationRequested: true, cancellationConfirmed: confirmed));
      return confirmed;
    } catch (_) {
      // Lost cancellation acknowledgement is never a confirmed stop.
      _updates.add(TaskUpdate(taskId: taskId, state: TaskState.cancellationRequested, cancellationRequested: true));
      return false;
    }
  }

  Future<TaskUpdate> status(String taskId) async {
    final result = await client.call('n2n/tasks/status', {'task_id': taskId});
    return TaskUpdate.fromAskResult({...result, 'task_id': taskId});
  }

  Future<TaskUpdate> recover(ConversationTurn turn) async {
    if (turn.ownerGeneration != null && ownerGeneration != turn.ownerGeneration) {
      return TaskUpdate(taskId: turn.taskId, state: TaskState.outcomeUnknown, outputText: 'This request belongs to an earlier device enrollment. Its outcome is unknown.');
    }
    if (!turn.taskId.startsWith('request-')) return result(turn.taskId);
    if (turn.requestId == null) return TaskUpdate(taskId: turn.taskId, state: TaskState.outcomeUnknown);
    final response = await client.call('n2n/tasks/result', {'request_id': turn.requestId});
    final taskId = response['task_id'];
    if (taskId is! String || taskId.isEmpty || response['state'] == 'unknown') {
      return TaskUpdate(taskId: turn.taskId, state: TaskState.outcomeUnknown);
    }
    await store?.bindAdmission(turn.requestId!, taskId);
    return TaskUpdate.fromAskResult(response);
  }

  /// Fetches the full answer for a task that already finished — unlike
  /// [status], which only reports state. Needed for recovery: a task that
  /// completes while this device is disconnected (or its `ask_result` push
  /// simply never arrives) has no other way to reach the phone, since the
  /// Border never re-pushes a result spontaneously (contracts/
  /// edge-ask-command-channel.md: "a disconnected phone recovers via
  /// n2n/tasks/status|result on reconnect"). The response shape matches
  /// `ask_result`'s exactly (`task_id`/`state`/`output_text`/`tokens_used`).
  Future<TaskUpdate> result(String taskId) async {
    // Manual/Watch status can retain a provisional receipt after phone recovery.
    // Query the persisted original admission; never submit the question again.
    if (taskId.startsWith('request-')) {
      for (final turn in store?.turns ?? <ConversationTurn>[]) {
        if (turn.taskId == taskId || 'request-${turn.requestId}' == taskId) {
          return recover(turn);
        }
      }
      return TaskUpdate(taskId: taskId, state: TaskState.outcomeUnknown);
    }
    final result = await client.call('n2n/tasks/result', {'task_id': taskId});
    return TaskUpdate.fromAskResult(result);
  }

  void dispose() {
    _updates.close();
  }
}
