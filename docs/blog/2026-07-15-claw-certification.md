# Draft blog post — for John's review before publishing (Constitution XVII)

**Proposed title:** Claws that prove who they are: certificate security comes to NetClaw federation

**Status:** DRAFT — do not publish until John approves. Target: WordPress via the
`wordpress-site` MCP.

---

When we first federated two NetClaws over the public internet, the identity of a
peer was, embarrassingly, just a string it typed on the wire: `as65001-4.4.4.4`.
If you knew a claw's tunnel address and its AS/router-id, you could *be* that
claw — and everything the two agents said to each other, every delegated task and
piece of network inventory, crossed the internet in the clear. Our own IETF
Internet-Draft said so out loud in its Security Considerations. This week we fixed
it.

## What we built

**Claw Certification** gives every federation channel TLS encryption and real
cryptographic identity, in two flavours:

- **Domain-verified.** If you own a DNS name, your claw gets a publicly-trusted
  Let's Encrypt certificate for it and peers verify you against the web PKI. The
  trick that makes this practical: issuance uses the DNS-01 challenge, so it works
  behind a constantly-changing ngrok tunnel with no inbound reachability and no A
  record. Your identity binds to the *name*, not the endpoint — the endpoint can
  churn all it likes.
- **Pinned.** No domain? Your claw presents a self-signed key that the peer pins
  on first contact (trust-on-first-use), confirmed the same out-of-band way
  consent already worked. Still encrypted, still un-spoofable afterward.

Authentication is mutual and bound to the specific TLS session (RFC 5929
channel binding), so an on-path attacker can't relay a proof. Inside a "risk" of
claws, the Border is now a certificate authority: members cryptographically verify
that the hub they dialed is the legitimate one — the last direction of trust the
draft flagged as missing. And every credential rotates itself before expiry with
an overlap window, so nothing ever drops because a cert aged out.

## The satisfying part

We validated it end to end on a real domain — `netclaw.automateyournetwork.ca` —
issuing a genuine Let's Encrypt certificate through GoDaddy's DNS API. That
surfaced a real-world wrinkle worth sharing: GoDaddy's new Personal Access Tokens
authenticate with `Bearer`, which the standard ACME client's GoDaddy plugin
doesn't speak (it wants the legacy key/secret header). Rather than tell operators
"go generate a different kind of key," we shipped a tiny hook so the token they
already have just works. Small thing; exactly the kind of friction that decides
whether security actually gets turned on.

## Honest engineering notes

A few things went the way good engineering is supposed to go: we caught, by
testing on real sockets instead of trusting the happy path, that the channel-
binding primitive we first reached for isn't available on our Python version — so
we switched to one that is, with the same security property. We kept the whole
feature behind a default-off switch so it couldn't destabilize a live mesh while
it was being built. And because we made certificates a *prerequisite* for
external federation, we built the migration first: one command, preserves all your
state, and an unpatched peer gets a clear "run the patch" message instead of a
silent failure.

## We cut over for real

This isn't a design doc — the first claw is live on it. `netclaw.automateyournetwork.ca`
now holds a genuine Let's Encrypt certificate (issued through GoDaddy's DNS API
via a small hook we had to write, because GoDaddy's new tokens don't speak the
shape the standard ACME client expects), federation runs certificate-authenticated,
and the credential auto-renews. The migration even caught its own bug: the patch
installer wrote config to the wrong env file and the daemon didn't pick it up —
found it, fixed it, shipped the fix. That's the system working as intended:
change, verify, correct, in the open.

## Try it

Existing operators: `scripts/patch-claw-certs.sh`. New to peering: see the
federation guide. Certificates in, cleartext out.

*Written collaboratively by John Capobianco and Claude, with a security fix
contributed by Josh (TunnelMind).*
