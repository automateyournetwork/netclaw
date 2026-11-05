import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../ncfed/edge_client.dart';
import '../ncfed/edge_identity.dart';
import '../ncfed/enrollment_flow.dart';
import '../ncfed/enrollment_qr_payload.dart';
import '../ncfed/enrollment_store.dart';
import 'manual_enrollment_screen.dart';
import 'cloud_owner_screen.dart';

/// "Scan Border QR Code" — feature 066, US1/T014. Explicit error states for
/// domain-mismatch, expired/already-used tokens, and any other enrollment
/// failure; on success hands the connected EdgeClient + parsed QR payload to
/// `onEnrolled` for the caller to act on.
///
/// Note: this deliberately does NOT show "the Border and existing members"
/// on success (as originally envisioned) — an edge channel's handler map is
/// scoped to exclude inventory/member-list methods by design (FR-012), so a
/// phone genuinely cannot query that from the Border. The success state here
/// is a plain confirmation instead.
typedef EnrollmentScannerBuilder =
    Widget Function(Future<void> Function(BarcodeCapture));

class EnrollmentScreen extends StatefulWidget {
  final String memberId;
  final EdgeIdentity identity;
  final EnrollmentStore? store;
  final VoidCallback? onRecoverPending;
  // Native simulator harness can feed decoded images through this SAME callback.
  // Production always uses MobileScanner's camera widget below.
  final EnrollmentScannerBuilder? scannerBuilder;
  final void Function(EdgeClient client, EnrollmentQrPayload payload)
  onEnrolled;

  const EnrollmentScreen({
    super.key,
    required this.memberId,
    required this.onEnrolled,
    this.identity = const EdgeIdentity(),
    this.store,
    this.onRecoverPending,
    this.scannerBuilder,
  });

  @override
  State<EnrollmentScreen> createState() => _EnrollmentScreenState();
}

class _EnrollmentScreenState extends State<EnrollmentScreen> {
  bool _busy = false;
  bool _pending = false;
  String? _errorText;

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_busy || _pending) return;
    if (capture.barcodes.isEmpty) return;
    final raw = capture.barcodes.first.rawValue;
    if (raw == null) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    final outcome = await attemptEnrollmentFromQr(
      raw,
      memberId: widget.memberId,
      identity: widget.identity,
      store: widget.store,
    );
    if (!mounted) return;
    switch (outcome) {
      case EnrollmentSuccess(client: final client, payload: final payload):
        widget.onEnrolled(client, payload);
      case EnrollmentFailure(message: final message, pending: final pending):
        setState(() {
          _errorText = message;
          _busy = false;
          _pending = pending;
        });
    }
  }

  Future<void> _enterManually() async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ManualEnrollmentScreen(
          memberId: widget.memberId,
          identity: widget.identity,
          store: widget.store,
          onEnrolled: widget.onEnrolled,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Border QR Code'),
        actions: [
          IconButton(
            tooltip: 'Cloud Border owner',
            icon: const Icon(Icons.cloud_outlined),
            onPressed: () => Navigator.of(
              context,
            ).push(MaterialPageRoute(builder: (_) => const CloudOwnerScreen())),
          ),
        ],
      ),
      body: Stack(
        children: [
          widget.scannerBuilder?.call(_onDetect) ??
              MobileScanner(onDetect: _onDetect),
          Positioned(
            left: 16,
            right: 16,
            top: 16,
            child: Center(
              child: TextButton(
                onPressed: _busy || _pending ? null : _enterManually,
                style: TextButton.styleFrom(backgroundColor: Colors.black54),
                child: const Text(
                  "Can't scan? Enter manually",
                  style: TextStyle(color: Colors.white),
                ),
              ),
            ),
          ),
          if (_errorText != null)
            Positioned(
              left: 16,
              right: 16,
              bottom: 32,
              child: Material(
                color: Colors.black87,
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        _errorText!,
                        style: const TextStyle(color: Colors.white),
                      ),
                      if (_pending && widget.onRecoverPending != null)
                        TextButton(
                          onPressed: widget.onRecoverPending,
                          child: const Text('Check retained enrollment'),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          if (_busy)
            const Positioned.fill(
              child: ColoredBox(
                color: Colors.black45,
                child: Center(child: CircularProgressIndicator()),
              ),
            ),
        ],
      ),
    );
  }
}
