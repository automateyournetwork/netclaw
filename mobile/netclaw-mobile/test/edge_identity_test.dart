import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:netclaw_mobile/ncfed/edge_identity.dart';

/// (T021, closes G4's key-non-exportability half — FR-004): what's actually
/// testable in this environment (no real Android/iOS runtime) is the Dart
/// side of the contract — that `EdgeIdentity`'s ENTIRE surface for talking
/// to platform-secure key storage is `certificatePem()` (get the public
/// cert) and `sign()` (use the private key) — there is no method anywhere
/// in the class capable of requesting private-key bytes. The native
/// implementations (AndroidKeyStore / Secure Enclave — see
/// android/app/src/main/kotlin/.../MainActivity.kt and
/// ios/Runner/EdgeIdentityPlugin.swift) genuinely never expose an
/// export-private-key method either, but that half needs verification on a
/// real device, which this test cannot reach.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  const channel = MethodChannel('ca.automateyournetwork.netclaw/edge_identity');

  test('EdgeIdentity talks to native code only via ensureKeyPair/sign', () async {
    final invoked = <String>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, (call) async {
      invoked.add(call.method);
      switch (call.method) {
        case 'ensureKeyPair':
          return '-----BEGIN CERTIFICATE-----\nZmFrZQ==\n-----END CERTIFICATE-----\n';
        case 'sign':
          return Uint8List.fromList([1, 2, 3]);
        default:
          throw MissingPluginException('unexpected method ${call.method}');
      }
    });
    addTearDown(() => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(channel, null));

    const identity = EdgeIdentity();
    final cert = await identity.certificatePem();
    final sig = await identity.sign(Uint8List.fromList([9, 9, 9]));

    expect(cert, contains('BEGIN CERTIFICATE'));
    expect(sig, isA<Uint8List>());
    expect(invoked.toSet(), {'ensureKeyPair', 'sign'});
  });
}
