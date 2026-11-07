import Foundation
import CryptoKit

/// Public-only verification. This helper never opens or changes device keys.
enum ClusterPublicCrypto {
    static func run(data: Data, spki: Data?, signature: Data?) throws -> [String: Any] {
        guard data.count <= 131072, (spki?.count ?? 0) <= 1024,
              (signature?.count ?? 0) <= 200 else {
            throw NSError(domain: "ClusterPublicCrypto", code: 1)
        }
        var value: [String: Any] = [
            "sha256": SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        ]
        if let spki = spki {
            let key = try P256.Signing.PublicKey(derRepresentation: spki)
            value["key_id"] = SHA256.hash(data: spki).map { String(format: "%02x", $0) }.joined()
            if let signature = signature {
                let decoded = try P256.Signing.ECDSASignature(derRepresentation: signature)
                value["verified"] = key.isValidSignature(decoded, for: data)
            }
        }
        return value
    }
}
