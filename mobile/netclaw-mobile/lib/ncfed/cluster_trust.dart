import 'dart:convert';
import 'dart:io';
import 'package:flutter/services.dart';

typedef ClusterJson = Map<String, dynamic>;
typedef PublicCrypto =
    Future<ClusterJson> Function(
      Uint8List data, {
      Uint8List? spki,
      Uint8List? signature,
    });

Future<ClusterJson> publicCrypto(
  Uint8List data, {
  Uint8List? spki,
  Uint8List? signature,
}) async {
  const channel = MethodChannel('ca.automateyournetwork.netclaw/edge_identity');
  return Map<String, dynamic>.from(
    await channel.invokeMethod('publicCrypto', {
          'data': data,
          'spki': ?spki,
          'signature': ?signature,
        })
        as Map,
  );
}

Never _bad() =>
    throw const FormatException('Cluster identity or authority changed');
void _check(bool value) {
  if (!value) _bad();
}

bool clusterUuid(dynamic v) =>
    v is String &&
    RegExp(
      r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$',
    ).hasMatch(v);
bool clusterDigest(dynamic v) =>
    v is String && RegExp(r'^[a-f0-9]{64}$').hasMatch(v);
void _exact(dynamic value, String keys) {
  _check(
    value is ClusterJson &&
        value.length == keys.split(' ').length &&
        keys.split(' ').every(value.containsKey),
  );
}

void _integer(dynamic v, int low, int high) =>
    _check(v is int && v >= low && v <= high);
void _host(dynamic v) => _check(
  v is String &&
      v.isNotEmpty &&
      v.length <= 253 &&
      RegExp(r'^[A-Za-z0-9._:\-]+$').hasMatch(v),
);
bool _identifier(dynamic v) =>
    v is String &&
    v.isNotEmpty &&
    v.length <= 200 &&
    !v.codeUnits.any((c) => c < 32);
dynamic _freeze(dynamic value) {
  if (value is Map<String, dynamic>) {
    return Map<String, dynamic>.unmodifiable(
      value.map((k, v) => MapEntry(k, _freeze(v))),
    );
  }
  if (value is List) return List<dynamic>.unmodifiable(value.map(_freeze));
  return value;
}

dynamic _sorted(dynamic value) {
  if (value is Map<String, dynamic>) {
    return {
      for (final key in value.keys.toList()..sort()) key: _sorted(value[key]),
    };
  }
  if (value is List) return value.map(_sorted).toList();
  _check(
    value == null ||
        value is String ||
        value is bool ||
        value is int && value.abs() <= 9007199254740991,
  );
  return value;
}

Uint8List clusterCanonical(dynamic value) =>
    Uint8List.fromList(utf8.encode(jsonEncode(_sorted(value))));

/// Scan object keys before decoding, so signed documents cannot use duplicate
/// keys to give different parsers different identities. No network or crypto.
dynamic clusterDecode(String source) {
  _check(utf8.encode(source).length <= 128 * 1024);
  final scan = _JsonKeys(source);
  scan.value(0);
  scan.space();
  _check(scan.at == source.length);
  return jsonDecode(source);
}

class _JsonKeys {
  final String source;
  int at = 0;
  _JsonKeys(this.source);
  void space() {
    while (at < source.length && ' \r\n\t'.contains(source[at])) {
      at++;
    }
  }

  String string() {
    _check(at < source.length && source[at] == '"');
    final start = at++;
    while (at < source.length) {
      final c = source[at++];
      if (c == '\\') {
        _check(at < source.length);
        at++;
      } else if (c == '"') {
        return jsonDecode(source.substring(start, at)) as String;
      }
    }
    _bad();
  }

  void value(int depth) {
    _check(depth <= 32);
    space();
    _check(at < source.length);
    final c = source[at];
    if (c == '"') {
      string();
      return;
    }
    if (c == '{' || c == '[') {
      final object = c == '{', end = c == '{' ? '}' : ']';
      final keys = <String>{};
      at++;
      space();
      if (at < source.length && source[at] == end) {
        at++;
        return;
      }
      while (true) {
        if (object) {
          space();
          _check(keys.add(string()));
          space();
          _check(at < source.length && source[at++] == ':');
        }
        value(depth + 1);
        space();
        _check(at < source.length);
        if (source[at] == end) {
          at++;
          return;
        }
        _check(source[at++] == ',');
      }
    }
    final start = at;
    while (at < source.length && !',]} \r\n\t'.contains(source[at])) {
      at++;
    }
    _check(at > start);
    jsonDecode(source.substring(start, at));
  }
}

class ClusterPin {
  final String clusterId, generation, anchorKeyId, manifestSha256;
  final int revision;
  const ClusterPin(
    this.clusterId,
    this.generation,
    this.anchorKeyId,
    this.revision,
    this.manifestSha256,
  );
  factory ClusterPin.fromJson(ClusterJson value) {
    _exact(
      value,
      'cluster_id generation anchor_key_id manifest_revision manifest_sha256',
    );
    _check(
      clusterUuid(value['cluster_id']) &&
          clusterUuid(value['generation']) &&
          clusterDigest(value['anchor_key_id']) &&
          clusterDigest(value['manifest_sha256']),
    );
    _integer(value['manifest_revision'], 1, 9007199254740991);
    return ClusterPin(
      value['cluster_id'],
      value['generation'],
      value['anchor_key_id'],
      value['manifest_revision'],
      value['manifest_sha256'],
    );
  }
  ClusterJson toJson() => {
    'cluster_id': clusterId,
    'generation': generation,
    'anchor_key_id': anchorKeyId,
    'manifest_revision': revision,
    'manifest_sha256': manifestSha256,
  };
  bool sameAudience(ClusterPin other) =>
      clusterId == other.clusterId &&
      generation == other.generation &&
      anchorKeyId == other.anchorKeyId;
}

class _Der {
  final Uint8List bytes;
  final int start, content, end, tag;
  _Der(this.bytes, this.start, this.content, this.end, this.tag);
  factory _Der.at(Uint8List bytes, int start) {
    _check(start >= 0 && start + 2 <= bytes.length);
    var at = start + 1, length = bytes[at++];
    if (length >= 128) {
      final count = length & 127;
      _check(
        count >= 1 &&
            count <= 3 &&
            at + count <= bytes.length &&
            bytes[at] != 0,
      );
      length = 0;
      for (var i = 0; i < count; i++) {
        length = length * 256 + bytes[at++];
      }
      _check(length >= 128);
    }
    _check(at + length <= bytes.length);
    return _Der(bytes, start, at, at + length, bytes[start]);
  }
  Uint8List get raw => Uint8List.sublistView(bytes, start, end);
  Uint8List get value => Uint8List.sublistView(bytes, content, end);
  List<_Der> children() {
    var at = content;
    final result = <_Der>[];
    while (at < end) {
      final child = _Der.at(bytes, at);
      _check(child.end <= end);
      result.add(child);
      at = child.end;
    }
    _check(at == end);
    return result;
  }
}

String _hex(List<int> bytes) =>
    bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
int _date(_Der der) {
  var text = ascii.decode(der.value);
  _check(der.tag == 23 || der.tag == 24);
  _check(RegExp(der.tag == 23 ? r'^\d{12}Z$' : r'^\d{14}Z$').hasMatch(text));
  if (der.tag == 23) {
    text = '${int.parse(text.substring(0, 2)) >= 50 ? '19' : '20'}$text';
  }
  final p = [
    int.parse(text.substring(0, 4)),
    for (var i = 4; i < 14; i += 2) int.parse(text.substring(i, i + 2)),
  ];
  final date = DateTime.utc(p[0], p[1], p[2], p[3], p[4], p[5]);
  _check(
    date.year == p[0] &&
        date.month == p[1] &&
        date.day == p[2] &&
        date.hour == p[3] &&
        date.minute == p[4] &&
        date.second == p[5],
  );
  return date.millisecondsSinceEpoch;
}

/// Strict bounded DER extraction; native P256 validates the extracted point.
Uint8List clusterCertificateSpki(String pem, int nowMs) {
  _check(pem.length <= 8192);
  final match = RegExp(
    r'^-----BEGIN CERTIFICATE-----\s+([A-Za-z0-9+/=\s]+)-----END CERTIFICATE-----\s*$',
  ).firstMatch(pem);
  _check(match != null);
  final bytes = base64.decode(match![1]!.replaceAll(RegExp(r'\s'), ''));
  final root = _Der.at(bytes, 0);
  _check(root.tag == 48 && root.end == bytes.length);
  final cert = root.children();
  _check(cert.length == 3 && cert[0].tag == 48);
  final fields = cert[0].children();
  final offset = fields[0].tag == 160 ? 1 : 0;
  _check(fields.length >= offset + 6);
  final validity = fields[offset + 3].children();
  _check(
    validity.length == 2 &&
        _date(validity[0]) <= nowMs &&
        nowMs <= _date(validity[1]),
  );
  final spki = fields[offset + 5];
  final public = spki.children();
  _check(
    spki.tag == 48 &&
        public.length == 2 &&
        public[0].tag == 48 &&
        public[1].tag == 3 &&
        public[1].value.length == 66 &&
        public[1].value[0] == 0 &&
        public[1].value[1] == 4,
  );
  _check(_hex(public[0].raw) == '301306072a8648ce3d020106082a8648ce3d030107');
  return spki.raw;
}

class ClusterBinding {
  final ClusterPin pin;
  final ClusterJson descriptor;
  ClusterBinding._(this.pin, ClusterJson value) : descriptor = _freeze(value);
  String get nodeId => descriptor['node_id'];
  String get installationId => descriptor['installation_id'];
  ClusterJson get authority => descriptor['authority'];
  List<ClusterJson> get nodes =>
      (descriptor['manifest']['manifest']['nodes'] as List).cast<ClusterJson>();
  ClusterJson node(String id) =>
      nodes.singleWhere((n) => n['node_id'] == id, orElse: _bad);
  bool get available => ['leader', 'follower'].contains(authority['state']);
  int? get epoch => authority['epoch'] as int?;
  String get origin => node(nodeId)['endpoints']['https'];
  Uri get websocketUri {
    final uri = Uri.parse(node(nodeId)['endpoints']['wss']);
    return uri.replace(port: uri.hasPort ? uri.port : 443);
  }

  static Future<ClusterBinding> verify(
    dynamic raw,
    ClusterPin pin, {
    required String origin,
    required String installationId,
    String? nodeId,
    int? nowMs,
    PublicCrypto crypto = publicCrypto,
  }) async {
    _check(clusterCanonical(raw).length <= 128 * 1024);
    final value = jsonDecode(jsonEncode(raw)) as ClusterJson;
    _exact(
      value,
      'schema_version mode cluster_id generation manifest_revision node_id installation_id manifest anchor_certificate anchor_key_id authority',
    );
    _check(
      value['schema_version'] == 1 &&
          value['mode'] == 'cluster' &&
          value['cluster_id'] == pin.clusterId &&
          value['generation'] == pin.generation &&
          value['anchor_key_id'] == pin.anchorKeyId &&
          value['installation_id'] == installationId &&
          (nodeId == null || value['node_id'] == nodeId),
    );
    _integer(value['manifest_revision'], pin.revision, 9007199254740991);
    final signed = value['manifest'];
    _exact(signed, 'schema manifest signature');
    _check(signed['schema'] == 'netclaw.ncfed.cluster-manifest.v1');
    final manifest = signed['manifest'];
    _exact(
      manifest,
      'schema_version cluster_id generation organization revision nodes limits',
    );
    _check(
      manifest['schema_version'] == 1 &&
          manifest['cluster_id'] == pin.clusterId &&
          manifest['generation'] == pin.generation &&
          manifest['revision'] == value['manifest_revision'],
    );
    _check(_identifier(manifest['organization']));
    final now = nowMs ?? DateTime.now().millisecondsSinceEpoch;
    final signature = signed['signature'];
    _exact(signature, 'algorithm key_id value');
    _check(
      signature['algorithm'] == 'ecdsa-p256-sha256' &&
          signature['key_id'] == pin.anchorKeyId &&
          signature['value'] is String &&
          RegExp(r'^[A-Za-z0-9_-]{8,200}$').hasMatch(signature['value']),
    );
    final sig = base64Url.decode(base64Url.normalize(signature['value']));
    _check(base64Url.encode(sig).replaceAll('=', '') == signature['value']);
    final body = clusterCanonical({
      'schema': signed['schema'],
      'manifest': manifest,
    });
    final verified = await crypto(
      Uint8List.fromList([
        ...utf8.encode('netclaw.ncfed.ha/manifest/v1\u0000'),
        ...body,
      ]),
      spki: clusterCertificateSpki(value['anchor_certificate'], now),
      signature: sig,
    );
    _check(
      verified['verified'] == true && verified['key_id'] == pin.anchorKeyId,
    );
    final hash = (await crypto(clusterCanonical(manifest)))['sha256'];
    _check(
      clusterDigest(hash) &&
          (value['manifest_revision'] > pin.revision ||
              hash == pin.manifestSha256),
    );
    final nodes = manifest['nodes'];
    _check(nodes is List && nodes.isNotEmpty && nodes.length <= 3);
    final ids = <String, Set<String>>{
      for (final key in ['node_id', 'installation_id', 'key_id']) key: {},
    };
    for (final node in nodes) {
      _exact(
        node,
        'node_id installation_id identity key_id certificate role endpoints',
      );
      _check(
        clusterUuid(node['node_id']) &&
            clusterUuid(node['installation_id']) &&
            node['installation_id'] != pin.clusterId &&
            node['role'] == 'border' &&
            _identifier(node['identity']),
      );
      final info = await crypto(
        Uint8List(0),
        spki: clusterCertificateSpki(node['certificate'], now),
      );
      _check(clusterDigest(node['key_id']) && info['key_id'] == node['key_id']);
      for (final key in ids.keys) {
        _check(ids[key]!.add(node[key]));
      }
      final endpoints = node['endpoints'];
      _exact(endpoints, 'cluster in2n https wss');
      for (final name in ['cluster', 'in2n']) {
        _exact(endpoints[name], 'host port server_name');
        _host(endpoints[name]['host']);
        _host(endpoints[name]['server_name']);
        _integer(endpoints[name]['port'], 1, 65535);
      }
      for (final scheme in ['https', 'wss']) {
        final uri = endpoints[scheme] is String
            ? Uri.tryParse(endpoints[scheme])
            : null;
        _check(
          uri != null &&
              endpoints[scheme].length <= 1024 &&
              uri.scheme == scheme &&
              uri.host.isNotEmpty &&
              uri.userInfo.isEmpty &&
              !uri.hasQuery &&
              !uri.hasFragment &&
              (scheme == 'https'
                  ? ['', '/'].contains(uri.path)
                  : uri.path == '/mobile/ws'),
        );
        _host(uri!.host);
        _integer(uri.hasPort ? uri.port : 443, 1, 65535);
      }
    }
    final limits = manifest['limits'];
    _exact(
      limits,
      'leader_lease_s renewal_s admission_ms clock_uncertainty_ms max_operations max_members',
    );
    _integer(limits['leader_lease_s'], 6, 60);
    _integer(limits['renewal_s'], 1, limits['leader_lease_s'] ~/ 3);
    _integer(limits['admission_ms'], 100, 10000);
    _integer(limits['clock_uncertainty_ms'], 0, 1000);
    _integer(limits['max_operations'], 1, 1024);
    _integer(limits['max_members'], 1, 32);
    final authority = value['authority'];
    _exact(authority, 'state leader_node_id epoch observed_at_ms');
    _check(
      [
        'leader',
        'follower',
        'no_quorum',
        'fenced',
        'retired',
      ].contains(authority['state']),
    );
    _integer(authority['observed_at_ms'], 0, 9007199254740991);
    _check(
      authority['leader_node_id'] == null ||
          ids['node_id']!.contains(authority['leader_node_id']),
    );
    if (authority['epoch'] != null) {
      _integer(authority['epoch'], 1, 9007199254740991);
    }
    _check(
      !['leader', 'follower'].contains(authority['state']) ||
          authority['leader_node_id'] != null && authority['epoch'] != null,
    );
    _check(authority['state'] != 'retired' && authority['state'] != 'fenced');
    final result = ClusterBinding._(
      ClusterPin(
        pin.clusterId,
        pin.generation,
        pin.anchorKeyId,
        value['manifest_revision'],
        hash,
      ),
      value,
    );
    final selected = result.node(value['node_id']);
    _check(
      selected['installation_id'] == installationId &&
          Uri.parse(selected['endpoints']['https']).origin == origin,
    );
    return result;
  }
}

/// Public HTTPS discovery never follows redirects and never carries credentials.
Future<ClusterJson> fetchClusterDescriptor(String origin) async {
  final uri = Uri.parse(origin);
  _check(uri.scheme == 'https' && uri.origin == origin);
  final client = HttpClient()..connectionTimeout = const Duration(seconds: 10);
  try {
    final request = await client.getUrl(Uri.parse('$origin/api/runtime'));
    request.followRedirects = false;
    final response = await request.close().timeout(const Duration(seconds: 10));
    _check(response.statusCode == 200);
    final bytes = <int>[];
    await for (final chunk in response.timeout(const Duration(seconds: 10))) {
      bytes.addAll(chunk);
      _check(bytes.length <= 128 * 1024);
    }
    final runtime = clusterDecode(utf8.decode(bytes));
    _check(runtime is ClusterJson && runtime['cluster'] is ClusterJson);
    return runtime['cluster'];
  } finally {
    client.close(force: true);
  }
}
