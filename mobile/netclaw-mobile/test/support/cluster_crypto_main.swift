import Foundation

/// Source-test driver for the exact public verifier linked into the iOS plugin.
/// No Keychain, device enrollment, provider or network access.
@main struct ClusterCryptoDriver {
    static func main() throws {
        let input = try JSONSerialization.jsonObject(with: Data(CommandLine.arguments[1].utf8)) as! [String: String]
        let result = try ClusterPublicCrypto.run(data: Data(base64Encoded: input["data"]!)!,
            spki: input["spki"].flatMap { Data(base64Encoded: $0) },
            signature: input["signature"].flatMap { Data(base64Encoded: $0) })
        print(String(data: try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys]), encoding: .utf8)!)
    }
}
