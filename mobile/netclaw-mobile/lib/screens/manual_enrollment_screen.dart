import 'dart:convert';

import 'package:flutter/material.dart';

import '../ncfed/edge_client.dart';
import '../ncfed/edge_identity.dart';
import '../ncfed/enrollment_flow.dart';
import '../ncfed/enrollment_qr_payload.dart';

/// Builds the exact same JSON shape a scanned QR would decode to — pulled
/// out so the form's actual behavior is testable without a real network
/// dial (mirrors `enrollment_flow.dart`'s own reason for existing).
/// `border_host`/`claw_domain` are always the same value here since this
/// app's own QR generation (`netclaw risk token --edge`) never produces a
/// deliberate mismatch — a manually-entered one has no reason to either.
String buildManualEnrollmentQr({
  required String domain,
  required int port,
  required String token,
}) =>
    jsonEncode({
      'border_host': domain,
      'border_port': port,
      'claw_domain': domain,
      'enrollment_token': token,
    });

/// "Can't scan? Enter manually" — the fallback enrollment path alongside
/// `EnrollmentScreen`'s QR scanner. Builds the exact same JSON payload a
/// scanned QR would decode to and hands it to the SAME
/// `attemptEnrollmentFromQr` — no separate enrollment logic, no protocol
/// change, just a second way to produce the raw string. `border_host` and
/// `claw_domain` are always the same value in this app's own QR generation
/// (`netclaw risk token --edge`), so this form only asks for it once rather
/// than exposing that redundancy.
class ManualEnrollmentScreen extends StatefulWidget {
  final String memberId;
  final EdgeIdentity identity;
  final void Function(EdgeClient client, EnrollmentQrPayload payload) onEnrolled;

  const ManualEnrollmentScreen({
    super.key,
    required this.memberId,
    required this.onEnrolled,
    this.identity = const EdgeIdentity(),
  });

  @override
  State<ManualEnrollmentScreen> createState() => _ManualEnrollmentScreenState();
}

class _ManualEnrollmentScreenState extends State<ManualEnrollmentScreen> {
  final _domainController = TextEditingController();
  final _portController = TextEditingController(text: '8443');
  final _tokenController = TextEditingController();
  /// Optional. Blank falls back to a derived label — the Border is never
  /// sent a null display_name again (see defaultDeviceLabel).
  final _nameController = TextEditingController();
  bool _busy = false;
  String? _errorText;

  @override
  void dispose() {
    _domainController.dispose();
    _portController.dispose();
    _tokenController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final domain = _domainController.text.trim();
    final token = _tokenController.text.trim();
    final port = int.tryParse(_portController.text.trim());
    if (domain.isEmpty || token.isEmpty) {
      setState(() => _errorText = 'Border domain and enrollment token are both required.');
      return;
    }
    if (port == null) {
      setState(() => _errorText = 'Port must be a number.');
      return;
    }
    setState(() {
      _busy = true;
      _errorText = null;
    });
    final raw = buildManualEnrollmentQr(domain: domain, port: port, token: token);
    final outcome = await attemptEnrollmentFromQr(
      raw,
      memberId: widget.memberId,
      identity: widget.identity,
      displayName: _nameController.text,
    );
    switch (outcome) {
      case EnrollmentSuccess(client: final client, payload: final payload):
        widget.onEnrolled(client, payload);
      case EnrollmentFailure(message: final message):
        setState(() {
          _errorText = message;
          _busy = false;
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Enter Border Details')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Ask your operator for these three values — the same ones '
                'encoded in the QR code.',
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _domainController,
                enabled: !_busy,
                decoration: const InputDecoration(
                  labelText: 'Border domain',
                  hintText: 'e.g. netclaw.example.com or 10.0.2.2',
                ),
                keyboardType: TextInputType.url,
                autocorrect: false,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _portController,
                enabled: !_busy,
                decoration: const InputDecoration(labelText: 'Port'),
                keyboardType: TextInputType.number,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _tokenController,
                enabled: !_busy,
                decoration: const InputDecoration(
                  labelText: 'Enrollment token',
                  hintText: 'in2n_...',
                ),
                autocorrect: false,
                minLines: 1,
                maxLines: 3,
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _nameController,
                enabled: !_busy,
                decoration: const InputDecoration(
                  labelText: 'Device name (optional)',
                  hintText: "e.g. John's iPhone",
                  helperText: 'Helps the Border tell your devices apart',
                ),
              ),
              const SizedBox(height: 20),
              if (_errorText != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Text(_errorText!, style: const TextStyle(color: Colors.red)),
                ),
              FilledButton(
                onPressed: _busy ? null : _submit,
                child: _busy
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Enroll'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
