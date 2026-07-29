import 'package:app_links/app_links.dart';
import 'package:flutter/foundation.dart';

import 'edge_ask_client.dart';

/// Extracts the device id from a `netclaw://device/<id>` URI string, or
/// `null` if the string isn't that shape. Also the format a QR code
/// encodes for this feature (research D8) — a raw scanned string is passed
/// through this same parser, not a separate JSON shape.
String? parseDeviceDeepLink(String raw) {
  final uri = Uri.tryParse(raw);
  if (uri == null || uri.scheme != 'netclaw' || uri.host != 'device') return null;
  final id = uri.pathSegments.isNotEmpty ? uri.pathSegments.first : null;
  if (id == null || id.isEmpty) return null;
  return id;
}

/// The templated request text a device deep link resolves to (contract's
/// client-side-shortcuts section) — no new wire method, no device registry.
String deviceStatusRequestText(String deviceId) =>
    'What is the current status of device $deviceId?';

/// Resolves a device deep link (URI or QR) into an automatically-submitted
/// `n2n/edge/ask` request (feature 067, US5). An unrecognized-but-well-formed
/// deep link (e.g. `netclaw://device/does-not-exist`) is NOT distinguished
/// here — "unknown device" surfaces from the normal agent-turn failure path
/// (the same one US1/T010 already covers), not a new client-side error code
/// (research D8). `handle()` returning `null` means the string wasn't even
/// shaped like a device deep link in the first place.
class DeviceDeepLinkHandler {
  final EdgeAskClient askClient;

  DeviceDeepLinkHandler(this.askClient);

  Future<String?> handle(String raw) async {
    final deviceId = parseDeviceDeepLink(raw);
    if (deviceId == null) return null;
    return askClient.ask(deviceStatusRequestText(deviceId));
  }
}

/// Wires OS-level `netclaw://` links (cold-start AND foreground-tap) to
/// `DeviceDeepLinkHandler` — T022's "cold-start-from-link and a
/// foreground-tap both land on chat_screen.dart" requirement.
class DeviceDeepLinkListener {
  final DeviceDeepLinkHandler handler;
  final void Function(String taskId, String requestText) onSubmitted;
  // Previously a failed ask() here (disconnected, timeout) was completely
  // silent -- the operator taps a device link and, from their perspective,
  // simply nothing happens, with no way to tell why. Defaults to a debug
  // log so this is at minimum visible during development even if the
  // owner doesn't wire a UI-visible handler.
  final void Function(Object error) onError;
  final AppLinks _appLinks;

  DeviceDeepLinkListener({
    required this.handler,
    required this.onSubmitted,
    void Function(Object error)? onError,
    AppLinks? appLinks,
  })  : onError = onError ?? ((e) => debugPrint('device deep link failed: $e')),
        _appLinks = appLinks ?? AppLinks();

  Future<void> start() async {
    _appLinks.uriLinkStream.listen(_handleUri);
    final initial = await _appLinks.getInitialLink();
    if (initial != null) await _handleUri(initial);
  }

  Future<void> _handleUri(Uri uri) async {
    final deviceId = parseDeviceDeepLink(uri.toString());
    if (deviceId == null) return;
    final text = deviceStatusRequestText(deviceId);
    try {
      final taskId = await handler.askClient.ask(text);
      onSubmitted(taskId, text);
    } catch (e) {
      onError(e);
    }
  }
}
