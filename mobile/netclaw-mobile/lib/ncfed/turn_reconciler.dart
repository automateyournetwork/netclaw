import 'conversation_store.dart';
import 'edge_ask_client.dart';

/// Asks the Border for the outcome of every turn this device still believes is
/// running, and folds the answers into [store].
///
/// This exists because `n2n/edge/ask_result` is best-effort: the Border pushes a
/// finished answer only if a live channel is there at that instant, and never
/// re-pushes spontaneously. A phone reconnects constantly (a real device
/// reconnected four times during one two-minute turn), so a completed answer
/// routinely has no channel to land on and the turn sits on "Working" forever
/// with the answer sitting on the Border.
///
/// It used to live in `ChatScreen.initState`, which meant it ran only when that
/// widget was constructed. That was already fragile — it happened to re-run
/// because switching tabs destroyed and rebuilt the screen — and it stopped
/// running at all once the tab bodies moved to an IndexedStack (which keeps all
/// four mounted so the chat's scroll position survives). Recovery must not
/// depend on UI lifecycle, so it lives here and is driven by real events:
/// first load, and every reconnect.
///
/// Idempotent and safe to call concurrently: a turn already in a terminal state
/// is skipped, and a still-unfinished turn is left alone for the next pass.
/// Never throws — a Border that is unreachable right now simply means the next
/// reconnect retries.
Future<int> reconcileStaleTurns(
  EdgeAskClient askClient,
  ConversationStore store, {
  void Function()? onChanged,
}) async {
  askClient.store ??= store;
  final stale = store.turns.where((t) => ['pending', 'working', 'outcome_unknown', 'cancellation_requested'].contains(t.state)).toList();
  var recovered = 0;
  for (final turn in stale) {
    try {
      final update = await askClient.recover(turn);
      if (update.state == TaskState.pending) continue;
      await store.updateState(turn.taskId, update.state.wireName,
          answerText: update.outputText ?? (update.state.needsAttention ? update.state.explanation : null));
      recovered++;
    } catch (_) {
      // Read-only reconciliation may fail on an old Border or after another
      // disconnect. Keep a visible, durable uncertainty instead of a spinner.
      if (turn.state != 'cancellation_requested') {
        await store.updateState(turn.taskId, 'outcome_unknown', answerText: TaskState.outcomeUnknown.explanation);
        recovered++;
      }
    }
  }
  if (recovered > 0) onChanged?.call();
  return recovered;
}
