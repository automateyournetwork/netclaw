import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import '../cloud/owner_client.dart';

/// Native cloud-owner workflow. It does not access EdgeClient, enrollment keys,
/// headless Chat, local services or a gateway. Back returns to the existing profile.
class CloudOwnerScreen extends StatefulWidget {
  final CloudOwnerStore? store;
  final OwnerTransport? transport;
  final CloudOwnerClient? initialClient;
  const CloudOwnerScreen({
    super.key,
    this.store,
    this.transport,
    this.initialClient,
  });
  @override
  State<CloudOwnerScreen> createState() => _CloudOwnerScreenState();
}

class _CloudOwnerScreenState extends State<CloudOwnerScreen>
    with WidgetsBindingObserver {
  late final CloudOwnerStore _store;
  CloudOwnerClient? _client;
  final _origin = TextEditingController(),
      _installation = TextEditingController(),
      _ticket = TextEditingController();
  List<CloudProfile> _profiles = [];
  bool _busy = false, _covered = false, _reviewed = false;
  String? _error;
  int _member = 0, _model = 0, _tool = 0;
  Timer? _expiry;
  @override
  void initState() {
    super.initState();
    _store = widget.store ?? widget.initialClient?.store ?? CloudOwnerStore();
    _client = widget.initialClient;
    WidgetsBinding.instance.addObserver(this);
    _loadProfiles();
  }

  Future<void> _loadProfiles() async {
    try {
      final rows = await _store.profiles();
      if (mounted) setState(() => _profiles = rows);
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = const CloudOwnerError('storage_invalid').toString(),
        );
      }
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      _client?.suspend();
      _ticket.clear();
      if (mounted) {
        setState(() {
          _covered = true;
          _reviewed = false;
        });
      }
    } else {
      if (mounted) setState(() => _covered = false);
      final client = _client;
      if (client != null) _resume(client);
    }
  }

  Future<void> _resume(CloudOwnerClient client) async {
    // Wait for an interrupted native request to release its lock. No mutation is
    // replayed; resume only verifies identity/session and reads the same reference.
    try {
      await client.resume();
      if (mounted && identical(client, _client)) {
        setState(() {
          _error = null;
          _reviewed = false;
          _member = 0;
          _model = 0;
          _tool = 0;
        });
      }
    } catch (error) {
      if (mounted) setState(() => _error = _message(error));
    }
  }

  String _message(Object error) => error is CloudOwnerError
      ? error.toString()
      : const CloudOwnerError('request_refused').toString();
  Future<void> _run(Future<void> Function() action) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } catch (error) {
      if (mounted) setState(() => _error = _message(error));
    } finally {
      if (mounted) {
        setState(() {
          _busy = false;
          _reviewed = false;
        });
        _expiry?.cancel();
        final expiry =
            _client?.operation?['review']?['limits']?['expires_at_ms'];
        if (expiry is int && expiry > DateTime.now().millisecondsSinceEpoch) {
          _expiry = Timer(
            Duration(
              milliseconds: expiry - DateTime.now().millisecondsSinceEpoch + 1,
            ),
            () {
              if (mounted) setState(() => _reviewed = false);
            },
          );
        }
      }
    }
  }

  Future<void> _connect() => _run(() async {
    final profile = CloudProfile(
      _origin.text.trim(),
      _installation.text.trim(),
    );
    final client = CloudOwnerClient(
      profile,
      store: _store,
      transport: widget.transport,
    );
    _client?.suspend();
    _client = client;
    _member = 0;
    _model = 0;
    _tool = 0;
    await client.initialize();
    await _loadProfiles();
  });
  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _client?.suspend();
    _expiry?.cancel();
    _origin.dispose();
    _installation.dispose();
    _ticket.dispose();
    super.dispose();
  }

  Widget _json(String label, dynamic value) => Column(
    crossAxisAlignment: CrossAxisAlignment.start,
    children: [
      Text(label, style: Theme.of(context).textTheme.titleMedium),
      const SizedBox(height: 8),
      SelectableText(
        const JsonEncoder.withIndent('  ').convert(value),
        key: ValueKey(label),
        style: const TextStyle(fontFamily: 'monospace', fontSize: 12),
      ),
      const SizedBox(height: 16),
    ],
  );
  Widget _button(String text, VoidCallback? action) => Padding(
    padding: const EdgeInsets.only(bottom: 8),
    child: FilledButton(
      onPressed: _busy || _covered ? null : action,
      child: Text(text),
    ),
  );

  @override
  Widget build(BuildContext context) {
    final client = _client, op = client?.operation, ref = client?.reference;
    final ready = client?.operationsReady == true;
    final members = (client?.catalog?['members'] as List?) ?? [];
    final member = members.isEmpty ? null : members[_member] as Json;
    final models = (member?['model_profiles'] as List?) ?? [],
        tools = (member?['tools'] as List?) ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('Cloud Border owner')),
      body: _covered
          ? const Center(child: Text('Cloud session covered'))
          : SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Protected read-only operations. Enrolled Chat, voice, camera, watch and local service controls belong to your separate edge profile.',
                    ),
                    const SizedBox(height: 16),
                    if (_busy) const LinearProgressIndicator(),
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          _error!,
                          key: const ValueKey('cloud-error'),
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ),
                    if (client == null || !client.identityVerified) ...[
                      if (_profiles.isNotEmpty)
                        DropdownButtonFormField<String>(
                          decoration: const InputDecoration(
                            labelText: 'Saved cloud profile',
                          ),
                          isExpanded: true,
                          items: _profiles
                              .map(
                                (profile) => DropdownMenuItem(
                                  value: profile.key,
                                  child: Text(
                                    '${profile.origin} · ${profile.installationId}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              )
                              .toList(),
                          onChanged: _busy
                              ? null
                              : (key) {
                                  final p = _profiles.firstWhere(
                                    (p) => p.key == key,
                                  );
                                  _origin.text = p.origin;
                                  _installation.text = p.installationId;
                                },
                        ),
                      TextField(
                        controller: _origin,
                        key: const ValueKey('cloud-origin'),
                        autocorrect: false,
                        enableSuggestions: false,
                        decoration: const InputDecoration(
                          labelText: 'Exact HTTPS origin',
                          hintText: 'https://border.example.com',
                        ),
                      ),
                      TextField(
                        controller: _installation,
                        key: const ValueKey('cloud-installation'),
                        autocorrect: false,
                        enableSuggestions: false,
                        decoration: const InputDecoration(
                          labelText: 'Expected installation UUID',
                        ),
                      ),
                      const SizedBox(height: 12),
                      _button('Verify cloud Border', _connect),
                    ],
                    if (client != null) ...[
                      SelectableText(
                        'Border: ${client.profile.origin}\nInstallation: ${client.profile.installationId}',
                        key: const ValueKey('cloud-identity'),
                      ),
                      const SizedBox(height: 12),
                      if (!ready && client.identityVerified) ...[
                        TextField(
                          controller: _ticket,
                          key: const ValueKey('cloud-ticket'),
                          obscureText: true,
                          autocorrect: false,
                          enableSuggestions: false,
                          enableIMEPersonalizedLearning: false,
                          decoration: const InputDecoration(
                            labelText: 'One-use owner sign-in ticket',
                          ),
                        ),
                        _button('Sign in as owner', () {
                          final ticket = _ticket.text.trim();
                          _ticket.clear();
                          _run(() => client.login(ticket));
                        }),
                      ],
                      if (ready) ...[
                        Text(
                          client.openLab
                              ? 'Connected: ${client.principal!['display_name']}'
                              : 'Signed in: ${client.principal!['display_name']}',
                          key: const ValueKey('cloud-owner'),
                        ),
                        const SizedBox(height: 12),
                        if (ref == null) ...[
                          const Text(
                            'Select one catalogued read. Preparing the complete review does not execute it. The review identifies the member, model/provider and exact input sent for execution.',
                          ),
                          if (members.isEmpty)
                            const Text(
                              'No eligible member profiles are available.',
                            ),
                          if (members.isNotEmpty) ...[
                            DropdownButtonFormField<int>(
                              key: ValueKey('members-${client.profile.key}'),
                              initialValue: _member,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Member',
                              ),
                              items: List.generate(
                                members.length,
                                (i) => DropdownMenuItem(
                                  value: i,
                                  child: Text(
                                    members[i]['member']['member_id'],
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ),
                              onChanged: _busy
                                  ? null
                                  : (i) => setState(() {
                                      _member = i!;
                                      _model = 0;
                                      _tool = 0;
                                    }),
                            ),
                            DropdownButtonFormField<int>(
                              key: ValueKey('models-$_member'),
                              initialValue: models.isEmpty ? null : _model,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Model profile',
                              ),
                              items: List.generate(
                                models.length,
                                (i) => DropdownMenuItem(
                                  value: i,
                                  child: Text(
                                    '${models[i]['profile_id']} · ${models[i]['provider']} / ${models[i]['model']}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ),
                              onChanged: _busy
                                  ? null
                                  : (i) => setState(() => _model = i!),
                            ),
                            DropdownButtonFormField<int>(
                              key: ValueKey('tools-$_member'),
                              initialValue: tools.isEmpty ? null : _tool,
                              isExpanded: true,
                              decoration: const InputDecoration(
                                labelText: 'Read-only call',
                              ),
                              items: List.generate(
                                tools.length,
                                (i) => DropdownMenuItem(
                                  value: i,
                                  child: Text(
                                    '${tools[i]['tool']} · ${tools[i]['device_ref']}',
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                ),
                              ),
                              onChanged: _busy
                                  ? null
                                  : (i) => setState(() => _tool = i!),
                            ),
                            if (tools.isNotEmpty)
                              _json(
                                'Exact candidate arguments',
                                tools[_tool]['arguments'],
                              ),
                            _button(
                              'Prepare review',
                              models.isNotEmpty && tools.isNotEmpty
                                  ? () => _run(
                                      () => client.prepare(
                                        _member,
                                        _model,
                                        _tool,
                                      ),
                                    )
                                  : null,
                            ),
                          ],
                        ],
                        if (ref != null) ...[
                          SelectableText(
                            'Operation: ${ref['operation_id'] ?? 'Awaiting admission'}\nClient nonce: ${ref['client_nonce']}\nState: ${op?['state'] ?? 'Unknown'}\nRecorded attempts: ${op?['attempt_count'] ?? 'Unconfirmed'}',
                            key: const ValueKey('cloud-operation'),
                          ),
                          if (ref['decision_sent'] == true &&
                              op?['state'] == 'review_pending')
                            const Text(
                              'A decision was already sent for this reference. Recover or reconcile it; approval cannot be sent again from this device.',
                            ),
                          if (client.uncertain ||
                              op?['reconciliation_required'] == true)
                            const Text(
                              'Work may have been accepted or executed. Recover this same reference; no preparation or approval will be repeated automatically.',
                            ),
                          _button(
                            'Check same operation',
                            () => _run(client.status),
                          ),
                          if (ref['operation_id'] != null)
                            _button(
                              'Reconcile existing operation',
                              () => _run(client.reconcile),
                            ),
                          if (op?['review'] != null) ...[
                            SelectableText(
                              'Revision: ${op!['revision']}\nReview digest: ${op['review_digest']}',
                            ),
                            _json('Complete immutable review', op['review']),
                            CheckboxListTile(
                              key: const ValueKey('cloud-review-confirmation'),
                              value: _reviewed,
                              onChanged: _busy || !client.canDecide('approve')
                                  ? null
                                  : (value) => setState(
                                      () => _reviewed = value ?? false,
                                    ),
                              title: const Text(
                                'I reviewed this exact member, provider/model, arguments and limits. Approve this operation once.',
                              ),
                            ),
                            _button(
                              'Approve once',
                              _reviewed && client.canDecide('approve')
                                  ? () => _run(
                                      () => client.decide(
                                        'approve',
                                        revision: op['revision'],
                                        reviewDigest: op['review_digest'],
                                      ),
                                    )
                                  : null,
                            ),
                            _button(
                              'Deny',
                              client.canDecide('deny')
                                  ? () => _run(
                                      () => client.decide(
                                        'deny',
                                        revision: op['revision'],
                                        reviewDigest: op['review_digest'],
                                      ),
                                    )
                                  : null,
                            ),
                          ],
                          if (op?['approval'] != null)
                            _json('Recorded approval', op!['approval']),
                          if (op?['result'] != null) ...[
                            Text(
                              'Signature and bindings verified by Border: ${op!['result']['verified'] == true ? 'Yes' : 'Not confirmed'}\nDurable Border ACK: ${op['result']['durable_ack'] == true ? 'Yes' : 'Not confirmed'}\nACK delivery: ${op['result']['ack_delivery_pending'] == true ? 'Pending reconciliation' : 'No pending delivery reported'}',
                              key: const ValueKey('cloud-receipt'),
                            ),
                            SelectableText(
                              'Result digest: ${op['result']['digest'] ?? 'Not reported'}',
                            ),
                            if (op['result']['verified'] == true)
                              _json(
                                'Verified execution evidence and audit references',
                                op['result']['evidence'],
                              ),
                          ],
                          if (op?['error_code'] != null)
                            Text('Recorded outcome: ${op!['error_code']}'),
                          if (client.canRemove)
                            _button(
                              client.notSubmitted
                                  ? 'Discard unsubmitted reference'
                                  : 'Remove resolved reference',
                              () => _run(client.removeResolvedReference),
                            ),
                        ],
                        if (!client.openLab)
                          _button('Sign out', () => _run(client.logout)),
                      ],
                      TextButton(
                        onPressed: _busy
                            ? null
                            : () {
                                client.suspend();
                                _ticket.clear();
                                setState(() {
                                  _client = null;
                                  _reviewed = false;
                                });
                                _loadProfiles();
                              },
                        child: const Text('Choose cloud profile'),
                      ),
                    ],
                  ],
                ),
              ),
            ),
    );
  }
}
