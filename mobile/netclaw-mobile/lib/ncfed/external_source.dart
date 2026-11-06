/// Border-attested native eN2N activity. Never parsed from answer text.
class ExternalSource {
  final String peer;
  final String kind;
  final String requestId;
  final String? taskId;
  const ExternalSource({required this.peer, required this.kind, required this.requestId, this.taskId});

  Map<String, dynamic> toJson() => {
    'peer': peer, 'kind': kind, 'request_id': requestId,
    'task_id': taskId, 'trust': 'remote-untrusted',
  };

  static List<ExternalSource> parse(Object? value) {
    if (value is! List || value.length > 16) {
      return const [];
    }
    final id = RegExp(r'^[A-Za-z0-9_.:-]{1,200}$');
    final sources = <ExternalSource>[];
    for (final row in value) {
      if (row is! Map || row['trust'] != 'remote-untrusted' ||
          row['peer'] is! String || !id.hasMatch(row['peer'] as String) ||
          row['request_id'] is! String || !id.hasMatch(row['request_id'] as String) ||
          !['tool', 'skill', 'chat'].contains(row['kind']) ||
          row['task_id'] != null && (row['task_id'] is! String || !id.hasMatch(row['task_id'] as String))) {
        continue;
      }
      sources.add(ExternalSource(peer: row['peer'] as String, kind: row['kind'] as String,
          requestId: row['request_id'] as String, taskId: row['task_id'] as String?));
    }
    return List.unmodifiable(sources);
  }
}
