# Phase 0 Research: iN2N — Internal NetClaw Federation

All open decisions from the spec's clarifications and the plan's Technical Context, resolved. Each: Decision / Rationale / Alternatives considered.

---

## R1. Member runtime model

**Decision**: A Member is a **standalone OpenClaw runtime** (its own process or container), not an in-process profile. The runtime model is **selectable per member** so one risk can mix a co-located member and a member in another cloud.

**Rationale**: The distributed-microservices case (members across hosts/clouds/datacenters) is a first-class requirement (spec FR-028, operator's explicit note). In-process profiles cannot leave the host, so they can't satisfy it. Standalone runtimes give real isolation (separate context, separate blast radius — the "focus and token economy" goal) and let the same abstraction cover both co-located and distributed members. Per-member selection avoids forcing container overhead on a small single-host risk.

**Alternatives considered**: (B) in-process scoped agent profiles in one OpenClaw — simplest and cheapest but co-located only; rejected because it can't do distributed members at all. (Always-container) — uniform but pays network+container cost even for a tiny local risk; rejected in favor of per-member choice.

---

## R2. Internal transport & topology

**Decision**: iN2N is a **hub-and-spoke star** centered on the Border. Members communicate **only** with the Border (never member-to-member). Reachability is achieved by **each member dialing OUTBOUND** to the Border's single reachable endpoint. The transport **reuses the NCFED wire framing** (`[4-byte length][1-byte flags][JSON-RPC 2.0]`, chunking, heartbeats from `channel.py`) over this member-initiated connection — a new *binding*, not a new protocol. No iBGP, no routing protocol, no full mesh.

**Rationale**: Single-owner, centralized coordination has no n×n reachability to solve — only member↔Border. Outbound-dial means members need no inbound ports, no public address, and no ngrok, and works from behind NAT or inside a private cloud (SC-011). Reusing NCFED framing means the JSON-RPC method dispatch, chunking, and heartbeat logic already written and tested for eN2N carry straight over. It is literally the eN2N dial pattern pointed inward at the operator's own Border. Distributed members ride the operator's own private network / overlay-VPN (WireGuard/Tailscale) / tunnel — that connectivity is the operator's concern, iN2N just needs a TCP path to the Border.

**Alternatives considered**: A routing-protocol/mesh (iBGP-style) — unnecessary complexity for a star; rejected. Border-initiated dial to members — would require members to have reachable inbound endpoints (defeats the no-inbound-ports goal, breaks NAT/private-cloud members); rejected. A brand-new wire protocol for internal use — needless divergence from the proven, tested NCFED framing; rejected.

---

## R3. Enrollment & channel authentication (no CA)

**Decision**: **Enrollment token + member-generated self-signed key, pinned trust-on-first-use.** At risk creation the Border can issue a **single-use enrollment token**. A member generates its own self-signed keypair at runtime. On first dial it presents `(token, public_key)`; the Border validates the token, **pins** the public key to a risk-local member ID, and marks the token spent. Every subsequent internal channel is authenticated by the pinned key (channel encrypted end-to-end). Key rotation ⇒ re-enroll (new token) or explicit operator re-pin. No certificate authority.

**Rationale**: One operator owns the whole risk, so full mutual-consent (as in eN2N) is unnecessary friction — but the channel must still be authenticated so a rogue local process can't impersonate a member (esp. over a distributed transport). TOFU with a spent-once token gives strong practical security with zero PKI to operate across clouds: the token gates *becoming* a member; the pinned key authenticates *being* one thereafter. This is the operator's explicit choice (clarify Q1), strengthened with runtime self-signed keys (operator's suggestion) instead of a shared long-lived secret.

**Alternatives considered**: Mutual TLS with a risk-local CA — cert-based auth but an operator-run CA to stand up and rotate; rejected as heavier than pinning buys. Shared long-lived risk secret used on every connection — simplest but a single reusable secret is a worse compromise blast radius than a spent-once token + pinned per-member key; rejected. Manual per-member approval only — good control but tedious at provisioning scale; folded in as the *re-pin* path, not the default enroll path.

---

## R4. Member identity scheme

**Decision**: **Risk-local member ID** `<risk-name>/<member-name>` (e.g. `johns-risk/cml`), assigned at provisioning, **bound to the pinned key**. The name is the stable handle used in the registry, audit log, routing, and HUD; the pinned key is the authenticator. The ID is stable across relocation (a member moving between clouds keeps its ID; only its transport binding changes).

**Rationale**: Members don't run BGP, so the eN2N identity `as<AS>-<router-id>` doesn't apply. A human-readable risk-local ID reads well in audit/routing and is stable independent of network location — critical because location can change. Binding it to the pinned key means the name is a convenience, not a security boundary; impersonation is prevented by the key, not the string.

**Alternatives considered**: Key-fingerprint-as-identity (self-sovereign) — stable and unforgeable but opaque in logs/UX; kept as the underlying binding but not the display identity. Reuse BGP-style identity for members — false consistency (members aren't mesh peers, don't have an AS); rejected.

---

## R5. Border-side routing & deterministic tie-break

**Decision**: The Border matches an operator request to a Member using the **reused capability inventory** (skill/tool names + descriptions each member advertises, spec 052 model). Selection is by capability match; when **multiple** members match, tie-break is **deterministic** by a documented rule: (1) most-specific scope (fewest advertised capabilities that still cover the request) wins, then (2) lexicographic member ID. When **no** member matches, the Border reports "no member in this risk can do that" rather than attempting it or silently failing.

**Rationale**: Reusing the inventory means routing rides the same capability data eN2N already exchanges — no new discovery mechanism. "Most-specific scope wins" favors the true specialist (the CML claw over a broader claw that also happens to list CML), which matches the focus goal; lexicographic ID is a stable final tiebreak so the same request always lands on the same member (testable, SC — deterministic). Explicit "no member" is required by FR-011 to avoid the Border quietly doing work no specialist owns.

**Base-floor exclusion (FR-021b)**: specificity is measured over each member's **specialty** capabilities only. The mandatory base floor (R7a) that every member shares is excluded from the count, otherwise the common base tools would blur how specialized a member looks and could tie or invert the true specialist.

**Alternatives considered**: LLM-freeform routing with no tie-break — non-deterministic, hard to test, could fan out; rejected (the Border may still *use* reasoning to interpret the request, but the member *selection* among matches is deterministic). Load-balancing/scoring across equivalent members — out of scope for v1 (spec Out of Scope); a deterministic pick is sufficient.

---

## R6. Role model & standalone equivalence

**Decision**: **Two roles — Border and Member** — plus the identity "a standalone NetClaw is a risk of one that is its own Border." eN2N/iN2N/both is a **Border-side setting**, not a role. The daemon gains a `role` (`standalone|border|member`) and, for a Border, `enabled_stacks` (`en2n`, `in2n`, or both). A standalone install sets `role=standalone` and behaves exactly as today.

**Rationale**: Collapsing "eN2N NetClaw" into "a Border with eN2N enabled" removes a redundant role and matches the operator's own statement that the Border is where the stack is chosen. It also makes backwards-compat trivial: `standalone` is the default and is behaviorally identical to pre-054 NetClaw (SC-008). Exactly-one-Border-per-risk is enforced at config time (FR-003).

**Alternatives considered**: Three roles (Border / eN2N / iN2N-member) as originally brainstormed — the "eN2N" role duplicates "Border with eN2N enabled"; rejected for simplicity per the design discussion. A separate standalone codepath — unnecessary; standalone is just the degenerate risk.

---

## R7. Installer: risk/role selection & profile provisioning

**Decision**: Extend the existing **modular installer** (spec 049: `scripts/lib/catalog.sh` + `install-steps.sh`), not a new installer, and drive every prompt through **Nick's existing TUI primitives in `scripts/lib/tui.sh`** (PRs #96, #115, #117) — no new prompt style. Concretely:
- **`tui_menu`** for standalone-vs-part-of-a-risk, for role (Border/Member), and for eN2N/iN2N/both (all single-select, arrow-key, → `TUI_CHOICE`).
- **`tui_yesno`** for confirmations (matches installer style).
- **`tui_checklist`** (the category-headed multi-select with `CL_IDS/CL_LABELS/CL_ON`, exactly as the component picker uses it) for the **Custom** member skill/tool selection, and for choosing which seed profiles to provision.
- **Claw profiles derived at runtime from the installed skill catalog** by a new `scripts/in2n-profiles.py` (CML claw, pyATS claw, security claw, … + Custom), so profiles can't drift from what's installed (FR-019); the specialty profile is layered on the mandatory base floor (R7a).

Additionally, the **`scripts/netclaw` command gains a Risk surface that mirrors `peering_menu`**: an interactive `risk_menu` (Overview · Members · Add member · Remove member · Enrollment token) under the main menu, plus non-interactive subcommands `netclaw risk [status|members|add|remove|token|route]` mirroring the existing `netclaw peering [status|bgp|n2n|ngrok]` pattern. Reuses the same neon palette, `TUI_CHOICE` dispatch, off-TTY degradation, and daemon HTTP (`api_get`/`api_post` against `bgp-daemon-v2.py`) as the peering tree.

**Rationale**: Constitution XI mandates the catalog/`install-steps` touchpoints, and spec 049 + Nick's #96/#115/#117 already established the modular installer AND the TUI look-and-feel and the `netclaw` command tree — reusing them is required for consistency and is lowest-friction. Deriving profiles from the live catalog (rather than a hardcoded list) is a direct FR-019 requirement. A `risk` sub-tree parallel to `peering` means an operator navigates iN2N exactly the way they already navigate eN2N/BGP/ngrok.

**Alternatives considered**: A standalone iN2N installer/wizard or a bespoke prompt style — violates the modular-installer convention and Nick's TUI format; rejected. Hardcoded profile definitions — drift from the real catalog; rejected per FR-019. Putting Risk only in the installer with no `netclaw` command surface — inconsistent with how peering is operated day-to-day; rejected.

### R7a. Mandatory base floor for every member (FR-021a)

**Decision**: Every provisioned member — any profile, including Custom — includes a **non-removable base floor**: (a) the iN2N member runtime (enroll/dial/heartbeat, provided by `internal_channel.py` — infrastructure, always present), (b) self-status + capability reporting (so the Border can discover/route to it), (c) audit/GAIT reporting of its own actions back to the Border (Constitution IV), and (d) the constitutional safety behaviors (read-before-write; no unapproved destructive commands — Constitution I/II). `scripts/in2n-profiles.py` layers the chosen specialty profile *on top of* this floor; the floor is tagged as base so it is excluded from the routing specificity tie-break (R5 / FR-021b).

**Rationale**: A member scoped to *only* its specialty can't heartbeat, can't be routed to, can't be audited by the Border, and could bypass the safety principles — all of which the architecture and constitution require. Making the floor explicit and non-removable keeps members focused (small specialty) without leaving them crippled or unsafe. Excluding it from specificity keeps the specialist-selection honest.

**Alternatives considered**: No base floor (profile-only) — leaves members unable to report/heartbeat/audit and risks unsafe behavior; rejected. Counting base tools toward specificity — distorts which member is the true specialist; rejected (hence FR-021b).

---

## R8. Audit centralization & no-secrets guard

**Decision**: The Border is the **single audit/GAIT point** (FR-024). Internal delegations are recorded in the existing `remote_invocation_record` table with a `channel_kind` column (`en2n|in2n`) so one query shows all activity. An external (eN2N) request satisfied by internal delegation writes **both** records, linked (FR-025). The **no-secrets guard reused from 052** applies to iN2N unchanged — inventories carry only capability names/descriptions, and no credentials cross any claw boundary (FR-026).

**Rationale**: Reusing the audit table + guard avoids a parallel audit path and keeps the "one place to see everything" promise real with minimal new code. `channel_kind` is a one-column migration. The no-secrets guard is already the enforcement point for cross-boundary data; iN2N is just another boundary type it covers.

**Alternatives considered**: A separate iN2N audit table — fragments the audit trail against FR-024; rejected. Relaxing the no-secrets guard internally because "one operator" — tempting but a member in another cloud is still a separate trust surface; keeping the guard is safer and costs nothing; rejected relaxation.

---

## Cross-cutting: frozen eN2N core

All of the above are **additive bindings/profiles over 052/053**. The eN2N `n2n/hello` handshake, mutual-consent state machine, default-deny authorization, budget/kill-switch, and no-secrets guard are **not modified**. iN2N adds an `in2n/hello` handshake variant and an internal-transport dial that live alongside them, discriminated at connect time. `test_en2n_regression.py` guards this (SC-009).
