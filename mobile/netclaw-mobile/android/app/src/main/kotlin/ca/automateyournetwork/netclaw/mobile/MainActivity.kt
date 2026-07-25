package ca.automateyournetwork.netclaw.mobile

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import io.flutter.embedding.android.FlutterFragmentActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec

private const val EDGE_IDENTITY_CHANNEL = "ca.automateyournetwork.netclaw/edge_identity"
private const val KEYSTORE_PROVIDER = "AndroidKeyStore"

/**
 * NCFED edge-node identity (feature 066, FR-004): the enrollment key is
 * generated inside the AndroidKeyStore (hardware-backed keymaster where the
 * device supports it) and never leaves it. Only two operations are exposed
 * to Dart — get the auto-issued self-signed certificate for the public key,
 * and sign a challenge — there is no method anywhere in this class that
 * returns private key bytes.
 *
 * Verified on an API-34 emulator (2026-07-23 onward): this plugin links and
 * runs, and a full enrollment + ask round trip against the real Border
 * succeeds. Keygen and signing have not been exercised on a device with a
 * hardware-backed keymaster (StrongBox) — the emulator's Keystore is
 * software-backed, so hardware attestation remains unproven.
 */
class MainActivity : FlutterFragmentActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, EDGE_IDENTITY_CHANNEL)
            .setMethodCallHandler { call, result ->
                try {
                    val alias = call.argument<String>("alias") ?: "ncfed_edge_identity"
                    when (call.method) {
                        "ensureKeyPair" -> result.success(ensureKeyPair(alias))
                        "sign" -> {
                            val data = call.argument<ByteArray>("data")
                            if (data == null) {
                                result.error("BAD_ARGS", "missing data", null)
                            } else {
                                result.success(sign(alias, data))
                            }
                        }
                        else -> result.notImplemented()
                    }
                } catch (e: Exception) {
                    result.error("EDGE_IDENTITY_ERROR", e.message, null)
                }
            }
    }

    /**
     * Generates (once, idempotent) an EC P-256 keypair in the AndroidKeyStore
     * and returns the Keystore's own auto-issued self-signed certificate for
     * the public key, PEM-encoded. NCFED's enrollment protocol only reads the
     * public key and its SHA-256 fingerprint out of this certificate
     * (RiskManager.consume_token/fingerprint_of) — the certificate's Subject
     * is otherwise unused, so no explicit `setCertificateSubject` call is
     * needed (keeps this compatible with the widest range of API levels).
     */
    private fun ensureKeyPair(alias: String): String {
        val ks = KeyStore.getInstance(KEYSTORE_PROVIDER)
        ks.load(null)
        if (!ks.containsAlias(alias)) {
            val kpg = KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, KEYSTORE_PROVIDER)
            val spec = KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
            )
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                .build()
            kpg.initialize(spec)
            kpg.generateKeyPair()
        }
        val cert = ks.getCertificate(alias)
            ?: throw IllegalStateException("AndroidKeyStore has no certificate for alias $alias")
        val b64 = Base64.encodeToString(cert.encoded, Base64.NO_WRAP)
        val wrapped = b64.chunked(64).joinToString("\n")
        return "-----BEGIN CERTIFICATE-----\n$wrapped\n-----END CERTIFICATE-----\n"
    }

    /**
     * Signs `data` (the Border-issued nonce, optionally with a channel-binding
     * suffix already appended by the Dart side) with the Keystore-resident
     * private key. SHA256withECDSA produces a DER-encoded ECDSA signature —
     * the same wire format `cryptography.hazmat...ec.ECDSA(hashes.SHA256())`
     * produces/verifies on the Border (risk.py verify_possession), so no
     * format conversion is needed on either side.
     */
    private fun sign(alias: String, data: ByteArray): ByteArray {
        val ks = KeyStore.getInstance(KEYSTORE_PROVIDER)
        ks.load(null)
        val key = ks.getKey(alias, null) as? PrivateKey
            ?: throw IllegalStateException("AndroidKeyStore has no private key for alias $alias")
        val sig = Signature.getInstance("SHA256withECDSA")
        sig.initSign(key)
        sig.update(data)
        return sig.sign()
    }
}
