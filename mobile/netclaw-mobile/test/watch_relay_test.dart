import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/approval_client.dart';
import 'package:netclaw_mobile/ncfed/conversation_store.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_client.dart';
import 'package:netclaw_mobile/ncfed/message_feed.dart';
import 'package:netclaw_mobile/ncfed/watch_relay.dart';

/// Records every `call()` and lets a test script canned results per method —
/// mirrors the `_RecordingEdgeRpcSource` pattern already used throughout this
/// test suite (approval_client_test.dart, capture_client_test.dart).
class _ScriptedEdgeRpcSource implements EdgeRpcSource {
  final List<(String method, Map<String, dynamic> params)> calls = [];
  final Map<String, Map<String, dynamic>> results;

  _ScriptedEdgeRpcSource([this.results = const {}]);

  @override
  void on(String method, EdgeMethodHandler handler) {}

  @override
  Future<Map<String, dynamic>> call(String method, Map<String, dynamic> params,
      {Duration timeout = const Duration(seconds: 30)}) async {
    calls.add((method, params));
    return results[method] ?? {};
  }
}

void main() {
  group('watch/approvals/list', () {
    test('enrolled: false with no approval client', () async {
      final relay = const WatchRelay();
      final result = await relay.handle('watch/approvals/list', {});
      expect(result, {'enrolled': false, 'approvals': []});
    });

    test('returns the current pending approvals, shaped per contracts/watch-relay.md', () async {
      final source = _ScriptedEdgeRpcSource();
      final approvalClient = ApprovalClient(source);
      approvalClient.receiveApproval({
        'approval_id': 42,
        'target_type': 'skill',
        'target_name': 'reboot-router',
        'requesting_agent': 'risk/netclaw-core',
        'risk_name': 'acme-ops',
        'pushed_at': '2026-07-27T14:00:00Z',
      });
      final relay = WatchRelay(approvalClient: approvalClient);

      final result = await relay.handle('watch/approvals/list', {});

      expect(result['enrolled'], isTrue);
      expect(result['approvals'], [
        {
          'approval_id': 42,
          'target_type': 'skill',
          'target_name': 'reboot-router',
          'requesting_agent': 'risk/netclaw-core',
          'risk_name': 'acme-ops',
          'pushed_at': '2026-07-27T14:00:00.000Z',
        }
      ]);
    });
  });

  group('watch/approvals/resolve', () {
    test('calls ApprovalClient.resolve with confirmation_method=watch_passcode (research D4)',
        () async {
      final source = _ScriptedEdgeRpcSource();
      final approvalClient = ApprovalClient(source);
      approvalClient.receiveApproval({
        'approval_id': 42,
        'target_type': 'skill',
        'target_name': 'reboot-router',
        'requesting_agent': 'agent',
        'pushed_at': '2026-07-27T14:00:00Z',
      });
      final relay = WatchRelay(approvalClient: approvalClient);

      final result = await relay.handle(
          'watch/approvals/resolve', {'approval_id': 42, 'action': 'approve'});

      expect(result, {'resolved': true});
      expect(source.calls, hasLength(1));
      expect(source.calls.single.$1, 'n2n/edge/approval_resolve');
      // Never "biometric" for a watch-originated resolution (FR-004) --
      // must be explicitly present and correct, not merely absent.
      expect(source.calls.single.$2['confirmation_method'], 'watch_passcode');
      expect(approvalClient.currentPending, isEmpty);
    });

    test('reports not enrolled when no approval client is available', () async {
      final relay = const WatchRelay();
      final result =
          await relay.handle('watch/approvals/resolve', {'approval_id': 42, 'action': 'approve'});
      expect(result['error'], isNotNull);
    });
  });

  group('watch/feed/list', () {
    test('enrolled: false with no feed store', () async {
      final relay = const WatchRelay();
      final result = await relay.handle('watch/feed/list', {});
      expect(result, {'enrolled': false, 'messages': []});
    });

    test('text messages pass through in full; non-text content is dropped (FR-007)', () async {
      final dir = await Directory.systemTemp.createTemp('ncfed_watch_relay_test_');
      addTearDown(() => dir.delete(recursive: true));
      final store = MessageFeedStore(dir);
      await store.append(EdgeMessage(
        contentType: MessageContentType.text,
        content: 'R2 flapping session cleared.',
        designatedBy: 'agent',
        pushedAt: DateTime.utc(2026, 7, 27, 13, 58),
      ));
      await store.append(EdgeMessage(
        contentType: MessageContentType.image,
        content: 'aGVsbG8=', // some base64 payload the watch never needs
        designatedBy: 'agent',
        pushedAt: DateTime.utc(2026, 7, 27, 13, 40),
      ));
      final relay = WatchRelay(feedStore: store);

      final result = await relay.handle('watch/feed/list', {});

      expect(result['enrolled'], isTrue);
      final messages = result['messages'] as List;
      expect(messages, hasLength(2));
      expect(messages[0]['content_type'], 'text');
      expect(messages[0]['content'], 'R2 flapping session cleared.');
      expect(messages[1]['content_type'], 'image');
      expect(messages[1]['content'], '', reason: 'non-text payload must not be relayed at all');
    });
  });

  group('watch/history/list', () {
    test('enrolled: false with no conversation store', () async {
      final relay = const WatchRelay();
      final result = await relay.handle('watch/history/list', {});
      expect(result, {'enrolled': false, 'turns': []});
    });

    test('returns turns newest-first, answer only present once completed', () async {
      final dir = await Directory.systemTemp.createTemp('ncfed_watch_relay_history_test_');
      addTearDown(() => dir.delete(recursive: true));
      final store = ConversationStore(dir);
      await store.addPending('task-1', 'is R2 still flapping');
      await store.updateState('task-1', 'completed', answerText: 'All clear.');
      await store.addPending('task-2', 'check bgp neighbors');
      final relay = WatchRelay(conversationStore: store);

      final result = await relay.handle('watch/history/list', {});

      expect(result['enrolled'], isTrue);
      final turns = result['turns'] as List;
      expect(turns, hasLength(2));
      // Newest first.
      expect(turns[0]['task_id'], 'task-2');
      expect(turns[0]['request_text'], 'check bgp neighbors');
      expect(turns[0]['state'], 'waiting');
      expect(turns[0].containsKey('answer_text'), isFalse);
      expect(turns[1]['task_id'], 'task-1');
      expect(turns[1]['state'], 'answered');
      expect(turns[1]['answer_text'], 'All clear.');
    });
  });

  group('watch/ask/submit', () {
    test('calls EdgeAskClient.ask and returns its task_id', () async {
      final source = _ScriptedEdgeRpcSource({
        'n2n/edge/ask': {'task_id': 'task-watch-1'},
      });
      final askClient = EdgeAskClient(source);
      final relay = WatchRelay(askClient: askClient);

      final result = await relay.handle('watch/ask/submit', {'text': 'is R2 still flapping'});

      expect(result, {'task_id': 'task-watch-1'});
      expect(source.calls.single.$2, {'text': 'is R2 still flapping'});
    });

    test('empty/whitespace-only text never calls ask() at all (FR-010)', () async {
      final source = _ScriptedEdgeRpcSource();
      final askClient = EdgeAskClient(source);
      final relay = WatchRelay(askClient: askClient);

      final result = await relay.handle('watch/ask/submit', {'text': '   '});

      expect(result['error'], isNotNull);
      expect(source.calls, isEmpty);
    });

    test('reports not enrolled when no ask client is available', () async {
      final relay = const WatchRelay();
      final result = await relay.handle('watch/ask/submit', {'text': 'hello'});
      expect(result['error'], isNotNull);
    });
  });

  group('watch/ask/status', () {
    Future<Map<String, dynamic>> statusFor(String wireState, {String? extraKey, dynamic extraValue}) async {
      final params = {'task_id': 'task-1', 'state': wireState};
      if (extraKey != null) params[extraKey] = extraValue;
      final source = _ScriptedEdgeRpcSource({'n2n/tasks/result': params});
      final askClient = EdgeAskClient(source);
      final relay = WatchRelay(askClient: askClient);
      return relay.handle('watch/ask/status', {'task_id': 'task-1'});
    }

    test('pending and working both narrow to waiting', () async {
      expect((await statusFor('submitted'))['state'], 'waiting'); // maps to TaskState.pending
      expect((await statusFor('working'))['state'], 'waiting');
    });

    test('completed narrows to answered, with the answer text carried through', () async {
      final result =
          await statusFor('completed', extraKey: 'output_text', extraValue: 'All clear.');
      expect(result['state'], 'answered');
      expect(result['answer_text'], 'All clear.');
    });

    test('failed and cancelled both narrow to failed', () async {
      expect((await statusFor('failed'))['state'], 'failed');
      expect((await statusFor('cancelled'))['state'], 'failed');
    });
  });
}
