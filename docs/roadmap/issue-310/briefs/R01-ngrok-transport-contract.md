# R01 — direct cloud transport contract and TLS identity fixes

- **Roadmap item:** prerequisite for everything cloud
- **Depends on:** none (runs beside R02)
- **Gate:** human review of verification.md before R03
- **Status (2026-11-01):** Spec168 complete for the owner-amended R01 lab scope;
  [actual evidence](../../../../specs/168-ngrok-transport-contract/verification.md).
  R02/R03 have not started.

## Owner amendment — 2026-11-01

Direct cloud TCP is now primary, as explicitly approved by the owner. A stable
provider IP with separate service ports replaces mandatory ngrok reservations;
ngrok remains optional for NAT-constrained Borders. G2/G9 in the roadmap record
the exact security/exposure boundary. R01 includes preparation of a transport-only
GCP pilot for approved live evidence. The owner subsequently delegated DNS/HTTPS,
the full open lab HUD, and an Anthropic Sonnet question routed to the on-prem
subnet-calculator member. No R02/R03 production or device workload is included. The original ngrok implementation and historical evidence are retained.

## Specify input

NetClaw Borders must accept member connections (iN2N) and independent-peer
connections (eN2N/NCFED) through stable native cloud TCP endpoints, without Tailscale, so a
Border can run in a public cloud while members stay on-premises behind
outbound-only firewalls. Members dial out; they need no ngrok agent and no
inbound listener. Optional ngrok is needed only when a Border lacks direct reachable ingress.

An operator registers each Border service explicitly: its public routing
address, the TLS server name the client must verify, and the trust anchor. A
tunnel hostname never doubles as an identity. Connections fail closed: a wrong
certificate, a missing or altered channel binding, an unknown member key, a
replayed enrollment or a lost tunnel never falls back to a weaker mode. Existing
cloudflared (spec 108) and direct LAN transports keep working.

User stories:
- P1: An operator brings up a Border with separate registered TCP endpoints
  for iN2N and eN2N and sees both in status.
- P1: A member on a different network enrolls and attaches using the routing
  address while verifying the Border certificate's own name.
- P1: Impersonation, downgrade and replay attempts are refused and logged.
- P2: An operator replaces an endpoint address without re-issuing member
  identities.

## Clarify: decisions (recommended default first)

1. Endpoint registry: a versioned file in the Border's runtime home, delivered to
   members inside the enrollment bundle; never derived from ngrok's API at
   connect time.
2. iN2N TLS minimum: TLS 1.3 for every non-local endpoint; existing local
   deployments keep their current setting with a documented migration (XV).
3. Channel binding under TLS 1.3: RFC 9266 leaves `tls-unique` undefined for
   TLS 1.3 and defines `tls-exporter` instead, while Python's `ssl` only exposes
   `tls-unique`. Measure what the pinned Python/OpenSSL returns, then choose
   between keeping `tls-unique` with a recorded rationale and moving to an
   exporter-based binding through a library that exposes keying-material export.
   [HUMAN if the measurement is ambiguous]
4. Border certificate trust for iN2N: Border-owned CA or pinned certificate
   distributed in enrollment; a public CA is allowed only with explicit name
   verification.
5. Lifecycle: existing owned Border daemon supervision for direct TCP; optional
   ngrok has its own owned agent with reserved addresses, never ephemeral endpoints.
6. 443-only egress networks: documented as unsupported in R01 (members dial the
   endpoint's assigned port). TLS passthrough on 443 for iN2N is recorded as a
   later option; it does not help eN2N, which starts with a cleartext preamble.

## Plan notes

Confirmed gaps at upstream `9ba12ffc`:
- `scripts/in2n-member.py:53` calls `svc.dial_border(host, port, ...)` with no
  SSL context; the daemon dial loop passes `internal_security.client_context(host)`.
- `bgp/federation/service.py:2251` `dial_border` calls
  `asyncio.open_connection(host, port, ssl=ssl_context)` with no `server_hostname`,
  so the routing hostname is the verified name. Add an explicit TLS server-name
  field; never solve a mismatch by disabling verification.
- `bgp/federation/internal_security.py` sets `TLSv1_2` minimum (lines 21, 34);
  `tls.py` (eN2N) already requires 1.3.

Wire facts to preserve:
- eN2N sends the NCFED identification preamble before upgrading the same
  connection to TLS (`tls.py`), so only raw TCP byte forwarding works. HTTP or
  SNI-routed TLS endpoints cannot carry it. Its binding hashes the listener
  certificate (`tls-server-end-point`); it is not an exporter despite some names.
- iN2N starts with TLS, then an internal preamble and a fresh challenge that the
  member signs with its enrolled key including the channel binding; the Border
  attests its hub identity.
- The shared-port BGP/NCFED dispatcher must refuse routing-control paths on any
  publicly reachable listener (split listeners or refuse by protocol).
- `scripts/netclaw peering` and `scripts/peering-setup.sh` already drive ngrok:
  extend them rather than adding a parallel path. Spec 108 research R0 rejected
  ephemeral addresses because of address rot. Direct deployments use provider-reserved
  IPs and explicit ports; optional ngrok uses TCP reservations.
- Verify the selected provider's address/firewall/instance limits and costs; record
  projected R14 service endpoints separately from public-IP count. Optional ngrok
  account limits remain separately qualified.

## Out of scope

Unapproved cloud provisioning, production/device workloads, HA and execution-model
changes. The owner-approved pilot includes its full public HTTPS HUD and scoped
Sonnet/subnet/RAG demonstration. R02/R03 remain unstarted.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Positive | Member on a separate network attaches through a direct cloud TCP endpoint; eN2N peer completes preamble, TLS upgrade and consent through a second service port |
| Identity | Wrong TLS name, wrong CA or pin, altered binding, forged key possession, expired or replayed enrollment, revoked member: each refused |
| Downgrade | Cleartext attempt, injected PROXY header, TLS 1.2 client on a remote endpoint: refused, no fallback |
| Exposure | Unenrolled TCP connect is reachable but refused (recorded separately from admission); BGP routing path via the public endpoint refused; member-to-member attempt refused |
| Lifecycle | Owned Border daemon restart reconnects to the same stable address; endpoint replacement works without new member identities |
| Regression | cloudflared transport, direct LAN iN2N and `tests/n2n/test_internal_tls_security.py` pass |
