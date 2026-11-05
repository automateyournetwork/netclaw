import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../cloud/owner_client.dart';

/// Paired NetClaw calculators retain separate immutable reviews and decisions.
class CombinedOperationsPanel extends StatefulWidget {
  final CloudOwnerClient client;
  final bool busy;
  final Future<void> Function(Future<void> Function()) run;
  const CombinedOperationsPanel({
    super.key,
    required this.client,
    required this.busy,
    required this.run,
  });
  @override
  State<CombinedOperationsPanel> createState() =>
      _CombinedOperationsPanelState();
}

class _CombinedOperationsPanelState extends State<CombinedOperationsPanel> {
  final Map<int, int> selected = {4: 0, 6: 0};
  final Map<int, String> reviewed = {};
  Timer? expiry;
  @override
  void didUpdateWidget(covariant CombinedOperationsPanel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.busy || !identical(widget.client, oldWidget.client)) {
      reviewed.clear();
    }
    expiry?.cancel();
    final times =
        (widget.client.combined?['children'] as List? ?? [])
            .map((c) => c['review']['limits']['expires_at_ms'])
            .whereType<int>()
            .where((t) => t > DateTime.now().millisecondsSinceEpoch)
            .toList()
          ..sort();
    if (times.isNotEmpty) {
      expiry = Timer(
        Duration(
          milliseconds: times.first - DateTime.now().millisecondsSinceEpoch + 1,
        ),
        () {
          if (mounted) setState(reviewed.clear);
        },
      );
    }
  }

  @override
  void dispose() {
    expiry?.cancel();
    super.dispose();
  }

  Widget json(String label, dynamic value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label),
      SelectableText(
        const JsonEncoder.withIndent('  ').convert(value),
        key: ValueKey(label),
      ),
    ],
  );
  Widget button(String label, Future<void> Function()? action) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: FilledButton(
      onPressed: widget.busy || action == null
          ? null
          : () => widget.run(action),
      child: Text(label),
    ),
  );
  @override
  Widget build(BuildContext context) {
    final client = widget.client,
        ref = client.combinedReference,
        parent = client.combined,
        choices = client.combinedChoices();
    if (ref == null &&
        (client.reference != null ||
            choices[4]!.isEmpty ||
            choices[6]!.isEmpty)) {
      return const SizedBox.shrink();
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(),
        Text(
          'Local IPv4 + cloud IPv6',
          style: Theme.of(context).textTheme.titleLarge,
        ),
        const Text(
          'Two separate NetClaw approvals, with Ollama on each member. Provider API charge is zero; compute and transfer costs remain separate.',
        ),
        if (ref == null) ...[
          for (final family in [4, 6])
            DropdownButtonFormField<int>(
              key: ValueKey('combined-ipv$family'),
              initialValue: selected[family]! < choices[family]!.length
                  ? selected[family]
                  : 0,
              isExpanded: true,
              decoration: InputDecoration(labelText: 'IPv$family calculator'),
              items: [
                for (var i = 0; i < choices[family]!.length; i++)
                  DropdownMenuItem(
                    value: i,
                    child: Text(
                      '${choices[family]![i]['member_id']} · ${choices[family]![i]['cidr']}',
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
              ],
              onChanged: widget.busy
                  ? null
                  : (value) => setState(() => selected[family] = value!),
            ),
          button(
            'Prepare both reviews',
            () => client.prepareCombined([
              for (final family in [4, 6])
                choices[family]![selected[family]! < choices[family]!.length
                    ? selected[family]!
                    : 0],
            ]),
          ),
        ] else ...[
          SelectableText(
            'Combined request: ${ref['parent_id'] ?? 'Awaiting confirmation'}\nState: ${parent?['state'] ?? (ref['not_submitted'] == true ? 'Not submitted' : 'Unknown')}',
          ),
          if (client.combinedUncertain)
            const Text(
              'Check this same request. No preparation, approval or model call is repeated automatically.',
            ),
          if (ref['not_submitted'] != true)
            button('Check combined status', client.combinedStatus),
          for (final c in parent?['children'] ?? []) ...[
            Text(
              'IPv${c['family']} · ${c['state']}',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            SelectableText(
              'Operation: ${c['operation_id']}\nRevision: ${c['revision']}\nReview digest: ${c['review_digest']}',
            ),
            json('IPv${c['family']} immutable review', c['review']),
            CheckboxListTile(
              key: ValueKey('combined-review-${c['index']}'),
              value: reviewed[c['index']] == c['review_digest'],
              onChanged:
                  widget.busy ||
                      !client.canDecideCombined(c['index'], 'approve')
                  ? null
                  : (value) => setState(
                      () => value == true
                          ? reviewed[c['index']] = c['review_digest']
                          : reviewed.remove(c['index']),
                    ),
              title: Text(
                'I reviewed this exact IPv${c['family']} member, provider/model, CIDR and limits.',
              ),
            ),
            button(
              'Approve IPv${c['family']} once',
              reviewed[c['index']] == c['review_digest'] &&
                      client.canDecideCombined(c['index'], 'approve')
                  ? () => client.decideCombined(
                      c['index'],
                      'approve',
                      revision: c['revision'],
                      reviewDigest: c['review_digest'],
                    )
                  : null,
            ),
            button(
              'Deny IPv${c['family']}',
              client.canDecideCombined(c['index'], 'deny')
                  ? () => client.decideCombined(
                      c['index'],
                      'deny',
                      revision: c['revision'],
                      reviewDigest: c['review_digest'],
                    )
                  : null,
            ),
            if (c['result'] != null) ...[
              Text(
                'Signed result verified: ${c['result']['verified'] == true ? 'Yes' : 'Not confirmed'} · Durable ACK: ${c['result']['durable_ack'] == true ? 'Yes' : 'Not confirmed'}',
              ),
              if (c['result']['verified'] == true)
                json(
                  'IPv${c['family']} verified evidence',
                  c['result']['evidence'],
                ),
            ],
            if (c['error_code'] != null)
              Text('Recorded outcome: ${c['error_code']}'),
          ],
          if (ref['parent_id'] != null)
            button(
              'Cancel remaining children',
              ref['cancel_sent'] == true ? null : client.cancelCombined,
            ),
          if (client.canRemoveCombined)
            button(
              ref['not_submitted'] == true
                  ? 'Discard unsubmitted combined reference'
                  : 'Remove resolved combined reference',
              client.removeCombinedReference,
            ),
        ],
      ],
    );
  }
}
