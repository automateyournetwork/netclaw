# IETF MCP / agent-protocol landscape → NCFED `-01` input

**Surveyed 2026-08-04** · roadmap **R23** · feeds `NCFED-HARDENING-BACKLOG.md` and
`AGENTPROTO-POSITIONING.md`

All draft states verified against `datatracker.ietf.org` on the survey date. Internet-Drafts expire
six months after revision, so **every citation below carries its revision and expiry** — a `-01` that cites
a lapsed draft is worse than one that cites nothing.

---

## Three things the roadmap got wrong

The roadmap's R23 entry was written from an April 2026 snapshot. Correcting it is the first deliverable.

### 1. One of the four named drafts is dead

**`draft-zw-opsawg-mcp-network-mgmt` is EXPIRED. Do not cite it.**

It is `-00`, last revised 2025-11-02, and datatracker banners it *"no longer active"*. Worse, it is one
terminal of a four-name venue-shopping chain in which **every link is now expired or replaced**:

| Name | Rev | Date | State |
|---|---|---|---|
| `draft-zeng-mcp-network-mgmt` | 01 | 2025-10-16 | Replaced |
| `draft-zw-rtgwg-mcp-network-mgmt` | 00 | 2025-10-20 | Replaced |
| `draft-zw-nmrg-mcp-network-mgmt` | 00 | 2025-10-20 | **Expired**, no successor recorded |
| `draft-zw-opsawg-mcp-network-mgmt` | 00 | 2025-11-02 | **Expired** |

There is **no active revision** of the MCP-extensions-for-network-equipment work anywhere. Four sibling
Huawei drafts from the same cluster also expired on 2025-11-02.

The live successor to that line is **`draft-zeng-nmrg-mcp-usecases-requirements-00`** (2026-02-14) — but
it **expires 2026-08-18, two weeks after this survey**. Cite it only if `-01` is submitted before then, or
expect it to lapse.

### 2. The draft count went *down*, not up

The roadmap says "15+ active as of April 2026". Measured: **13 active**. The Huawei cluster expired faster
than new drafts arrived. "MCP at the IETF is growing" is not currently true — *agent protocols* at the IETF
are growing (199 active drafts match "agent"), and MCP is a small corner of that.

### 3. The roadmap misses the single biggest development

**A WG-forming BOF happened.** `agentproto` — "Agent Communication Protocols", ART area, chairs **Leslie
Daigle** and **Orie Steele**, AD Charles Eckel — met at **IETF 126 Vienna on 2026-07-23**.

The sense-of-the-room results are the load-bearing detail:

| Question | Yes | No |
|---|---|---|
| Problem space is real | 124 | 72 |
| Interoperability needed | 155 | 30 |
| IETF is the right venue | 158 | 30 |
| **Proposed scope acceptable** | **38** | **124** ← rejected |
| **Form a WG** | **154** | **51** ← clear support |

**The room wants a WG and rejected the charter it was handed.** Recommended refocus: away from a "session
layer", toward **context propagation signalling across trust boundaries and multiple parties**. Next steps
were a new list, a narrowed charter, and a time-boxed call for contributions.

`charter-ietf-agentproto` returns 404 and the group page still reads *"Not chartered yet"* — **treat as not
chartered** as of 2026-08-04. BOF minutes remain *"DRAFT for chair review"*.

`AGENTPROTO-POSITIONING.md` still describes this BOF in the future tense and has been updated accordingly.

---

## Current state of the four named drafts

| Draft | Rev | Revised | Expires | State |
|---|---|---|---|---|
| `draft-zw-opsawg-mcp-network-mgmt` | 00 | 2025-11-02 | — | **EXPIRED — do not cite** |
| `draft-yang-nmrg-mcp-nm` | **03** | 2026-07-06 | 2027-01-07 | Active, not adopted. **The healthy one** |
| `draft-serra-mcp-discovery-uri` | 04 | 2026-03-25 | **2026-09-25** | Active, single author, lapses soon |
| `draft-morrison-mcp-dns-discovery` | **05** | 2026-07-22 | 2027-01-23 | Active, single author, 66pp |

**`draft-yang-nmrg-mcp-nm-03`** is the one to cite for *"MCP is being discussed for network management at
the IETF"*: six authors across Huawei, Telefónica, Deutsche Telekom, Orange and Nokia, four revisions,
presented at NMRG. It is an individual submission — an adopted RG document would be `draft-irtf-nmrg-*`.
No adoption call was found.

**opsawg has no live MCP work.** All opsawg-named MCP drafts expired; the work migrated to **NMRG** and
**NMOP**. The roadmap's "check opsawg / nmrg activity" item resolves to: opsawg dead, NMRG alive but no
adoption call.

---

## The discovery drafts: they do not solve NCFED's problem

Both answer *"given a domain name I already trust, where is its MCP endpoint and what does it speak?"*
**Neither answers "how do two agents come to trust each other in the first place?"** — which is the entire
substance of NCFED's enrollment.

### Serra — `mcp://` URI + `/.well-known/mcp-server`

Three-step cascade: an optional `_mcp.{host}` TXT hint, then a **required** `GET
https://{host}/.well-known/mcp-server` returning a JSON manifest (`mcp_version`, `name`, `endpoint`,
`transport`), then a last-resort `https://{host}/mcp`.

Trust is **WebPKI plus same-origin**: authenticity comes from the HTTPS certificate, and the manifest's
`endpoint` host must match or be a subdomain of the manifest's own host. DNSSEC is SHOULD only.

**Key pinning is explicitly absent** — the draft states *"No key pinning"*. Authentication is only
*declared*, never performed: the `auth` object advertises `none`/`bearer`/`mtls`/`apikey`/`oauth2`, and the
draft says outright that authentication *"is covered by … OAuth 2.1 respectively"*.

### Morrison — DNS TXT records at underscore labels

`_mcp.<domain>` for service discovery, `_org-alter.` and `_alter.` for identity. Records carry
`pk=ed25519:<base64url>` and an `epoch=` rotation counter, with detached Ed25519 signatures over
RFC 8785-canonicalised JSON.

Trust is **DNSSEC + DANE + in-DNS key pinning**. DNSSEC is REQUIRED for `_alter` envelopes; where an
envelope and a session are one transaction a **DANE TLSA record is mandatory** and clients *"MUST NOT fall
back to PKIX-only validation"*.

Two things to know before citing it:

- **`-05` is a retraction revision.** It *withdraws* `-04`'s requirement to cross-reference an IdentityLog
  root against four named witness surfaces — *"That requirement is WITHDRAWN. It named surfaces that do not
  exist"* — and marks per-individual DNS envelope publication NOT RECOMMENDED. The author has publicly
  walked back his own trust machinery.
- **It admits it has no revocation.** *"Revocation status cannot presently be established from DNS alone.
  This is a gap in the mechanism."*

### The argument this gives NCFED

A clean Related-Work position, citing both as **contrast, not dependency**:

- **vs Serra** — WebPKI + name binding, **zero key pinning**, authentication deferred to OAuth. NCFED's
  enrollment-token + pinned-key model is *strictly stronger on peer authentication* and **does not require
  the peer to operate a public HTTPS origin at all**.
- **vs Morrison** — genuine key pinning, and the only real overlap with NCFED's TOFU model. But it pins
  keys *in the DNS zone*, relocating trust to the zone operator plus DNSSEC plus DANE, and then concedes it
  cannot do revocation. NCFED pins out-of-band via single-use enrollment tokens, so it needs neither a
  signed zone nor DANE, and severing is a local database operation.
- **vs both** — they assume a **public, name-addressable server**. NCFED peers are explicitly configured,
  may be NAT'd or private, and are *peers* rather than servers. The discovery problem genuinely does not
  arise.

---

## The better citation target the roadmap missed: DAWN

**`draft-akhavain-moussa-dawn-problem-statement-05`** (2026-07-19, expires 2027-01-20, Active) — plus a
second BOF, **`dawn`** ("Discovery of Agents, Workloads, Named Entities", Internet area, chairs Adrian
Farrel and Wes Hardaker, also **not chartered yet**).

DAWN frames the general cross-organisational agent discovery problem — and **explicitly assumes trust is
already solved**:

> *"Assuming that trust has already been established between entities… the discovering entity must learn
> what the remote entity does."*

It names the two trust questions — whether the discovery source is authoritative, and whether the
registered entity is what it claims — and **proposes no trust model, identity binding, or key
distribution**. It also declines to endorse DNS or well-known-URI discovery, listing DNS-SD/SSDP/WebFinger
as prior art *"needing careful analysis to identify key gaps"*.

**This is the strongest citation available to NCFED.** NCFED's explicit-configuration-plus-TOFU model is a
legitimate answer to DAWN's unfilled trust-establishment slot, and DAWN's own framing licenses manual
configuration as a current approach rather than dismissing it. It is a better fit than either MCP discovery
draft, because it is a *problem statement in the area NCFED occupies* rather than a competing mechanism.

---

## The most actionable item: fill in the security-principal-binding matrix

**`draft-bu-agentproto-security-principal-binding-04`**, revised **2026-08-02** — two days before this
survey — and it sits in the `agentproto` document set.

It defines a verifier-facing model separating claims about user authority, agent instance identity, tool
identity, delegation state, session continuity and action evidence — and provides a **reusable matrix that
protocol authors are meant to fill in**, stating for each claim which field carries it, who verifies it,
what binding and freshness rules apply, and the required failure behaviour.

**Filling that matrix in for NCFED is the single highest-value, lowest-cost `-01` addition identified by
this survey.** It is cheap (NCFED already has the mechanisms; this is a tabulation), it is high-credibility
(it demonstrates engagement with agentproto rather than the MCP corner), and it aligns NCFED with a
document that is *current within the forming WG* rather than with drafts that are expiring.

---

## The pushback to pre-empt in `-01`: revocation

The IETF consensus direction for agent identity is **WIMSE/SPIFFE identifiers with short-lived
credentials and OAuth-based delegation**. The heavyweight is **`draft-klrc-aiagent-auth-03`** (2026-07-06,
expires 2027-01-07) — Kasselman (Defakto), Lombardo (AWS), Rosomakho (Zscaler), Campbell (Ping), Steele
(OpenAI), Parecki (Okta) — which mandates *"exactly one WIMSE identifier, which MAY be a SPIFFE ID"* with
short-lived X.509-SVID / JWT-SVID credentials **rather than static keys**, and does cover agent-to-agent via
transaction tokens and OAuth token exchange.

**NCFED's TOFU-pinned long-lived keys are orthogonal to that**, and reviewers from this crowd will push on
exactly one thing: **revocation**. The agentproto BOF minutes explicitly flag *"continued discussion on
trust boundaries, revocation, and authorization frameworks"*, and it is the same gap Morrison admits to.

NCFED does have an answer — severing revokes the local grant, and it is a local database operation rather
than a log pre-image reveal — but `-00` treats severing as an operator lifecycle action rather than framing
it as *the* revocation story. **`-01` should make the revocation argument explicitly and up front**, because
it is the first question this audience will ask.

Adjacent drafts worth a sentence each if space allows: `draft-okutomi-session-bound-agent-identity-06`
(channel binding — conceptually close to NCFED's long-lived pinned session),
`draft-singla-agent-identity-protocol-03` (DIDs + capability delegation),
`draft-niyikiza-oauth-attenuating-agent-tokens-01` (attenuating tokens — relevant if NCFED ever narrows a
delegated task's authority).

MCP-specific security work exists but is thin: `draft-mohiuddin-mcp-security-considerations-00`
(2026-06-01) and `draft-sharif-mcps-secure-mcp-00` (2026-03-14, 43pp).

---

## Also new since April 2026, relevant to NCFED

| Draft | Why it matters |
|---|---|
| **`draft-abbott-mcp-ax-00`** (2026-05-04) | Hierarchical tool-namespace delegation across MCP servers — the closest thing to a federation/aggregation story in MCP-land. Worth comparing against NCFED's iN2N hub-and-spoke |
| `draft-feng-nmop-naim-mcp-00` (2026-07-18) | NAIM framework over MCP, in NMOP |
| `draft-morrison-mcp-tool-surface-names-registry-00` | IANA registry for tool names |
| `draft-jennings-agentproto-mcp-over-moqt-00` | MCP over MoQ; note it is now `agentproto`-named |

---

## Recommendations for `-01`

In priority order, each traceable to a finding above:

1. **Fill in the `draft-bu-agentproto-security-principal-binding` matrix.** Cheapest high-credibility win.
2. **Make revocation an explicit, prominent argument**, not a lifecycle footnote. It is the first question
   this audience asks, and NCFED's answer is genuinely better than the DNS-based alternatives'.
3. **Cite DAWN's problem statement** as the framing NCFED answers — a stronger position than citing either
   MCP discovery draft.
4. **Cite Serra `-04` and Morrison `-05` as contrast**, with revisions stated, noting that Serra defines no
   key pinning and Morrison admits no revocation. **Note Serra may lapse 2026-09-25.**
5. **Cite `draft-yang-nmrg-mcp-nm-03`** for MCP-in-network-management. **Do not cite
   `draft-zw-opsawg-mcp-network-mgmt` — it is dead.**
6. **Compare against `draft-abbott-mcp-ax`** on hierarchical delegation, since iN2N solves an adjacent
   problem.
7. **Reconcile with the WIMSE/SPIFFE direction** — a paragraph acknowledging short-lived credentials as the
   consensus direction and explaining why a pinned long-lived key is appropriate for a BGP-adjacent peering
   session that must survive control-plane restarts.
8. **Watch the `agentproto` charter.** The scope was rejected 38–124 and is being rewritten toward *context
   propagation across trust boundaries* — which is closer to NCFED's actual contribution than the original
   session-layer framing was. If the revised charter lands there, NCFED's fit improves.

## What this survey did not verify

Stated so nothing here is mistaken for settled:

- Whether the `agentproto` charter has been approved since the BOF. Group page still reads "Not chartered
  yet"; minutes are still draft.
- Whether any NMRG/NMOP **adoption call** exists for `draft-yang-nmrg-mcp-nm` — session presence and
  "related work" status were found, an adoption call was not.
- Which expired terminal name Huawei treats as canonical for the network-equipment-extensions work.
- Serra `-04`'s exact revision date — datatracker's document page says 2026-03-25, its search index says
  2026-03-26.
- The full 199-draft "agent" set was not enumerated; datatracker paginates at ~10 rows across 83 pages. The
  `agentproto` and `dawn` document sets were captured in full.
