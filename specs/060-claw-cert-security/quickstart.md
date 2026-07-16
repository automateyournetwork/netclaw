# Quickstart: Claw Certification — Reference Deployment

Worked end-to-end against the normative reference deployment (spec §Reference Deployment): the operator owns **`automateyournetwork.ca`** (DNS at **GoDaddy**) and certifies their claw as **`netclaw.automateyournetwork.ca`**. Every step is exact; SC-008 requires this document to work on the first attempt.

## A. Existing claw (John, Nick, Byrn, AB): one-command patch

```bash
cd ~/netclaw && git pull
scripts/patch-claw-certs.sh          # pinned model — no domain needed, ~2 min
```

What it does (idempotent, state-preserving): migrates the federation DB schema, generates your claw's credential and risk CA, re-issues durable-member certs, restarts services, prints posture. Your peers, consent records, grants, members, and audit history are untouched (verified by before/after counts).

After the patch: channels to **patched** peers resume automatically (pinned/TOFU). **Unpatched** peers are refused with the reason `peer requires certificate-secured federation — run scripts/patch-claw-certs.sh` — send them section A.

## B. Upgrade to domain-verified identity (`netclaw.automateyournetwork.ca`)

### B.1 GoDaddy — VALIDATED path (new-style Personal Access Token)

GoDaddy's current tokens are `gd_pat_…` Personal Access Tokens that authenticate
with `Authorization: Bearer`. lego's built-in `godaddy` provider expects the
**legacy** `sso-key KEY:SECRET` header, so a PAT does **not** work with
`--dns godaddy`. NetClaw ships a small exec-provider hook that drives GoDaddy
with the PAT. This is the exact path validated end-to-end against
`netclaw.automateyournetwork.ca` (real Let's Encrypt cert issued 2026-07-15).

1. GoDaddy → **Developer Portal → Personal Access Tokens** → create one with
   **Domains: read/write** for the account holding your domain.
2. Add to `~/.openclaw/.env`:

   ```bash
   N2N_CLAW_DOMAIN=netclaw.automateyournetwork.ca
   N2N_ACME_DNS_PROVIDER=exec
   N2N_ACME_EMAIL=you@example.com
   EXEC_PATH=/home/<you>/netclaw/scripts/lib/godaddy-acme-hook.sh
   EXEC_PROPAGATION_TIMEOUT=300
   EXEC_POLLING_INTERVAL=15
   # GoDaddy propagates to its authoritative NS in ~30s; make lego wait for THEM,
   # not the local resolver, or the CA gets NXDOMAIN. Use your zone's NS:
   N2N_ACME_RESOLVERS=ns51.domaincontrol.com:53,ns52.domaincontrol.com:53
   GODADDY_PAT=gd_pat_xxxxxxxx           # your PAT (find your NS: dig +short NS <domain>)
   ```

3. `scripts/patch-claw-certs.sh --domain netclaw.automateyournetwork.ca --dns-provider exec`
   The claw obtains the cert via DNS-01 (temporary TXT at
   `_acme-challenge.netclaw.automateyournetwork.ca`, written + removed by the hook)
   and the daemon auto-renews at ~2/3 lifetime with the same settings.

> If your account **can** mint a legacy API key+secret instead, you may use the
> native provider (`N2N_ACME_DNS_PROVIDER=godaddy`, `GODADDY_API_KEY`/`_SECRET`)
> and drop the EXEC_* lines. The PAT + exec hook is the path that works today.

### B.2 Universal fallback: challenge delegation (works on ANY provider)

1. The patch installer (or `component_install_claw_certs`) can host a tiny **acme-dns** challenge zone for you, or use any API-capable DNS zone you already have. It prints your delegation target, e.g. `d4f9c2.auth.acme-dns.io` (self-hosted preferred; see docs).
2. In GoDaddy's DNS manager for `automateyournetwork.ca`, create **one CNAME, once**:

   ```text
   _acme-challenge.netclaw  CNAME  <your-delegation-target>
   ```

3. Add to `~/.openclaw/.env`:

   ```bash
   N2N_CLAW_DOMAIN=netclaw.automateyournetwork.ca
   N2N_ACME_DNS_PROVIDER=acme-dns
   N2N_ACME_EMAIL=john.capobianco@example.com
   ACME_DNS_API_BASE=<printed by installer>
   ACME_DNS_STORAGE_PATH=~/.openclaw/n2n/keys/acme/acme-dns.json
   ```

4. Re-run `scripts/patch-claw-certs.sh --domain netclaw.automateyournetwork.ca --dns-provider acme-dns`. Issuance and every future renewal are automatic; GoDaddy stays your registrar and primary DNS and is never touched again.

### B.3 Cloudflare (and other providers) — same shape

```bash
N2N_CLAW_DOMAIN=<claw>.<your-domain>
N2N_ACME_DNS_PROVIDER=cloudflare
CLOUDFLARE_DNS_API_TOKEN=<zone-scoped token>
```

Any of lego's 100+ providers works with its documented env vars; delegation (B.2) covers everything else.

## C. Federate and verify

1. Peers dial your existing endpoint (e.g. `8.tcp.ngrok.io:20203`) — the tunnel is transport only; your identity is now `netclaw.automateyournetwork.ca` (a verified attribute of `as65001-4.4.4.4`; nothing re-keys).
2. On the peer: `n2n_connect` as usual, optionally passing `claw_domain: netclaw.automateyournetwork.ca`. Their claw verifies the Let's Encrypt chain + name; your claw pins them (if pinned model) or verifies their domain.
3. Check the HUD certificate panel (http://localhost:3000): your row shows `domain-verified / netclaw.automateyournetwork.ca / Let's Encrypt / ~90d / auto-renew on`; each peer row shows its trust model and days remaining.
4. Wire check (SC-002): `tcpdump` on the channel shows TLS, no readable payloads.
5. Negative check (SC-001): a connection asserting your peer's identity with the wrong key is refused and appears in `n2n_audit` as `verify-refused`.

## D. What rotation looks like (no action required)

- ~Day 60 of the 90-day certificate: renewal fires automatically; the HUD event feed logs `renewed`; peers verifying by name notice nothing.
- Pinned credentials and risk-CA/member certs: successors are announced over the live channel (`overlap-opened` → `overlap-closed` events); zero channel drops (SC-004).
- If renewal ever fails, the row turns amber at 30 days remaining, red at 14, with the failure reason shown (SC-005) — you'll see it long before it matters.
