import 'dart:async';

import 'edge_client.dart';

enum TaskState { pending, working, completed, failed, cancelled, unknown }

TaskState _parseTaskState(String? s) {
  switch (s) {
    case 'completed':
      return TaskState.completed;
    case 'failed':
      return TaskState.failed;
    case 'cancelled':
      return TaskState.cancelled;
    case 'working':
      return TaskState.working;
    case 'submitted':
      return TaskState.pending;
    default:
      return TaskState.unknown;
  }
}

class TaskUpdate {
  final String taskId;
  final TaskState state;
  final String? outputText;
  final int? tokensUsed;

  /// Set only by an `n2n/edge/task_progress` notification — a still-alive turn
  /// reporting in. Never persisted; purely a live hint for the UI.
  final String? progressDetail;

  const TaskUpdate({
    required this.taskId,
    required this.state,
    this.outputText,
    this.tokensUsed,
    this.progressDetail,
  });

  factory TaskUpdate.fromAskResult(Map<String, dynamic> params) => TaskUpdate(
        taskId: params['task_id'] as String,
        state: _parseTaskState(params['state'] as String?),
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

  EdgeAskClient(this.client) {
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
  Future<String> ask(String text, {Map<String, dynamic>? attachment}) async {
    final result = await client.call('n2n/edge/ask', {
      'text': text,
      'attachment': ?attachment,
    });
    return result['task_id'] as String;
  }

  Future<bool> cancel(String taskId) async {
    final result = await client.call('n2n/tasks/cancel', {'task_id': taskId});
    return result['cancelled'] as bool? ?? false;
  }

  Future<TaskUpdate> status(String taskId) async {
    final result = await client.call('n2n/tasks/status', {'task_id': taskId});
    return TaskUpdate(taskId: taskId, state: _parseTaskState(result['state'] as String?));
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
    final result = await client.call('n2n/tasks/result', {'task_id': taskId});
    return TaskUpdate.fromAskResult(result);
  }

  void dispose() {
    _updates.close();
  }
}
