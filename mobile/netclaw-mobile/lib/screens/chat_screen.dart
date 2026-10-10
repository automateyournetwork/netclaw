import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/semantics.dart';
import 'package:flutter/services.dart';
import 'package:share_plus/share_plus.dart';

import '../ncfed/capture_client.dart';
import '../ncfed/conversation_search.dart';
import '../ncfed/conversation_store.dart';
import '../ncfed/edge_ask_client.dart';
import '../ncfed/haptics.dart';
import '../ncfed/turn_reconciler.dart';
import '../ncfed/voice_transcription.dart';
import 'answer_body.dart';
import 'capture_screen.dart';
import 'highlighted_text.dart';

/// Chat screen (feature 067, FR-006): request/answer history, in-progress
/// state while a task is pending, and a cancel action per in-progress turn
/// (T007/T012).
class ChatScreen extends StatefulWidget {
  final EdgeAskClient askClient;
  final ConversationStore store;
  final VoiceTranscription voiceTranscription;

  /// When a chat notification is tapped (073/FR-006, `NotificationDeepLink`),
  /// the turn it referred to is scrolled into view and highlighted —
  /// mirrors `FeedScreen.highlightPushedAt`'s pattern exactly.
  final String? highlightTaskId;

  /// Fires after an acknowledge or delete action (073/FR-012/FR-013) so
  /// `main.dart` can recompute the combined app badge (FR-008).
  final VoidCallback? onChanged;

  /// Injectable so tests never touch the real share platform channel
  /// (109/research.md R4).
  final Future<ShareResult> Function(ShareParams params)? shareAction;

  /// Injectable so tests never touch the real haptic platform channel
  /// (109/research.md R4).
  final Haptics haptics;

  ChatScreen({
    super.key,
    required this.askClient,
    required this.store,
    this.highlightTaskId,
    this.onChanged,
    this.shareAction,
    VoiceTranscription? voiceTranscription,
    Haptics? haptics,
  })  : voiceTranscription = voiceTranscription ?? VoiceTranscription(),
        haptics = haptics ?? Haptics();

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen>
    with WidgetsBindingObserver {
  final _controller = TextEditingController();
  final _scroll = ScrollController();
  final _highlightKey = GlobalKey();
  bool _loading = true;
  bool _listening = false;
  /// taskId -> latest progress detail from n2n/edge/task_progress.
  final Map<String, String> _progress = {};

  /// 109/US6: transient search/filter state -- deliberately never persisted
  /// (FR-015), reset to defaults on every fresh mount.
  final _searchController = TextEditingController();
  String _searchQuery = '';
  final Set<String> _selectedStates = {};
  final Set<String> _selectedOrigins = {};

  static const _stateChoices = ['pending', 'working', 'completed', 'failed', 'cancelled', 'outcome_unknown', 'interrupted', 'cancellation_requested'];
  static const _originChoices = ['phone', 'watch', 'siri'];

  @override
  void initState() {
    super.initState();
    widget.askClient.store ??= widget.store;
    WidgetsBinding.instance.addObserver(this);
    widget.store.load().then((_) async {
      if (mounted) setState(() => _loading = false);
      if (widget.highlightTaskId != null) {
        _scrollToHighlight();
      } else {
        _jumpToNewest();
      }
      await _reconcileStaleTurns();
    });
    widget.askClient.updates.listen((update) async {
      await _applyUpdate(update);
    });
  }

  @override
  void didUpdateWidget(ChatScreen old) {
    super.didUpdateWidget(old);
    // A second notification tap while the chat is already open.
    if (widget.highlightTaskId != null && widget.highlightTaskId != old.highlightTaskId) {
      _scrollToHighlight();
    }
  }

  /// Deferred to the next frame: the target tile only has a render object
  /// once the list has been laid out. Mirrors `FeedScreen._scrollToHighlight`.
  void _scrollToHighlight() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final ctx = _highlightKey.currentContext;
      if (ctx != null) Scrollable.ensureVisible(ctx, alignment: 0.3);
    });
  }

  @override
  void dispose() {
    // Release the microphone if we're torn down mid-recording. The plugin is
    // explicit that "each listen session should be ended with either stop or
    // cancel, for example in the dispose method of a Widget" — and because the
    // recogniser is a single platform-wide resource, a session left running
    // here silently poisons the NEXT recording: initialize() still succeeds,
    // listen() attaches to a busy recogniser, and no audio is captured. That is
    // the reported "sometimes it just doesn't record", reached by navigating
    // away while the mic was live.
    WidgetsBinding.instance.removeObserver(this);
    widget.voiceTranscription.cancel();
    _scroll.dispose();
    _controller.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Same leak by a different route: backgrounding the app. The OS may revoke
    // microphone access without telling the recogniser, leaving a session that
    // looks live and captures nothing. Keeping the audio stream open while
    // hidden would also be the wrong thing to do regardless.
    if (state != AppLifecycleState.resumed && _listening) {
      widget.voiceTranscription.cancel();
    }
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
    // A progress ping is a liveness hint, not a state change — record the
    // detail and repaint, but don't touch the persisted turn.
    if (update.progressDetail != null) {
      _progress[update.taskId] = update.progressDetail!;
      if (mounted) setState(() {});
      return;
    }
    _progress.remove(update.taskId); // terminal update supersedes any hint
    final stateName = update.state.wireName;
    final follow = _isNearBottom;
    await widget.store.updateState(update.taskId, stateName, answerText: update.outputText ?? (update.state.needsAttention ? update.state.explanation : null));
    if (stateName == 'completed') widget.haptics.chatAnswerCompleted();
    if (mounted) setState(() {});
    if (follow) _jumpToNewest(animate: true);
  }

  /// First-load recovery. The same reconciliation also runs on every
  /// reconnect, driven by HomeShell — see [reconcileStaleTurns] for why it must
  /// not depend on this widget's lifecycle.
  Future<void> _reconcileStaleTurns() async {
    await reconcileStaleTurns(widget.askClient, widget.store,
        onChanged: () { if (mounted) setState(() {}); });
  }

  Future<void> _send() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    try {
      final taskId = await widget.askClient.ask(text);
      await widget.store.addPending(taskId, text);
      _controller.clear();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$error')));
    }
    if (!mounted) return;
    setState(() {});
    _jumpToNewest(animate: true);
  }

  Future<void> _recordVoice() async {
    if (_listening) return; // already recording — ignore a double tap
    setState(() => _listening = true);
    // Announce for screen-reader users, who get none of the visual state.
    _announce('Listening');
    try {
      final result = await widget.voiceTranscription.recordAndAsk(
        widget.askClient,
        // Previously every voice failure was a silent no-op: the operator
        // tapped the mic and nothing whatsoever happened. Always say why.
        onFailure: (failure) {
          if (!mounted) return;
          // Don't report a cancellation back at the operator who just asked
          // for it.
          if (failure.failure == VoiceFailure.cancelled) return;
          ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(failure.message ?? 'Voice request failed.'),
            duration: const Duration(seconds: 4),
          ));
        },
      );
      if (result == null) return; // nothing sent; the operator has been told why
      final (taskId, text) = result;
      await widget.store.addPending(taskId, text);
      if (mounted) setState(() {});
      _jumpToNewest(animate: true);
    } finally {
      if (mounted) setState(() => _listening = false);
      _announce('Stopped listening');
    }
  }

  /// Speaks recording state to assistive tech. Recording start/stop is exactly
  /// what a live region is for: a blind operator otherwise has no way to know
  /// whether the mic is open.
  void _announce(String message) {
    if (!mounted) return;
    SemanticsService.sendAnnouncement(
        View.of(context), message, TextDirection.ltr);
  }

  /// Re-sends a turn's original request as a NEW turn, leaving the failed one
  /// in place as a record. Requested by a tester: a failed turn was a dead end
  /// with no way to try again short of retyping the whole thing. A photo
  /// turn's bytes ARE retained locally (`ConversationTurn.photoPath`), so
  /// this actually resends the photo too rather than asking the operator to
  /// retake it.
  Future<void> _retry(ConversationTurn turn) async {
    if (!['failed', 'cancelled', 'interrupted'].contains(turn.state)) return;
    var text = turn.requestText;
    Map<String, dynamic>? attachment;
    final photoPath = turn.photoPath;
    if (photoPath != null) {
      final file = File(photoPath);
      if (await file.exists()) {
        attachment = {'content_type': 'image', 'content': base64Encode(await file.readAsBytes())};
      }
      // requestText carries a " [Photo]"/"[Photo]" suffix added purely for
      // display (see _capturePhoto) -- strip it so a retry doesn't literally
      // ask "... [Photo]" as if that were part of the question.
      text = text.replaceAll(RegExp(r'\s?\[Photo\]$'), '');
    }
    if (text.trim().isEmpty && attachment == null) {
      // Nothing to resend at all -- a bare photo turn whose file has since
      // gone missing, or an empty request. Say so rather than doing nothing.
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Nothing to resend — take the photo again.'),
        ));
      }
      return;
    }
    final taskId = await widget.askClient.ask(text, attachment: attachment);
    List<int>? photoBytes;
    if (attachment != null) photoBytes = base64Decode(attachment['content'] as String);
    await widget.store.addPending(taskId, turn.requestText, photoBytes: photoBytes);
    if (mounted) setState(() {});
    _jumpToNewest(animate: true);
  }

  Future<void> _capturePhoto() async {
    if (widget.askClient.attachmentsUnavailable) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Photo and video Ask Border requests are unavailable on this Hermes Border.')));
      return;
    }
    // Whatever's already typed becomes the question that goes with the
    // photo (feature 068, US2) -- same pattern _send() uses for a typed-only
    // request. Previously this was never read at all, so a photo could only
    // ever be sent bare with no way to ask something about it.
    final text = _controller.text.trim();
    List<int>? capturedBytes;
    // feature 068, US2: a bare capture with no accompanying text is a valid
    // request (FR-005) -- captureAndAsk() sends nothing at all if the
    // operator declines/cancels (CaptureScreen returns null).
    final client = CaptureClient(
      askClient: widget.askClient,
      capture: (type) => CaptureScreen.capture(context, type),
    );
    final taskId = await client.captureAndAsk(
      'camera.capture',
      text: text,
      onCaptured: (result) => capturedBytes = result.bytes,
    );
    if (taskId == null) return;
    _controller.clear();
    await widget.store.addPending(
      taskId,
      text.isEmpty ? '[Photo]' : '$text [Photo]',
      photoBytes: capturedBytes,
    );
    if (mounted) setState(() {});
    _jumpToNewest(animate: true);
  }

  Future<void> _cancel(String taskId) async {
    await widget.askClient.cancel(taskId);
    // The Border pushes n2n/edge/ask_result with state='cancelled' once the
    // worker actually stops — ConversationStore.updateState's terminal-state
    // guard means a completed answer that races the cancel is preserved.
  }

  Future<void> _acknowledge(String taskId) async {
    await widget.store.acknowledge(taskId);
    if (mounted) setState(() {});
    widget.onChanged?.call();
  }

  Future<void> _delete(String taskId) async {
    await widget.store.delete(taskId);
    if (mounted) setState(() {});
    widget.onChanged?.call();
  }

  /// 109/US6: live text search plus state/origin filter chips (FR-012/
  /// FR-013). Search/filter state lives entirely in this widget's own
  /// State -- never persisted (FR-015), never touching `widget.store`.
  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'Search chat',
              prefixIcon: const Icon(Icons.search),
              isDense: true,
              suffixIcon: _searchQuery.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear),
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _searchQuery = '');
                      },
                    ),
              border: const OutlineInputBorder(),
            ),
            onChanged: (value) => setState(() => _searchQuery = value),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            children: [
              for (final state in _stateChoices)
                FilterChip(
                  label: Text(state),
                  selected: _selectedStates.contains(state),
                  onSelected: (selected) => setState(() {
                    if (selected) {
                      _selectedStates.add(state);
                    } else {
                      _selectedStates.remove(state);
                    }
                  }),
                ),
              for (final origin in _originChoices)
                FilterChip(
                  label: Text(origin),
                  selected: _selectedOrigins.contains(origin),
                  onSelected: (selected) => setState(() {
                    if (selected) {
                      _selectedOrigins.add(origin);
                    } else {
                      _selectedOrigins.remove(origin);
                    }
                  }),
                ),
            ],
          ),
          const SizedBox(height: 4),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    final allTurns = List.of(widget.store.turns)
      ..sort((a, b) => a.submittedAt.compareTo(b.submittedAt));
    final turns = filterTurns(allTurns,
        query: _searchQuery, states: _selectedStates, origins: _selectedOrigins);
    final filtering =
        _searchQuery.trim().isNotEmpty || _selectedStates.isNotEmpty || _selectedOrigins.isNotEmpty;
    return Column(
      children: [
        _buildSearchBar(),
        Expanded(
          child: allTurns.isEmpty
              ? const Center(child: Text('Ask your Border something.'))
              : turns.isEmpty
                  ? const Center(child: Text('No matching turns.'))
                  : ListView.builder(
                      controller: _scroll,
                      itemCount: turns.length,
                      itemBuilder: (context, index) {
                        final highlighted = !filtering &&
                            widget.highlightTaskId != null &&
                            turns[index].taskId == widget.highlightTaskId;
                        return _TurnTile(
                          key: highlighted ? _highlightKey : null,
                          turn: turns[index],
                          highlighted: highlighted,
                          progressDetail: _progress[turns[index].taskId],
                          onCancel: () => _cancel(turns[index].taskId),
                          onCheckStatus: _reconcileStaleTurns,
                          onRetry: () => _retry(turns[index]),
                          onAcknowledge: () => _acknowledge(turns[index].taskId),
                          onDelete: () => _delete(turns[index].taskId),
                          shareAction: widget.shareAction,
                          highlightQuery: _searchQuery,
                        );
                      },
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
                // While recording, tapping the mic must SUBMIT what was said —
                // it reads as "stop" and stopping a recording means keeping it.
                // This previously called cancel(), which the plugin documents as
                // guaranteeing no final result, so an operator who finished
                // speaking and tapped stop silently lost their entire request.
                // Discarding is now a separate, deliberately distinct control.
                if (_listening)
                  IconButton(
                    icon: const Icon(Icons.close),
                    tooltip: 'Discard recording',
                    onPressed: () => widget.voiceTranscription.cancel(),
                  ),
                IconButton(
                  // Visible listening state — the mic previously gave no
                  // indication it was live, so a working recording looked
                  // identical to a broken one.
                  icon: Icon(_listening ? Icons.stop_circle : Icons.mic_none,
                      color: _listening ? Theme.of(context).colorScheme.error : null),
                  tooltip: _listening ? 'Done — send what I said' : 'Voice request',
                  onPressed: _listening
                      ? () => widget.voiceTranscription.finishNow()
                      : _recordVoice,
                ),
                IconButton(icon: const Icon(Icons.send), onPressed: _send),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

enum _AnswerAction { copyAnswer, copyBoth, share }

class _TurnTile extends StatelessWidget {
  final ConversationTurn turn;
  final VoidCallback onCancel;
  final VoidCallback onCheckStatus;
  final VoidCallback onRetry;
  final VoidCallback onAcknowledge;
  final VoidCallback onDelete;
  final bool highlighted;

  /// Live detail from the Border for an in-progress turn (e.g. "Still working
  /// on this — 120s so far"). Null when there's nothing to add beyond
  /// "Working…".
  final String? progressDetail;

  /// Injectable so tests never touch the real share platform channel (109/
  /// research.md R4's injectable-function-with-production-default pattern).
  final Future<ShareResult> Function(ShareParams params)? shareAction;

  /// 109/US6: the active search query, for highlighting matches in the
  /// question header and (when not Markdown-rendered) the answer body.
  final String highlightQuery;

  const _TurnTile({
    super.key,
    required this.turn,
    required this.onCancel,
    required this.onCheckStatus,
    required this.onRetry,
    required this.onAcknowledge,
    required this.onDelete,
    this.highlighted = false,
    this.progressDetail,
    this.shareAction,
    this.highlightQuery = '',
  });

  bool get _isRetryable => turn.state == 'failed' || turn.state == 'cancelled' || turn.state == 'interrupted';

  bool get _inProgress => turn.state == 'pending' || turn.state == 'working';

  /// 109/FR-005: the overflow menu / long-press actions operate on the
  /// answer, so they only make sense once there is one.
  bool get _hasAnswer => (turn.answerText ?? '').isNotEmpty;

  bool get _isTerminal => turn.state == 'completed' || turn.state == 'failed';

  /// Matches `ConversationStore.unreadCount`'s own definition (073/FR-011):
  /// an in-progress turn has nothing to acknowledge yet.
  bool get _isUnread => !_inProgress && !turn.acknowledged;

  @override
  Widget build(BuildContext context) {
    final card = _card(context);
    // "Or if you click on fail it asks to retry" — make the whole tile a retry
    // affordance, not just the button, so a failed turn is never a dead end.
    // 109/FR-005's long-press fast-path lives in AnswerBody's own
    // contextMenuBuilder (see answer_body.dart's doc comment for why it
    // isn't an ancestor onLongPress here).
    if (!_isRetryable) return card;
    return InkWell(onTap: () => _confirmRetry(context), child: card);
  }

  Future<void> _showAnswerActions(BuildContext context) async {
    final action = await showModalBottomSheet<_AnswerAction>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          ListTile(
            leading: const Icon(Icons.copy),
            title: const Text('Copy answer'),
            onTap: () => Navigator.pop(ctx, _AnswerAction.copyAnswer),
          ),
          ListTile(
            leading: const Icon(Icons.copy_all),
            title: const Text('Copy question + answer'),
            onTap: () => Navigator.pop(ctx, _AnswerAction.copyBoth),
          ),
          ListTile(
            leading: const Icon(Icons.share),
            title: const Text('Share'),
            onTap: () => Navigator.pop(ctx, _AnswerAction.share),
          ),
        ]),
      ),
    );
    if (action == null || !context.mounted) return;
    await _runAnswerAction(context, action);
  }

  /// Shared by the overflow menu (bottom sheet, above) and the long-press
  /// context menu (answer_body.dart's `buildActions`) — one implementation,
  /// two entry points, per FR-005's "not a second, different action."
  Future<void> _runAnswerAction(BuildContext context, _AnswerAction action) async {
    switch (action) {
      case _AnswerAction.copyAnswer:
        await Clipboard.setData(ClipboardData(text: turn.answerText ?? ''));
        if (context.mounted) {
          ScaffoldMessenger.of(context)
              .showSnackBar(const SnackBar(content: Text('Answer copied')));
        }
      case _AnswerAction.copyBoth:
        await Clipboard.setData(
            ClipboardData(text: '${turn.requestText}\n\n${turn.answerText ?? ''}'));
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Copied')));
        }
      case _AnswerAction.share:
        final share = shareAction ?? SharePlus.instance.share;
        await share(ShareParams(
          text: turn.answerText,
          files: turn.photoPath != null ? [XFile(turn.photoPath!)] : null,
        ));
    }
  }

  /// Long-press context-menu buttons for `AnswerBody.buildActions` — the
  /// same three actions as the overflow menu.
  List<ContextMenuButtonItem> _answerContextMenuItems(BuildContext context) => [
        ContextMenuButtonItem(
          label: 'Copy answer',
          onPressed: () {
            ContextMenuController.removeAny();
            _runAnswerAction(context, _AnswerAction.copyAnswer);
          },
        ),
        ContextMenuButtonItem(
          label: 'Copy question + answer',
          onPressed: () {
            ContextMenuController.removeAny();
            _runAnswerAction(context, _AnswerAction.copyBoth);
          },
        ),
        ContextMenuButtonItem(
          label: 'Share',
          onPressed: () {
            ContextMenuController.removeAny();
            _runAnswerAction(context, _AnswerAction.share);
          },
        ),
      ];

  Future<void> _confirmRetry(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Retry this request?'),
        content: Text(turn.requestText),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Retry')),
        ],
      ),
    );
    if (ok ?? false) onRetry();
  }

  Future<void> _confirmDelete(BuildContext context) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete this question?'),
        content: const Text('This cannot be undone.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          TextButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Delete')),
        ],
      ),
    );
    if (ok ?? false) onDelete();
  }

  Widget _card(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      color: highlighted ? scheme.secondaryContainer : null,
      shape: highlighted
          ? RoundedRectangleBorder(
              side: BorderSide(color: scheme.secondary, width: 2),
              borderRadius: BorderRadius.circular(12),
            )
          : null,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                // Unread indicator (073/FR-011) -- a deliberate, explicit
                // acknowledge clears it (FR-012); merely viewing this tab
                // does not (spec Assumptions).
                if (_isUnread) ...[
                  Icon(Icons.circle, size: 8, color: scheme.primary),
                  const SizedBox(width: 6),
                ],
                Expanded(
                  child: HighlightedText(
                    turn.requestText,
                    query: highlightQuery,
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                ),
                if (_isUnread)
                  IconButton(
                    icon: const Icon(Icons.check_circle_outline, size: 20),
                    tooltip: 'Acknowledge',
                    onPressed: onAcknowledge,
                  ),
                // 109/FR-005: always-visible overflow menu -- the primary
                // way to reach copy/share; long-press (build(), above) is a
                // fast-path shortcut to this identical menu.
                if (_hasAnswer)
                  IconButton(
                    icon: const Icon(Icons.more_vert, size: 20),
                    tooltip: 'Answer actions',
                    onPressed: () => _showAnswerActions(context),
                  ),
                IconButton(
                  icon: const Icon(Icons.delete_outline, size: 20),
                  tooltip: 'Delete',
                  onPressed: () => _confirmDelete(context),
                ),
              ],
            ),
            if (turn.photoPath != null) ...[
              const SizedBox(height: 8),
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: Image.file(
                  File(turn.photoPath!),
                  height: 160,
                  fit: BoxFit.cover,
                  errorBuilder: (context, error, stackTrace) => Text('[Photo unavailable]',
                      style: TextStyle(color: scheme.onSurfaceVariant)),
                ),
              ),
            ],
            const SizedBox(height: 8),
            if (_inProgress)
              Row(
                children: [
                  const SizedBox(
                      width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
                  const SizedBox(width: 8),
                  Expanded(child: Text(progressDetail ?? 'Working…')),
                  TextButton(onPressed: onCancel, child: const Text('Cancel')),
                ],
              )
            else if (['outcome_unknown', 'cancellation_requested', 'interrupted'].contains(turn.state))
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(parseTaskState(turn.state).explanation, style: TextStyle(color: scheme.error)),
                if (turn.state != 'interrupted')
                  TextButton(onPressed: onCheckStatus, child: const Text('Check status')),
                if (turn.state == 'interrupted')
                  TextButton(onPressed: onRetry, child: const Text('Retry')),
              ])
            else if (turn.state == 'cancelled')
              Row(children: [
                Text('Cancelled', style: TextStyle(color: scheme.onSurfaceVariant)),
                const Spacer(),
                TextButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh, size: 18),
                    label: const Text('Retry')),
              ])
            else if (turn.state == 'failed')
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                turn.answerText == null
                    ? Text('Failed', style: TextStyle(color: scheme.error))
                    : AnswerBody(
                        text: turn.answerText!,
                        isTerminal: _isTerminal,
                        textColor: scheme.error,
                        buildActions: _answerContextMenuItems,
                        highlightQuery: highlightQuery,
                      ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton.icon(
                      onPressed: onRetry,
                      icon: const Icon(Icons.refresh, size: 18),
                      label: const Text('Retry')),
                ),
              ])
            else
              AnswerBody(
                text: turn.answerText ?? '',
                isTerminal: _isTerminal,
                buildActions: _answerContextMenuItems,
                highlightQuery: highlightQuery,
              ),
          ],
        ),
      ),
    );
  }
}
