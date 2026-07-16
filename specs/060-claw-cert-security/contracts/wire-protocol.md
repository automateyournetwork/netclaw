# Contract: Secured Channel Wire Protocol (060)

## 1. Shared-port discrimination (extends NCFED draft §Discrimination)

First byte of a new connection on the shared listening port:

| First byte | Protocol | Action |
|---|---|---|
| `0x16` | TLS handshake | Server-side TLS wrap with the claw's active credential (host-pinned or ACME chain); then read the standard 5-byte `NCFED` magic + 8-byte handshake **inside** TLS |
| `0xFF` | BGP-4 marker | Unchanged |
| `0x4E` (`N`) | Legacy `NCFED`/`NCTUN` magic | Lab mode only; in production, close with refusal frame (below) |
| other | — | Close (existing timeout/refusal rules retained) |

ALPN `ncfed/1` is offered/accepted but is not the discriminator.

## 2. NCFED hello v2 (dialer authentication)

After TLS establishment and the `NCFED` magic + AS/router-id handshake, the first JSON-RPC exchange is extended:

```json
// listener → dialer (response to n2n/hello, new fields)
{
  "nonce": "<32B base64>",            // listener-generated, single-use
  "server_identity": {
    "as": 65001, "router_id": "4.4.4.4",
    "claw_domain": "netclaw.automateyournetwork.ca"   // absent for pinned model
  }
}

// dialer → listener (n2n/hello.auth, NEW request)
{
  "cert_pem": "<dialer certificate chain>",
  "claw_domain": "nick.example.net",   // absent for pinned model
  "sig": "<base64 ECDSA-P256-SHA256 over nonce || tls_exporter>",
  "sig_alg": "ecdsa-p256-sha256"
}
```

- `tls_exporter` = 32 bytes of TLS exported keying material, label `EXPORTER-ncfed-claw-auth` (channel binding; both sides derive it from the session).
- Listener verification: (a) domain-verified → WebPKI chain valid AND leaf SAN == declared `claw_domain` AND `claw_domain` matches the peer trust record; (b) pinned → leaf fingerprint == `pinned_fp` OR `pinned_fp_next`; then in both models verify `sig` with the leaf key. First-contact pinned peers (consent exists, no pin yet): pin now (TOFU) and audit.
- Dialer verification of the listener happened at TLS time: (a) domain-verified → WebPKI + SAN == expected `claw_domain`; (b) pinned → leaf fingerprint == pin (TLS verify_mode NONE + app-layer pin check, the existing iN2N pattern).
- Any verification failure → JSON-RPC error `-32061 CERT_VERIFY_FAILED` with a human-readable `reason`, connection closed, `verify-refused` rotation_event + audit record (FR-005).

## 3. Refusal of legacy peers (FR-021/029)

Production listener receiving legacy magic (or a dialer hitting a legacy listener) sends one cleartext close frame before FIN so the unpatched side logs *why*:

```json
{"error": {"code": -32060, "message": "peer requires certificate-secured federation — run scripts/patch-claw-certs.sh (feature 060)"}}
```

## 4. New channel methods

| Method | Direction | Purpose |
|---|---|---|
| `n2n/hello.auth` | dialer→listener | signed-nonce proof (above) |
| `n2n/cert/update` | either | announce successor credential during rotation: `{fingerprint, cert_pem, not_before, not_after}`; receiver stores `pinned_fp_next` / new CA anchor (FR-013) |
| `n2n/heartbeat` (extended) | both | adds `cred: {fp, not_after, renew_state}` (FR-024); receivers update peer/member health, staleness ≤ 1 interval (SC-011) |

## 5. iN2N transport (extends `IN2N1` preamble)

- Border presents its **hub** credential (risk-CA-signed) in the TLS server hello; members with `credential_state=authority` verify chain → enrolled anchor and SAN == risk name, else abort dial (FR-010).
- Legacy members (pre-060) continue pin-based verification unchanged (FR-011).
- Enrollment reply (token-authenticated, single-use) adds: `risk_ca_pem`, `member_cert_pem`, `enroll_fingerprint` (SHA-256 of member cert DER). Member recomputes and compares; mismatch → hard abort, no partial state (FR-023). Both sides log the fingerprint.
