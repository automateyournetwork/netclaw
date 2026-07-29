import Flutter
import Foundation
import Security

private let edgeIdentityChannel = "ca.automateyournetwork.netclaw/edge_identity"
private let keyTag = "ca.automateyournetwork.netclaw.ncfed_edge_identity".data(using: .utf8)!

/// NCFED edge-node identity (feature 066, FR-004): the enrollment key is
/// generated inside the Secure Enclave and never leaves it. Only two
/// operations are exposed to Dart — get a self-signed certificate for the
/// public key (X509SelfSigned.swift), and sign a challenge — there is no
/// private-key-export method anywhere in this plugin.
///
/// UNVERIFIED as of this commit — written on a Linux dev container with no
/// Xcode/iOS device available. Build and exercise on a real device (the
/// Secure Enclave is unavailable on the Simulator) before relying on it.
public class EdgeIdentityPlugin: NSObject, FlutterPlugin {
    public static func register(with registrar: FlutterPluginRegistrar) {
        let channel = FlutterMethodChannel(name: edgeIdentityChannel, binaryMessenger: registrar.messenger())
        let instance = EdgeIdentityPlugin()
        registrar.addMethodCallDelegate(instance, channel: channel)
    }

    public func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        switch call.method {
        case "ensureKeyPair":
            do { result(try ensureKeyPairPem()) }
            catch { result(FlutterError(code: "EDGE_IDENTITY_ERROR", message: "\(error)", details: nil)) }
        case "sign":
            guard let args = call.arguments as? [String: Any],
                  let typed = args["data"] as? FlutterStandardTypedData else {
                result(FlutterError(code: "BAD_ARGS", message: "missing data", details: nil))
                return
            }
            do { result(try sign(data: typed.data)) }
            catch { result(FlutterError(code: "EDGE_IDENTITY_ERROR", message: "\(error)", details: nil)) }
        default:
            result(FlutterMethodNotImplemented)
        }
    }

    private func loadPrivateKey() throws -> SecKey? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag,
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecReturnRef as String: true,
        ]
        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let key = item else {
            throw NSError(domain: "EdgeIdentity", code: Int(status),
                         userInfo: [NSLocalizedDescriptionKey: "SecItemCopyMatching failed (\(status))"])
        }
        return (key as! SecKey)
    }

    /// Generates the enrollment keypair inside the Secure Enclave. No
    /// biometric gate on this key — it authenticates the device's NCFED
    /// identity (heartbeats, message delivery), not a human approval
    /// decision (that's a separate, per-approval biometric prompt in a later
    /// feature) — requiring Face ID on every heartbeat would be unusable.
    private func generatePrivateKey() throws -> SecKey {
        guard let access = SecAccessControlCreateWithFlags(
            nil, kSecAttrAccessibleWhenUnlockedThisDeviceOnly, [.privateKeyUsage], nil) else {
            throw NSError(domain: "EdgeIdentity", code: -1,
                         userInfo: [NSLocalizedDescriptionKey: "SecAccessControlCreateWithFlags failed"])
        }
        let attributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecAttrKeySizeInBits as String: 256,
            kSecAttrTokenID as String: kSecAttrTokenIDSecureEnclave,
            kSecPrivateKeyAttrs as String: [
                kSecAttrIsPermanent as String: true,
                kSecAttrApplicationTag as String: keyTag,
                kSecAttrAccessControl as String: access,
            ],
        ]
        var error: Unmanaged<CFError>?
        guard let key = SecKeyCreateRandomKey(attributes as CFDictionary, &error) else {
            throw (error!.takeRetainedValue() as Error)
        }
        return key
    }

    private func ensurePrivateKey() throws -> SecKey {
        if let existing = try loadPrivateKey() { return existing }
        return try generatePrivateKey()
    }

    private func ensureKeyPairPem() throws -> String {
        let privateKey = try ensurePrivateKey()
        guard let publicKey = SecKeyCopyPublicKey(privateKey) else {
            throw NSError(domain: "EdgeIdentity", code: -1,
                         userInfo: [NSLocalizedDescriptionKey: "no public key for enrollment identity"])
        }
        var error: Unmanaged<CFError>?
        guard let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, &error) as Data? else {
            throw (error!.takeRetainedValue() as Error)
        }
        // publicKeyData is the raw X9.62 uncompressed point (0x04 || X || Y).
        let certDer = try X509SelfSigned.build(publicKeyPoint: publicKeyData, signer: privateKey)
        let b64 = certDer.base64EncodedString(options: [.lineLength64Characters, .endLineWithLineFeed])
        return "-----BEGIN CERTIFICATE-----\n\(b64)\n-----END CERTIFICATE-----\n"
    }

    /// Signs `data` (the Border-issued nonce, optionally with a
    /// channel-binding suffix already appended by the Dart side) with the
    /// Secure-Enclave-resident private key. The DER-encoded ECDSA signature
    /// matches the wire format `cryptography.hazmat...ec.ECDSA(hashes.SHA256())`
    /// produces/verifies on the Border (risk.py verify_possession).
    private func sign(data: Data) throws -> Data {
        let privateKey = try ensurePrivateKey()
        var error: Unmanaged<CFError>?
        guard let signature = SecKeyCreateSignature(
            privateKey, .ecdsaSignatureMessageX962SHA256, data as CFData, &error) as Data? else {
            throw (error!.takeRetainedValue() as Error)
        }
        return signature
    }
}
