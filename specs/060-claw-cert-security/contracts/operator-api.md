# Contract: Operator API — daemon HTTP routes, n2n-mcp tools, CLI (060)

## Daemon HTTP (localhost:8179, extends existing /n2n/*)

| Route | Method | Request | Response |
|---|---|---|---|
| `/n2n/certs` | GET | — | `{credentials: [{kind, subject_identity, fingerprint, issuer, not_after, days_remaining, renew_state, state}], peers: [{identity, trust_model, claw_domain, verify_state, peer_cred_fp, peer_cred_not_after}], members: [...]}` — feeds the HUD panel (FR-017) |
| `/n2n/certs/rotate` | POST | `{target: "<identity>|risk-ca|host", emergency: false}` | `{rotated: true, overlap_until: "..."}\|{error}` (FR-015) |
| `/n2n/certs/renew` | POST | `{}` | force an immediate ACME renewal check `{checked: n, renewed: n, failed: [...]}` |
| `/n2n/posture` | GET (extended) | — | adds `channel_security: {by_trust_model: {...}, degraded: n, amber: n, red: n, renewals_failing: n, clock_suspect: bool}` (FR-019) |
| `/n2n/connect` | POST (extended) | adds optional `claw_domain` | records the peer's declared domain (verified attribute, FR-003a) |

## n2n-mcp tools (new)

| Tool | Args | Behavior |
|---|---|---|
| `n2n_certs` | `scope?: all\|peers\|members\|self` | wraps `GET /n2n/certs`; renders trust model, fingerprint, days remaining, amber/red flags |
| `n2n_cert_rotate` | `target, emergency?: bool` | wraps `/n2n/certs/rotate`; emergency requires explicit confirmation text |

## Patch installer CLI (FR-028)

```bash
scripts/patch-claw-certs.sh \
  [--domain netclaw.automateyournetwork.ca] \
  [--dns-provider godaddy|cloudflare|route53|acme-dns|...] \
  [--yes]            # non-interactive
```

Exit contract: `0` success (posture printed, state counts asserted equal before/after); `2` schema migration failure (DB untouched — migration is transactional); `3` credential generation failure; idempotent — re-run converges to the same state. Never deletes peers, members, consent, grants, or audit rows.

## Fresh-install component (Constitution XI)

- `scripts/lib/catalog.sh`: `"claw-certs|Federation|Claw Certification|TLS credentials, risk CA, ACME domain identity + rotation for N2N"`
- `scripts/lib/install-steps.sh`: `component_install_claw_certs()` — fetch lego binary (checksum-pinned), create keys dir, generate host credential + risk CA, optional domain wizard, write `.env` entries.

## HUD contract (ui/netclaw-visual)

Certificate panel consumes `GET /n2n/certs` + `GET /n2n/posture`:
- per-row: trust-model badge (`domain-verified` green / `pinned` blue / `legacy` grey-red), identity, fingerprint (truncated, click-to-copy), issuer, `days_remaining` with amber `<30` / red `<14` (FR-018)
- posture strip: counts by trust model, degraded count, failing renewals
- event feed: `rotation_event` rows (renewed/rotated/failed/emergency, verify-refused) from the audit stream
