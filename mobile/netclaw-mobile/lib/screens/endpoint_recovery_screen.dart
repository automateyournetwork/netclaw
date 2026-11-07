import 'package:flutter/material.dart';
import '../ncfed/endpoint_recovery.dart';
import '../ncfed/edge_client.dart';
import '../ncfed/edge_identity.dart';
import '../ncfed/enrollment_store.dart';

/// The current channel is closed before entering this screen. Only an explicit
/// same-host port is accepted; reconnect to it uses the retained native key.
class EndpointRecoveryScreen extends StatefulWidget {
  final EnrollmentStore store;
  final StoredEnrollment enrollment;
  final VoidCallback onReconnect;
  final RetainedDeviceReconnect? reconnect;
  final EdgeIdentity identity;
  const EndpointRecoveryScreen({
    super.key,
    required this.store,
    required this.enrollment,
    required this.onReconnect,
    this.reconnect,
    this.identity = const EdgeIdentity(),
  });
  @override
  State<EndpointRecoveryScreen> createState() => _EndpointRecoveryScreenState();
}

class _EndpointRecoveryScreenState extends State<EndpointRecoveryScreen>
    with WidgetsBindingObserver {
  late final _port = TextEditingController(
    text: '${widget.enrollment.borderPort}',
  );
  bool _busy = false;
  int _generation = 0;
  String? _error;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) _generation++;
  }

  Future<void> _change() async {
    if (_busy) return;
    final generation = _generation;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final arguments = int.tryParse(_port.text.trim());
      if (arguments == null) throw const FormatException('Invalid port');
      await replaceEnrollmentPort(
        store: widget.store,
        expected: widget.enrollment,
        port: arguments,
        identity: widget.identity,
        reconnect: widget.reconnect ?? EdgeClient.reconnect,
        isCurrent: () => mounted && generation == _generation,
      );
      if (mounted && generation == _generation) widget.onReconnect();
    } catch (error) {
      if (mounted) setState(() => _error = recoveryFailureMessage(error));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  void dispose() {
    _generation++;
    WidgetsBinding.instance.removeObserver(this);
    _port.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Recover connection')),
    body: ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text('Retained Border: ${widget.enrollment.clawDomain}'),
        const SizedBox(height: 12),
        const Text(
          'Enter the replacement secure connection port supplied by your Border operator. '
          'The device key, Border identity and saved operations stay the same.',
        ),
        TextField(
          controller: _port,
          enabled: !_busy,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(
            labelText: 'Secure connection port',
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: Text(_error!),
          ),
        FilledButton(
          onPressed: _busy ? null : _change,
          child: const Text('Verify and update port'),
        ),
        TextButton(
          onPressed: _busy ? null : widget.onReconnect,
          child: const Text('Reconnect saved endpoint'),
        ),
      ],
    ),
  );
}
