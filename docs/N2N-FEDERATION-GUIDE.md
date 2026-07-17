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

## 6. Wire hardening (feature 063)

A live two-operator packet capture confirmed the 060 channel is fully encrypted
with zero JSON-RPC leakage. Feature 063 hardens the four follow-ups that capture
surfaced. What it means for you as a peer:

- **Endpoint auto-persist (automatic, no config).** When you dial a peer and the
  authenticated channel comes up, that current address is remembered. After a
  restart or an ngrok address rotation the reconnect supervisor re-dials the
  *current* endpoint — **you no longer need to re-dial every time an address
  changes.** A failed dial never overwrites a known-good address.
- **Post-quantum posture (`N2N_PQ_MODE`).** Default `opportunistic`: your claw
  offers the X25519MLKEM768 hybrid where the stack supports it and accepts a
  classical fallback, so a channel gets PQ only when *both* peers can. The
  `/n2n/certs` and `/n2n/posture` views now show each channel's `tls_version`,
  `cipher`, `kex_group`, and `pq: available|unavailable` — honestly. **Real PQ and
  ECH need OpenSSL ≥ 3.5 / Python ≥ 3.13**; on the common Python-3.10/OpenSSL-3.0.2
  host `pq_available` is `false` and `kex_group` is unreadable — that is expected,
  not a fault. `N2N_PQ_MODE=require` fails fast at startup on a stack that can't do
  PQ rather than silently refusing every peer.
- **Mesh-layer TLS (P2, a coordinated flag day).** The BGP mesh/keepalive session
  that rides alongside NCFED can now be brought under NetClaw's own TLS + auth on
  untrusted paths, gated by the **same `N2N_CERT_MODE` flag** as the eN2N channel.
  This is a wire change for mesh peers — enable it on **all** mesh peers together,
  exactly like the 060 rollout; an un-upgraded mesh peer is refused with an
  actionable reason in `enforce` mode, never silently downgraded.
- **Accepted residuals (documented by design).** Two identity signals remain
  observable to a passive on-path observer and are accepted on purpose: (a) the
  13-byte NCFED preamble carries AS + router-id in the clear so the shared
  listening port can discriminate NCFED from BGP/NCTUN *before* TLS — structural,
  cannot move inside TLS without breaking port discrimination; (b) the TLS SNI
  carries the claw domain until an ECH-capable stack is available (an ECH-ready
  seam is in place and activates automatically once `ssl` exposes ECH). Both are
  reported in `/n2n/posture` so operators can see the exposure rather than assume
  it away.
