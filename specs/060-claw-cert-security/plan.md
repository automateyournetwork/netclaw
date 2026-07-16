# Implementation Plan: NCFED/N2N Certificate-Based Channel Security ("Claw Certification")

**Branch**: `060-claw-cert-security` | **Date**: 2026-07-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/060-claw-cert-security/spec.md`

## Summary

Close the eN2N crypto gap: every external federation channel becomes TLS-encrypted and credential-authenticated on the existing shared port (TLS discriminated by first byte `0x16` alongside BGP `0xFF` and legacy `NCFED` magic), under two per-peer trust models — **domain-verified** (ACME/Let's Encrypt certificate for an operator-owned DNS name, obtained via DNS-01 with provider-agnostic automation and challenge-delegation fallback; reference deployment `netclaw.automateyournetwork.ca` on GoDaddy) and **pinned** (self-signed + TOFU, the existing iN2N pattern extended to eN2N). Dialer authentication uses an application-layer signed nonce (the proven iN2N mechanism) rather than TLS client certificates, because Let's Encrypt is removing the clientAuth EKU. iN2N gains hub attestation: the Border becomes a risk-local CA issuing member certs, and members verify the hub's chain at dial. All credentials rotate automatically before expiry with dual-trust overlap; heartbeats carry credential health; the HUD gets a certificate panel; quarantine-DoS accounting and enrollment-fingerprint logging are fixed per the 059 Security Considerations; a fresh-install path and a single-command idempotent patch for existing claws (Nick, Byrn, AB) complete the rollout. Certificates are a prerequisite of eN2N — production refuses cleartext.

## Technical Context

**Language/Version**: Python 3.10+ (daemon + `bgp/federation/*`, matching 052/053/056/057); Node.js 18+/ES2022 (HUD render only); Bash (installer/patch)
**Primary Dependencies**: Existing `bgp-daemon-v2.py` + `bgp/federation/*` (channel, internal_channel, risk, service, manager, audit, gateway, negotiate); `cryptography` (already a repo dependency — keys, CSRs, X.509 issuance/verification); **lego** (single-binary ACME client, vendored/downloaded at install, drives DNS-01 across 100+ providers); Python stdlib `ssl`/`asyncio`/`sqlite3`/`json`. No new Python packages.
**Storage**: Extend existing SQLite `~/.openclaw/n2n/federation.db` (peer trust columns, credential + rotation-event tables); key material under `~/.openclaw/n2n/keys/` (CA, host credential, ACME account) with `0600`/`0700` permissions
**Testing**: pytest (unit: discrimination, issuance, verification, rotation-overlap state machine); live two-claw loopback federation tests (the 056/057 pattern); reference-deployment walkthrough per quickstart.md
**Target Platform**: Linux (WSL2 + native), systemd --user present (matches 057)
**Project Type**: Daemon/protocol feature + installer + HUD panel (single repo, existing layout)
**Performance Goals**: TLS adds one handshake RTT at channel open (channels are long-lived — negligible); heartbeat credential payload ≤ 200 bytes; renewal daemon task wakes ≤ once/hour
**Constraints**: One tunnel/port per operator (FR-001a — TLS shares the discriminated port); no inbound reachability ever required for issuance (DNS-01 only); zero channel drops across rotations (dual-trust overlap); patch preserves 100% of federation state and is idempotent
**Scale/Scope**: Mesh of ~2–10 external peers, 1 risk with ~25 members per claw — small-N; correctness and operability dominate over throughput

## Constitution Check

*GATE: evaluated pre-Phase-0 and re-checked post-Phase-1.*

| Principle | Status | Notes |
|---|---|---|
| I/II/VIII Safety, read-before-write, verify | PASS | No managed-device interaction; channel changes verified by live loopback federation tests before/after |
| IV Immutable audit (GAIT) | PASS | FR-005/016/022 route refusals + rotation events through the existing `audit.record` + GAIT trail |
| V MCP-native | PASS | Operator surface lands in existing `n2n-mcp` tools + daemon HTTP routes; no bespoke integration |
| IX Security by default | PASS | This feature *is* the security default; least-privilege DNS credentials documented; `0600` key material |
| X Observability | PASS | HUD cert panel (US4), posture counts (FR-019), heartbeat health (FR-024) |
| XI Full-stack artifact coherence | PASS (planned) | README, catalog.sh (`claw-certs` component), install-steps.sh, HUD, SOUL.md, .env.example, TOOLS.md updates are FR-030 deliverables in tasks |
| XIII Credential safety | PASS | DNS API token + ACME account key in `.env`/keys dir, never in git; `.env.example` documents names only |
| XV Backwards compatibility | PASS w/ justification | eN2N cleartext is *intentionally* refused in production (Q4 clarification: "certificates are a prerequisite of eN2N"); documented migration path = one-command patch (FR-028); iN2N legacy members keep compatibility window (FR-011). See Complexity Tracking |
| XVI Spec-driven | PASS | spec.md ratified + clarified (5 Qs) on branch `060-claw-cert-security` |
| XVII Milestone blog | NOTED | Draft after `/speckit.implement` completes |

## Project Structure

### Documentation (this feature)

```text
specs/060-claw-cert-security/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output (reference deployment: netclaw.automateyournetwork.ca)
├── contracts/           # Phase 1 output (wire + HTTP/MCP contracts)
└── tasks.md             # Phase 2 (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
mcp-servers/protocol-mcp/
├── bgp-daemon-v2.py                 # listener discrimination (+0x16 TLS branch), /n2n/certs* HTTP routes, renewal task startup
└── bgp/
    ├── constants.py                 # TLS_FIRST_BYTE, cert defaults (lifetimes, thresholds), NCFED hello v2 fields
    └── federation/
        ├── certs.py                 # NEW — key/CSR/X.509 issue+verify (risk CA, host credential), fingerprints, overlap logic
        ├── acme.py                  # NEW — lego driver (issue/renew, provider env, delegation), renewal scheduler task
        ├── channel.py               # eN2N: TLS server accept + client dial, signed-nonce hello v2, trust-model verification
        ├── internal_channel.py      # iN2N: hub presents CA-signed cert; member verifies chain to enrolled anchor
        ├── risk.py                  # Border-as-CA issuance at enrollment; fingerprint logging; per-source quarantine accounting
        ├── service.py               # trust records, heartbeat credential payload, refusal reasons, posture counts
        ├── manager.py               # schema migration v3 (trust columns, credential/rotation tables)
        └── audit.py                 # rotation + refusal event kinds

scripts/
├── in2n-member.py                   # member-side hub verification + fingerprint log
├── patch-claw-certs.sh              # NEW — single-command idempotent upgrade for existing claws (FR-028)
└── lib/
    ├── catalog.sh                   # + "claw-certs" component entry
    └── install-steps.sh             # + component_install_claw_certs() (lego fetch, keygen, optional domain wizard)

ui/netclaw-visual/                    # HUD certificate panel (trust model, fingerprint, expiry, amber/red, rotation events)

docs/
├── N2N-RISK.md                      # trust models, fingerprint step, heartbeat health (FR-030)
└── N2N-RISK-MIGRATION-FOR-PEERS.md  # patch instructions for Nick/Byrn/AB (FR-030)

mcp-servers/n2n-mcp/                 # n2n_certs / n2n_cert_rotate tool surface (existing server, new tools)

tests/
└── protocol/                        # unit: discrimination, certs.py, overlap; integration: two-claw loopback TLS federation
```

**Structure Decision**: extend the existing `bgp/federation/` package in place (same pattern as 052→057); two new modules (`certs.py`, `acme.py`) keep issuance concerns out of channel code. No new services or repos; the renewal scheduler is a daemon asyncio task, not a systemd timer (one less unit to manage, daemon is already durable under systemd per 057).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle XV: production eN2N refuses cleartext peers (breaking for unpatched claws) | Operator decision (Clarification Q4): "if you want eN2N you need this" — impersonation + cleartext on the public internet is the gap being closed; a compatibility mode would preserve the vulnerability it exists to remove | Warn-only production mode rejected: it leaves the downgrade path an attacker needs; migration is a one-command patch (FR-028) and refusals carry an actionable reason (FR-029), keeping the break visible and recoverable |
| Vendored external binary (lego) rather than pure-Python ACME | DNS-01 across 100+ providers + ARI support is a solved problem in lego; hand-rolling ACME violates the spec's assumption and is high-risk crypto code | certbot rejected (heavy Python install, plugin sprawl per provider); acme.sh rejected (shell, harder to drive programmatically); pure-`cryptography` ACME rejected (reimplementing RFC 8555 + provider APIs) |
