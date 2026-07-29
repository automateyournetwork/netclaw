import Foundation
import Security

/// Minimal DER/ASN.1 encoder + a self-signed X.509v3 certificate builder for
/// a Secure-Enclave-backed EC P-256 key (feature 066, FR-004). iOS has no
/// built-in "self-signed cert for this SecKey" API the way AndroidKeyStore
/// does, so this constructs the TBSCertificate by hand and signs it with the
/// same Secure Enclave key it describes.
///
/// UNVERIFIED — written on a Linux dev container with no Xcode/iOS toolchain
/// available to compile or test against. Review carefully and exercise on a
/// real device (the Secure Enclave is unavailable on the Simulator) before
/// relying on this.
enum X509SelfSigned {
    // OIDs, DER-encoded content (tag/length added by `oid(_:)`).
    static let oidEcPublicKey: [UInt8] = [0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x02, 0x01]        // 1.2.840.10045.2.1
    static let oidPrime256v1: [UInt8] = [0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x03, 0x01, 0x07]   // 1.2.840.10045.3.1.7
    static let oidEcdsaWithSHA256: [UInt8] = [0x2A, 0x86, 0x48, 0xCE, 0x3D, 0x04, 0x03, 0x02] // 1.2.840.10045.4.3.2
    static let oidCommonName: [UInt8] = [0x55, 0x04, 0x03]                                 // 2.5.4.3

    static func derLength(_ length: Int) -> [UInt8] {
        if length < 0x80 { return [UInt8(length)] }
        var bytes: [UInt8] = []
        var l = length
        while l > 0 { bytes.insert(UInt8(l & 0xFF), at: 0); l >>= 8 }
        return [UInt8(0x80 | bytes.count)] + bytes
    }

    static func der(tag: UInt8, _ content: [UInt8]) -> [UInt8] {
        [tag] + derLength(content.count) + content
    }

    static func sequence(_ content: [UInt8]) -> [UInt8] { der(tag: 0x30, content) }
    static func setOf(_ content: [UInt8]) -> [UInt8] { der(tag: 0x31, content) }
    static func oid(_ bytes: [UInt8]) -> [UInt8] { der(tag: 0x06, bytes) }
    static func bitString(_ content: [UInt8]) -> [UInt8] { der(tag: 0x03, [0x00] + content) } // 0 unused bits
    static func utf8String(_ s: String) -> [UInt8] { der(tag: 0x0C, Array(s.utf8)) }
    static func explicit(_ tagNumber: UInt8, _ content: [UInt8]) -> [UInt8] { der(tag: 0xA0 | tagNumber, content) }

    static func integer(_ value: Int) -> [UInt8] {
        var v = UInt64(value)
        var bytes: [UInt8] = []
        repeat {
            bytes.insert(UInt8(v & 0xFF), at: 0)
            v >>= 8
        } while v != 0
        if bytes.first! & 0x80 != 0 { bytes.insert(0x00, at: 0) }
        return der(tag: 0x02, bytes)
    }

    static func utcTime(_ date: Date) -> [UInt8] {
        let fmt = DateFormatter()
        fmt.dateFormat = "yyMMddHHmmss'Z'"
        fmt.timeZone = TimeZone(identifier: "UTC")
        fmt.locale = Locale(identifier: "en_US_POSIX")
        return der(tag: 0x17, Array(fmt.string(from: date).utf8))
    }

    /// RDNSequence with a single commonName attribute — the Subject is
    /// otherwise unused by NCFED's enrollment protocol (it only reads the
    /// public key and its SHA-256 fingerprint out of the certificate).
    static func name(commonName: String) -> [UInt8] {
        let attr = sequence(oid(oidCommonName) + utf8String(commonName))
        return sequence(setOf(attr))
    }

    static func algorithmIdentifierNoParams(_ oidBytes: [UInt8]) -> [UInt8] {
        sequence(oid(oidBytes))
    }

    static func subjectPublicKeyInfo(publicKeyPoint: Data) -> [UInt8] {
        let algId = sequence(oid(oidEcPublicKey) + oid(oidPrime256v1))
        let spk = bitString(Array(publicKeyPoint))
        return sequence(algId + spk)
    }

    /// Builds + self-signs a minimal X.509v3 certificate wrapping
    /// `publicKeyPoint` (the raw X9.62 uncompressed EC point returned by
    /// `SecKeyCopyExternalRepresentation`), signed with `signer` — the same
    /// Secure Enclave key the point was derived from (self-signed).
    static func build(publicKeyPoint: Data, signer: SecKey) throws -> Data {
        let commonName = "netclaw-mobile-edge"
        let serial = integer(Int(Date().timeIntervalSince1970))
        let sigAlgId = algorithmIdentifierNoParams(oidEcdsaWithSHA256)
        let issuer = name(commonName: commonName)
        let subject = issuer // self-signed: issuer == subject
        let notBefore = utcTime(Date().addingTimeInterval(-60))
        let notAfter = utcTime(Date().addingTimeInterval(10 * 365 * 24 * 3600))
        let validity = sequence(notBefore + notAfter)
        let spki = subjectPublicKeyInfo(publicKeyPoint: publicKeyPoint)
        let version = explicit(0, integer(2)) // v3

        let tbs = sequence(version + serial + sigAlgId + issuer + validity + subject + spki)

        var error: Unmanaged<CFError>?
        guard let signature = SecKeyCreateSignature(
            signer, .ecdsaSignatureMessageX962SHA256, Data(tbs) as CFData, &error) as Data? else {
            throw (error!.takeRetainedValue() as Error)
        }

        let cert = sequence(tbs + sigAlgId + bitString(Array(signature)))
        return Data(cert)
    }
}
