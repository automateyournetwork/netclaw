# Socializing `draft-capobianco-ncfed-00` at IETF `agentproto`

How to place NCFED in the 2026 agent-protocol landscape and drive it toward
adoption (spec US4 / FR-021).

## Venue

- **Primary: the IETF `agentproto` effort.** A Birds-of-a-Feather (`agentproto`, at
  IETF 126) is building on an IETF 124 side meeting and framework/use-case work
  (Rosenberg, Jennings), aiming to charter a Working Group for agent-to-agent and
  agent-to-tool communication (MCP, A2A, ACP, ANP, and related I-Ds are in scope).
  This is the correct home for NCFED. Submit the `-00` (submissiontype `IETF`,
  individual), then post to the `agentproto` list and request a slot at a
  side meeting / the BoF.
- **Fallback: Independent Submission (ISE), Experimental.** If the WG does not take
  it up, the ISE can publish it as an Experimental RFC for citability. Note that
  under RFC 5742 the IESG conflict-review would likely defer to a forming WG, so the
  WG path is both primary and the one the ISE would point back to.
- **Caveat:** new I-D submissions freeze for ~2 weeks around each IETF meeting — plan
  revisions accordingly.

## The one-line pitch

> **NCFED is a cross-operator federation, identity, and transport layer —
> multiplexed with BGP on one port — that carries A2A/MCP between independently
> operated network agents.** It is complementary to A2A/MCP, not a competitor.

## Differentiation from the closest work

- **`draft-yan-a2a-device-agent-applicability`** applies A2A to network management
  **within one administrative domain** (controller → device), over mutual TLS. It
  does **not** federate independently operated agents. NCFED adds the
  **cross-operator** case (eN2N: AS/router-id identity + mutual consent) and a
  lightweight **intra-operator hub-and-spoke** (iN2N: enrollment token + TOFU),
  and it *carries* A2A/MCP rather than redefining their semantics.
- **A2A / MCP**: NCFED transports them. A2A's signed Agent Cards map onto NCFED's
  capability cards; MCP `tools/*` maps onto `n2n/tools/call`. NCFED contributes the
  federation/identity/transport substrate and the BGP port-multiplexing, which no
  other agent protocol does.
- **ALPN (RFC 7301)**: NCFED discriminates in cleartext at the head of the TCP
  stream (to co-tenant with BGP), rather than negotiating within TLS.

## Talking points for review (pre-answer the hard questions)

- **Why share a port with BGP?** Operational reuse of the existing mesh session; the
  Security Considerations RECOMMEND applying BGP-grade ACL/TTL protections and
  enforce strict discrimination timeouts.
- **Why TOFU / cleartext?** Small set of mutually known peers; opportunistic security
  (RFC 7435) with an out-of-band identity check; SHOULD run under an encrypted
  underlay off-net. Not a PKI, by design.
- **Loop/prompt-injection safety?** Default-deny per-peer authorization, Border audit,
  production-mode guardrails, cross-boundary content treated as untrusted, and a
  SHOULD-level delegation-depth bound.
