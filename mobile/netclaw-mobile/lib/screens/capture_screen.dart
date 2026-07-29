import 'package:camera/camera.dart';
import 'package:flutter/material.dart';

import '../ncfed/capture_client.dart';

/// The real capture UI behind `CaptureFn` (feature 068, US2/US3) — a live
/// camera preview with a shutter button. Backing out (the app bar's back
/// button) is a true no-op: nothing is sent, matching FR-005's acceptance
/// scenario 4 (cancelling a capture in progress) and US3's declined/
/// cancelled handling — both simply see `Navigator.pop(null)`.
///
/// Only implements photo capture for now — video/audio recording share the
/// same permission-decline/cancel contract but need separate recording UI
/// this pass didn't build out; `captureType` is accepted so the caller
/// (Border-requested or phone-initiated) can label the request, but every
/// path currently produces a photo. A future task should add real
/// video/audio recording without changing this screen's `CaptureResult`
/// contract.
class CaptureScreen extends StatefulWidget {
  final String captureType;

  const CaptureScreen({super.key, required this.captureType});

  @override
  State<CaptureScreen> createState() => _CaptureScreenState();

  /// Pushes this screen and returns the capture, or `null` if the operator
  /// declined the camera permission or backed out — usable directly as a
  /// `CaptureFn`.
  static Future<CaptureResult?> capture(BuildContext context, String captureType) {
    return Navigator.of(context).push<CaptureResult?>(
      MaterialPageRoute(builder: (_) => CaptureScreen(captureType: captureType)),
    );
  }
}

class _CaptureScreenState extends State<CaptureScreen> {
  CameraController? _controller;
  String? _error;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final cameras = await availableCameras();
      if (cameras.isEmpty) {
        setState(() => _error = 'No camera available.');
        return;
      }
      final controller = CameraController(cameras.first, ResolutionPreset.medium);
      await controller.initialize();
      if (!mounted) return;
      setState(() => _controller = controller);
    } catch (e) {
      // Covers a declined OS camera permission -- an explicit failure
      // state, never a silent hang (FR-005/FR-009 acceptance scenario 3).
      if (mounted) setState(() => _error = 'Camera unavailable: $e');
    }
  }

  Future<void> _shutter() async {
    final controller = _controller;
    if (controller == null) return;
    try {
      final file = await controller.takePicture();
      final bytes = await file.readAsBytes();
      if (mounted) {
        Navigator.of(context).pop(CaptureResult(contentType: 'image', bytes: bytes));
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Capture failed: $e');
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Capture')),
      body: Builder(builder: (context) {
        if (_error != null) {
          return Center(child: Text(_error!));
        }
        final controller = _controller;
        if (controller == null) {
          return const Center(child: CircularProgressIndicator());
        }
        return Stack(
          alignment: Alignment.bottomCenter,
          children: [
            CameraPreview(controller),
            Padding(
              padding: const EdgeInsets.all(24),
              child: FloatingActionButton(onPressed: _shutter, child: const Icon(Icons.camera)),
            ),
          ],
        );
      }),
    );
  }
}
