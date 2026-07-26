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

  ConversationTurn({
    required this.taskId,
    required this.requestText,
    this.answerText,
    this.state = 'pending',
    required this.submittedAt,
  });

  Map<String, dynamic> toJson() => {
        'task_id': taskId,
        'request_text': requestText,
        'answer_text': answerText,
        'state': state,
        'submitted_at': submittedAt.toIso8601String(),
      };

  factory ConversationTurn.fromJson(Map<String, dynamic> json) => ConversationTurn(
        taskId: json['task_id'] as String,
        requestText: json['request_text'] as String,
        answerText: json['answer_text'] as String?,
        state: json['state'] as String,
        submittedAt: DateTime.parse(json['submitted_at'] as String),
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

  ConversationStore(this.directory);

  List<ConversationTurn> get turns => List.unmodifiable(_turns);

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

  /// Deletes the local conversation history. On-device only — the Border keeps
  /// its own audit trail (GAIT) and this does not and must not touch it, so
  /// clearing here is a display convenience, never an audit-evasion path.
  ///
  /// In-progress turns go too. That's deliberate: the Border keeps working and
  /// `_reconcileStaleTurns()` no longer has a local row to reconcile against,
  /// so a cleared in-flight answer simply never appears. Callers should warn
  /// when anything is still running — see the confirmation in `main.dart`.
  Future<void> clear() async {
    await load();
    _turns.clear();
    final file = _file();
    if (await file.exists()) await file.delete();
  }

  /// True when at least one turn is still awaiting an answer — lets the UI warn
  /// before [clear] discards it.
  bool get hasInProgressTurns =>
      _turns.any((t) => t.state == 'pending' || t.state == 'working');

  Future<void> addPending(String taskId, String requestText) async {
    await load();
    _turns.add(ConversationTurn(
      taskId: taskId,
      requestText: requestText,
      submittedAt: DateTime.now().toUtc(),
    ));
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
        break;
      }
    }
    await _save();
  }

  static bool _isTerminal(String state) =>
      state == 'completed' || state == 'failed' || state == 'cancelled';
}
