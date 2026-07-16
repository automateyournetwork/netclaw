# Phase 0 Research: Claw Certification (060)

All NEEDS CLARIFICATION items from Technical Context are resolved below. Ground truth was read from the reference implementation (`bgp/constants.py`, `bgp/federation/channel.py`, `internal_channel.py`, `risk.py`, `service.py`) and the NCFED draft (`docs/ietf/draft-capobianco-ncfed-00.md`, §Discrimination, §Trust, §Security Considerations).

## R1 — Dialer authentication: signed nonce, not TLS client certificates

**Decision**: The channel listener presents a TLS server certificate (domain-verified or pinned self-signed). The **dialer** authenticates at the application layer: the NCFED hello (v2) carries the dialer's certificate (PEM) and a signature over a listener-supplied nonce + TLS channel-binding value (`tls-exporter` keying material, RFC 9266 pattern), proving key possession and binding the proof to this TLS session.

**Rationale**: Let's Encrypt is removing the `clientAuth` EKU from its certificates (Chrome root-program change; default since late 2025). Literal mutual TLS with LE certs on both ends therefore cannot work going forward. The signed-nonce pattern already exists and is proven in iN2N (`internal_channel.py` — "signed nonce... pinning happens at the app layer"); extending it to eN2N is the exact candidate mechanism the 059 draft names in §seccons-peer-auth. Using the TLS exporter as channel binding closes the draft's "no channel binding" observation.

**Alternatives considered**: TLS client certs from a CA that keeps clientAuth (ZeroSSL) — rejected: couples the design to one CA's policy surviving. Double-dial mutual server-auth (each side dials the other's listener and binds sessions with a token) — rejected: requires both sides to be dialable, breaking the awaiting-inbound/higher-AS pattern and doubling tunnel traffic.

## R2 — ACME client: lego, driven by the daemon

**Decision**: Vendor **lego** (single static Go binary, Apache-2.0) fetched at install time into `~/.openclaw/n2n/bin/`. New `bgp/federation/acme.py` drives it: `lego --dns <provider> run/renew` with provider credentials passed as env vars from `.env`. Renewal runs as a daemon asyncio task (hourly check; renew at 2/3 lifetime elapsed; honor ARI where lego supports it), not a systemd timer.

**Rationale**: lego covers 100+ DNS providers (Cloudflare, Route53, GoDaddy, deSEC, …) with one flag; single binary matches the repo's "no new Python packages" constraint; programmatic exit codes and file layout (`.lego/certificates/`) are easy to drive from asyncio. A daemon task avoids a new systemd unit and inherits 057's durable-daemon guarantees; the daemon is already the thing that must react to a renewed cert (re-load SSL context).

**Alternatives considered**: certbot — rejected (Python package + per-provider plugin installs conflict with the isolated-deps principle). acme.sh — rejected (bash, awkward to supervise programmatically). Hand-rolled RFC 8555 on `cryptography` — rejected (high-risk crypto/protocol code, explicitly out of scope per spec assumption).

## R3 — Provider-agnostic DNS-01 with challenge delegation (FR-004a)

**Decision**: Two documented paths, auto-selected by config:
1. **Direct provider API**: `N2N_ACME_DNS_PROVIDER=<lego provider id>` + that provider's env vars (e.g. `GODADDY_API_KEY`/`GODADDY_API_SECRET`, `CLOUDFLARE_DNS_API_TOKEN`). lego handles record write/cleanup.
2. **Challenge delegation** (universal fallback): operator creates one permanent CNAME `_acme-challenge.<claw-domain>` → `<claw-id>.auth.<delegation-zone>`; the claw fulfills challenges in the delegation zone (an **acme-dns** instance or any API-capable zone). ACME CAs follow CNAMEs on `_acme-challenge` per RFC 8555 practice; lego supports acme-dns natively (`--dns acme-dns`).

**Rationale**: GoDaddy (the reference deployment's provider) restricted its DNS API for small accounts in 2024 — availability cannot be assumed; delegation makes *any* provider automatable with one manual CNAME, exactly matching the clarification. The reference deployment documents both against `automateyournetwork.ca`.

**Alternatives considered**: Manual DNS-01 — rejected (breaks unattended renewal, violates FR-012). HTTP-01/TLS-ALPN-01 — rejected (require inbound reachability, violating FR-004).

## R4 — TLS on the shared port: first-byte discrimination (FR-001a)

**Decision**: The listener peeks the first byte before consuming: `0x16` (TLS handshake record) → wrap the socket via `asyncio` `start_tls`-equivalent server-side with the claw's credential, then read the normal 5-byte `NCFED` magic + handshake *inside* TLS. `0xFF` → BGP marker path unchanged. `N` (0x4E) → legacy `NCFED`/`NCTUN` magic, accepted only in lab mode (`N2N_RISK_MODE != production`), else refused with an actionable close reason ("peer requires certificate-secured federation — run the patch").

**Ground truth**: `constants.py:187/195` — `NCTUN`/`NCFED` are 5-byte ASCII magics; BGP begins with a 16-byte `0xFF` marker; TLS records begin `0x16 0x03`. The three first bytes (`0x16`, `0xFF`, `0x4E`) are mutually exclusive, so discrimination is a single-byte decision with the existing read-timeout DoS bounds retained.

**Alternatives considered**: dedicated TLS port — rejected in Clarification Q2 (second tunnel per operator). ALPN-based discrimination — unnecessary; ALPN is still set (`ncfed/1`) for future use but is not the discriminator.

## R5 — iN2N hub attestation: risk CA (FR-008..011)

**Decision**: `certs.py` adds `create_risk_ca()` (self-signed CA cert, `CN=<risk-name> Risk CA`, pathlen=0, default 2y) and `issue_member_cert()` / `issue_hub_cert()` (90d default, SAN=member-id/risk-id). `risk.py` `_generate_self_signed` is replaced by CA issuance at enrollment; the enrollment reply delivers the CA anchor to the member alongside its issued credential; `in2n-member.py` stores the anchor and `internal_channel.build_ssl_contexts` gains a member-side verify mode (`load_verify_locations(risk_ca)`, `check_hostname=False`, identity checked against the SAN at app layer). Legacy members (pinned, pre-CA) keep working: the Border retains their pins and flags `credential_state=legacy` until re-enrollment (FR-011).

**Rationale**: Minimal-delta on the working 056/057 enrollment: same token bootstrap, same pin table, plus a chain. The anchor rides the same single-use-token-authenticated reply that today delivers the member its identity — no new trust assumptions.

## R6 — Rotation with dual-trust overlap (FR-012..016)

**Decision**: A `credential` table tracks every managed cert (kind: acme|risk-ca|hub|member|host-pinned) with `not_after`, `renew_after` (issued + 2/3 lifetime), `state` (active|overlap|retired|failed). Rotation flow: issue successor → distribute over the live authenticated channel (`n2n/cert/update` notify for eN2N pinned peers and iN2N members) → both fingerprints accepted (`pin OR successor-pin`, `old-CA OR new-CA`) until `not_after(old)` or explicit close of the overlap → retire. ACME certs need no peer distribution (WebPKI chains verify the successor automatically); pinned/risk credentials do. Emergency re-key (`n2n_cert_rotate --emergency`) skips overlap and immediately distrusts the old anchor.

**Rationale**: Trust-by-name (domain-verified) rotates for free; trust-by-key (pinned, risk CA) is where overlap matters — delivering the successor over the *existing authenticated channel* is the standard SSH-style key-continuity pattern and satisfies FR-006's "rotation overlap" carve-out.

## R7 — Trust hardening details (FR-022/023)

**Decision**: Quarantine accounting keys on `(member_id, source)` where source = the authenticated channel origin; unauthenticated failures count only against a per-source rate limiter (token bucket, default 5/min then drop+audit) and never toward the member's quarantine threshold. Enrollment fingerprint: both sides compute SHA-256 over the issued cert DER; Border logs + audits `enroll_fingerprint` and the member prints it; mismatch (member-side verification of the anchor/cert it received vs what the Border recorded, confirmed in the enrollment ack) hard-aborts with full state rollback. No interactive pause (Clarification Q5).

## R8 — Heartbeat credential health (FR-024..026)

**Decision**: The existing `channel.py` `_heartbeat_loop` payload gains `cred: {fp, not_after, renew_state}` in both directions; receivers store it on the peer/member record (staleness ≤ one heartbeat interval, SC-011). Rotation mid-session is announced by `n2n/cert/update`; heartbeat carries the *current* fp so a missed notify is still detected at the next beat. Liveness logic untouched.

## R9 — Patch installer (FR-028/029)

**Decision**: `scripts/patch-claw-certs.sh` — idempotent, single command: (1) git pull/checkout release; (2) stop services; (3) `manager.py` schema migration v3 (additive tables/columns only — no destructive DDL); (4) generate host credential + risk CA if absent; (5) re-issue member certs for `service`-managed members automatically (their channels re-dial), mark cold members `legacy` for lazy re-issue at next enrollment contact; (6) optional domain wizard (`--domain netclaw.automateyournetwork.ca --dns-provider godaddy|cloudflare|acme-dns`); (7) restart services; (8) print posture (peers by trust model, refused-pending-patch list). State counts before/after asserted (SC-009). Fresh install gets the same via `component_install_claw_certs()`.

## R10 — Cross-spec/document deltas (FR-030/031)

**Decision**: README federation section, `docs/N2N-RISK.md`, `docs/N2N-RISK-MIGRATION-FOR-PEERS.md`, `scripts/peering-setup.sh`, `.env.example` (new vars: `N2N_CLAW_DOMAIN`, `N2N_ACME_DNS_PROVIDER`, provider creds, `N2N_ACME_EMAIL`), SOUL.md, TOOLS.md, HUD. Specs 052/053/056/057 get a one-line "superseded by 060 for channel trust" note in their spec.md headers. The 059 draft revision (-01) is out of scope (spec assumption) but the research here (R1 channel binding, R4 discrimination byte) is written to be lifted into it later.
