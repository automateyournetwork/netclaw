import 'package:flutter/services.dart';

/// NCFED edge-node identity (feature 066, FR-004). Wraps the native
/// Android Keystore / iOS Secure Enclave plugin: the private key is
/// generated in and never leaves platform-secure hardware storage. Neither
/// this class nor the native plugins behind it (see
/// android/app/src/main/kotlin/.../MainActivity.kt and
/// ios/Runner/EdgeIdentityPlugin.swift) ever return raw private-key bytes —
/// only a self-signed public certificate, its public fingerprint, and sign().
class EdgeIdentity {
  static const MethodChannel _channel = MethodChannel(
    'ca.automateyournetwork.netclaw/edge_identity',
  );

  const EdgeIdentity();

  /// Ensures the enrollment keypair exists (idempotent) and returns its
  /// self-signed certificate, PEM-encoded — this is the `cert_pem` NCFED's
  /// enrollment protocol expects (contracts/edge-enrollment-and-push.md).
  Future<String> certificatePem() async {
    final result = await _channel.invokeMethod<String>('ensureKeyPair');
    if (result == null) {
      throw StateError(
        'platform returned no certificate for enrollment identity',
      );
    }
    return result;
  }

  /// SHA-256 of the public SubjectPublicKeyInfo DER, matching Border pins.
  /// No private key material leaves the native store.
  Future<String> publicKeyFingerprint() async {
    final value = await _channel.invokeMethod<String>('publicKeyFingerprint');
    if (value == null || !RegExp(r'^[a-f0-9]{64}$').hasMatch(value)) {
      throw StateError('Invalid public key fingerprint');
    }
    return value;
  }

  /// Signs `data` (the Border-issued nonce, optionally with a
  /// channel-binding suffix already appended by the caller) with the
  /// platform-secure private key. Returns a DER-encoded ECDSA signature.
  Future<Uint8List> sign(Uint8List data) async {
    final result = await _channel.invokeMethod<Uint8List>('sign', {
      'data': data,
    });
    if (result == null) {
      throw StateError('platform returned no signature');
    }
    return result;
  }
}
