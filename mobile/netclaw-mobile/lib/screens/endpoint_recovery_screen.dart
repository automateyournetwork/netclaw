import 'package:flutter/material.dart';
import '../ncfed/endpoint_recovery.dart';
import '../ncfed/edge_client.dart';
import '../ncfed/edge_identity.dart';
import '../ncfed/enrollment_store.dart';
import '../ncfed/cluster_trust.dart';

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
  ClusterBinding? _cluster;
  String? _nodeId;
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    if (widget.enrollment.clusterPin != null) {
      retainedCluster(widget.enrollment)
          .then((cluster) {
            if (mounted) setState(() => _cluster = cluster);
          })
          .catchError((Object error) {
            if (mounted) setState(() => _error = recoveryFailureMessage(error));
          });
    }
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
      if (widget.enrollment.clusterPin != null) {
        if (_cluster == null || _nodeId == null) {
          throw const FormatException('Select a verified Border');
        }
        await replaceClusterEndpoint(
          store: widget.store,
          expected: widget.enrollment,
          nodeId: _nodeId!,
          identity: widget.identity,
          reconnect: widget.reconnect ?? EdgeClient.reconnect,
          isCurrent: () => mounted && generation == _generation,
        );
        if (mounted && generation == _generation) widget.onReconnect();
        return;
      }
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
        Text(
          widget.enrollment.clusterPin != null
              ? 'Select a Border from the retained signed cluster manifest. Your device identity and saved operations stay the same.'
              : 'Enter the replacement secure connection port supplied by your Border operator. '
                    'The device key, Border identity and saved operations stay the same.',
        ),
        if (widget.enrollment.clusterPin != null)
          DropdownButtonFormField<String>(
            initialValue: _nodeId,
            decoration: const InputDecoration(
              labelText: 'Trusted cluster Border',
            ),
            items: (_cluster?.nodes ?? [])
                .where(
                  (node) => node['node_id'] != widget.enrollment.clusterNodeId,
                )
                .map(
                  (node) => DropdownMenuItem<String>(
                    value: node['node_id'],
                    child: Text(node['endpoints']['https']),
                  ),
                )
                .toList(),
            onChanged: _busy ? null : (node) => setState(() => _nodeId = node),
          )
        else
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
          child: Text(
            widget.enrollment.clusterPin != null
                ? 'Verify and select Border'
                : 'Verify and update port',
          ),
        ),
        TextButton(
          onPressed: _busy ? null : widget.onReconnect,
          child: const Text('Reconnect saved endpoint'),
        ),
      ],
    ),
  );
}
