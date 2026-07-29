import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../ncfed/device_deep_link.dart';

/// Lets an already-enrolled operator scan an equipment QR code at any time
/// (feature 067, US5) — distinct from 066's `EnrollmentScreen`, which only
/// ever runs once, before enrollment.
class DeviceScanScreen extends StatefulWidget {
  final DeviceDeepLinkHandler handler;
  final void Function(String taskId) onSubmitted;

  const DeviceScanScreen({super.key, required this.handler, required this.onSubmitted});

  @override
  State<DeviceScanScreen> createState() => _DeviceScanScreenState();
}

class _DeviceScanScreenState extends State<DeviceScanScreen> {
  bool _busy = false;
  String? _errorText;

  Future<void> _onDetect(BarcodeCapture capture) async {
    if (_busy || capture.barcodes.isEmpty) return;
    final raw = capture.barcodes.first.rawValue;
    if (raw == null) return;
    setState(() {
      _busy = true;
      _errorText = null;
    });
    String? taskId;
    try {
      taskId = await widget.handler.handle(raw);
    } catch (e) {
      // Previously unhandled -- a disconnected/timed-out ask() left _busy
      // stuck true forever with no error shown, freezing the scanner.
      setState(() {
        _errorText = 'Could not submit: $e';
        _busy = false;
      });
      return;
    }
    if (taskId == null) {
      setState(() {
        _errorText = 'That QR code is not a NetClaw device link.';
        _busy = false;
      });
      return;
    }
    widget.onSubmitted(taskId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Scan Device')),
      body: Stack(
        children: [
          MobileScanner(onDetect: _onDetect),
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
                  child: Text(_errorText!, style: const TextStyle(color: Colors.white)),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
