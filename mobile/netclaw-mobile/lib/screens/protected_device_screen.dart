import 'dart:async';
import 'package:flutter/material.dart';
import '../cloud/owner_client.dart';
import '../ncfed/edge_client.dart';
import '../ncfed/enrollment_store.dart';
import '../ncfed/protected_device_client.dart';
import 'cloud_owner_screen.dart';

/// Device enrollment lands here directly. The legacy HomeShell and its
/// background, capture, Ask and watch registrations are never constructed.
class ProtectedDeviceScreen extends StatefulWidget {
  final EdgeClient edge;
  final StoredEnrollment enrollment;
  final CloudOwnerStore? store;
  const ProtectedDeviceScreen({
    super.key,
    required this.edge,
    required this.enrollment,
    this.store,
  });
  @override
  State<ProtectedDeviceScreen> createState() => _ProtectedDeviceScreenState();
}

class _ProtectedDeviceScreenState extends State<ProtectedDeviceScreen> {
  late final CloudOwnerClient _client;
  bool _starting = true;
  String? _error;
  Future<void>? _connecting;
  @override
  void initState() {
    super.initState();
    _client = protectedDeviceClient(widget.edge, store: widget.store);
    widget.edge.onDisconnected = () {
      _client.suspend();
      if (mounted) setState(() {});
    };
    _start();
  }

  Future<void> _ensureConnected() async {
    if (_connecting != null) return _connecting!;
    final task = () async {
      if (widget.edge.isClosed) {
        await widget.edge.reconnectInPlace(
          widget.enrollment.toPayload(),
          memberId: widget.enrollment.memberId,
          keyFingerprint: widget.enrollment.keyFingerprint,
        );
      }
    }();
    _connecting = task;
    try {
      await task;
    } finally {
      _connecting = null;
    }
  }

  Future<void> _start() async {
    try {
      await _ensureConnected();
      await _client.initialize();
      if (mounted) {
        setState(() {
          _starting = false;
          _error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(() {
          _starting = false;
          _error =
              'Could not load this enrolled Border. Your enrollment and operation remain saved.';
        });
      }
    }
  }

  @override
  void dispose() {
    widget.edge.onDisconnected = null;
    _client.suspend();
    unawaited(widget.edge.close());
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_starting) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }
    if (_error != null) {
      return Scaffold(
        appBar: AppBar(title: const Text('Mobile operations')),
        body: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(_error!),
              TextButton(
                onPressed: _start,
                child: const Text('Reconnect device'),
              ),
            ],
          ),
        ),
      );
    }
    return CloudOwnerScreen(
      initialClient: _client,
      deviceMode: true,
      beforeResume: _ensureConnected,
      onSuspend: () => unawaited(widget.edge.close()),
    );
  }
}
