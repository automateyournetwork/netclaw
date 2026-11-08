# R08 cross-language fixtures

FIXTURE only. Public P256 certificates and Python-generated domain-separated manifest signatures; private keys were generated in memory and discarded. No production credentials or execution proof. `canonical_manifest_body` is UTF-8 canonical Python JSON. Signature value is unpadded base64url ASN.1 DER ECDSA; browser WebCrypto requires conversion to 64-byte r||s. Test vectors use explicit `now_ms`. Node installations and cluster audience are distinct.

`canonical_manifest_body` contains `{schema,manifest}` and its hash is
`canonical_body_sha256`. `canonical_manifest_value` contains just the manifest;
`canonical_manifest_sha256` and `pin.manifest_sha256` hash that value, matching
Python `ha/config.py`. The domain prefix is added only for signature verification.
Negative descriptors, stale-review and unknown-operation records are deliberately
invalid or unexecutable fixture observations, never live execution evidence.
