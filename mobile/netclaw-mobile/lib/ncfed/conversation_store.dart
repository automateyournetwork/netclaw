import 'dart:convert';
import 'dart:io';

/// One request/answer turn in the phone's conversation with its Border
/// (feature 067, FR-006/FR-007).
class ConversationTurn {
  final String taskId;
  final String requestText;
  String? answerText;
  String state; // 'pending' | 'working' | 'completed' | 'failed' | 'cancelled'
  final DateTime submittedAt;
  // Absolute path to a locally-saved copy of a photo this turn sent, if any
  // -- purely for showing what was sent in the UI; never re-read to build
  // the wire request (that already went out as base64 at send time).
  final String? photoPath;
  // Clears once the operator explicitly acknowledges this turn (073/FR-012)
  // -- distinct from [state]; a completed-but-unacknowledged turn still
  // counts toward the unread badge.
  bool acknowledged;
  // Which surface submitted this turn -- "phone" or "watch" (073/FR-016).
  // Purely informational; no requirement reads it back for behavior.
  String origin;

  ConversationTurn({
    required this.taskId,
    required this.requestText,
    this.answerText,
    this.state = 'pending',
    required this.submittedAt,
    this.photoPath,
    this.acknowledged = false,
    this.origin = 'phone',
  });

  Map<String, dynamic> toJson() => {
        'task_id': taskId,
        'request_text': requestText,
        'answer_text': answerText,
        'state': state,
        'submitted_at': submittedAt.toIso8601String(),
        'photo_path': photoPath,
        'acknowledged': acknowledged,
        'origin': origin,
      };

  /// A turn written before 073 has no `acknowledged`/`origin` keys at all.
  /// `acknowledged` MUST default to `true` (already-acknowledged) on a
  /// missing key -- never `false` -- or every turn ever submitted before
  /// this feature shipped would suddenly appear unread after upgrade
  /// (research D5). `origin` defaults to `"phone"` on a missing key: the
  /// watch had no way to write into this store at all before FR-016, so a
  /// pre-existing turn was never watch-originated.
  factory ConversationTurn.fromJson(Map<String, dynamic> json) => ConversationTurn(
        taskId: json['task_id'] as String,
        requestText: json['request_text'] as String,
        answerText: json['answer_text'] as String?,
        state: json['state'] as String,
        submittedAt: DateTime.parse(json['submitted_at'] as String),
        photoPath: json['photo_path'] as String?,
        acknowledged: json['acknowledged'] as bool? ?? true,
        origin: json['origin'] as String? ?? 'phone',
      );
}

/// Per-device persisted conversation history (FR-007: independent per
/// enrolled edge node, no cross-device sync — trivially true since this is
/// already per-installation; survives app restart/reboot, SC-004). Mirrors
/// 066's `MessageFeedStore` JSON-Lines pattern exactly, but turns are
/// mutable (a pending turn gets its answer filled in later), so this store
/// rewrites the whole file on each save rather than appending.
class ConversationStore {
  final Directory directory;
  final List<ConversationTurn> _turns = [];
  bool _loaded = false;

  /// Fires the moment a turn transitions INTO `completed` -- from either
  /// `updateState()` call site (`chat_screen.dart`'s foreground poll or
  /// `turn_reconciler.dart`'s post-reconnect catch-up), regardless of which
  /// tab the operator is looking at. `main.dart` uses this single hook to
  /// post the chat-answer notification (073/FR-002) rather than needing one
  /// at each call site. Mirrors `EdgeClient.onDisconnected`'s
  /// settable-after-construction pattern.
  void Function(ConversationTurn turn)? onCompleted;

  ConversationStore(this.directory);

  List<ConversationTurn> get turns => List.unmodifiable(_turns);

  /// Count of terminal-state turns not yet acknowledged -- feeds the
  /// combined app badge (073/FR-008). An in-progress turn has no answer to
  /// acknowledge yet, so it never counts as unread.
  int get unreadCount => _turns.where((t) => _isTerminal(t.state) && !t.acknowledged).length;

  File _file() => File('${directory.path}/ncfed_conversation.json');

  Future<void> load() async {
    if (_loaded) return;
    _loaded = true;
    final file = _file();
    if (!await file.exists()) return;
    final raw = await file.readAsString();
    if (raw.trim().isEmpty) return;
    final list = jsonDecode(raw) as List<dynamic>;
    _turns
      ..clear()
      ..addAll(list.map((e) => ConversationTurn.fromJson(e as Map<String, dynamic>)));
  }

  Future<void> _save() async {
    await _file().writeAsString(jsonEncode(_turns.map((t) => t.toJson()).toList()));
  }

  /// True when at least one turn is still awaiting an answer — lets the UI warn
  /// before [clear] discards it.
  bool get hasInProgressTurns =>
      _turns.any((t) => t.state == 'pending' || t.state == 'working');

  Future<void> addPending(String taskId, String requestText,
      {List<int>? photoBytes, String origin = 'phone'}) async {
    await load();
    String? photoPath;
    if (photoBytes != null) {
      final file = File('${directory.path}/photo_$taskId.jpg');
      await file.writeAsBytes(photoBytes);
      photoPath = file.path;
    }
    _turns.add(ConversationTurn(
      taskId: taskId,
      requestText: requestText,
      submittedAt: DateTime.now().toUtc(),
      photoPath: photoPath,
      origin: origin,
    ));
    await _save();
  }

  /// Marks the turn with this [taskId] as acknowledged -- clears its unread
  /// state but leaves it visible in [turns] (073/FR-012).
  Future<void> acknowledge(String taskId) async {
    await load();
    for (final t in _turns) {
      if (t.taskId == taskId) {
        t.acknowledged = true;
        break;
      }
    }
    await _save();
  }

  /// Permanently removes the turn with this [taskId] (073/FR-013) -- unlike
  /// [clear], which removes many turns at once. Also removes its saved
  /// photo file, if any, matching [clear]'s own cleanup.
  Future<void> delete(String taskId) async {
    await load();
    final matches = _turns.where((t) => t.taskId == taskId);
    final photoPath = matches.isEmpty ? null : matches.first.photoPath;
    if (photoPath != null) {
      final file = File(photoPath);
      if (await file.exists()) await file.delete();
    }
    _turns.removeWhere((t) => t.taskId == taskId);
    await _save();
  }

  Future<void> updateState(String taskId, String state, {String? answerText}) async {
    await load();
    for (final t in _turns) {
      if (t.taskId == taskId) {
        // Never let a stray late update flip an already-terminal turn (the
        // cancel-after-completion race from spec.md's edge cases).
        if (_isTerminal(t.state)) return;
        t.state = state;
        if (answerText != null) t.answerText = answerText;
        await _save();
        if (state == 'completed') onCompleted?.call(t);
        return;
      }
    }
    await _save();
  }

  static bool _isTerminal(String state) =>
      state == 'completed' || state == 'failed' || state == 'cancelled';

  /// Deletes the local conversation history, including every saved photo file
  /// -- without this, there was no way to manage a conversation that only
  /// ever grows, and `photo_*.jpg` files would accumulate on disk forever
  /// with nothing ever deleting them. On-device only — the Border keeps its
  /// own audit trail (GAIT) and this does not and must not touch it, so
  /// clearing here is a display convenience, never an audit-evasion path.
  ///
  /// **In-progress turns are PRESERVED by default.** This previously deleted
  /// them along with everything else, which destroyed work the Border was
  /// still actively doing: the answer arrives, reconciliation finds no local
  /// row to attach it to, and it is silently dropped forever. Reported by a
  /// tester — "it clears all messages including the pending actual working
  /// messages that are processing currently". Clearing *history* should not
  /// cancel the *future*, and the operator asking to tidy a transcript is not
  /// asking to throw away a running request.
  ///
  /// Pass `includeInProgress: true` for the old all-or-nothing behaviour — the
  /// caller must have explicitly confirmed that intent.
  ///
  /// Note: preserving a turn is *not* the same as cancelling it. A request the
  /// operator genuinely wants stopped should go through
  /// `EdgeAskClient.cancel()`, which tells the Border to stop working; deleting
  /// the local row never did that.
  Future<void> clear({bool includeInProgress = false}) async {
    await load();
    final kept = includeInProgress
        ? const <ConversationTurn>[]
        : _turns.where((t) => !_isTerminal(t.state)).toList();

    for (final turn in _turns) {
      if (kept.contains(turn)) continue; // its photo is still on display
      final path = turn.photoPath;
      if (path == null) continue;
      final file = File(path);
      if (await file.exists()) await file.delete();
    }

    _turns
      ..clear()
      ..addAll(kept);

    if (kept.isEmpty) {
      final file = _file();
      if (await file.exists()) await file.delete();
    } else {
      // Rewrite rather than delete, so the surviving in-flight turns are still
      // there after a restart and can still be reconciled.
      await _save();
    }
  }
}
