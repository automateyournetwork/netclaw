import 'dart:convert';
import 'package:flutter/material.dart';
import '../cloud/owner_client.dart';

bool _same(dynamic a, dynamic b) {
  if (a is Map && b is Map) {
    return a.length == b.length &&
        a.keys.every((k) => b.containsKey(k) && _same(a[k], b[k]));
  }
  if (a is List && b is List) {
    return a.length == b.length &&
        List.generate(a.length, (i) => i).every((i) => _same(a[i], b[i]));
  }
  return a == b;
}

bool _digest(dynamic v) => v is String && RegExp(r'^[a-f0-9]{64}$').hasMatch(v);

/// Receipt provenance and independently verified native facts never verify prose.
Json operationEvidence(Json operation) {
  final result = operation['result'];
  final output = result?['evidence']?['output'];
  final tool = output is Map ? output['tool'] : null;
  final call = operation['review']?['tool_call'];
  Map? facts;
  var summary = 'Unavailable';
  if (result?['verified'] == true && tool is Map && tool['output'] is Map) {
    if (call?['tool'] == 'pyats_run_show_command' && tool['parsed'] == true) {
      facts = tool['output'];
    } else if (tool['schemaVersion'] == 1 &&
        tool['mcp_calls'] == 1 &&
        call?['tool'] == tool['tool'] &&
        [
          'endpoint_sha256',
          'source_sha256',
          'skill_sha256',
          'mcp_schema_sha256',
        ].every((k) => _digest(tool[k])) &&
        tool['endpoint_sha256'] == call?['endpoint_sha256'] &&
        _same(call?['arguments'], tool['arguments'])) {
      facts = tool['output'];
    }
  }
  if (facts?['schema_version'] == 1 &&
      ['subnet_calculator', 'subnet_calculator_v6'].contains(call?['tool'])) {
    final family = call['tool'] == 'subnet_calculator' ? 4 : 6;
    final bits = family == 4 ? 32 : 128;
    final prefix = facts!['prefix_length'],
        count = facts['address_count'],
        network = facts['network'];
    if (tool['independent_verification'] != true ||
        !_digest(tool['native_result_sha256']) ||
        facts['family'] != family ||
        call['arguments'] is! Map ||
        call['arguments'].length != 1 ||
        network != call['arguments']['cidr'] ||
        network is! String ||
        prefix is! int ||
        prefix < 0 ||
        prefix > bits ||
        int.tryParse(network.split('/').last) != prefix ||
        count is! String ||
        !RegExp(r'^[1-9]\d{0,38}$').hasMatch(count) ||
        BigInt.parse(count) != (BigInt.one << (bits - prefix))) {
      facts = null;
    } else if (family == 4 &&
        facts['usable_count'] ==
            (BigInt.parse(count) - BigInt.from(prefix < 31 ? 2 : 0))
                .toString()) {
      summary = '$network · ${facts['usable_count']} usable hosts';
    } else if (family == 6 &&
        facts['subnets_64'] ==
            (prefix <= 64 ? BigInt.one << (64 - prefix) : BigInt.zero)
                .toString()) {
      summary = '$network · $count addresses';
    } else {
      facts = null;
    }
  }
  final commentary = output is Map ? output['model_answer'] : null;
  return {
    'facts': facts,
    'summary': summary,
    'commentary': result?['verified'] == true && commentary is String
        ? commentary
        : null,
  };
}

class OperationEvidence extends StatelessWidget {
  final Json operation;
  const OperationEvidence({super.key, required this.operation});
  @override
  Widget build(BuildContext context) {
    if (operation['result']?['verified'] != true) {
      return const SizedBox.shrink();
    }
    final value = operationEvidence(operation);
    const encoder = JsonEncoder.withIndent('  ');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (value['facts'] != null) ...[
          const Text(
            'Authoritative tool facts',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          if (value['summary'] != 'Unavailable')
            SelectableText(value['summary']),
          SelectableText(
            encoder.convert(value['facts']),
            key: const ValueKey('authoritative-tool-facts'),
          ),
        ],
        if (value['commentary'] != null) ...[
          const Text(
            'Unverified model commentary',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const Text(
            'Model commentary can be inaccurate. Use the authoritative tool facts.',
          ),
          SelectableText(
            value['commentary'],
            key: const ValueKey('unverified-model-commentary'),
          ),
        ],
        ExpansionTile(
          title: const Text('Signed receipt and audit references'),
          children: [
            const Text(
              'The signature verifies the receipt and its bindings. Model commentary is not independently verified.',
            ),
            SelectableText(encoder.convert(operation['result']['evidence'])),
          ],
        ),
      ],
    );
  }
}
