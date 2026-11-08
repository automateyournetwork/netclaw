import 'dart:async';
import 'package:flutter/material.dart';
import '../cloud/owner_client.dart';
import '../ncfed/edge_client.dart';
import '../ncfed/enrollment_store.dart';
import '../ncfed/endpoint_recovery.dart';
import '../main.dart' show EnrollmentGate, AppLockGate;
import 'package:path_provider/path_provider.dart';
import '../ncfed/protected_device_client.dart';
import 'cloud_owner_screen.dart';

/// Device enrollment lands here directly. The legacy HomeShell and its
/// background, capture, Ask and watch registrations are never constructed.
class ProtectedDeviceScreen extends StatefulWidget {
  final EdgeClient edge;
  final StoredEnrollment enrollment;
  final CloudOwnerStore? store;
  final EnrollmentStore? enrollmentStore;
  const ProtectedDeviceScreen({
    super.key,
    required this.edge,
    required this.enrollment,
    this.store,
    this.enrollmentStore,
  });
  @override
  State<ProtectedDeviceScreen> createState() => _ProtectedDeviceScreenState();
}

class _ProtectedDeviceScreenState extends State<ProtectedDeviceScreen> {
  late final CloudOwnerClient _client;
  bool _starting = true;
  String? _error;
  Future<void>? _connecting;
  late StoredEnrollment _retained;
  @override
  void initState() {
    super.initState();
    _retained = widget.enrollment;
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
          _retained.toPayload(),
          memberId: _retained.memberId,
          keyFingerprint: _retained.keyFingerprint,
        );
        final cluster = widget.edge.clusterBinding;
        if (cluster != null &&
            _retained.clusterPin != null &&
            cluster.pin.revision > _retained.clusterPin!.revision) {
          final store =
              widget.enrollmentStore ??
              EnrollmentStore(await getApplicationDocumentsDirectory());
          final next = StoredEnrollment.fromJson({
            ..._retained.toJson(),
            'cluster_pin': cluster.pin.toJson(),
            'cluster_descriptor': cluster.descriptor,
          });
          try {
            await store.replaceEndpoint(
              _retained,
              next,
              isCurrent: () => mounted && !widget.edge.isClosed,
            );
          } catch (_) {
            await widget.edge.close();
            rethrow;
          }
          _retained = next;
        }
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
    } catch (error) {
      if (mounted) {
        setState(() {
          _starting = false;
          _error = recoveryFailureMessage(error);
        });
      }
    }
  }

  Future<void> _recoverConnection() async {
    _client.suspend();
    widget.edge.onDisconnected = null;
    await widget.edge.close();
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(
        builder: (_) => AppLockGate(
          child: EnrollmentGate(
            recoverConnection: true,
            documentsDirectory: widget.enrollmentStore == null
                ? getApplicationDocumentsDirectory
                : () async => widget.enrollmentStore!.directory,
          ),
        ),
      ),
    );
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
              TextButton(
                onPressed: _recoverConnection,
                child: Text(
                  widget.enrollment.clusterPin != null
                      ? 'Select trusted cluster Border'
                      : 'Change connection port',
                ),
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
      onRecoverConnection: _recoverConnection,
    );
  }
}
