# Data Model: iOS Port Verification and App Store Roadmap for NetClaw Mobile

This feature introduces no new persisted storage, database schema, or wire-format entity — it is a
verification and documentation pass over existing, already-specified structures. The "Key
Entities" from `spec.md` are documentation/process concepts, not runtime data. They are captured
here for completeness rather than as a conventional data model.

## Device Identity (iOS)

Not a new entity — this is the existing Secure Enclave key pair + self-signed X.509 certificate
already implemented in `EdgeIdentityPlugin.swift`/`X509SelfSigned.swift` (feature 066, FR-004).
Documented here only for its verification-relevant shape:

| Field | Type | Source | Verified by |
|---|---|---|---|
| Private key | Secure Enclave-resident `SecKey`, EC P-256 | `SecKeyCreateRandomKey` w/ `kSecAttrTokenIDSecureEnclave` | US2 (never exported; only `ensureKeyPair`/`sign` cross the platform channel) |
| Public key | Raw X9.62 uncompressed point (`0x04 \|\| X \|\| Y`) | `SecKeyCopyExternalRepresentation` | US2 |
| Certificate | Self-signed X.509v3 DER, PEM-wrapped | `X509SelfSigned.build()` | US1 (Border must accept it during enrollment) |
| Signature | DER-encoded ECDSA over SHA-256 | `SecKeyCreateSignature(.ecdsaSignatureMessageX962SHA256)` | US2 (Border's `risk.py verify_possession` must accept it) |

No fields, types, or relationships change in this feature — verification confirms the above
matches what the Border already expects (proven against Android's AndroidKeyStore equivalent).

## Verification Record

Not a database row — a documentation convention applied consistently across the README update
(FR-010) and this feature's task outcomes. Each capability in scope gets one row of this shape:

| Field | Meaning |
|---|---|
| Capability | e.g. "Secure Enclave keygen", "Face ID approval", "photo capture (operator→Border)" |
| Status | `Verified` (evidence exists) \| `Assumed` (implemented, not exercised) \| `Blocked` (attempted, could not complete — reason required) |
| Evidence | What was observed: Xcode console output, a GAIT/task-audit log line, a screenshot, a transcript timestamp — matching the specificity of the existing Android README section |
| Date | When the verification occurred |

This table is the acceptance mechanism for SC-005 ("no claim that cannot be traced to a specific
verification step").

## App Store Publication Roadmap

Not data — a standalone Markdown document (`mobile/netclaw-mobile/APP-STORE-ROADMAP.md`), one per
platform, mirroring the existing `PLAY-STORE-ROADMAP.md`. Its internal structure (five phases) is
fixed by research decision D5 in `research.md`; no further data modeling applies.
