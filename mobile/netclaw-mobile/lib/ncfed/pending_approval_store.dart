import 'dart:convert';
import 'dart:io';

/// Durable holding pen for approval pushes that arrive during a headless
/// `BGAppRefreshTask` window (103/US3), where no live `ApprovalClient` exists
/// to hold them in memory — that class is in-memory-only by design (068) and
/// would silently lose an approval delivered while no UI is running,
/// EVEN THOUGH the Border correctly marks it delivered the moment the
/// background handler ACKs the RPC. `main.dart` drains this into the real
/// `ApprovalClient` on the next foreground launch, then clears it.
class PendingApprovalStore {
  final Directory directory;
  PendingApprovalStore(this.directory);

  File _file() => File('${directory.path}/ncfed_pending_approvals.jsonl');

  /// Returns every approval `n2n/edge/message` payload recorded since the
  /// last drain, and clears the file. Call exactly once per foreground
  /// launch, before anything else might reasonably act on approvals.
  Future<List<Map<String, dynamic>>> loadAndClear() async {
    final file = _file();
    if (!await file.exists()) return [];
    final lines = await file.readAsLines();
    await file.delete();
    return [
      for (final line in lines)
        if (line.trim().isNotEmpty) jsonDecode(line) as Map<String, dynamic>,
    ];
  }

  Future<void> append(Map<String, dynamic> params) async {
    await _file().writeAsString('${jsonEncode(params)}\n', mode: FileMode.append, flush: true);
  }
}
