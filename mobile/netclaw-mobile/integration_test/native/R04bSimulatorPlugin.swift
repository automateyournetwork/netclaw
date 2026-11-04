// Qualification-only: never register this plugin in the production application.
#if targetEnvironment(simulator)
import Flutter
import Foundation
import Security
import CryptoKit
import CoreImage

final class R04bSimulatorPlugin: NSObject, FlutterPlugin {
    private let tag = "ca.automateyournetwork.r04b.qualification.key".data(using: .utf8)!
    static func register(with registrar: FlutterPluginRegistrar) {
        let instance = R04bSimulatorPlugin()
        for name in ["ca.automateyournetwork.netclaw/edge_identity", "netclaw.r04b/qr_image"] {
            let channel = FlutterMethodChannel(name: name, binaryMessenger: registrar.messenger())
            registrar.addMethodCallDelegate(instance, channel: channel)
        }
    }
    private func key() throws -> SecKey {
        let query: [String: Any] = [kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: tag,
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecReturnRef as String: true]
        var found: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &found)
        if status == errSecSuccess, let found = found { return found as! SecKey }
        guard status == errSecItemNotFound else { throw NSError(domain: "SimulatorIdentity", code: Int(status)) }
        // Software Keychain P256 for the simulator only; production remains
        // Secure Enclave backed. There is no private-key-export interface.
        let attributes: [String: Any] = [kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecAttrKeySizeInBits as String: 256, kSecPrivateKeyAttrs as String: [
                kSecAttrIsPermanent as String: true, kSecAttrApplicationTag as String: tag,
                kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly]]
        var error: Unmanaged<CFError>?
        guard let key = SecKeyCreateRandomKey(attributes as CFDictionary, &error) else {
            throw error!.takeRetainedValue() as Error
        }
        return key
    }
    func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
        do {
            if call.method == "decodeQrImage" {
                guard let args = call.arguments as? [String: Any], let path = args["path"] as? String,
                    path.hasPrefix(NSHomeDirectory()+"/Documents/"),
                    let data = FileManager.default.contents(atPath: path), data.count <= 4*1024*1024,
                    let image = CIImage(data: data) else { throw NSError(domain: "QrImage", code: 1) }
                let context = CIContext(options: [.useSoftwareRenderer: true])
                guard let detector = CIDetector(ofType: CIDetectorTypeQRCode, context: context,
                    options: [CIDetectorAccuracy: CIDetectorAccuracyHigh]) else { throw NSError(domain: "QrImage", code: 2) }
                let features = detector.features(in: image).compactMap { ($0 as? CIQRCodeFeature)?.messageString }
                guard features.count == 1 else { throw NSError(domain: "QrImage", code: 3) }
                result(["raw": features[0], "sha256": SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined(),
                    "decoder": "CoreImage.CIDetector.CPU", "camera": false])
                return
            }
            let privateKey = try key()
            switch call.method {
            case "ensureKeyPair", "publicKeyFingerprint":
                guard let pub = SecKeyCopyPublicKey(privateKey),
                    let point = SecKeyCopyExternalRepresentation(pub, nil) as Data? else { throw NSError(domain: "SimulatorIdentity", code: 2) }
                if call.method == "publicKeyFingerprint" {
                    let spki = Data(X509SelfSigned.subjectPublicKeyInfo(publicKeyPoint: point))
                    result(SHA256.hash(data: spki).map { String(format: "%02x", $0) }.joined())
                } else {
                    let der = try X509SelfSigned.build(publicKeyPoint: point, signer: privateKey)
                    let b64 = der.base64EncodedString(options: [.lineLength64Characters, .endLineWithLineFeed])
                    result("-----BEGIN CERTIFICATE-----\n"+b64+"\n-----END CERTIFICATE-----\n")
                }
            case "sign":
                guard let args = call.arguments as? [String: Any], let data = args["data"] as? FlutterStandardTypedData,
                    let signed = SecKeyCreateSignature(privateKey, .ecdsaSignatureMessageX962SHA256, data.data as CFData, nil) as Data? else {
                    throw NSError(domain: "SimulatorIdentity", code: 3)
                }
                result(FlutterStandardTypedData(bytes: signed))
            default: result(FlutterMethodNotImplemented)
            }
        } catch {
            result(FlutterError(code: "QUALIFICATION_NATIVE_FAILURE", message: "Native qualification operation failed", details: nil))
        }
    }
}
#endif
