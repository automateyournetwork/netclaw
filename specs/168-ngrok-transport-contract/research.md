# R01 research — 2026-11-01

## TLS binding

**Decision:** in2n-tls-exporter-v1; isolated pyOpenSSL 26.4.0, cryptography 50.0.2,
service-identity 26.1.0. Preserve separate certificate-helper dependencies.

**Rationale:** [RFC9266](https://www.rfc-editor.org/rfc/rfc9266.html) defines
TLS1.3 tls-exporter and leaves tls-unique undefined. Python3.12.12/OpenSSL3.6.3
measurement returned matching48-byte tls-unique, but no public exporter API.
At 2026-11-01T17:37:45.066068Z the selected libraries/OpenSSL4.0.3 produced equal
32-byte exporters per connection, different across connections; correct SAN
passed, wrong SAN/CA and TLS1.2 failed. Existing certificate/possession primitives
worked at 17:38:30.787025Z; wrong application identity/altered binding failed.
These are SYNTHETIC IN-MEMORY measurements, not sockets/application/ngrok.
Private receipts: ~/.local/share/netclaw/spec168-tls-research-20261101/
stdlib-result.json, exporter-current-result.json, repo-crypto-current-result.json.
Earlier exporter-result.json used older candidates; do not select those pins.

**Alternatives:** Undefined binding semantics and private CPython pointers rejected.
aioopenssl latest release dates to2021; Twisted requires reactor/stream bridging
and has Windows loop constraints. Use a bounded owned asyncio adapter with
[public pyOpenSSL](https://www.pyopenssl.org/en/stable/api/ssl.html) and
[service-identity](https://service-identity.readthedocs.io/en/stable/api.html).
[Cryptography49+](https://cryptography.io/en/latest/changelog/) removes Intel macOS
wheels; strict packaging on that platform remains unqualified.

## Registry and ngrok

**Decision:** Owned versioned registry, named v3 endpoints, exact reserved TCP
URLs and per-installation lifecycle.

**Rationale:** Baseline netclaw allocates ephemeral addresses and globally stops
processes; daemon selects first localhost:4040 tunnel. Neither supports safe two-
service operation. Reserved addresses last until deletion, recreation is not a
same-address guarantee; ngrok PoP is not cloud deployment region.
[Config](https://ngrok.com/docs/gateway/agent/config/v3),
[CLI](https://ngrok.com/docs/gateway/agent/cli),
[TCP reservations](https://ngrok.com/docs/gateway/domains/tcp-addresses),
[CLI API](https://ngrok.com/docs/gateway/agent/cli-api).
Authtoken is not API key; neither is application identity.

**Installed-agent correction:** ngrok3.36.1 rejected the documented `tcp://`
upstream-origin syntax during a read-only config check at18:23:23Z. The renderer
now uses bare `127.0.0.1:port` upstreams under exact public `tcp://` endpoints.
At2026-11-01T18:24:08.547000Z the same installed agent accepted the rendered v3
configuration. Both receipts are private (`ngrok-config-check.json` and
`ngrok-config-check-fixed.json`). These checks used synthetic reservations and
started no agent or endpoint. This is a measured compatibility adjustment, not
permission to terminate TLS in ngrok.

At 2026-11-01T17:36:48.765364+00:00, ngrok api reserved-addrs list failed: API key
required. Receipt ~/.local/share/netclaw/spec168-preflight-20261101/ngrok-account-read.json.
Account entitlements/limits/addresses are UNQUALIFIED. Review
[account limits](https://dashboard.ngrok.com/usage/limits); R14's30–40 endpoints
plus HUD is a planning envelope, not entitlement/pricing.

**Alternatives:** Connect-time API discovery conflates trust/routing and adds
member credentials. Ephemeral URLs reproduce spec108's rejected address rot.

## Protocol, compatibility and portability

**Decision:** Strict iN2N starts TLS; eN2N preserves identification then mandatory
TLS1.3/certificate-hash proof on a dedicated NCFED-only listener. Explicit legacy
profiles remain, with no fallback. Stable application identity survives routing
moves; full runtime-state migration is qualified in later briefs.

**Rationale:** Forwarded loopback cannot imply trust. Both iN2N launchers must
use independent server names. SNI routing cannot carry cleartext-first eN2N.
Preamble metadata is disclosed; protected application frames are not. Public TOFU
would not prove the intended Border. Account/DNS/location are not application ID.
Move versus clone, fenced cutover, durable audit and secret rebinding matter.
Thermidor is design/evidence only; import no code.

## Owner-approved direct-cloud pivot — 2026-11-01

The owner asked whether cloud ingress removes the home-NAT reason for ngrok and
explicitly approved the pivot. GCP supports a stable external VM address with
firewall-controlled reachability; a single Border does not require a load balancer.
[Google IP addressing](https://docs.cloud.google.com/compute/docs/ip-addresses)
and [static external addresses](https://docs.cloud.google.com/compute/docs/ip-addresses/configure-static-external-ip-address)
support this deployment choice. A future [L4 passthrough load balancer](https://docs.cloud.google.com/load-balancing/docs/network/networklb-backend-service)
retains backend connection termination and the raw NCFED preamble.

This changes placement/exposure, not cryptography or federation: iN2N is still
member-to-Border, eN2N/NCFED is external Border-to-Border, and application TLS,
name/CA checks, exporter binding, peer trust and consent remain required.
Schema2 makes transport explicit and permits only exact direct unicast bindings;
schema1 retains the original loopback/reservation contract. No automatic migration.
The owner-confirmed Free ngrok plan and successful API inventory are historical
optional-provider facts, no longer blockers to the chosen direct-cloud qualification.
