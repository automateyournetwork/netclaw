# Federating with a NetClaw — onboarding guide

So you want to peer your NetClaw with someone else's (eN2N federation). This is
the short, current guide as of **feature 060 (Claw Certification)**: federation
is now **TLS-encrypted and certificate-authenticated by default**. Cleartext
peering is refused in production — you and your peer each need a claw credential
(one command) before the channel will open.

## 0. Prerequisites

- A running NetClaw with the mesh daemon (`netclaw-mesh.service`) up.
- A way to be reached: typically an ngrok TCP tunnel to your mesh port (the
  endpoint may change freely — identity does not depend on it).
- Your BGP identity `as<ASN>-<router-id>` (e.g. `as65001-4.4.4.4`).

## 1. Get a claw credential (once)

```bash
cd ~/netclaw && git pull && scripts/patch-claw-certs.sh
```

Fresh installs get this automatically (the `claw-certs` component). You now have
a pinned-model self-signed credential under `~/.openclaw/n2n/keys/` and secured
channels are enabled (`N2N_CERT_MODE`).

**Two trust models** — pick per what you have:

- **Pinned (default, no domain):** your key is pinned by the peer on first
  contact (trust-on-first-use), confirmed out of band — exactly like today's
  consent, plus cryptographic continuity after. Nothing else to set up.
- **Domain-verified (optional):** bind your identity to a DNS name you own so
  peers verify you against public trust (Let's Encrypt). Works behind changing
  tunnels — issuance is DNS-01, no inbound reachability, no A record. See §4.

## 2. Exchange identities out of band

Confirm with your peer, over a channel you trust (Slack/Signal/in person):

- each side's `as<ASN>-<router-id>`
- each side's reachable `host:port` (ngrok endpoint)
- (domain-verified only) each side's claw domain

This out-of-band confirmation is the trust root — the certificate then makes it
un-spoofable on the wire.

## 3. Dial and federate

The lower-AS side dials; the higher-AS side waits for inbound. To dial a peer:

```bash
curl -s -X POST http://127.0.0.1:8179/n2n/connect -H 'Content-Type: application/json' \
  -d '{"peer":"as65007-7.7.7.7","host":"<their-host>","port":<their-port>,
       "display_name":"Nick"}'          # add "claw_domain":"..." if they are domain-verified
```

The channel upgrades to TLS, both sides prove key possession (channel-bound
signed nonce), and pin each other's key. Consent + per-peer authorization work
exactly as before — default-deny; grant tools/skills explicitly.

Verify:

```bash
curl -s http://127.0.0.1:8179/n2n/certs   | python3 -m json.tool   # trust model, fingerprint, expiry
curl -s http://127.0.0.1:8179/n2n/health  | python3 -m json.tool   # channel state
```

Both should show your peer `verified`. If a peer hasn't run §1, they're refused
with `peer requires certificate-secured federation — run scripts/patch-claw-certs.sh`;
send them this guide.

## 4. Optional: domain-verified identity

If you control a DNS name, bind your claw to it so peers validate you via public
trust. Provider-agnostic via `lego` (Cloudflare, Route53, GoDaddy, acme-dns
delegation). The full GoDaddy walkthrough (including the new-style Personal
Access Token path with NetClaw's exec hook) and the universal acme-dns fallback
are in [the reference-deployment quickstart](../specs/060-claw-cert-security/quickstart.md).
Short version:

```bash
# example: Cloudflare
#   ~/.openclaw/.env:
#     N2N_CLAW_DOMAIN=claw.yourdomain.com
#     N2N_ACME_DNS_PROVIDER=cloudflare
#     CLOUDFLARE_DNS_API_TOKEN=<zone-scoped token>
scripts/patch-claw-certs.sh --domain claw.yourdomain.com --dns-provider cloudflare
```

Certificates renew automatically at ~2/3 of lifetime with a dual-trust overlap —
no channel ever drops for expiry, nothing to remember.

## 5. Rotation, health, and what your peers see

- The HUD (and `/n2n/posture` → `channel_security`) shows every channel's trust
  model, credential fingerprint, days-to-expiry (amber <30, red <14), and
  renewal state; heartbeats keep this fresh between reconnects.
- If your pinned key ever changes outside a rotation window, peers refuse and
  flag you for out-of-band re-verification (this is the anti-impersonation
  guarantee working).

That's it. Pinned mode gets two claws federating securely in a couple of minutes
with no domain; domain-verified is a superset for operators who want public-trust
identity.
