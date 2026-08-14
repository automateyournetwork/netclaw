import 'approval_client.dart';
import 'conversation_store.dart';
import 'device_heartbeat.dart';
import 'edge_ask_client.dart';
import 'message_feed.dart';

/// Answers Apple Watch companion-app requests (feature 072) relayed in by
/// `WatchRelayPlugin.swift`'s method channel. Deliberately has NO
/// `MethodChannel`/platform-channel code of its own (mirrors
/// `ApprovalClient`/`CaptureClient`'s existing injected-dependency pattern)
/// so `handle()` is directly unit-testable — the channel wiring itself lives
/// in `main.dart`, a thin adapter with nothing to unit-test.
///
/// Answers using the SAME `ApprovalClient`/`EdgeAskClient`/`MessageFeedStore`
/// instances the phone's own UI already uses (research D1) — the watch has
/// no identity, enrollment, or connection of its own (FR-011).
class WatchRelay {
  final ApprovalClient? approvalClient;
  final EdgeAskClient? askClient;
  final MessageFeedStore? feedStore;
  final ConversationStore? conversationStore;
  final DeviceHeartbeatStore? heartbeatStore;

  const WatchRelay(
      {this.approvalClient,
      this.askClient,
      this.feedStore,
      this.conversationStore,
      this.heartbeatStore});

  /// Dispatches on the `method` name from contracts/watch-relay.md. Never
  /// throws for a recognized method — every not-connected/not-enrolled case
  /// is reported as a normal reply shape (FR-012), not an exception, since
  /// `WCSession.sendMessage`'s own reachability failure is what already
  /// carries the "phone unreachable" signal (research D2); this layer only
  /// needs to distinguish "reachable but nothing to relay to yet".
  Future<Map<String, dynamic>> handle(String method, Map<String, dynamic> args) async {
    switch (method) {
      case 'watch/approvals/list':
        return _listApprovals();
      case 'watch/approvals/resolve':
        return _resolveApproval(args);
      case 'watch/feed/list':
        return await _listFeed();
      case 'watch/history/list':
        return await _listHistory();
      case 'watch/feed/acknowledge':
        return _acknowledgeFeed(args);
      case 'watch/feed/delete':
        return _deleteFeed(args);
      case 'watch/history/acknowledge':
        return _acknowledgeHistory(args);
      case 'watch/history/delete':
        return _deleteHistory(args);
      case 'watch/ask/submit':
        return _submitAsk(args);
      case 'watch/ask/status':
        return _askStatus(args);
      case 'watch/heartbeat/latest':
        return await _latestHeartbeat();
      default:
        return {'error': 'unknown method $method'};
    }
  }

  Map<String, dynamic> _listApprovals() {
    final client = approvalClient;
    if (client == null) return {'enrolled': false, 'approvals': <Map<String, dynamic>>[]};
    return {
      'enrolled': true,
      'approvals': client.currentPending
          .map((a) => {
                'approval_id': a.approvalId,
                'target_type': a.targetType,
                'target_name': a.targetName,
                'requesting_agent': a.requestingAgent,
                'risk_name': a.riskName,
                'pushed_at': a.pushedAt.toIso8601String(),
              })
          .toList(),
    };
  }

  /// Trusts the watch to have already completed its own on-device passcode
  /// confirmation (FR-003) before calling this — exactly the same trust
  /// boundary `ApprovalClient.resolve()` itself already documents for the
  /// phone's Face ID gate (research D3 mirrors that shape, doesn't change it).
  Future<Map<String, dynamic>> _resolveApproval(Map<String, dynamic> args) async {
    final client = approvalClient;
    if (client == null) return {'error': 'not enrolled'};
    final approvalId = args['approval_id'] as int;
    final action = args['action'] as String;
    await client.resolve(approvalId, action, confirmationMethod: 'watch_passcode');
    return {'resolved': true};
  }

  Future<Map<String, dynamic>> _listFeed() async {
    final store = feedStore;
    if (store == null) return {'enrolled': false, 'messages': <Map<String, dynamic>>[]};
    // The phone's own FeedScreen loads persisted history lazily in its
    // initState() — the watch must not depend on that tab having been
    // opened first, so it loads (a safe no-op once already loaded) here.
    await store.load();
    return {
      'enrolled': true,
      'messages': store.messages
          .map((m) => {
                'content_type': m.contentType.name,
                // Non-text content isn't renderable on a watch screen at all
                // (FR-007) -- only the type indicator matters there, so the
                // actual payload is dropped rather than sending a
                // potentially multi-MB base64 blob over WatchConnectivity
                // for something that will never be shown.
                'content': m.contentType == MessageContentType.text ? m.content : '',
                'designated_by': m.designatedBy,
                'pushed_at': m.pushedAt.toIso8601String(),
                'acknowledged': m.acknowledged,
              })
          .toList(),
    };
  }

  /// `pushed_at` is the same identifier `watch/feed/list` already sends per
  /// message -- contracts/watch-relay-extensions.md §1.
  Future<Map<String, dynamic>> _acknowledgeFeed(Map<String, dynamic> args) async {
    final store = feedStore;
    if (store == null) return {'error': 'not enrolled'};
    final pushedAt = DateTime.parse(args['pushed_at'] as String);
    await store.acknowledge(pushedAt);
    return {'acknowledged': true};
  }

  Future<Map<String, dynamic>> _deleteFeed(Map<String, dynamic> args) async {
    final store = feedStore;
    if (store == null) return {'error': 'not enrolled'};
    final pushedAt = DateTime.parse(args['pushed_at'] as String);
    await store.delete(pushedAt);
    return {'deleted': true};
  }

  /// Read-only chat history (added after real-hardware testing showed the
  /// operator wanted past Q&A visible on the wrist, not just new pushes) --
  /// mirrors the phone's own `ChatScreen` conversation list, newest first,
  /// capped at 30 turns since a watch screen has no use for a longer scroll.
  Future<Map<String, dynamic>> _listHistory() async {
    final store = conversationStore;
    if (store == null) return {'enrolled': false, 'turns': <Map<String, dynamic>>[]};
    await store.load();
    final turns = store.turns.reversed.take(30);
    return {
      'enrolled': true,
      'turns': turns
          .map((t) => {
                'task_id': t.taskId,
                'request_text': t.requestText,
                if (t.answerText != null) 'answer_text': t.answerText,
                'state': _narrowState(_taskStateFromString(t.state)),
                'submitted_at': t.submittedAt.toIso8601String(),
                'acknowledged': t.acknowledged,
              })
          .toList(),
    };
  }

  /// `task_id` is the same identifier `watch/history/list` already sends
  /// per turn -- contracts/watch-relay-extensions.md §2.
  Future<Map<String, dynamic>> _acknowledgeHistory(Map<String, dynamic> args) async {
    final store = conversationStore;
    if (store == null) return {'error': 'not enrolled'};
    await store.acknowledge(args['task_id'] as String);
    return {'acknowledged': true};
  }

  Future<Map<String, dynamic>> _deleteHistory(Map<String, dynamic> args) async {
    final store = conversationStore;
    if (store == null) return {'error': 'not enrolled'};
    await store.delete(args['task_id'] as String);
    return {'deleted': true};
  }

  /// The latest device heartbeat's status (103/US4/FR-015), or
  /// `has_heartbeat: false` if the phone has never received one for this
  /// enrollment — contracts/watch-heartbeat.md. `enrolled: false` (no store at
  /// all) and `has_heartbeat: false` (store exists, nothing in it yet) are
  /// deliberately distinct replies: the watch renders each differently
  /// (US4 acceptance scenario 3 needs "no data yet" to read as genuinely
  /// empty, not as a misleadingly confident "all clear").
  Future<Map<String, dynamic>> _latestHeartbeat() async {
    final store = heartbeatStore;
    if (store == null) return {'enrolled': false, 'has_heartbeat': false};
    final status = await store.load();
    if (status == null) return {'enrolled': true, 'has_heartbeat': false};
    return {
      'enrolled': true,
      'has_heartbeat': true,
      'summary': status.summary,
      'pushed_at': status.pushedAt.toIso8601String(),
      'is_alarm': status.isAlarm,
    };
  }

  TaskState _taskStateFromString(String state) {
    switch (state) {
      case 'completed':
        return TaskState.completed;
      case 'failed':
        return TaskState.failed;
      case 'cancelled':
        return TaskState.cancelled;
      case 'working':
        return TaskState.working;
      case 'pending':
        return TaskState.pending;
      default:
        return TaskState.unknown;
    }
  }

  /// Fixes a real, existing defect (073/FR-016): a question asked from the
  /// watch used to call `EdgeAskClient.ask()` directly and never recorded
  /// into `conversationStore` at all, so it never showed up in the phone's
  /// Chat tab or the watch's own History tab. `conversationStore` is
  /// optional here only because unit tests exercise `askClient` alone --
  /// every real caller (`main.dart`) always provides both.
  Future<Map<String, dynamic>> _submitAsk(Map<String, dynamic> args) async {
    final client = askClient;
    if (client == null) return {'error': 'not enrolled'};
    final text = (args['text'] as String? ?? '').trim();
    if (text.isEmpty) return {'error': 'nothing to submit'};
    final taskId = await client.ask(text);
    await conversationStore?.addPending(taskId, text, origin: 'watch');
    return {'task_id': taskId};
  }

  /// Persists the resolved answer into the SAME turn `_submitAsk` created,
  /// in addition to narrowing state for the watch's own reply (073/FR-016) --
  /// previously this only ever told the watch the answer, never wrote it
  /// into the shared store.
  Future<Map<String, dynamic>> _askStatus(Map<String, dynamic> args) async {
    final client = askClient;
    if (client == null) return {'error': 'not enrolled'};
    final taskId = args['task_id'] as String;
    final update = await client.result(taskId);
    if (update.state == TaskState.completed ||
        update.state == TaskState.failed ||
        update.state == TaskState.cancelled) {
      await conversationStore?.updateState(
        taskId,
        update.state.name,
        answerText: update.outputText,
      );
    }
    return {
      'task_id': taskId,
      'state': _narrowState(update.state),
      if (update.outputText != null) 'answer_text': update.outputText,
    };
  }

  /// Narrows the phone's full `TaskState` vocabulary to the three watch-sized
  /// values from data-model.md — `pending`/`working` both mean "still going"
  /// from a glance-and-go watch screen's point of view.
  String _narrowState(TaskState state) {
    switch (state) {
      case TaskState.completed:
        return 'answered';
      case TaskState.failed:
      case TaskState.cancelled:
        return 'failed';
      case TaskState.pending:
      case TaskState.working:
      case TaskState.unknown:
        return 'waiting';
    }
  }
}
