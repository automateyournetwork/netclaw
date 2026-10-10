import 'conversation_store.dart';
import 'edge_ask_client.dart';
import 'live_activity.dart';

/// Wires the in-flight query Live Activity's full lifecycle (spec 113,
/// User Story 3) to events [store] and [askClient] already produce --
/// [store.onAdded] starts one per new turn (FR-004), [store.onTerminal] ends
/// it (FR-007), and a direct subscription to [askClient.updates] updates it
/// on a progress ping (FR-006) using the Border's own free-text detail
/// verbatim, never a member count.
///
/// Wired once at the `main.dart`/`_HomeShellState` level, alongside the
/// existing `approvalClient.pending.listen(...)` wiring — NOT inside
/// `chat_screen.dart`, whose own `askClient.updates` listener only runs
/// while that screen is mounted (research.md's "single hook, not duplicated
/// per call site" reasoning, matching why `onCompleted`/`onAdded`/
/// `onTerminal` exist on `ConversationStore` in the first place). A terminal
/// `ask_result` arriving while Chat isn't mounted still needs to reach
/// `ConversationStore.updateState(...)` for `onTerminal` to fire at all, so
/// this also calls it directly here — `updateState`'s own terminal-state
/// guard makes this safe to call a second time if Chat is also mounted and
/// does the same thing independently.
void wireAskLiveActivity({
  required ConversationStore store,
  required EdgeAskClient askClient,
  required LiveActivityLike liveActivity,
}) {
  store.onAdded = (turn) {
    liveActivity.startAsk(taskId: turn.taskId, questionPreview: turn.requestText);
  };
  store.onTerminal = (turn) {
    liveActivity.endAsk(taskId: turn.taskId, state: turn.state);
  };
  askClient.updates.listen((update) async {
    if (update.progressDetail != null) {
      liveActivity.updateAsk(taskId: update.taskId, progressDetail: update.progressDetail!);
      return;
    }
    final stateName = update.state.wireName;
    await store.updateState(update.taskId, stateName, answerText: update.outputText ?? (update.state.needsAttention ? update.state.explanation : null));
  });
}
