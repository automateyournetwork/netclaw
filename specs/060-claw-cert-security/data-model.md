# Phase 1 Data Model: Claw Certification (060)

All state extends the existing SQLite `~/.openclaw/n2n/federation.db` (FR-020; schema migration v3, additive only). Key material lives under `~/.openclaw/n2n/keys/` (`0700` dir, `0600` files).

## 1. `credential` (new table)

Every certificate the claw manages, local or observed.

| Column | Type | Notes |
|---|---|---|
| `credential_id` | INTEGER PK | |
| `kind` | TEXT | `acme` \| `host-pinned` (this claw's self-signed) \| `risk-ca` \| `hub` \| `member` |
| `subject_identity` | TEXT | claw domain, `as<ASN>-<router-id>`, risk name, or member_id |
| `fingerprint` | TEXT | SHA-256 over DER, hex — UNIQUE |
| `issuer` | TEXT | e.g. `Let's Encrypt R11`, `johns-risk Risk CA`, `self-signed` |
| `not_before` / `not_after` | TEXT | ISO-8601 UTC |
| `renew_after` | TEXT | issued + 2/3 lifetime (FR-012); NULL for observed-only certs |
| `state` | TEXT | `active` \| `overlap` \| `retired` \| `failed` |
| `cert_pem` | TEXT | public cert only — private keys NEVER in the DB (keys dir only) |
| `key_path` | TEXT | path under keys dir for locally-held keys, else NULL |
| `created_at` / `updated_at` | TEXT | |

State transitions: `active → overlap` (successor issued) `→ retired` (overlap closed / expiry); `active → failed` (renewal exhausted, FR-014); emergency re-key: `active → retired` immediately (FR-015).

## 2. `federation_peer` (existing table — new columns)

| New column | Type | Notes |
|---|---|---|
| `trust_model` | TEXT | `domain-verified` \| `pinned` \| `legacy` (pre-patch; refused in production per FR-021) |
| `claw_domain` | TEXT | verified attribute of the unchanged identity key (FR-003a); NULL for pinned |
| `pinned_fp` | TEXT | SHA-256 pin (pinned model); NULL for domain-verified |
| `pinned_fp_next` | TEXT | successor pin during rotation overlap (FR-013/R6); NULL otherwise |
| `peer_cred_fp` / `peer_cred_not_after` / `peer_renew_state` | TEXT | last credential health seen via heartbeat (FR-024, SC-011) |
| `verify_state` | TEXT | `verified` \| `mismatch` (FR-006 flag) \| `refused-pending-patch` (FR-021/029) |

Identity key (`identity` = `as<ASN>-<router-id>`) is unchanged — Q1 clarification.

## 3. `member` (existing table — new columns)

| New column | Type | Notes |
|---|---|---|
| `credential_state` | TEXT | `authority` (risk-CA-issued) \| `legacy` (pre-060 pin, FR-011) |
| `cred_fp` / `cred_not_after` / `renew_state` | TEXT | member credential health (heartbeat + issuance records) |
| `enroll_fingerprint_logged` | INTEGER | 1 when both-side fingerprint log completed (FR-023) |

`pinned_key` column remains authoritative for legacy members; authority members verify by chain.

## 4. `rotation_event` (new table)

| Column | Type | Notes |
|---|---|---|
| `event_id` | INTEGER PK | |
| `subject_identity` | TEXT | |
| `credential_id` | INTEGER FK | |
| `kind` | TEXT | `renewed` \| `rotated` \| `overlap-opened` \| `overlap-closed` \| `renewal-failed` \| `emergency-rekey` \| `verify-refused` |
| `detail` | TEXT | reason / error / peer response |
| `at` | TEXT | ISO-8601 UTC |

Mirrored into the existing `audit.record` + GAIT trail (FR-016; Constitution IV).

## 5. `auth_failure_bucket` (new table — FR-022)

| Column | Type | Notes |
|---|---|---|
| `source` | TEXT PK | remote address / channel origin of unauthenticated failures |
| `member_id` | TEXT | asserted identity (informational) |
| `count` / `window_start` | INTEGER/TEXT | token-bucket state (default 5/min then drop+audit) |

Member quarantine counters (existing) now increment **only** from failures on the member's own authenticated origin.

## 6. Keys directory layout

```text
~/.openclaw/n2n/keys/
├── host/            # this claw's pinned-model credential (key + cert)
├── acme/            # lego account + live certs for <claw-domain> (lego-managed tree)
├── risk-ca/         # risk CA key + cert (+ retired anchors, kept for audit)
├── members/<id>/    # issued member certs (public); member holds its own key
└── pinned/          # existing eN2N/iN2N observed-pin store (unchanged location)
```

## 7. Config surface (`.env`, documented in `.env.example`)

| Variable | Meaning |
|---|---|
| `N2N_CLAW_DOMAIN` | claw's domain identity (e.g. `netclaw.automateyournetwork.ca`); unset → pinned model |
| `N2N_ACME_DNS_PROVIDER` | lego provider id (`godaddy`, `cloudflare`, `route53`, `acme-dns`, …) |
| `N2N_ACME_EMAIL` | ACME account contact |
| provider creds | per lego convention (e.g. `GODADDY_API_KEY`/`GODADDY_API_SECRET`, `CLOUDFLARE_DNS_API_TOKEN`, `ACME_DNS_API_BASE`/`ACME_DNS_STORAGE_PATH`) |
| `N2N_CERT_RENEW_FRACTION` | default `0.667` (FR-012) |
| `N2N_CERT_MEMBER_DAYS` / `N2N_CERT_CA_DAYS` | defaults `90` / `730` |
| `N2N_RISK_MODE` | existing; `production` ⇒ cleartext eN2N refused (FR-021) |
