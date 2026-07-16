# N2N Risk model — technical readout for federated peers (Nick, Byrn)

**TL;DR:** Feature 056 (iN2N / "a risk of NetClaws") is an **internal** federation
layer. **eN2N — the NCFED mesh you federate with John over — is frozen and
unchanged.** Your federation keeps working with **no re-consent**. There is one
brief mesh blip when John restarts his daemon to become a Border, and after that
John's claw advertises *more* capabilities (the aggregate of his internal
members) under the same identity you already trust.

---

## What changed

- **New: iN2N (internal federation).** One operator can now split their monolithic
  NetClaw into a **risk** — a group of focused member claws behind one **Border
  Claw**. John is decomposing his ~190-skill monolith into a Border + ~27 scoped
  members (CML claw, pyATS claw, Azure claw, …). See [N2N-RISK.md](N2N-RISK.md).
- **Frozen: eN2N (the NCFED mesh).** The wire framing, `n2n/hello` handshake,
  mutual consent, default-deny invocation, budgets, kill switch, and the
  no-secrets guard are **byte-for-byte unchanged** and regression-tested (the
  full eN2N test suite still passes). Nothing you rely on moved.
- **Members are invisible to you.** A risk presents **one identity** externally
  (the Border). You will **never** see member IDs, endpoints, or internal
  topology (design guarantee FR-016).

## What this means for your federation with John

- **John's Border keeps his existing BGP identity — AS 65001 / router-id
  4.4.4.4.** So your consent, grants, and cached state for `as65001-4.4.4.4` stay
  valid. **No re-consent, no re-grant.**
- **One brief blip:** promoting the monolith to a Border requires a daemon
  restart. Your NCFED channel to John drops for <60s and **auto-reconnects** (the
  053 reconnect supervisor). If John's ngrok endpoint rolls on that restart,
  endpoint auto-re-announce redials you; if you're on a pre-053 build, redial
  once with his new `host:port`.
- **You'll see MORE of John's capabilities, not fewer.** John's Border now
  advertises the **union** of his members' specialties under `as65001-4.4.4.4`.
  So `n2n_peer_capabilities(peer="as65001-4.4.4.4")` will list cml, pyats, azure,
  ise, forward, ipfabric, … as risk-level capabilities (tagged as aggregate),
  with no member breakdown. Asking John's claw to run one of those still works
  exactly as before — the Border routes it internally to the right member.

## What YOU need to do

**To keep federating with John: essentially nothing.** Concretely:

1. `git pull` your netclaw repo to pick up 056 (safe — eN2N is frozen; your
   `N2N_ROLE` defaults to `standalone`, so your behavior does not change).
2. Restart your mesh daemon at your convenience (or don't — you'll re-federate
   with John's Border automatically after his restart regardless).
3. Confirm: `n2n_status` → `as65001-4.4.4.4` shows `federated`. Optionally
   `n2n_peer_capabilities(peer="as65001-4.4.4.4")` to see John's new aggregate
   capability set.

That's it. No config changes are required on your side.

## Optional — adopt the Risk model yourself

If you want the same focus / token-economy / least-privilege benefits, you can
turn your own claw into a risk. It's the same tooling:

1. Read [N2N-RISK.md](N2N-RISK.md).
2. See what members your box could run: `python3 scripts/in2n-profiles.py list`
   (env-gated to your configured backends).
3. Generate a **parallel-cutover** plan (generate-only, touches nothing):
   `python3 scripts/in2n-migrate.py --risk <your-risk> --border-endpoint <host:port>`
   then read `migration-staging/RUNBOOK.md`.
4. Your Border keeps your existing AS/router-id, so **John's** federation with
   **you** likewise continues uninterrupted. Members can be co-located or spread
   across your own hosts/clouds (they dial your Border outbound — no mesh, no
   inbound ports). Pick any provider/model per member, including local/Ollama.

## Interop notes

- eN2N stays **Border-to-Border** between risks. A member of one risk never talks
  to another operator's risk directly.
- Different OpenClaw builds/models keep interoperating via the 053 capability
  negotiation — unchanged.
- Questions or anything odd during John's cutover: ping the Slack thread.

---

# Feature 060 — Claw Certification: certify & refederate (for peers)

**What changed and why it matters to you:** eN2N used to run cleartext with your
identity asserted as a plain string — anyone who learned an endpoint could
impersonate a federated peer, and traffic crossed the internet unencrypted.
Feature 060 closes that: **every external federation channel is now TLS-encrypted
and cryptographically authenticated.** Because certificates are now a
prerequisite for eN2N, **an unpatched claw can no longer federate** — you'll be
refused with a message telling you to run the patch. This is intentional.

## The one command

On your claw host:

```bash
cd ~/netclaw && git pull
scripts/patch-claw-certs.sh
```

That's it for the **pinned model** (no domain required). It:
- preserves all your state (peers, consent, grants, members, tasks, audit — asserted by before/after counts),
- runs an additive DB migration, generates your claw credential (and, if you're a Border, your risk CA),
- turns on `N2N_CERT_MODE=on` and restarts your services,
- prints which peers are refused pending their own patch.

After both ends have patched, your channel to that peer **resumes automatically**
— TOFU-pins each other's key on the first secured contact (same out-of-band trust
root as today's consent). Nothing else to do.

## Optional: domain-verified identity

If you own a DNS name and want peers to verify you against public trust (Let's
Encrypt) instead of a pinned key:

```bash
scripts/patch-claw-certs.sh --domain claw.yourdomain.com --dns-provider cloudflare
```

- Works behind changing ngrok endpoints — identity binds to the **name**, not the
  tunnel (issuance uses DNS-01, no inbound reachability, no A record needed).
- Providers: `cloudflare`, `route53`, `godaddy` (needs API access), or `acme-dns`
  (universal fallback — one CNAME `_acme-challenge.claw → delegation-zone`, then
  automatic forever). Set the provider's credentials in `~/.openclaw/.env` per
  lego's convention.

## Rotation & visibility (automatic)

Certificates renew themselves at ~2/3 of lifetime with a dual-trust overlap — no
channel ever drops for expiry, nothing to remember. Check status anytime:

```bash
curl -s http://127.0.0.1:8179/n2n/certs | python3 -m json.tool
```

Each row shows trust model, fingerprint, days remaining (amber <30, red <14), and
renewal state; refusals and rotations also appear in `/n2n/posture` and the audit
trail.

## If a peer can't reach you

They'll see `peer requires certificate-secured federation — run
scripts/patch-claw-certs.sh`. Send them this section. Until they patch, that
channel stays down by design; every already-patched peer keeps working.
