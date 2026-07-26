import 'package:flutter/material.dart';

import '../ncfed/capture_client.dart';
import '../ncfed/conversation_store.dart';
import '../ncfed/edge_ask_client.dart';
import '../ncfed/voice_transcription.dart';
import 'capture_screen.dart';

/// Chat screen (feature 067, FR-006): request/answer history, in-progress
/// state while a task is pending, and a cancel action per in-progress turn
/// (T007/T012).
class ChatScreen extends StatefulWidget {
  final EdgeAskClient askClient;
  final ConversationStore store;
  final VoiceTranscription voiceTranscription;

  ChatScreen({
    super.key,
    required this.askClient,
    required this.store,
    VoiceTranscription? voiceTranscription,
  }) : voiceTranscription = voiceTranscription ?? VoiceTranscription();

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    widget.store.load().then((_) async {
      if (mounted) setState(() => _loading = false);
      _jumpToNewest();
      await _reconcileStaleTurns();
    });
    widget.askClient.updates.listen((update) async {
      await _applyUpdate(update);
    });
  }

  @override
  void dispose() {
    _scroll.dispose();
    _controller.dispose();
    super.dispose();
  }

  /// Turns are rendered oldest-first, so offset 0 is the OLDEST message —
  /// opening the chat there means scrolling all the way down to find what you
  /// were just reading. A chat should open on the newest message, so jump to
  /// the bottom once the list has been laid out.
  ///
  /// Deferred to the next frame because `maxScrollExtent` is meaningless until
  /// the ListView has measured its children.
  void _jumpToNewest({bool animate = false}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      final target = _scroll.position.maxScrollExtent;
      if (animate) {
        _scroll.animateTo(target,
            duration: const Duration(milliseconds: 250), curve: Curves.easeOut);
      } else {
        _scroll.jumpTo(target);
      }
    });
  }

  /// Only follow the newest message when the operator is already at (or near)
  /// the bottom. Yanking the view down while they're reading back through
  /// history is worse than not following at all.
  bool get _isNearBottom {
    if (!_scroll.hasClients) return true;
    return _scroll.position.maxScrollExtent - _scroll.position.pixels < 120;
  }

  Future<void> _applyUpdate(TaskUpdate update) async {
    final stateName = switch (update.state) {
      TaskState.completed => 'completed',
      TaskState.failed => 'failed',
      TaskState.cancelled => 'cancelled',
      TaskState.working => 'working',
      _ => 'pending',
    };
    final follow = _isNearBottom;
    await widget.store.updateState(update.taskId, stateName, answerText: update.outputText);
    if (mounted) setState(() {});
    if (follow) _jumpToNewest(animate: true);
  }

  /// A task that finishes while this device is disconnected (or whose
  /// `ask_result` push simply never arrives — e.g. a connection already
  /// going stale by the time the answer was ready) has no other way to
  /// reach the phone; the Border never re-pushes a result spontaneously.
  /// Called once after the store loads: for every turn still `pending`/
  /// `working` locally, ask the Border directly whether it actually
  /// finished already.
  Future<void> _reconcileStaleTurns() async {
    final staleTaskIds = widget.store.turns
        .where((t) => t.state == 'pending' || t.state == 'working')
        .map((t) => t.taskId)
        .toList();
    for (final taskId in staleTaskIds) {
      try {
        final update = await widget.askClient.result(taskId);
        if (update.state != TaskState.pending && update.state != TaskState.unknown) {
          await _applyUpdate(update);
        }
      } catch (_) {
        // Still disconnected, or the Border is unreachable right now --
        // the next reconnect will retry; never blocks the rest of the UI.
      }
    }
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    final taskId = await widget.askClient.ask(text);
    await widget.store.addPending(taskId, text);
    setState(() {});
    _jumpToNewest(animate: true);
  }

  Future<void> _recordVoice() async {
    final result = await widget.voiceTranscription.recordAndAsk(widget.askClient);
    if (result == null) return; // nothing heard — no request sent
    final (taskId, text) = result;
    await widget.store.addPending(taskId, text);
    if (mounted) setState(() {});
    _jumpToNewest(animate: true);
  }

  Future<void> _capturePhoto() async {
    // feature 068, US2: a bare capture with no accompanying text is a valid
    // request (FR-005) -- captureAndAsk() sends nothing at all if the
    // operator declines/cancels (CaptureScreen returns null).
    final client = CaptureClient(
      askClient: widget.askClient,
      capture: (type) => CaptureScreen.capture(context, type),
    );
    final taskId = await client.captureAndAsk('camera.capture');
    if (taskId == null) return;
    await widget.store.addPending(taskId, '[Photo]');
    if (mounted) setState(() {});
    _jumpToNewest(animate: true);
  }

  Future<void> _cancel(String taskId) async {
    await widget.askClient.cancel(taskId);
    // The Border pushes n2n/edge/ask_result with state='cancelled' once the
    // worker actually stops — ConversationStore.updateState's terminal-state
    // guard means a completed answer that races the cancel is preserved.
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final turns = List.of(widget.store.turns)
      ..sort((a, b) => a.submittedAt.compareTo(b.submittedAt));
    return Column(
      children: [
        Expanded(
          child: turns.isEmpty
              ? const Center(child: Text('Ask your Border something.'))
              : ListView.builder(
                  controller: _scroll,
                  itemCount: turns.length,
                  itemBuilder: (context, index) => _TurnTile(
                    turn: turns[index],
                    onCancel: () => _cancel(turns[index].taskId),
                  ),
                ),
        ),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _controller,
                    decoration: const InputDecoration(hintText: 'Ask something…'),
                    onSubmitted: (_) => _send(),
                  ),
                ),
                IconButton(icon: const Icon(Icons.camera_alt), onPressed: _capturePhoto),
                IconButton(icon: const Icon(Icons.mic), onPressed: _recordVoice),
                IconButton(icon: const Icon(Icons.send), onPressed: _send),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _TurnTile extends StatelessWidget {
  final ConversationTurn turn;
  final VoidCallback onCancel;

  const _TurnTile({required this.turn, required this.onCancel});

  bool get _inProgress => turn.state == 'pending' || turn.state == 'working';

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(turn.requestText, style: const TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            if (_inProgress)
              Row(
                children: [
                  const SizedBox(
                      width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                  const SizedBox(width: 8),
                  const Text('Working…'),
                  const Spacer(),
                  TextButton(onPressed: onCancel, child: const Text('Cancel')),
                ],
              )
            else if (turn.state == 'cancelled')
              const Text('Cancelled', style: TextStyle(color: Colors.grey))
            else if (turn.state == 'failed')
              Text(turn.answerText ?? 'Failed', style: const TextStyle(color: Colors.red))
            else
              Text(turn.answerText ?? ''),
          ],
        ),
      ),
    );
  }
}
