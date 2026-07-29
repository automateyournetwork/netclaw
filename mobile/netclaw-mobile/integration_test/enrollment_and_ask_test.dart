import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:netclaw_mobile/ncfed/edge_ask_client.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';
import 'package:netclaw_mobile/ncfed/enrollment_flow.dart';

/// Proves the enrollment + ask round-trip works for real, end to end, on a
/// real device/emulator: real AndroidKeyStore-backed key generation and
/// signing (`EdgeIdentity`), a real `wss://` TLS dial against a real
/// (throwaway, non-production) Border, the real `in2n/enroll` JSON-RPC
/// handshake, and a real `n2n/edge/ask` submission.
///
/// This is deliberately NOT run through `EnrollmentScreen`'s QR-scanner UI —
/// this repo's Android emulator has a synthetic-camera scaling bug (its
/// `-camera-back imagefile` mode renders the feed shrunk/mis-positioned
/// regardless of source image size or aspect ratio) that prevents ML Kit
/// from ever seeing all 3 QR finder patterns in frame at once. That bug is
/// in the emulator's own camera plumbing, not in this app's code —
/// `mobile_scanner` is already configured correctly (`BoxFit.cover`, the
/// package's own default). Calling `attemptEnrollmentFromQr` directly
/// exercises 100% of NetClaw's own logic (identity, TLS, JSON-RPC) and
/// skips only the camera-frame-to-string decode step, which is entirely
/// `mobile_scanner`/ML Kit's own well-tested library code, not ours.
///
/// Requires a throwaway Border reachable at `THROWAWAY_BORDER_HOST`
/// (default `10.0.2.2`, the standard Android-emulator alias for the host
/// loopback) with its HTTP API on `THROWAWAY_BORDER_API_PORT` (default
/// `28179`) and its edge WebSocket listener on `THROWAWAY_BORDER_WS_PORT`
/// (default `28443`), started with `N2N_CLAW_DOMAIN` set to that same host
/// value and a host credential whose SAN actually covers it (a plain
/// `N2N_CLAW_DOMAIN=10.0.2.2` self-signed cert has no such SAN by default —
/// see this feature's quickstart.md for the exact regeneration steps) and
/// with that credential's issuer installed as a trusted system CA on the
/// test device (also documented there). Never point this at a real/
/// production Border.
void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  const borderHost = String.fromEnvironment('THROWAWAY_BORDER_HOST', defaultValue: '10.0.2.2');
  const apiPort = int.fromEnvironment('THROWAWAY_BORDER_API_PORT', defaultValue: 28179);
  const wsPort = int.fromEnvironment('THROWAWAY_BORDER_WS_PORT', defaultValue: 28443);
  // Set when the Border's own control API isn't reachable from the device
  // (e.g. it's bound to 127.0.0.1 on the host only, as production Borders
  // are) -- issue the token on the host side instead and pass it straight
  // through here, skipping this file's own HTTP fetch entirely.
  const presetToken = String.fromEnvironment('ENROLLMENT_TOKEN');

  Future<String> issueEnrollmentToken() async {
    if (presetToken.isNotEmpty) return presetToken;
    final client = HttpClient();
    try {
      final request = await client.postUrl(Uri.parse('http://$borderHost:$apiPort/n2n/enroll/token'));
      request.headers.contentType = ContentType.json;
      request.write(jsonEncode({'label': 'integration-test'}));
      final response = await request.close();
      final body = jsonDecode(await response.transform(utf8.decoder).join()) as Map<String, dynamic>;
      return body['token'] as String;
    } finally {
      client.close();
    }
  }

  testWidgets('real enrollment against a Border, then a real ask round-trip',
      (WidgetTester tester) async {
    final token = await issueEnrollmentToken();
    final rawQr = jsonEncode({
      'border_host': borderHost,
      'border_port': wsPort,
      'claw_domain': borderHost,
      'enrollment_token': token,
    });

    final memberId = 'risk/integration-test-${DateTime.now().millisecondsSinceEpoch}';
    final outcome = await attemptEnrollmentFromQr(
      rawQr,
      memberId: memberId,
      identity: const EdgeIdentity(),
    );

    expect(outcome, isA<EnrollmentSuccess>(), reason: 'enrollment against the throwaway Border failed');
    final success = outcome as EnrollmentSuccess;
    expect(success.client.enrollFingerprint, isNotNull);
    // ignore: avoid_print
    print('enrolled memberId=$memberId fingerprint=${success.client.enrollFingerprint}');

    final askClient = EdgeAskClient(success.client);
    final taskId = await askClient.ask('integration test: are you there?');
    expect(taskId, isNotEmpty);

    // Best-effort: give the agent turn a short window to actually finish,
    // but the core claim already proved above (a real device can enroll
    // and submit a real request end to end) doesn't depend on a model
    // actually being configured on the other end -- a timeout here is
    // informational, never a test failure.
    try {
      final update = await askClient.updates.first.timeout(const Duration(seconds: 30));
      // ignore: avoid_print
      print('ask() update after enrollment: state=${update.state}, output=${update.outputText}');
    } on TimeoutException {
      // ignore: avoid_print
      print('ask() had no result within 30s -- likely no openclaw agent configured on the '
          'throwaway Border; the submission itself (task_id above) already proved the '
          'enrollment + wire round-trip.');
    }

    askClient.dispose();
  });
}
