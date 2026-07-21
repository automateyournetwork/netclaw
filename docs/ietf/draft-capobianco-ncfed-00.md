---
title: "The NetClaw-to-NetClaw Federation Protocol (NCFED)"
abbrev: "NCFED"
category: exp
docname: draft-capobianco-ncfed-00
submissiontype: IETF
number:
date:
consensus: false
v: 3
keyword:
 - federation
 - ai-agents
 - mcp
 - a2a
 - bgp
 - multiplexing
venue:
  github: "automateyournetwork/netclaw"
  latest: "https://github.com/automateyournetwork/netclaw"

author:
 -
    fullname: "John Capobianco"
    organization: "Automate Your Network"
    email: "ptcapo@gmail.com"
    uri: "https://automateyournetwork.ca"
 -
    fullname: "Nicholas Calcutti"
    email: "calcuttin@gmail.com"
    uri: "https://nicholascalcutti.substack.com"
 -
    fullname: "Byrn Baker"
    email: "byrn@byrnbaker.me"
    uri: "https://byrnbaker.me"

normative:
  RFC4271:
  RFC8259:
  RFC5280:
  RFC5480:
  RFC6090:
  RFC6234:
  RFC9846:
  RFC5929:
  RFC8555:
  RFC9525:
  JSONRPC:
    title: "JSON-RPC 2.0 Specification"
    target: https://www.jsonrpc.org/specification
    author:
      - org: "JSON-RPC Working Group"
    date: 2013
  MCP:
    title: "Model Context Protocol"
    target: https://modelcontextprotocol.io/specification
    date: 2025
  A2A:
    title: "Agent2Agent (A2A) Protocol"
    target: https://a2a-protocol.org
    date: 2025

informative:
  RFC5082:
  RFC6335:
  RFC6455:
  RFC7301:
  RFC9266:
  RFC7435:
  RFC8126:
  WIREGUARD:
    title: "WireGuard: Next Generation Kernel Network Tunnel"
    target: https://www.wireguard.com/papers/wireguard.pdf
    author:
      - name: "Jason A. Donenfeld"
    date: 2017
  YAN-A2A:
    title: "Applicability of A2A Protocol for Network Management Agents"
    target: https://datatracker.ietf.org/doc/draft-yan-a2a-device-agent-applicability/
    author:
      - org: "Yan et al."
    date: 2025
  ANS:
    title: "Agent Name Service (ANS): A Universal Directory for Secure AI Agent Discovery and Interoperability"
    target: https://datatracker.ietf.org/doc/draft-narajala-ans/
    author:
      - org: "Narajala et al."
    date: 2025

--- abstract

This document specifies the NetClaw-to-NetClaw Federation Protocol (NCFED), an
implementation-agnostic application-layer protocol that lets independently
operated, heterogeneous AI network-engineering agents ("NCFED peers", or "claws")
discover one another's capabilities, invoke remote tools, and delegate tasks over
long-lived TCP sessions. Although named for its reference instantiation, NCFED is a
wire specification, not an SDK, and federates arbitrary autonomous agent
architectures across distinct administrative boundaries; a peer needs no knowledge
of its counterparty's internal reasoning framework, prompt structure, or execution
runtime. NCFED multiplexes its federation
channel with BGP-4 and an associated tunneling data plane on a single listening
port, using first-octet protocol discrimination. Its payload is JSON-RPC 2.0, onto
which Model Context Protocol (MCP) tool-invocation semantics and Agent2Agent (A2A)
task-delegation semantics are mapped. Federation between different trust domains
(eN2N) requires mutual operator consent; within a single operator's trust domain
(iN2N) it is hub-and-spoke, bootstrapped by an enrollment token. For eN2N, the
channel is encrypted with TLS 1.3 and each peer is cryptographically authenticated
by proof of possession of the credential bound to its identity, under either a
domain-verified (publicly certified) or a pinned (trust-on-first-use) model. For
iN2N, members and the Border mutually authenticate at the application layer with
pinned credentials and a hub attestation, and TLS may additionally protect the
transport. NCFED does not replace MCP or A2A; it is a cross-operator federation,
identity, and transport layer beneath them. This
document describes the protocol as implemented in the open-source NetClaw project
and is published as Experimental to enable interoperability and public review.

--- middle

# Introduction

Large-language-model agents that operate network infrastructure are increasingly
deployed as long-running services with tool access to routers, controllers, and
network sources of truth. When two such agents are operated by different parties,
there is value in letting them cooperate: one agent may hold capabilities, data, or
vantage points the other lacks. When one operator runs many narrowly scoped agents,
there is equal value in coordinating them behind a single point of contact.

NCFED addresses both cases with one wire protocol. It provides:

1. First-octet protocol discrimination so that NCFED, BGP-4 {{RFC4271}}, and an
   associated data-plane tunnel (NCTUN, out of scope here) can share a single TCP
   listening port ({{discrimination}}).

2. A compact federation handshake that identifies each peer by an Autonomous System
   number and a router identifier, reusing operational identities already familiar
   from BGP deployments ({{handshake}}).

3. A minimal length-prefixed message framing with a continuation flag and a
   zero-length-frame heartbeat ({{framing}}, {{heartbeat}}).

4. A semantic layer in which capability inventory, remote tool calls (MCP {{MCP}}),
   and task delegation (A2A {{A2A}}) are expressed as JSON-RPC 2.0 {{JSONRPC}}
   messages ({{semantics}}).

5. In-band version and capability negotiation ({{negotiation}}).

6. Two trust-establishment models ({{trust}}): mutual operator consent (eN2N) and
   enrollment-token + TOFU pinning (iN2N).

NCFED is complementary to, not competing with, MCP and A2A: it is the
cross-operator federation/identity/transport layer onto which their tool-invocation
and task-delegation semantics are mapped ({{semantics}}). NCFED does not tunnel
either protocol's native transport messages unmodified.

## Motivation and Applicability {#applicability}

The motivating deployment is a small mesh of independently operated NetClaws. Three
operators each run a lab and automation stack; their agents are already BGP-mesh
peered and can see one another, but could not, before NCFED, discover or use one
another's capabilities. Separately, a single operator may decompose one monolithic
agent (carrying on the order of a hundred skills) into a **risk**: a group of
narrowly focused member agents fronted by a single Border agent that routes requests
to them. (The Border is one member of the risk, not the risk itself.)

NCFED assumes **long-lived sessions between a small number of mutually known
peers**, established deliberately by their operators. It is **not** designed for
anonymous, open, or large-scale federation, and it does not attempt spam
resistance, discovery of unknown peers, or public key infrastructure. These
assumptions shape the trust models ({{trust}}) and the Security Considerations
({{seccons}}): the design combines explicit operator consent with cryptographic
peer authentication ({{channel-sec}}), under either publicly certified domain
identity or pinned credentials depending on the deployment model.

## Status of this Protocol Description

This is an individual submission, published as **Experimental**. The authors seek
adoption of this work by an IETF Working Group addressing agent-to-agent and
agent-to-tool communication (e.g., the effort emerging from the `agentproto` Birds-
of-a-Feather), with the goal of a future Standards-Track document. This document
asserts no IETF consensus. The technical content is category-neutral and may be
re-targeted without change if adopted.

# Conventions and Definitions {#terminology}

{::boilerplate bcp14-tagged}

The following terms are used:

NCFED peer (or "claw"):
: Any long-running, autonomous AI agent process that implements the NCFED state
  machine and exposes network-engineering capabilities over JSON-RPC. The term is
  implementation-agnostic: distinct agent architectures (for example, the NetClaw
  reference implementation, the independently developed Hermes agent, OpenClaw, or
  a proprietary vendor framework) are all NCFED peers when they speak this
  protocol. "NetClaw" refers specifically to the reference implementation
  ({{impl-status}}); "claw" is used generically for any peer.

Risk:
: A named, logical cluster of NCFED peers under a single operator's administrative
  control, coordinated by a Border. The members of a risk MAY run entirely
  different agent engines. ("A risk" is the collective noun for lobsters, the
  reference project's mascot.)

Border:
: The single NCFED peer in a risk that terminates external communication, routes
  requests to members, and holds the risk's external identity.

Member:
: A narrowly scoped NCFED peer within a risk that dials outbound to its Border and
  accepts delegated work only over that channel.

eN2N (external federation):
: Federation between claws in different trust domains (different operators),
  established by mutual consent.

iN2N (internal federation):
: Federation between a Border and its members within one trust domain, established
  by an enrollment token and TOFU key pinning.

Peer AS / Router-ID:
: The 4-octet Autonomous System number and 4-octet router identifier presented in
  the NCFED handshake. They MAY coincide with BGP identifiers but are not required
  to; they are assigned by operator convention.

# Protocol Stack Overview

The NCFED stack is layered as shown in {{fig-stack}}.

~~~
+---------------------------------------------------------------+
| Application semantics (NCFED payload)                         |
|   MCP:  n2n/tools/call                                        |
|   A2A:  capability card, n2n/tasks/{submit,status,result,...} |
+---------------------------------------------------------------+
| Encoding: UTF-8 JSON-RPC 2.0                                  |
+---------------------------------------------------------------+
| Framing:  <4-octet BE length><1-octet flags><payload>        |
|           flags bit0 = CONTINUATION; length 0 = heartbeat     |
+---------------------------------------------------------------+
| Federation handshake (13 octets):                            |
|   "NCFED" + <4-octet AS> + <4-octet router-id (IPv4)>        |
+---------------------------------------------------------------+
| Discrimination on the shared listen port:                    |
|   0xFF          -> BGP-4        (RFC 4271 marker)             |
|   'N' + "CFED"  -> NCFED (this document)                     |
|   'N' + "CTUN"  -> NCTUN data plane (out of scope)           |
+---------------------------------------------------------------+
| TCP  /  IP                                                    |
+---------------------------------------------------------------+
~~~
{: #fig-stack title="NCFED protocol stack"}

iN2N ({{trust-in2n}}) reuses the same framing and JSON-RPC layers over a separate,
member-initiated transport with its own preamble instead of the shared-port
discrimination.

# Protocol Discrimination {#discrimination}

An NCFED node listens on a single configured TCP port. (In the reference deployment
this is the operator's BGP/mesh port; NCFED defines no fixed well-known port -- see
{{iana}}.) The peer that opened the TCP connection is the **initiator** and MUST send
its protocol preamble (the 0xFF BGP marker, or the 5-octet 'N' magic of
{{handshake}}) immediately upon connection establishment; the peer that accepted the
connection is the **acceptor** and reads it. On accepting a connection, the acceptor
reads the first octet. It MUST close the connection if the first octet is not
received within 30 seconds.

* If the first octet is 0xFF, the connection is a BGP-4 session and is handed to the
  BGP engine. (A BGP message header begins with a 16-octet marker of all ones
  {{RFC4271}}.) An implementation that consumes the first octet in order to
  discriminate MUST make it available to the BGP engine again (for example, by
  re-prepending it to the byte stream), because a BGP parser expects to read the
  16-octet marker from the first octet of the stream. The reference implementation
  reads one octet and, for a BGP connection, replays it ahead of the remainder of
  the stream before handing the session to its BGP engine.

* If the first octet is 0x4E ('N'), the node reads the following 4 octets. It MUST
  close the connection if those 4 octets are not received within 10 seconds. The
  resulting 5-octet magic selects the protocol:

  * "NCFED" (0x4E 0x43 0x46 0x45 0x44): the connection proceeds as an NCFED
    federation channel ({{handshake}}).

  * "NCTUN" (0x4E 0x43 0x54 0x55 0x4E): the connection proceeds as an NCTUN
    data-plane channel. NCTUN is out of scope for this document.

  * Any other 5-octet value: the node MUST close the connection.

* Any other first octet: the node MUST close the connection without a response.

This first-octet discrimination is deliberately simpler than, and distinct from,
TLS ALPN {{RFC7301}}, which negotiates at the TLS layer; NCFED discriminates in
cleartext at the start of the TCP byte stream. It follows that NCFED does **not**
perform a TLS handshake on the shared port: the first octet of a TLS ClientHello
record is 0x16 (the TLS "handshake" content type), which is not a recognized
discriminator value, so a direct TLS connection to the shared port is closed like
any other unrecognized preamble. NCFED therefore never begins with a TLS ClientHello;
instead, once the NCFED preamble is recognized, the channel is upgraded to TLS in place
after the handshake ("STARTTLS"-style; see {{channel-sec}}), which keeps the shared port
and its discrimination unchanged. {{seccons}} discusses the security consequences of
sharing a port with BGP.

The shared port is a deployment constraint, not an aesthetic preference: the
reference deployments reach one another through single-port tunnel forwarders (and
the equivalent NAT and firewall pinholes), where every additional listening port is
an additional tunnel endpoint, credential, and access-control exception to
provision, advertise after every address rotation, and keep consistent across
operators. Multiplexing NCFED and its data plane onto the port the BGP mesh
already uses lets one pinhole -- and one endpoint re-announcement ({{operational}})
-- carry all three protocols. The discrimination layer is internal to the NCFED
daemon, **which embeds its own BGP engine**; this document does *not* propose that
general-purpose BGP implementations adopt first-octet discrimination or accept a
shim in front of TCP port 179. A deployment that peers with a conventional BGP
stack on its own port simply runs NCFED on a separate configured port, where the
discrimination step degenerates to validating the NCFED preamble.

# Federation Handshake {#handshake}

Immediately after the "NCFED" magic, the initiating peer sends 8 further octets: a
4-octet Autonomous System number followed by a 4-octet router identifier (a packed
IPv4 address). With the magic, the complete handshake is 13 octets, as shown in
{{fig-handshake}}.

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      'N'      |      'C'      |      'F'      |      'E'      |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|      'D'      |     Autonomous System Number (bits 0..23)     |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|  AS (24..31)  |        Router-ID (IPv4) (bits 0..23)         |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Router-ID24..31|
+-+-+-+-+-+-+-+-+
~~~
{: #fig-handshake title="NCFED federation handshake (13 octets)"}

The Autonomous System number is an unsigned 32-bit integer in network byte order
(big-endian). The router identifier is a 4-octet packed IPv4 address. All
multi-octet fields in NCFED are network byte order.

The initiator (the peer that opened the connection; see {{discrimination}}) sends its
13-octet handshake immediately. If the acceptor admits the connection, it replies with
its own 13-octet handshake -- the "NCFED" magic followed by the acceptor's AS and
router-id -- immediately followed by a 32-octet **possession challenge** (a random
nonce; see {{channel-sec}}). The initiator MUST verify that the reply begins with the
"NCFED" magic and that the AS/router-id identify the peer it expected, and MUST close
the connection otherwise. The handshake is therefore a request/reply exchange in which
each side presents its claimed identity to the other at the binary layer, and the
acceptor additionally issues the nonce the initiator must sign to prove that identity.
Mutual capability exchange and the remainder of session establishment then proceed at
the JSON-RPC layer via `n2n/hello` ({{semantics}}, {{negotiation}}), which the
initiator sends first, carrying its certificate and a signature over the nonce
({{channel-sec}}). The peer identity used throughout this document is the string
`as<AS>-<router-id>` (for example, `as65001-192.0.2.1`).

An acceptor that has not recorded a local consent grant for the claimed identity
({{trust-en2n}}) MUST close the connection without issuing a nonce, and SHOULD close
it without sending its handshake reply at all, so that a peer the operator has never
consented to obtains no channel and learns nothing about the acceptor's identity.
(The reference implementation closes with zero bytes returned.) When the channel is
encrypted ({{channel-sec}}), the TLS upgrade occurs between the handshake reply and
the nonce, so the nonce and all subsequent traffic are protected.

To avoid a simultaneous-open ambiguity (both peers dialing at once), NCFED designates
a deterministic initiator: peers are ordered by the tuple (AS number, router-id),
comparing AS numbers numerically and, if they are equal, comparing router-ids as
unsigned 32-bit integers in network byte order. The endpoint with the numerically
lower tuple opens the channel; the other only accepts. (For example, (65001,
192.0.2.1) orders before (65001, 192.0.2.2).) Two peers MUST NOT share both an AS
number and a router-id. An explicit re-dial replaces any existing channel to the
same peer identity.

The claimed AS/router-id in the handshake octets themselves is not self-authenticating;
it is authenticated by the possession proof that follows in `n2n/hello`, and (for a
domain-verified peer) by the certificate presented on the encrypted channel. The
complete authentication mechanism, its two trust models, and the admission tiers are
specified in {{channel-sec}}; the residual properties are analyzed in
{{seccons-peer-auth}}.

There is no version octet in the handshake; versioning is negotiated in-band
({{negotiation}}). Appending a version octet immediately after the magic is **not** a
safe way to signal a future incompatible change, because that octet position is
currently the most significant octet of the AS number and cannot be repurposed
without ambiguity for already-deployed peers. It is therefore RECOMMENDED that any
future incompatible change be negotiated in-band ({{negotiation}}), or be introduced
only in a form that a legacy peer rejects cleanly rather than misparses.

The 32-octet possession challenge appended to the acceptor's reply is
such an incompatible change. The nonce is *not* part of the 13-octet binary
handshake itself: it appears **after** the acceptor's 13-octet handshake, so
a peer implementing an earlier iteration of the protocol (which reads only 13 octets and sends
`n2n/hello` without a signature) does not interoperate with a peer implementing this
document. This is intentional -- the secured channel ({{channel-sec}}) is a prerequisite
for external federation -- and it is a coordinated upgrade rather than a
silent wire change: an acceptor implementing this document admits an unauthenticated
peer only at the restricted tier described in {{channel-sec}}, and refuses it outright
when operating in enforcing mode.

# Channel Security {#channel-sec}

NCFED makes its channel encrypted and its peer cryptographically
authenticated. Two properties are established before any semantic payload
({{semantics}}) is exchanged: the transport is confidential and integrity-protected,
and each peer proves possession of the credential bound to its claimed identity. This
closes the peer-impersonation exposure present in earlier iterations of the protocol
({{seccons-peer-auth}}).

## Transport encryption {#channel-sec-tls}

After the binary handshake ({{handshake}}) and before the possession challenge, the
connection is upgraded in place to TLS 1.3 {{RFC9846}} (a "STARTTLS"-style upgrade on
the already-open connection, so the shared discrimination port of {{discrimination}}
is preserved and no additional listener or tunnel is required). The acceptor acts as
the TLS server and presents its certificate; the initiator acts as the TLS client and
verifies that certificate according to the peer's trust model
({{channel-sec-models}}). The possession challenge nonce and all subsequent frames are
carried inside this TLS session.

A deployment MAY operate a channel in cleartext for a private, controlled environment
(for example, a loopback lab). An implementation MUST treat cleartext operation as an
explicit, operator-selected mode and MUST NOT negotiate down to it at a remote peer's
request; in enforcing mode ({{channel-sec-tiers}}) cleartext channels are refused.

## Trust models {#channel-sec-models}

Each peer is authenticated under one of two per-peer trust models, recorded locally:

* **Domain-verified.** The peer's identity is additionally bound to a DNS name its
  operator controls (its "claw domain"). The operator obtains a publicly trusted
  certificate for that name using ACME {{RFC8555}} with the DNS-01 challenge, which
  requires no inbound reachability and therefore works behind a dynamic tunnel or NAT.
  The verifying peer validates the certification path {{RFC5280}} and checks that the
  certificate identifies the expected claw domain {{RFC9525}}. Identity binds to the
  DNS name, **not** to the transport endpoint, which MAY change freely. The local
  consent record ({{trust-en2n}}) MUST bind the expected NCFED identity
  (AS/router-id) to the expected claw domain, and the verifying peer MUST check the
  presented certificate against the claw domain recorded for **that** identity:
  successful validation of a certificate for some other domain, however publicly
  trusted, MUST NOT authorize its holder to assert this NCFED identity.

* **Pinned.** A peer without a domain presents a self-signed certificate
  {{RFC5280}} (ECDSA P-256 / SHA-256, as in {{trust-in2n}}). Its key is pinned on
  first federation after the out-of-band consent of {{trust-en2n}} (trust on first
  use); the pinned value is the SHA-256 of the certificate's SubjectPublicKeyInfo, so
  the pin survives certificate rotation with the same key. A later connection under
  the same identity presenting a different key MUST be refused and flagged to the
  operator, and MUST NOT be silently re-pinned ({{seccons-tofu}}).

The trust model governs the credential a peer presents in the **acceptor
(listener) role**: when a peer is dialed, it presents either a domain-verified or a
pinned server certificate, and the dialer authenticates it accordingly during the
TLS handshake ({{channel-sec-tls}}). In the **initiator (dialer) role** a peer
authenticates itself at the application layer by proving possession of a self-signed
identity key ({{channel-sec-pop}}), which the acceptor pins on first contact (TOFU);
the initiator does not present a domain-verified certificate in this direction, and
in the reference implementation the possession proof is always over the self-signed
identity key regardless of the peer's acceptor-role trust model. Because the
deterministic-initiator rule ({{handshake}}) assigns the two roles per peer pair,
each identity is domain-validated in the direction where it is dialed and pinned in
the direction where it dials. Authentication is therefore mutual on every encrypted
channel, but the mechanism is asymmetric by role; a deployment that requires a
peer's identity to be domain-anchored in both directions cannot rely on the
initiator-role possession proof for that and SHOULD constrain the domain-verified
peer to the acceptor role (i.e., assign it the higher-or-equal (AS, router-id)
tuple).

## Proof of possession {#channel-sec-pop}

Identity is proven by possession of the private key for the certificate a peer
presents, over the acceptor's per-connection nonce:

1. The acceptor issues a fresh 32-octet random nonce (in the handshake reply, or, on an
   encrypted channel, immediately after the TLS upgrade; see {{handshake}}).
2. The initiator's `n2n/hello` carries its certificate and an ECDSA (P-256, SHA-256)
   signature over that nonce. The acceptor verifies the signature against the public
   key in the presented certificate; a certificate the caller cannot sign for is an
   active forgery and MUST be rejected with the channel closed.
3. On an encrypted channel the signed value is `nonce || B`, where `B` is the
   tls-server-end-point channel binding {{RFC5929}}: the SHA-256 of the acceptor's
   certificate. `B` is an *endpoint* binding, not a per-connection value -- the same
   certificate yields the same `B` across every connection that presents it -- so
   `B` alone does not make a proof session-unique. Replay and relay resistance come
   instead from the nonce: it is fresh, single-use, and -- on an encrypted channel --
   delivered confidentially under the acceptor's server certificate, which the
   initiator has already verified under its trust model. An initiator therefore signs
   only a nonce it received over a TLS session to the acceptor it authenticated, so a
   proof cannot be relayed to a different acceptor (whose certificate the relay
   cannot present); `B` adds defence in depth by additionally binding the proof to
   the acceptor's certificate. A future revision SHOULD adopt the {{RFC9266}}
   `tls-exporter` binding, which *is* per-connection, once the implementation's TLS
   stack exposes it (the reference deployment's Python `ssl` module does not through
   3.14; see {{impl-status}}). On a cleartext channel `B` is empty, the proof is over
   the nonce alone, and it does not authenticate the acceptor to the initiator --
   such a channel MUST NOT be described as mutually authenticated.

The acceptor authenticates the initiator by this proof; the initiator authenticates the
acceptor by verifying the acceptor's certificate during the TLS handshake
({{channel-sec-tls}}). Authentication is therefore mutual on an encrypted channel.

## Admission tiers {#channel-sec-tiers}

To let a set of already-consented peers upgrade without a flag-cut outage, an acceptor
admits a **consented** peer at one of two tiers, and refuses a non-consented one
outright:

* **possession** (full): the peer proved possession of a key (and, if pinned, matched
  its pin). It receives the full method surface subject to the per-peer authorization
  of {{trust-en2n}}.
* **self-asserted** (restricted): the peer is consented but presented no certificate.
  It is admitted for presence and capability-card exchange ({{cards}}) only. Tool
  invocation, task delegation ({{semantics}}), chat, and endpoint update
  ({{operational}}) MUST be denied at this tier.
* A peer for which no local consent exists is closed before a nonce is issued
  ({{handshake}}); it obtains no channel, not even the restricted tier.

An acceptor operating in **enforcing** mode admits only the possession tier and refuses
a self-asserted peer, making a certificate a hard prerequisite for federation. A
restricted-tier inbound session MUST NOT displace an established possession-tier channel
for the same identity.

Certificates are rotated automatically before expiry. A successor credential is
distributed over the existing authenticated channel before the predecessor expires, and
both are accepted during a bounded overlap, so rotation does not drop a channel; for
domain-verified peers the successor is validated by its certification path with no
distribution step.

# Message Framing {#framing}

After a successful handshake, all traffic on the channel consists of frames, shown
in {{fig-frame}}.

~~~
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|              Length (payload octets, unsigned, BE)            |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|     Flags     |            Payload (Length octets) ...        |
+-+-+-+-+-+-+-+-+                                               +
|                              ...                              |
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
~~~
{: #fig-frame title="NCFED frame"}

Length:
: Unsigned 32-bit integer, network byte order, counting the payload octets only.
  A payload MUST NOT exceed 65536 octets (64 KiB). A larger message MUST be split
  across multiple frames using the CONTINUATION flag. A receiver that reads a Length
  greater than 65536 MUST close the connection. The 64 KiB cap keeps a receiver's
  per-frame buffer small and predictable while still fitting typical NCFED
  messages -- hellos, capability cards, tool calls -- in a single frame;
  fragmentation is the exception, for bulk tool output and task results.

Flags:
: One octet. Bit 0 (0x01), CONTINUATION: when set, the payload is a fragment of a
  larger message and MUST be concatenated with the payloads of subsequent frames
  until a frame is received with CONTINUATION clear. Bits 1 through 7 are RESERVED;
  a sender MUST set them to 0 and a receiver MUST ignore them.

Frames carry no message identifier. Consequently, an endpoint MUST NOT interleave the
frames of different messages: once it sends a frame with CONTINUATION set, every
subsequent frame it sends on that channel MUST be a fragment of the same message
until a frame with CONTINUATION clear terminates the message. Fragments MUST be
transmitted contiguously. A frame with Length 0 and CONTINUATION set is a legal empty
fragment that contributes no octets to reassembly. Because a heartbeat ({{heartbeat}})
is a Length-0, CONTINUATION-clear frame, and because reassembly is never in progress
between messages, a heartbeat is sent only between complete messages, never between a
message's fragments; an endpoint MUST NOT emit a heartbeat while a message it is
sending is partially transmitted. A receiver that observes a Length-0,
CONTINUATION-clear frame while a reassembly is in progress MUST treat it as a
protocol error and close the channel.

A reassembled message is a complete JSON-RPC 2.0 message ({{semantics}}). Reassembly
is bounded in both size and time: a reassembled message MUST NOT exceed 16 MiB
(16,777,216 octets), and a receiver MUST close the channel when an in-progress
reassembly exceeds that bound or remains incomplete more than 30 seconds after its
first fragment was received. These bounds cap the memory and time a peer can consume
with CONTINUATION frames -- including a drip of the legal zero-length fragments,
each of which also counts as liveness ({{heartbeat}}); see {{seccons-dos}}.

# Heartbeat and Liveness {#heartbeat}

A frame with Length 0 and CONTINUATION clear, received when no reassembly is in
progress, is a heartbeat. A heartbeat carries no payload and MUST NOT be delivered to
the application layer; it is sent only between complete messages ({{framing}}).

An endpoint SHOULD send a heartbeat frame approximately every 30 seconds (the
heartbeat interval). Any inbound frame, including a heartbeat, is evidence of liveness
and resets the endpoint's missed-interval count for that channel. An endpoint that
receives no inbound frame for 3 consecutive intervals (approximately 90 seconds) MUST
consider the channel dead and close it. These values mirror the BGP keepalive (30 s)
and hold time (90 s) defaults {{RFC4271}}. On close, an endpoint that initiated the
session SHOULD attempt to re-establish it with bounded backoff.

# Semantic Payload {#semantics}

Reassembled payloads are UTF-8 JSON-RPC 2.0 {{JSONRPC}} messages ({{RFC8259}}). A
message carrying a `method` member is a request (if it also carries `id`) or a
notification (if it does not); a message carrying only `id` with `result` or `error`
is a response. Each request carries a unique `id` chosen by the sender, which the
response echoes. Batch requests (JSON-RPC arrays) are not used: an endpoint sends a
single JSON-RPC object per reassembled message. A reassembled message that is not
well-formed UTF-8 JSON is discarded and SHOULD be logged; its receipt does not by
itself require closing the channel. The concrete parameter and result objects for
each method are specified in {{method-ref}}.

Because NCFED is implementation-agnostic ({{terminology}}), its method families are
a normalized wire wrapper over whatever internal representation each peer uses:
disparate agent implementations translate their local tool-execution and
task-delegation strategies into the common MCP and A2A constructs carried here, and
a peer requires no knowledge of its counterparty's reasoning framework to
interoperate. A consequence is a clean separation between *protocol* errors and
*tool* errors. The JSON-RPC error codes of {{errors}} report NCFED-level failures --
federation, authorization, transport, framing. An error *inside* an invoked tool
(for example, a callee-side input-schema validation failure) is not an NCFED
protocol error: it is returned in the MCP tool-result object as a successful
`n2n/tools/call` response whose result carries the tool's own error indication,
and is relayed verbatim to the calling peer. This lets a foreign peer surface a
remote tool's failure to its operator without either side sharing tool internals,
and keeps the NCFED error space stable regardless of what tools a peer exposes.

Before federation (eN2N) or trust establishment (iN2N) completes, an endpoint MUST
reject any method other than the handshake method (`n2n/hello` for eN2N;
`in2n/hello` or `in2n/enroll` for iN2N) with the appropriate error ({{errors}}). On an
eN2N channel the initiator sends `n2n/hello` first.

## Method families

n2n/hello:
: Mutual identity plus the capability descriptor ({{negotiation}}). The only method
  permitted before eN2N federation is established.

n2n/inventory, n2n/inventory_get:
: Push and pull of the capability card ({{cards}}).

n2n/tools/call:
: MCP-style {{MCP}} invocation of a named remote tool with JSON arguments, subject
  to the callee's per-peer authorization policy.

n2n/tasks/submit, n2n/tasks/status, n2n/tasks/result, n2n/tasks/cancel:
: A2A-style {{A2A}} asynchronous task delegation and retrieval.

Additional methods (e.g., claw-to-claw chat) MAY be present; unknown methods are
rejected with METHOD_NOT_FOUND ({{errors}}).

## Asynchronous task delegation

A delegated task progresses through the states:

~~~
submitted --> working --> completed
                     \--> failed
                     \--> cancelled
~~~

The callee returns an opaque task identifier from `n2n/tasks/submit`; the caller
retrieves progress and the terminal result via `n2n/tasks/status` and
`n2n/tasks/result`, and MAY request cancellation via `n2n/tasks/cancel`. Task state
persists across channel drops so that results survive reconnection. Task retrieval
is bound to the submitter: the callee MUST verify that the caller of
`n2n/tasks/status`, `n2n/tasks/result`, or `n2n/tasks/cancel` is the authenticated
peer that submitted the task, and MUST answer a request for a task the caller does
not own exactly as it answers a request for a task that does not exist, so that
task identifiers can be neither used nor probed by a third party (see
{{seccons-deleg}}). This document does not define a retention or garbage-collection
policy for terminal task state, nor idempotency or retry semantics for resubmission.

Completion signalling is advisory; polled task state is authoritative. Any
notification that a task reached a terminal state is delivered at most once and dies
with the channel that carried it: operational experience with the reference
implementation showed tasks that the callee had completed remaining "submitted" at
the caller indefinitely after the channel between them was re-established, because
nothing re-delivered the terminal state. A caller therefore MUST NOT interpret the
absence of a completion signal as failure (or as any other task state), and SHOULD
reconcile each of its non-terminal outbound tasks via `n2n/tasks/status` after a
channel to that peer or member is re-established. A callee MAY re-announce
unacknowledged terminal states after reconnection; because task state is keyed by
the task identifier and terminal states are immutable, such re-delivery is
idempotent by construction.

## Error codes {#errors}

NCFED uses JSON-RPC error objects. All NCFED application error codes fall within the
JSON-RPC implementation-defined server-error range (-32000 to -32099) {{JSONRPC}};
this reuse is intentional and permitted. The following application error codes are
defined for eN2N:

| Code   | Name              |
|--------|-------------------|
| -32001 | NOT_ALLOWLISTED   |
| -32002 | APPROVAL_PENDING  |
| -32003 | APPROVAL_EXPIRED  |
| -32004 | BUDGET_EXHAUSTED  |
| -32005 | RATE_LIMITED      |
| -32006 | EXECUTION_TIMEOUT |
| -32007 | SEVERED           |
| -32008 | GUARDRAIL_BLOCKED |
| -32010 | NOT_FEDERATED     |
| -32601 | METHOD_NOT_FOUND (JSON-RPC standard) |
{: title="eN2N error codes"}

The following application error codes are defined for iN2N ({{trust-in2n}}):

| Code   | Name                  |
|--------|-----------------------|
| -32021 | ENROLL_TOKEN_INVALID  |
| -32022 | MEMBER_ID_TAKEN       |
| -32023 | MEMBER_NOT_TRUSTED    |
| -32024 | NOT_A_BORDER          |
| -32030 | NO_CAPABLE_MEMBER     |
| -32031 | OUT_OF_SCOPE          |
{: title="iN2N error codes"}

MEMBER_ID_TAKEN (-32022) reports an enrollment whose member identifier is already
pinned to a different key. A key-possession failure at `in2n/hello` or
`in2n/enroll` is reported as MEMBER_NOT_TRUSTED (-32023).

# Version Signaling and Capability Advertisement {#negotiation}

NCFED features are advertised in-band at `n2n/hello`, not in the binary handshake.
Each endpoint advertises a capability descriptor:

~~~
{ "proto_version": "053",
  "features": ["async_tasks", "endpoint_reannounce", "negotiate"],
  "agent_invoke": "session-id",
  "reply_shapes": ["finalAssistantVisibleText", "payloads"] }
~~~

`proto_version` is an opaque label identifying a baseline (for example "052" or
"053"); NCFED performs no ordering comparison on it, and an endpoint does not infer
capability from its value. Capability is instead determined field by field: use of an
optional feature is gated solely by its presence in the peer's `features` array, and
the other descriptor fields (for example `agent_invoke` and `reply_shapes`) let each
side adapt to the other's build. An endpoint that receives no descriptor treats the
peer as the baseline "052" with an empty feature set. This mechanism is therefore
feature advertisement with graceful degradation, not selection of a single common
version: an unrecognized feature name is simply not used, and no failure is defined
for a feature one side requires but the other lacks.

If a future revision defines a baseline with which an endpoint cannot interoperate,
the endpoint SHOULD reject the peer's `n2n/hello` with JSON-RPC error -32602
(invalid params), carrying a diagnostic message that names the baseline(s) it does
support, and then close the channel. This gives the remote operator a parseable,
attributable failure instead of a silently degraded feature set. The absence of a
descriptor is never an error; it selects the baseline as above.

Because the binary handshake carries no version indicator, an incompatible change
cannot be signaled below the JSON-RPC layer, and -- as noted in {{handshake}} -- a
version octet cannot simply be appended to the handshake. It is RECOMMENDED that any
future incompatible change be negotiated in-band through this mechanism. A true
version-negotiation scheme -- selecting a common protocol version and defining
behavior when one side requires a feature the other does not support -- is left to a
future revision (see {{impl-status}}).

# Capability Cards {#cards}

An endpoint advertises its capabilities in a card exchanged via `n2n/inventory` /
`n2n/inventory_get`. A card contains:

* `skills` and `mcp_servers`: the capabilities the endpoint is willing to expose to
  this peer, after applying the per-peer visibility/authorization policy (not the
  endpoint's full local set);
* `badges`: coarse capability tags;
* `posture`: the advertiser's operational security posture, as
  `{ "mode", "state", "controls" }` (e.g., mode `production`, state `enforced`, and
  the set of active controls);
* `llm`: the advertiser's reasoning-model capability, as
  `{ "primary_model", "guarded" }` -- the model family/tier and whether its
  input/output is routed through a guardrail.

A card MUST NOT contain secrets, credentials, or per-member topology of a risk. A
Border advertises its own reasoning model and MAY note that members run their own
tiered models, without revealing individual members.

Even so, because a card enumerates skills, MCP servers, security posture, and
reasoning-model family, it discloses metadata about the advertiser's attack surface.
An endpoint MUST advertise only the subset a given peer is authorized to see, and
operators SHOULD treat card contents as sensitive -- particularly on a cleartext channel
(the optional mode of {{channel-sec-tls}}) or when exposed to a restricted-tier peer
({{channel-sec-tiers}}, {{seccons-priv}}). A future revision may define a minimized or
integrity-protected card ({{seccons-priv}}).

# Trust Establishment {#trust}

## External federation: eN2N {#trust-en2n}

Peers in different trust domains federate only after explicit mutual operator
consent. The AS/router-id identity of each peer is confirmed **out of band** (for
example, by the operators exchanging it directly) before consent is granted. Consent
is durable and survives restarts and endpoint (e.g., tunnel address) changes; it is
keyed by the peer identity, not by a network address.

A peer's federation state is derived from two independent consent bits -- the local
operator's grant and the remote peer's grant -- as shown in {{fig-consent}}.
Federation requires both. Which "pending" state a peer occupies depends only on which
grant has been recorded so far, not on a fixed order.

~~~
                      not_federated
                     (neither grant)
                    /               \
        local grant                  remote grant
             v                           v
   consent_pending_remote       consent_pending_local
   (we granted; await peer)      (peer granted; await us)
                    \               /
                     \  both grants /
                      v            v
                        federated
                            |
                    sever (revoke local grant)
                            v
                        severed
                            |
                 re-consent (grant locally again)
                            v
                      not_federated --> ...
~~~
{: #fig-consent title="eN2N consent state, derived from the local and remote grants"}

Only `n2n/hello` is accepted before `federated`. Remote tool invocation is
default-deny: a tool call is rejected (NOT_ALLOWLISTED) unless a per-peer grant
authorizes it, and grants MAY carry approval requirements, budgets, and rate limits
(reflected in the error codes of {{errors}}). Severing revokes the local grant and
drops the channel (the operator kill switch); re-consent restores the local grant,
returning the peer to `not_federated`, from which it may re-federate. As noted in
{{handshake}}, the numerically lower AS initiates the channel.

The out-of-band identity confirmation above is the administrative root of trust. At
runtime it is enforced cryptographically: the channel is encrypted and the peer proves
possession of the credential bound to its identity, under the domain-verified or pinned
trust model of {{channel-sec}}. A consented peer that presents no credential is admitted
only at the restricted tier ({{channel-sec-tiers}}), which cannot invoke tools, delegate
tasks, chat, or update endpoints; in enforcing mode it is refused entirely. The residual
properties (the first-use pinning window, restricted-tier card exposure) are analyzed in
{{seccons-peer-auth}} and {{seccons-tofu}}.

## Internal federation: iN2N {#trust-in2n}

Within a single operator's risk, a member is authenticated by proving possession of
a self-signed key that the Border pinned at enrollment (TOFU), not by BGP identity
or mutual consent. iN2N is hub-and-spoke: a member connects only to its Border, and
a member MUST NOT accept inbound federation connections.

iN2N uses a **separate** Border listener (not the shared discrimination port of
{{discrimination}}). The transport preamble is shown in {{fig-in2n-preamble}}.

~~~
Border --> Member:  "IN2N1" (5 octets) || nonce (32 octets, random)
Member --> Border:  JSON-RPC  in2n/hello | in2n/enroll
   params: an ECDSA (P-256, SHA-256) signature over the nonce, proving
   the member holds its pinned self-signed key
   ... the standard NCFED framing/JSON-RPC channel then runs ...
~~~
{: #fig-in2n-preamble title="iN2N transport preamble"}

The trailing "1" in the "IN2N1" magic is a preamble version digit. The exact JSON
parameters and their encodings -- PEM certificate, hexadecimal DER-encoded ECDSA
signature, and hexadecimal key fingerprint -- are specified in {{method-ref}}.

Enrollment and pinning:

1. The Border issues a single-use enrollment token, conveyed to the member out of
   band (for example, at install time). The token has the form `in2n_<random>` with
   at least 128 bits of entropy; the Border stores only its SHA-256 and MAY set an
   expiry.

2. The member generates its own key pair at runtime: ECDSA {{RFC6090}} on NIST curve
   P-256 {{RFC5480}} with SHA-256 {{RFC6234}}, in a self-signed X.509 certificate
   {{RFC5280}}.

3. On first contact (`in2n/enroll`) the member presents the token and its
   certificate; the Border validates and spends the token and **pins** the member's
   key (TOFU). The pinned identity is the SHA-256 of the certificate's
   SubjectPublicKeyInfo.

4. On every subsequent connection (`in2n/hello`) the member signs the Border's
   32-octet nonce with the pinned key; the Border verifies the signature.

A Border routes a request to the member that owns the capability, selecting
deterministically (most-specific specialist first, then lexicographically by member
identity); if no active member covers the capability it returns NO_CAPABLE_MEMBER,
and a member asked to act beyond its advertised scope returns OUT_OF_SCOPE. Operator
removal of a member unpins its key; a member that fails pinned-key authentication more
than a configurable number of times is automatically quarantined -- its key unpinned --
and must be re-enrolled by the operator to return. The security implications of this
automatic quarantine are discussed in {{seccons-tofu}}.

iN2N authentication is mutual. The member proves possession of its pinned key over the
Border's nonce, as above. The Border, in turn, proves it is the legitimate hub for the
risk: the Border operates a risk-local certificate authority {{RFC5280}}, whose root
the member receives at enrollment (the "trust anchor"), and issues **its own hub
certificate** from that authority. (Member certificates are **not** issued by this
authority; they remain self-signed and pinned, as above.) On each connection the
member includes its own random
nonce in `in2n/hello` or `in2n/enroll`; the Border returns a hub attestation -- its
CA-issued hub certificate and an ECDSA (P-256, SHA-256) signature over the member's
nonce. The member verifies that the hub certificate chains to its enrolled anchor,
names the risk's Border, and signed the nonce, and MUST abort the connection if it does
not. A member enrolled before hub attestation was introduced holds no anchor and continues without hub
verification until it is re-enrolled, so the change is backward compatible within a
risk.

The iN2N socket MAY additionally be wrapped in TLS {{RFC9846}} for members reached
across an untrusted network, providing confidentiality that complements the
application-layer mutual authentication above.

# Operational Considerations {#operational}

* Lifecycle: severing is an operator action that revokes the local consent grant and
  drops the NCFED channel ({{trust-en2n}}); there is no dedicated peer-to-peer sever
  message. A severed peer is reachable again only after the operator re-consents.

* Hybrid runtime: a Border keeps a hot set of members connected and cold-starts
  others on demand, idling them out when quiet. Cold start appears on the wire only
  as connection-establishment latency.

* Least privilege: each member is provisioned with only the secrets its integration
  requires; compromise of one member does not expose another's credentials.

* A standalone claw is a degenerate risk of one that is its own Border; no protocol
  change is required for that case.

* Endpoint mobility: peers reached over ephemeral transports (tunnels whose public
  address rotates) change address routinely. An implementation SHOULD persist the
  most recently *successfully authenticated* endpoint for each peer and use it for
  automatic reconnection, and SHOULD NOT overwrite a known-good stored endpoint on a
  failed dial attempt.

# Security Considerations {#seccons}

## Sharing a listening port with BGP {#seccons-port}

Because NCFED, BGP-4, and NCTUN share a TCP listening port ({{discrimination}}), the
NCFED discrimination and handshake parsers are reachable by any host that can reach
the BGP port. Operators SHOULD protect the shared port with the same controls they
apply to BGP peers -- for example, access-control lists restricting the permitted
source addresses, connection rate limiting applied before discrimination, and,
where the deployment allows, the Generalized TTL Security Mechanism {{RFC5082}}.
Implementations MUST enforce the discrimination read timeouts
({{discrimination}}: 30 s for the first octet, 10 s for the magic) and close on any
malformed or unexpected preamble, to limit resource consumption by connections that
stall before discrimination.

Although the in-place TLS upgrade of {{channel-sec-tls}} is "STARTTLS"-style in
mechanics, it does not inherit the classic STARTTLS stripping weakness: there is no
cleartext upgrade command or capability offer on the wire for an active attacker to
strip. Discrimination is positional -- the first octets of the TCP stream select
the protocol -- and whether a given channel is then encrypted is decided by each
endpoint's local, per-peer configuration ({{channel-sec-tls}}), never by an in-band
offer from the remote peer. A peer therefore cannot induce cleartext operation:
cleartext exists only as an explicit local operator mode, and an acceptor in
enforcing mode ({{channel-sec-tiers}}) refuses a cleartext channel outright. An
attacker who tampers with the cleartext preamble octets can only change which
protocol engine receives the stream or which identity is claimed; the claimed
identity is then still subject to the certificate verification and possession
proof of {{channel-sec}}, which the attacker cannot satisfy.

The co-resident BGP-4 mesh session itself is not protected by NCFED's channel
security: after discrimination selects BGP, the mesh session proceeds as cleartext
BGP and, on an untrusted path, its confidentiality currently depends on whatever
encryption the underlay or tunnel transport provides -- which is incidental, not
guaranteed by this protocol. Bringing the mesh session under the same
post-identification TLS upgrade that NCFED channels use ({{channel-sec-tls}}) is
defined in the reference implementation's roadmap but is staged and optional at the
time of this writing; deployments that require mesh confidentiality on untrusted
legs MUST provide it at the transport layer until then.

## Peer authentication {#seccons-peer-auth}

NCFED cryptographically authenticates a peer ({{channel-sec}}). An eN2N peer proves
possession of the private key for the certificate bound to its identity, over a fresh
single-use nonce, on an encrypted channel whose server certificate the initiator has
verified (by certification path and name for a domain-verified peer {{RFC5280}}
{{RFC9525}}, or by pinned key for a self-signed one). A host that merely knows a peer's
AS/router-id can no longer impersonate it: presenting the identity without the key
fails the possession check and the channel is closed, and a consented peer that
presents no key is confined to the restricted tier ({{channel-sec-tiers}}), which
exposes no invocation, delegation, chat, or endpoint-update surface. iN2N is mutually
authenticated: the member proves possession of its pinned key, and the Border proves,
by an attestation chaining to the member's enrolled trust anchor, that it is the
legitimate hub ({{trust-in2n}}).

Two residual properties remain and are, by design, out of scope for the on-wire
mechanism:

* **First-use trust.** In the pinned model, and at iN2N enrollment, the initial key is
  accepted on first contact (see {{seccons-tofu}}). An attacker who is on-path at the
  very first federation with a never-before-seen identity could be pinned in place of
  the legitimate peer. Every subsequent contact is protected by the pin.
* **Restricted-tier metadata.** A consented-but-keyless peer at the restricted tier
  can still read the advertiser's capability card ({{seccons-priv}}). A deployment that
  considers card contents sensitive SHOULD operate in enforcing mode, which admits only
  the possession tier.

On an encrypted channel the possession proof cannot be relayed to a different
acceptor: the fresh single-use nonce is delivered confidentially under the
acceptor's verified server certificate, so an initiator only ever signs a nonce
bound to the acceptor it authenticated, and the tls-server-end-point value adds a
further endpoint binding ({{channel-sec-pop}}). (That value is an endpoint, not a
per-connection, binding; a future revision SHOULD adopt {{RFC9266}} `tls-exporter`
once the TLS stack exposes it.) Deployments SHOULD still apply defence in depth: the shared-port source controls of
{{seccons-port}} and the default-deny per-peer authorization of {{seccons-deleg}}. An
emerging agent-identity and naming layer such as the Agent Name Service {{ANS}} could in
future supply discovery and naming above this authentication layer.

## Trust on first use {#seccons-tofu}

eN2N relies on out-of-band confirmation of a peer's AS/router-id before consent; iN2N
relies on TOFU pinning of a member's self-signed key at enrollment ({{trust}}). TOFU
is vulnerable to an active attacker present at enrollment time. Enrollment tokens
therefore MUST have at least 128 bits of entropy, MUST be single-use, SHOULD carry an
expiry, and SHOULD be delivered over a confidential out-of-band channel. To detect an
intercepted enrollment, the member SHOULD display the SHA-256 fingerprint of its
generated certificate out of band so the operator can confirm it matches the value the
Border pinned. The Border SHOULD log every enrollment fingerprint mismatch and
surface it to the operator as a security alert, not merely a failed enrollment.
If enrollment is suspected to have been intercepted, the operator
removes (unpins) the member and re-enrolls it with a fresh token; the compromised key
is thereby refused. This model is a deliberate instance of opportunistic security
{{RFC7435}}: it raises the bar against passive attackers and is appropriate for the
small-set-of-known-peers applicability ({{applicability}}), but it is not a substitute
for a PKI.

To detect an intercepted first contact, the enrolling member's certificate fingerprint
is surfaced to the operator on both the Border and member sides for out-of-band
comparison; a mismatch aborts enrollment.

The automatic quarantine that unpins a member after repeated failed authentications
({{trust-in2n}}) was previously an availability hazard: a host that learned a member
identifier and could reach the Border's iN2N listener could submit failing
authentications to drive that member over the quarantine threshold and remove it from
routing. Failed-authentication accounting is now attributed per source: failures from a
source other than a member's established origin are rate-limited and MUST NOT count
toward that member's quarantine, so an off-path or foreign-source attacker can no longer
unpin a healthy member. Operators SHOULD still restrict reachability of the iN2N listener
to member hosts.

## Confidentiality and integrity {#seccons-conf}

NCFED provides its own confidentiality and integrity by upgrading the channel to TLS
1.3 {{RFC9846}} after the handshake ({{channel-sec-tls}}), with the peer's certificate
verified under its trust model. A deployment MAY additionally run over an encrypted
underlay or tunnel -- for example an encrypted data-plane tunnel, a VPN such as
WireGuard {{WIREGUARD}}, or an outer TLS tunnel -- and the reference deployment does so
(peers are reached over tunnels), but this is now defence in depth rather than the sole
source of transport security. Cleartext operation remains possible as an explicit,
operator-selected mode for a controlled environment ({{channel-sec-tls}}); it provides
no confidentiality and MUST NOT be used across an untrusted network or negotiated at a
remote peer's request.

NCFED inherits its key exchange from TLS 1.3 {{RFC9846}}. Implementations SHOULD
offer a post-quantum hybrid group (for example X25519MLKEM768) ahead of classical
curves where the TLS stack supports it; because a hybrid is negotiated only when both
peers' stacks support it, NCFED treats post-quantum key exchange as opportunistic by
default. A deployment MAY be configured to require a post-quantum negotiation
(refusing a channel that negotiated a classical group), noting that requiring
post-quantum on a stack that cannot offer it MUST fail loudly at configuration time
rather than silently refusing every peer. The negotiated group SHOULD be visible in
the operator posture view so an operator can tell whether a given channel obtained
post-quantum or classical key exchange. Where the implementation's TLS interface can
neither select nor report the negotiated group -- even though the underlying library
may negotiate a hybrid by default, as OpenSSL 3.5 does -- the posture view MUST
report the group as unknown rather than as classical or as post-quantum: posture
reports what the implementation can attest.

## Observable metadata {#seccons-metadata}

Even with the channel encrypted ({{seccons-conf}}), a passive on-path observer can
still learn *who federates with whom* from two signals that NCFED does not conceal.
First, the discrimination preamble ({{discrimination}}) carries the initiator's AS
and router-id in the clear; this is structural -- the shared port MUST discriminate
NCFED before any TLS ClientHello -- and cannot be moved inside TLS without a
dedicated port. Second, in the domain-verified trust model ({{channel-sec-models}})
the TLS SNI carries the acceptor's claw domain. Implementations SHOULD support
Encrypted ClientHello (ECH) to conceal the SNI where both the stack and the
deployment allow it, and operators who require unlinkability SHOULD prefer the
pinned trust model (no domain in SNI) or a dedicated non-shared port. These residual
exposures are accepted by design and are surfaced in the operator posture view.

## Agent-delegation hazards {#seccons-deleg}

`n2n/tools/call` and task delegation cause actions to be taken on real infrastructure
at the request of a remote AI agent. Deployments:

* MUST authorize remote invocation per peer (default-deny; explicit grants), and
  SHOULD constrain grants with approval requirements, budgets, and rate limits;
* MUST treat content returned across the federation boundary (tool results, task
  output) as untrusted input to the local agent, which can carry prompt-injection
  payloads; such content SHOULD NOT be interpreted as instructions;
* SHOULD log every federated invocation at the Border for audit, and MAY gate
  execution behind a production-mode guardrail that inspects model input/output;
* SHOULD bound delegation depth to prevent loops when federated agents can themselves
  re-delegate. This document does not define a delegation-depth or hop-count field;
  implementations that permit transitive delegation SHOULD add and enforce one, and a
  future revision is expected to carry a decrementing hop count in the tool and task
  method families ({{impl-status}}).

Task retrieval is bound to the submitting peer ({{semantics}}), so a task identifier
is not by itself a bearer capability: a third party that learns another peer's task
identifier is answered as if the task did not exist, and cannot read, cancel, or
even confirm the existence of the task. Implementations SHOULD still generate
unguessable task identifiers as defence in depth.

## Denial of service {#seccons-dos}

A payload is capped at 64 KiB per frame ({{framing}}) and an oversize Length MUST
cause a close. A message reassembled from CONTINUATION frames is further bounded to
16 MiB in aggregate and to 30 seconds of reassembly time ({{framing}}); a receiver
MUST close a channel that exceeds either bound. Without the time bound, a peer
could hold a reassembly buffer open indefinitely with a drip of legal zero-length
fragments, each of which also resets the liveness accounting of {{heartbeat}} --
the size bound alone does not close that hole. The heartbeat mechanism ({{heartbeat}}) and
cold-start ({{operational}}) can be abused as resource-exhaustion vectors; operators
SHOULD apply the per-peer rate/approval controls above and the port protections of
{{seccons-port}}.

## Capability-card privacy {#seccons-priv}

A capability card ({{cards}}) enumerates the advertiser's exposed skills, MCP servers,
security posture, and reasoning-model family. This is attack-surface metadata. An
endpoint MUST advertise only the subset a peer is authorized to see and MUST NOT
include secrets or per-member topology; operators SHOULD treat card contents as
sensitive, especially over cleartext transport ({{seccons-conf}}). A future revision
may define a minimized or integrity-protected card.

# IANA Considerations {#iana}

This document requests that IANA register the following service name in the Service
Name and Transport Protocol Port Number Registry {{RFC6335}}:

* Service Name: `ncfed`
* Transport Protocol: TCP
* Description: NetClaw-to-NetClaw Federation Protocol
* Assignee: John Capobianco <ptcapo@gmail.com>
* Contact: John Capobianco <ptcapo@gmail.com>
* Reference: This document
* Port Number: none requested. NCFED does not define a fixed well-known port; a
  deployment multiplexes NCFED onto an operator-configured port (in the reference
  deployment, the BGP/mesh port), discriminated as in {{discrimination}}.
* Assignment Notes: NCFED operates over unicast TCP only; it does not use UDP,
  broadcast, multicast, or anycast.

This document does **not** request a registry for the first-octet discrimination
tags ("NCFED", "NCTUN"); they are documented here for reference. Should third-party
extensions of the tag space emerge, a future document may define such a registry
(e.g., under a Specification Required or Expert Review policy {{RFC8126}}).

--- back

# Prior Art and Design Rationale {#prior-art}

NCFED's first-octet discrimination is analogous in spirit to, but distinct from, TLS
ALPN {{RFC7301}}, which negotiates the application protocol within the TLS
handshake; NCFED discriminates in cleartext at the head of the TCP stream so that it
can co-tenant with BGP without terminating TLS. Its length-prefixed, flag-bearing
framing and post-handshake message model are in the lineage of WebSocket {{RFC6455}}.
Its use of AS/router-id as agent identity reuses the operational identity model of
BGP-4 {{RFC4271}}, which fits the network-engineering deployment.

*Transport choice.* NCFED runs over raw TCP with its own minimal framing rather
than QUIC {{?RFC9000}} or WebSocket {{RFC6455}}. The deciding constraint is the
shared listening port ({{discrimination}}): co-tenancy with BGP-4 requires
discriminating the first octets of a TCP byte stream, which QUIC (UDP-based) cannot
share at all and WebSocket (an HTTP upgrade) could share only by putting an HTTP
server in front of BGP. QUIC is otherwise attractive for exactly the properties
this document works around: it integrates TLS 1.3 natively (removing the in-place
upgrade of {{channel-sec-tls}}), it survives endpoint address changes through
connection migration (removing much of the re-dial machinery of {{operational}}),
and its independent streams would eliminate the head-of-line blocking that a large
fragmented message imposes on this framing -- a heartbeat cannot be interleaved
mid-message ({{framing}}), so the 16 MiB reassembly bound caps, but does not
remove, the delay a bulk transfer can impose on liveness and cancellation traffic.
These trade-offs are accepted for the experimental deployment because the single
shared pinhole ({{discrimination}}) dominates the operational cost. A future
revision MAY define a QUIC binding for deployments that do not require BGP
co-tenancy; the framing layer is deliberately thin so that the semantic layers of
the two bindings would be identical.

NCFED is closest, among current IETF work, to
{{YAN-A2A}} ("Applicability of A2A Protocol for Network Management Agents"). That
work applies A2A to network management within a **single administrative domain**,
between a controller agent and device agents, over mutually authenticated TLS, and
does not address federation of independently operated agents. NCFED is
complementary: it federates agents across **different** operators (eN2N, keyed by
AS/router-id and mutual consent) and coordinates one operator's agents in a
hub-and-spoke risk (iN2N, enrollment-token + TOFU), and it **maps** MCP and A2A
semantics onto its method families rather than defining new agent-card or task
semantics of its own. A one-sentence differentiation: *NCFED is a cross-operator
federation, identity, and transport layer -- multiplexed with BGP -- that carries
MCP-style tool invocation and A2A-style task delegation between independently
operated network agents.*

Hub-and-spoke (rather than a full mesh) was chosen for iN2N so that a single Border
provides one audit, policy, and routing boundary and one external identity for a
risk; members never accept inbound connections, which minimizes their attack
surface.

Defining NCFED as a strict wire specification rather than an SDK API is a
deliberate choice for runtime agnosticism. Everything a peer must agree on is
on the wire -- first-octet discrimination ({{discrimination}}), the binary
handshake ({{handshake}}), the TLS upgrade and possession proof ({{channel-sec}}),
the frame format ({{framing}}), and the JSON-RPC method families ({{semantics}}) --
and nothing above the wire is prescribed. Two peers therefore interoperate with no
shared code and no knowledge of each other's LLM orchestration, prompt structures,
or local execution runtime; each side maps its internal representation onto the
common MCP/A2A constructs at the boundary. This is what lets a risk mix agent
engines ({{terminology}}) and lets independently developed agents federate across
operators. The multi-implementation interoperability recorded in {{impl-status}}
(the NetClaw reference engine and the independently developed Hermes agent) exercises
this separation directly.

# Implementation Status {#impl-status}
{:removeinrfc="true"}

This section records the status of known implementations of the protocol defined by
this specification at the time of posting, per {{?RFC7942}}. It is to be removed
before publication as an RFC.

**Implementation:** the open-source NetClaw project (`automateyournetwork/netclaw`).
NCFED (eN2N and iN2N) is deployed and in daily use across a live three-operator mesh
(AS 65001, AS 65007, AS 65099) and within one operator's risk (a Border and its
member claws). Coverage: protocol discrimination, the 13-octet handshake, the frame
format and heartbeat, JSON-RPC method families, in-band negotiation, and both trust
models are all implemented and in daily use across the operators of the mesh, all
running the reference implementation; interoperability with a second, independently
developed implementation (Hermes) is recorded separately below. The channel security of {{channel-sec}}
is implemented: the in-place TLS 1.3 upgrade, application-layer proof of possession
with the two trust models (domain-verified via ACME/DNS-01 and pinned/TOFU), the
possession/self-asserted admission tiers with enforcing mode, iN2N Border-as-CA hub
attestation, and automatic certificate rotation. The reference deployment's own claw is
domain-verified (a publicly trusted certificate for a claw domain, obtained and
auto-renewed via DNS-01).

**Multi-implementation interoperability (Hermes <-> NetClaw).** NCFED has been
exercised between two independently developed agent implementations with different
codebases and different reasoning runtimes: the NetClaw reference engine (running a
Claude model in the captured session) and Hermes, a separate agent framework
(running a GPT model). In the captured session a Hermes peer initiated NCFED
delegation over the federation channel (`n2n-federation` / `cml-lab-lifecycle`
skills) to audit a remote Cisco Modeling Labs (CML) environment held by a third
operator's claw. The federation layer behaved exactly as specified end to end: the
channel was discriminated, upgraded to TLS (the peer's trust auto-upgraded to
domain-verified when its claw connected), authenticated, and authorized, and the
delegated call was routed to the remote tool. The remote `cml-mcp` tool then failed
internally on an upstream input-schema (Pydantic) validation error -- a missing
`effective_permissions` field, its models out of sync with the remote CML 2.8.0
API -- and that tool-side error was returned to the Hermes peer within the tool
result, as a tool error rather than an NCFED protocol error ({{semantics}}), and
surfaced cleanly to its operator. Hermes's own summary recorded the distinction
precisely: "this isn't a connectivity or federation problem -- the N2N channel,
authorization, and delegation all worked end-to-end[;] it's a version mismatch
between [the remote] `cml-mcp` package and their CML 2.8.0 server." This exercises
the design's central claim: the transport, identity, and federation layers are
decoupled from any single agent's internal codebase, so two disparate
implementations interoperate over the wire with neither sharing the other's runtime,
and an in-tool failure is relayed faithfully rather than corrupting the channel.
This is genuine interoperability evidence (two independently developed
implementations exercising the same normative behavior), distinct from the
multi-operator *operational* evidence above (which runs one implementation). The
terminal captures (`captures/hermes00.png`, `captures/hermes01.png`) and the
correlated encrypted packet capture are retained in the project repository under a
SHA-256 manifest (`captures/MANIFEST.sha256`).

**Interoperability evidence (packet capture):** a 37.5-second capture of a live NCFED
channel between johns-risk (AS 65001) and Nick (AS 65007) was taken at the initiator
(`ncfed-johns-risk-nick-20260714.pcap` in the project repository) while three
application-level round-trips were exercised:

* One long-lived TCP conversation, `192.168.2.61:45722` <-> `13.58.157.220:10416`
  (the initiator to the peer's tunnel edge); 24 packets, 3141 octets, near-symmetric
  (13 in / 1567 octets, 11 out / 1574 octets).
* TCP health: only ACK and PSH-ACK segments in-window (no SYN/FIN/RST -- a persistent,
  already-established control channel), with zero retransmissions and zero duplicate
  ACKs.
* Payload segmentation: 12 zero-length (pure-ACK) segments plus data segments of 5,
  75, 110, 127, 153, 274, and 352 octets -- small, bursty, and request/response-shaped,
  consistent with a control/chat protocol rather than bulk transfer.

**Capture methodology and limitations (important, honest scope):** this capture was
taken on the wire *inside the peer's TLS-terminated tunnel transport* (the deployment
reaches the remote AS over a tunnel provider). The captured payload octets are
therefore **ciphertext**: the capture is accurate, first-hand evidence of the NCFED
**channel** -- real endpoints, a persistent established session, healthy TCP, and a
request/response traffic shape between two independently operated ASes -- but it does
**not** expose decrypted NCFED frames, so the segment sizes above are TLS-record
sizes carrying NCFED, not raw NCFED frame boundaries. A plaintext capture of the NCFED
frames themselves requires capturing at the application layer (e.g., on loopback,
before the tunnel) or on an underlay where the operator holds the keys (e.g.,
WireGuard); such a capture is future work and is the recommended way to demonstrate
the frame-level behavior specified in {{framing}} and {{handshake}} directly.

**Loopback discrimination and handshake conformance (AS 65099).** The frame- and
handshake-level behavior that the tunnel capture above could not expose was verified
directly against the reference daemon on its cleartext loopback listen port, before
any TLS upgrade, with a purpose-built conformance client. Observed results, each
matching this specification:

* {{discrimination}} discrimination. A first octet of 0x00 (unrecognized), a direct
  TLS ClientHello (first octet 0x16), and 'N' followed by an unknown four-octet magic
  ("NXXXX") were each closed by the acceptor with no bytes returned. A first octet of
  0xFF was handed to the BGP engine and the connection was held open awaiting the
  remainder of the 16-octet BGP marker. Only the "NCFED" magic advanced to the
  federation handshake. This confirms, on the wire, that a direct TLS connection to
  the shared port is refused (the STARTTLS-style in-place upgrade of
  {{channel-sec-tls}} is the only path to TLS), as {{discrimination}} requires.

* {{handshake}} handshake, consent gate. A connection presenting the "NCFED" magic
  and the AS/router-id of a consented peer (`as65001-4.4.4.4`) received the
  acceptor's 13-octet handshake reply ("NCFED" + the acceptor's AS + router-id). A
  connection presenting a non-consented stranger identity (and, separately, the
  acceptor's own identity, for which no peer-consent record exists) was closed with
  zero bytes returned.

* Implementation-vs-specification note ({{handshake}}). The reference implementation
  closes a non-consented peer **without sending any handshake reply**, never
  revealing its own AS and router-id to a peer it has not consented to. Earlier
  internal iterations of this document required the acceptor to reply before
  closing; {{handshake}} now standardizes the safer observed behavior (withholding
  the nonce is the MUST; withholding the handshake reply is the SHOULD).

* {{channel-sec-tls}} in-place TLS upgrade. Continuing the consented-peer handshake,
  the channel upgraded in place to TLS 1.3 with cipher suite TLS_AES_256_GCM_SHA384;
  the acceptor presented its domain-verified certificate (subject CN
  `netclaw.byrnbaker.me`), confirming both the STARTTLS-style upgrade and the
  domain-verified trust model of {{channel-sec-models}} on the live channel.

* {{framing}} framing bound. The receive path reads a five-octet header (four-octet
  big-endian length + one-octet flags) and closes the channel when the length field
  exceeds 65536. This was exercised inadvertently but informatively in production
  before the dialer-tier fix (below): a peer's TLS ClientHello, misread as an NCFED
  frame header during a transient sequencing bug, produced a length field of
  0x16030102 (369295618) and the channel was closed as oversized exactly as
  {{framing}} requires.

**Resolved during pre-submission iteration.** The peer-authentication gap that the
first internal iteration of this document recorded as a limitation is closed and
implemented: eN2N and iN2N are now
cryptographically, mutually authenticated ({{channel-sec}}, {{trust-in2n}}), and the
iN2N quarantine denial-of-service is fixed by per-source failed-authentication
accounting ({{seccons-tofu}}). A reported forged-handshake impersonation of a
consented, tool-granted peer was reproduced on a two-daemon loopback and is closed by
the possession proof and admission tiers of {{channel-sec}}.

**Dialer-side admission tier ({{channel-sec-tiers}}), resolved.** An earlier build
granted the possession tier only on the acceptor side of a channel, leaving the
listener role on a channel the local node had **dialed** stuck at the self-asserted
tier indefinitely. Because endpoint update ({{operational}}) is denied at the
self-asserted tier, this silently rejected a dialed peer's endpoint re-announcements
-- observed in production as a consented peer re-announcing a rotated tunnel endpoint
roughly every 30 seconds with the announcements refused, so the direct BGP session
never re-formed at the new endpoint. The fix grants the possession tier to a
TLS-verified listener on a dialed channel as well; after it was deployed across the
live mesh, a peer's rotated endpoint announcement was accepted and the direct BGP
session re-established at the new endpoint on the first re-dial, verified end to end
between AS 65099 and AS 65001.

**Hardened at pre-submission review.** Four protections that earlier internal
iterations recorded as known limitations are implemented in the reference
implementation as specified in this document: the (AS, router-id) deterministic-
initiator tie-break ({{handshake}}); the 16 MiB / 30 s reassembly bounds, including
closing on a heartbeat received mid-reassembly ({{framing}}, {{seccons-dos}});
task retrieval bound to the submitting peer, answering non-owners with the
missing-task shape ({{semantics}}, {{seccons-deleg}}); and MEMBER_ID_TAKEN (-32022)
emitted on the wire ({{errors}}). Each is covered by the project test suite.

**Known limitations recorded for a future revision.** The following gaps remain in the
current implementation and are targeted for a future NCFED revision:

* The tool and task method families carry no delegation hop count. Transitive
  re-delegation is not implemented, so the field is deferred until it exists; an
  implementation that adds transitive delegation MUST add and enforce one first.
  See {{seccons-deleg}}.
* In-band "version negotiation" is feature advertisement with graceful degradation,
  not selection of a common protocol version. See {{negotiation}}.
* The tuple tie-break of {{handshake}} governs the NCFED federation channel; the
  associated NCTUN data plane (out of scope here) still keys tunnels by AS alone
  and does not support equal-AS peers.

This evidence is provided to document running code and operational reality; it is not
a normative part of the protocol.

# JSON-RPC Method Reference {#method-ref}

This appendix specifies the parameter and result objects for each NCFED method, as
implemented in the reference implementation ({{impl-status}}). All objects are JSON
{{RFC8259}}; unless stated otherwise, an unrecognized member is ignored. Encodings: a
binary signature is a lowercase hexadecimal string of a DER-encoded ECDSA signature
{{RFC6090}} over the relevant nonce; a certificate is PEM-encoded {{RFC5280}}; a key
fingerprint is the lowercase hexadecimal SHA-256 {{RFC6234}} of the certificate's
SubjectPublicKeyInfo {{RFC5480}}. Examples are illustrative.

## eN2N methods

`n2n/hello` -- the only method permitted before federation is established. The
request `params` carry the sender's descriptor **and its possession proof**
({{channel-sec-pop}}): `cert_pem` is the sender's certificate and `signature`
proves possession of the matching private key over the acceptor's nonce.

~~~
params: {
  "identity": "as65001-192.0.2.1",
  "display_name": "johns-risk",
  "versions": ["1.0"],
  "cert_pem": "-----BEGIN CERTIFICATE----- ...",
  "signature": "<hex DER ECDSA over nonce || B>",
  "capabilities": {
    "proto_version": "053",
    "features": ["async_tasks", "endpoint_reannounce", "negotiate"],
    "agent_invoke": "session-id",
    "reply_shapes": ["finalAssistantVisibleText", "payloads"]
  }
}
result: {
  "display_name": "nick",
  "capabilities": { ...same shape as params.capabilities... }
}
~~~

The signed input is the raw octet concatenation `nonce || B`, with no length
prefix or separator: `nonce` is the acceptor's 32-octet possession challenge
({{handshake}}), and `B` is the tls-server-end-point channel binding
({{channel-sec-pop}}) -- the 32-octet SHA-256 of the acceptor's server
certificate -- on an encrypted channel, or empty on a cleartext one. Both
components are fixed-length, so the concatenation is unambiguous. A consented
peer that omits `cert_pem` and `signature` is admitted only at the restricted
self-asserted tier ({{channel-sec-tiers}}), and is refused outright in enforcing
mode.

`n2n/tools/call` -- the `tool` member MUST have the form `server_id/tool_name`;
otherwise the callee returns JSON-RPC error -32602 (invalid params). The `result` is
the MCP {{MCP}} tool-result object from the named server. Authorization failures use
the codes of {{errors}}.

~~~
params: { "tool":       "<server_id>/<tool_name>",
          "arguments":  { ...tool-specific JSON... },
          "request_id": "as65001-192.0.2.1:42" }
~~~

`n2n/tasks/submit` -- A2A-style {{A2A}} delegation:

~~~
params: { "skill":      "<skill-name>",
          "input_text": "<free text passed to the skill>",
          "request_id": "as65001-192.0.2.1:43" }
result: { "task_id": "<opaque string>", "state": "submitted" }
~~~

`n2n/tasks/status`, `n2n/tasks/result`, `n2n/tasks/cancel` -- each takes
`params: { "task_id": "<opaque string>" }`. Retrieval is bound to the submitter
({{semantics}}): a caller other than the authenticated peer that submitted the
task receives the same answer as for an unknown task_id (state `unknown`;
`cancelled: false`). Each returns:

~~~
status: {
  "task_id": "...", "target": "<skill-name>",
  "state": "submitted|working|completed|failed|cancelled|unknown",
  "progress": "<string or null>"
}
result: {
  "task_id": "...", "state": "...", "tokens_used": <number>,
  "output_text": "<present when completed>",
  "error": "<present when failed>"
}
cancel: { "task_id": "...", "cancelled": <boolean> }
~~~

`n2n/inventory`, `n2n/inventory_get` -- push and pull of the capability card
({{cards}}).

## iN2N methods

Each iN2N method is sent by the member after receiving the Border's "IN2N1" preamble
and 32-octet nonce ({{trust-in2n}}); the `signature` proves possession of the
member's pinned key over that nonce.

`in2n/enroll` -- first contact. On success the Border spends the token and pins the
certificate's SubjectPublicKeyInfo. Errors: NOT_A_BORDER (-32024); MEMBER_NOT_TRUSTED
(-32023) on possession failure; ENROLL_TOKEN_INVALID (-32021) for a spent or expired
token, or a member identifier already pinned to another key ({{errors}}).

~~~
params: { "token":             "in2n_<url-safe random>",
          "member_id":         "<risk-local id>",
          "cert_pem":          "-----BEGIN CERTIFICATE----- ...",
          "signature":         "<hex DER ECDSA over the nonce>",
          "scope":             "<optional capability scope>",
          "runtime_kind":      "process",
          "display_name":      "<optional>",
          "transport_binding": "distributed" }
~~~

`in2n/hello` -- reconnect. A mismatched fingerprint or signature returns
MEMBER_NOT_TRUSTED (-32023) and counts toward auto-quarantine ({{seccons-tofu}}).

~~~
params: { "member_id":       "<risk-local id>",
          "key_fingerprint": "<hex SHA-256 of SubjectPublicKeyInfo>",
          "signature":       "<hex DER ECDSA over the nonce>" }
result: { "risk": "<risk name>", "trusted": true,
          "member_state": "active" }
~~~

# Change History (Pre-Submission Iterations)
{:numbered="false"}

This note is to be removed before publishing as an RFC. Before this first
Datatracker submission as `-00`, the document was iterated in the project
repository as internal revisions `-01` and `-02`; those iterations are archived
there. The summaries below record what changed across them, for reviewers who
followed the repository drafts.

Changes in the pre-submission review passes (July 2026, from internal `-02`):

* Abstract and {{trust-in2n}}: the eN2N and iN2N security models are now stated
  distinctly -- TLS 1.3 is integral to eN2N, while iN2N is mutually authenticated
  at the application layer with TLS as an optional transport wrapper -- and the
  risk-local CA is clarified to issue only the Border's hub certificate; member
  certificates remain self-signed and pinned.
* {{handshake}}: a non-consented peer is closed without a handshake reply
  (matching the implementation), and the deterministic initiator is ordered by
  the (AS, router-id) tuple, removing the equal-AS ambiguity.
* {{channel-sec-models}}: the consent record's binding of the NCFED identity to
  the expected claw domain is now normative.
* {{method-ref}}: `n2n/hello` now specifies the `cert_pem`/`signature`
  authentication members and the exact signed input (`nonce || B`).
* {{negotiation}} retitled "Version Signaling and Capability Advertisement" to
  reflect that no common version is negotiated.
* Protocol hardening, specified and implemented together: reassembly bounded to
  16 MiB / 30 seconds with heartbeat-mid-reassembly a MUST-close protocol error
  ({{framing}}, {{seccons-dos}}); task retrieval bound to the submitting peer
  with non-owners answered as unknown ({{semantics}}, {{seccons-deleg}});
  MEMBER_ID_TAKEN (-32022) emitted on the wire ({{errors}}); and the
  (AS, router-id) tie-break implemented for the federation channel.
* Design rationale added from transport/routing-area review: {{discrimination}}
  now states why the shared port is a deployment constraint and that
  general-purpose BGP stacks are not asked to adopt discrimination; a
  transport-choice paragraph (TCP + custom framing versus QUIC/WebSocket,
  including the head-of-line-blocking trade-off) added to the prior-art
  appendix; {{seccons-port}} states why the in-place TLS upgrade has no
  strippable STARTTLS command; {{negotiation}} defines the failure for an
  unsupported future baseline (-32602 + close).
* Deep code-review reconciliation: the remote sever method was removed so
  severing is strictly local ({{operational}}); the reassembly timer was
  corrected so a zero-length-fragment drip cannot reset it ({{framing}}); TLS
  1.3 is enforced as the minimum ({{channel-sec-tls}}). The eN2N trust model is
  restated as asymmetric by role ({{channel-sec-models}}) -- domain-verification
  applies to the acceptor-role credential, while the initiator authenticates by a
  pinned self-signed possession proof -- matching the implementation rather than
  overstating symmetry. The channel binding is described accurately as an
  endpoint (not per-connection) binding, with replay/relay resistance from the
  fresh confidential nonce and {{RFC9266}} `tls-exporter` noted as the intended
  per-connection upgrade ({{channel-sec-pop}}, {{seccons-peer-auth}}).
* Agent agnosticism made explicit (abstract, {{terminology}}, {{semantics}},
  {{prior-art}}): NCFED is a wire specification that federates heterogeneous
  agent engines, and the protocol/tool error separation is stated. Multi-
  implementation interoperability with the independently developed Hermes agent
  is recorded in {{impl-status}}.

Changes in internal `-02` (July 2026, from internal `-01`):

* Asynchronous task delegation ({{semantics}}): completion signalling is now
  explicitly advisory with polled state authoritative; callers reconcile
  non-terminal tasks after channel re-establishment. Motivated by observed loss of
  completion notifications across channel bounces in the reference deployment.
* New Security Considerations subsection "Observable metadata"
  ({{seccons-metadata}}): the cleartext discrimination preamble (AS/router-id) and
  the domain-verified SNI are documented as accepted, posture-surfaced residuals;
  ECH is recommended where available.
* Confidentiality and integrity ({{seccons-conf}}): post-quantum hybrid key
  exchange (e.g. X25519MLKEM768) is recommended opportunistically, with a
  fail-loud require mode and honest posture reporting -- a group the
  implementation cannot attest is reported as unknown, never as classical or
  post-quantum.
* Sharing a listening port with BGP ({{seccons-port}}): the mesh session's trust
  boundary is stated honestly -- cleartext BGP relying on transport encryption on
  untrusted legs until the staged in-protocol upgrade ships.
* Operational Considerations ({{operational}}): endpoint persistence guidance --
  persist the last successfully authenticated endpoint; never overwrite it on a
  failed dial.

# Acknowledgments
{:numbered="false"}

This protocol is developed and interoperation-tested by its authors on the first
three-node NCFED mesh (AS 65001, AS 65007, and AS 65099). Thanks to the reviewers of
the NetClaw project.
