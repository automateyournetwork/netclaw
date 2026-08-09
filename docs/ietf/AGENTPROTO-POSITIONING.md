# Socializing `draft-capobianco-ncfed-00` at IETF `agentproto`

How to place NCFED in the 2026 agent-protocol landscape and drive it toward
adoption (spec US4 / FR-021).

## Venue

- **Primary: the IETF `agentproto` effort.** ART area, chairs **Leslie Daigle** and
  **Orie Steele**, responsible AD Charles Eckel. Still the correct home for NCFED.
  Post to `agentproto@ietf.org` and request a slot.

  **UPDATED 2026-08-04 — the BOF has happened, and the outcome matters.** The
  WG-forming BOF met at **IETF 126 Vienna on 2026-07-23**. Sense of the room:

  | Question | Yes | No |
  |---|---|---|
  | Problem space is real | 124 | 72 |
  | Interoperability needed | 155 | 30 |
  | IETF is the right venue | 158 | 30 |
  | **Proposed scope acceptable** | **38** | **124** ← rejected |
  | **Form a WG** | **154** | **51** ← clear support |

  **The room wants a WG and rejected the charter it was handed.** The recommended
  refocus — away from a "session layer", toward **context propagation signalling
  across trust boundaries and multiple parties** — is *closer* to NCFED's actual
  contribution than the original framing was, so NCFED's fit improves if the revised
  charter lands there.

  `charter-ietf-agentproto` 404s and the group page still reads *"Not chartered
  yet"*; BOF minutes remain *"DRAFT for chair review"*. **Treat as not chartered.**
  Watch for the narrowed charter and the time-boxed call for contributions.

  A second BOF is also relevant: **`dawn`** ("Discovery of Agents, Workloads, Named
  Entities", Internet area, chairs Adrian Farrel and Wes Hardaker, also not
  chartered). Its problem statement explicitly assumes trust is already established
  and proposes no trust model — which is precisely the slot NCFED fills. See
  `IETF-MCP-LANDSCAPE-2026-08.md`.
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

---

## Landscape survey

A full survey of the MCP / agent-protocol draft landscape, with verified revisions and
expiries, is in **[`IETF-MCP-LANDSCAPE-2026-08.md`](./IETF-MCP-LANDSCAPE-2026-08.md)**
(roadmap R23, surveyed 2026-08-04).

Three headlines from it that change this note:

1. **`draft-zw-opsawg-mcp-network-mgmt` is EXPIRED** — one terminal of a four-name
   rename chain in which every link is now expired or replaced. Do not cite it.
2. **The MCP draft count went down**, not up: 13 active, against the "15+" of April
   2026. MCP is a small corner of a 199-draft agent-protocol space.
3. **`draft-bu-agentproto-security-principal-binding-04`** (revised 2026-08-02)
   supplies a reusable claims matrix protocol authors are meant to fill in. Filling it
   for NCFED is the cheapest high-credibility `-01` addition available.
