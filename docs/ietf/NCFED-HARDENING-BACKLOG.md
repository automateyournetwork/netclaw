# NCFED Hardening Backlog — seed for a future spec (060+) and draft `-01`

This file records the **code / protocol changes** deliberately deferred while
authoring `draft-capobianco-ncfed-00`. The `-00` draft keeps the FREEZE (FR-024): it
describes the running wire exactly and honestly, including its limitations. None of
the items below are blockers for an **Experimental** submission — they are the
roadmap for the *next* revision (a hardening spec, then draft `-01`).

Each item lists: the gap, where it lives in the code, the proposed fix, and the draft
section that already documents it honestly today.

Source of truth verified 2026-07-14 against `mcp-servers/protocol-mcp/bgp/` and
`bgp/federation/*`.

---

## Tier 1 — cheap, high-value, unambiguous (recommended first)

### H1. Bounded message reassembly (DoS)
- **Gap:** the 64 KiB per-frame cap is enforced, but a message reassembled from many
  CONTINUATION frames grows an unbounded buffer.
- **Code:** `bgp/federation/channel.py` `_read_loop` — `self._recv_buf += chunk` with
  no aggregate limit or timeout.
- **Fix:** add an aggregate reassembled-size cap and a reassembly timeout; close the
  channel on exceed. Define the concrete bound in the spec.
- **Draft today:** §Denial of service (`seccons-dos`) + Implementation Status.

### H2. Delegation hop count (loop prevention)
- **Gap:** no hop-count/TTL in the wire; transitive delegation loops rely on each
  implementation adding its own guard.
- **Code:** `bgp/federation/invocation.py` `handle_tools_call` / `handle_task_submit`
  (no hop field in params).
- **Fix:** add a decrementing integer (e.g. `ncfed_hop_count`) to the tool + task
  method families; MUST decrement and reject at zero.
- **Draft today:** §Agent-delegation hazards (`seccons-deleg`).

### H3. Task ownership / authorization on retrieval
- **Gap:** `n2n/tasks/status|result|cancel` are keyed by `task_id` alone; any peer
  with the id can read/cancel. Task id is effectively a bearer token.
- **Code:** `bgp/federation/tasks.py` `status`/`result`/`cancel` — lookup by
  `task_id`, no caller check.
- **Fix:** bind a task to the submitting `peer_identity`; authorize retrieval against
  it. Keep task ids unguessable regardless.
- **Draft today:** §Semantic Payload (task note) + `seccons-deleg`.

### H4. Quarantine-as-DoS mitigation
- **STATUS: RESOLVED** — feature 060 / draft -01. Per-source failed-auth accounting (`risk.note_source_failure`); foreign-source failures rate-limited, never count toward a member's quarantine.
- **Gap:** repeated *unauthenticated* `in2n/hello` attempts with a known `member_id`
  drive `auth_failures` over the threshold, unpinning a legitimate member.
- **Code:** `bgp/federation/risk.py` `record_auth_failure` (global per-member count);
  triggered from `service.py` `_in2n_on_hello`.
- **Fix:** source-bind / rate-limit failed-auth accounting; do not let unauthenticated
  attempts alone unpin a member. Restrict iN2N listener reachability (deployment).
- **Draft today:** §Trust on first use (`seccons-tofu`) + Implementation Status.

### H5. Emit MEMBER_ID_TAKEN (-32022)
- **Gap:** `-32022` is defined but never reaches the wire; a member-id collision is
  reported as `-32021` (ENROLL_TOKEN_INVALID).
- **Code:** `service.py` `_in2n_on_enroll` maps any non-"TRUSTED" `ValueError` to
  `-32021`; `risk.py` `consume_token` raises `ValueError("IN2N_ERR_MEMBER_ID_TAKEN")`.
- **Fix:** map the member-id-taken `ValueError` to `-32022`.
- **Draft today:** §Error codes (`errors`) + Implementation Status.

### H6. Capability-card minimization / integrity
- **Gap:** cards disclose skills, MCP servers, posture, model family (attack-surface
  metadata) over cleartext.
- **Code:** `bgp/federation/inventory.py`, `posture.py`.
- **Fix:** per-peer minimized card; optional integrity protection. (Partly present via
  per-peer authz — tighten and document the minimization contract.)
- **Draft today:** §Capability-card privacy (`seccons-priv`).

---

## Tier 2 — real design work (the two "Critical" review findings)

### H7. eN2N cryptographic peer authentication  *(headline gap)*
- **STATUS: RESOLVED** — feature 060 / draft -01 §Channel Security. Encrypted (TLS 1.3) channel + application-layer proof-of-possession (signed nonce) with domain-verified (ACME) or pinned (TOFU) trust models + tier-0/tier-1 admission. Also closed the forged-handshake spoof reported by Josh/TunnelMind.
- **Gap:** the 13-octet handshake identity (AS/router-id) is a cleartext claim; no
  cryptographic proof. Consent/grants key off the claim.
- **Code:** `service.py` `accept_channel` / `open_channel` (identity from handshake,
  no signature); `manager.py` consent keyed by identity string.
- **Proposed fix (reuse what already works):** extend the **iN2N** proof-of-possession
  pattern to eN2N — at consent, operators also exchange a **key fingerprint**; each
  side pins the other's key; the handshake / `n2n/hello` carries a **signed nonce**.
  One mechanism, consistent across eN2N/iN2N, no new PKI. Decision (2026-07-14): do
  **not** invent PKI; acknowledge cert/mutual-TLS or the Agent Name Service (ANS,
  `draft-narajala-ans`) as alternatives in the draft; ship `-00` with BGP identity +
  OOB confirmation + strict default-deny consent as the interim model.
- **Draft today:** §Peer authentication (`seccons-peer-auth`) — disclosed + forward
  path named.

### H8. iN2N Border-to-member authentication + channel binding
- **STATUS: RESOLVED** — feature 060 / draft -01 §iN2N. Border-as-CA hub attestation: member verifies the Border's CA-signed hub cert chains to its enrolled anchor + signed the member's nonce. Mutual auth. (tls-server-end-point channel binding now wired into the primary channel path — draft §6.3.)
- **Gap:** member authenticates to Border, but Border is **not** authenticated to the
  member; optional TLS uses `CERT_NONE` (no channel binding). MITM can relay the
  nonce / interpose post-auth.
- **Code:** `service.py` iN2N accept path (member trusts any `IN2N1` preamble);
  `internal_channel.py` / TLS context with verification disabled.
- **Proposed fix:** member also pins the **Border's** key (mutual TOFU); enable real
  cert verification against pinned keys; bind the signed nonce to the session.
  Naturally solved together with H7.
- **Draft today:** §Peer authentication (`seccons-peer-auth`) + §iN2N.

---

## Documentation-only (already handled in `-00`, no code change)

- **D1. TLS vs shared port:** a TLS ClientHello (0x16) is not a discriminator value and
  is closed; encryption comes from an underlay/tunnel or the separate iN2N listener,
  not inline TLS on the shared port. → §Discrimination, §Confidentiality.
- **D2. Version negotiation is feature-advertisement + graceful degrade,** not version
  selection. A real negotiation scheme (common-version selection, required-feature
  failure) is future work. → §Negotiation.

---

## Suggested sequencing (per 2026-07-14 discussion)

1. Ship `draft-capobianco-ncfed-00` (this honest Experimental draft) — optional now.
2. New spec `060-ncfed-hardening`: Tier 1 (H1–H6) + the H7/H8 mutual-pin design.
3. Implement on the frozen base; **test with a real claw** + the live 3-node mesh.
4. Coordinate the mesh: Byrn (AS 65099) & Nick (AS 65007) `git pull`, re-exchange key
   fingerprints, re-consent / re-enroll (pins change). Ship an upgrade note.
5. Rewrite the draft to describe the hardened wire → `draft-capobianco-ncfed-01`.

---

## `-02` seed — wire-hardening deltas from spec 063 (2026-07-17)

Surfaced by the live two-operator packet capture (Nicholas AS 65007 ↔ Byrn AS 65099,
`captures/n2n-encrypted-20260717.pcap`), which confirmed the `-01` channel is fully
TLS-encrypted with zero JSON-RPC leakage and flagged four follow-ups. Spec 063 lands
three of the four in code (endpoint persistence, PQ posture, metadata seam);
mesh-layer TLS is a deferred, coordinated flag-day (below). The `-01` markdown +
rendered artifacts stay FROZEN and coherent; fold the text below when cutting `-02`.

### H9. Endpoint persistence — *STATUS: RESOLVED (spec 063 / US1)*
- **Was:** `/n2n/connect` + `open_channel` dialed a peer's fresh address but never
  persisted `endpoint_host/port`, so after a restart the reconnect supervisor used the
  STALE stored endpoint → connection-refused → manual re-dial on every ngrok rotation.
- **Fix (shipped):** `open_channel` persists the reached endpoint via `upsert_peer`
  **only on a successful, authenticated dial** (never on the failure path);
  `upsert_peer` centralizes the `endpoint_updated_at` freshness bump; the supervisor
  already reads these. Operational behavior; not a wire-format change.
- **Draft:** operational note only (§Operational Considerations) — no normative change.

### H10. Observable metadata residuals — *document in `-02` (accepted by design)*
- **Reality:** two identity signals remain visible to a passive on-path observer after
  `-01`'s TLS: (a) the cleartext 13-octet NCFED preamble carries AS + router-id (kept
  cleartext so the shared port can discriminate NCFED from BGP/NCTUN *before* TLS —
  structural, cannot move inside TLS without breaking discrimination, §discrimination);
  (b) the TLS SNI carries the claw domain in domain-verified mode (ECH not yet
  available on the reference stack). Together they let an observer enumerate who
  federates with whom.
- **Shipped (063/US3):** an ECH-ready no-op seam in the dialer TLS context that
  activates automatically once `ssl` exposes ECH; posture (`/n2n/posture`) now reports
  both residuals so operators see the exposure rather than assume it away.
- **Ready-to-fold `-02` prose (new §seccons subsection "Observable metadata"):**
  > Even with the channel encrypted ({{seccons-conf}}), a passive on-path observer can
  > still learn *who federates with whom* from two signals that NCFED does not conceal.
  > First, the discrimination preamble ({{discrimination}}) carries the initiator's AS
  > and router-id in the clear; this is structural — the shared port MUST discriminate
  > NCFED before any TLS ClientHello — and cannot be moved inside TLS without a
  > dedicated port. Second, in the domain-verified trust model ({{channel-sec-models}})
  > the TLS SNI carries the acceptor's claw domain. Implementations SHOULD support
  > Encrypted ClientHello (ECH) to conceal the SNI where both the stack and the
  > deployment allow it, and operators who require unlinkability SHOULD prefer the
  > pinned trust model (no domain in SNI) or a dedicated non-shared port. These residual
  > exposures are accepted by design and are surfaced in the operator posture view.

### H11. Post-quantum key-exchange posture — *document in `-02`*
- **Reality:** the capture showed the initiator offering the X25519MLKEM768 hybrid but
  the peer negotiating classical X25519 — acceptance depends on *both* TLS stacks.
- **Shipped (063/US4):** `N2N_PQ_MODE` (opportunistic default) offers the hybrid where
  the stack supports it and accepts classical fallback; `require` hard-refuses classical
  on a capable stack and **fails fast at startup** on a stack that cannot do PQ at all
  (never silently refusing every peer); per-channel `tls_version`/`cipher`/`kex_group`
  + `pq: available|unavailable` are surfaced honestly (`kex_group` is unreadable, hence
  `null`, until Python exposes `SSLObject.group` — Python 3.15+, verified absent on 3.14).
- **Verified 2026-07-17 (Ubuntu 26.04, Python 3.14.4, OpenSSL 3.5.5):** OpenSSL 3.5
  ships X25519MLKEM768 in its *default* group list, so two OpenSSL>=3.5 peers negotiate
  the PQ hybrid on the wire with no code change — while Python <= 3.14 can neither
  request nor read the group. `pq: unavailable` therefore means "cannot offer-and-verify",
  not "the wire is classical"; the `-02` prose below should keep that distinction
  (posture reports what the implementation can attest, and unknown is reported as
  unknown, never as classical or as PQ).
- **Ready-to-fold `-02` prose (add to §seccons-conf):**
  > NCFED inherits its key exchange from TLS 1.3 {{RFC8446}}. Implementations SHOULD
  > offer a post-quantum hybrid group (e.g. X25519MLKEM768) ahead of classical curves;
  > because a hybrid is negotiated only when both peers' TLS stacks support it, NCFED
  > treats PQ as opportunistic by default and MAY be configured to require it (refusing
  > a classical negotiation), noting that requiring PQ on a stack that cannot offer it
  > MUST fail loudly at configuration time rather than silently refusing all peers. The
  > negotiated group SHOULD be visible in the operator posture view so an operator can
  > tell whether a given channel obtained PQ or classical key exchange.

### H12. Mesh-layer confidentiality — *DEFERRED: coordinated flag-day (spec 063/US2)*
- **Reality:** the BGP mesh/keepalive session that co-tenants the shared port
  (§discrimination) is still cleartext BGP; on the WAN leg it currently rides inside the
  transport's TLS (ngrok), which is incidental, not guaranteed. Routing/identity
  metadata on that leg is observable on an untrusted path.
- **Plan (not yet shipped):** bring the mesh session under NCFED's own STARTTLS-style
  in-protocol TLS + auth (the same `tls.upgrade_to_tls` primitive `-01`/060 already
  use), gated by `N2N_CERT_MODE`, upgraded *after* the BGP OPEN identify. Deferred from
  063 implementation because it modifies the BGP routing core (`agent.py` collision /
  OPEN-replay path + `session.py`), requires two-node validation against the live FRR/
  mesh FSM, and only pays off in a coordinated multi-peer rollout — a supervised flag-day
  like the 060 cutover, not an unsupervised change.
- **Draft:** until shipped, `-02` MUST describe the mesh trust boundary honestly as
  "relies on the transport's encryption on untrusted legs; bringing the mesh session
  under NCFED's own TLS is defined but optional/staged" — do NOT claim it as done.

### H13. Async task completion is lost across a channel bounce — *LIVE BUG (found 2026-07-17)*
- **Reality:** during the 2026-07-17 heartbeat cycles, the pyats member *completed*
  three delegated `pyats-health-check` tasks (member-side audit shows
  `in_scope/success` at 16:46/17:52/18:56 UTC) but the Border's `delegated_task`
  rows stayed `submitted` forever — the iN2N channel had bounced ("Channel closed
  by peer" → redial) between submit and completion, and the completion notification
  died with the old channel. The Border then reported "no live picture" even though
  every check had succeeded. A fourth task's completion was recovered only because
  the member re-delivered after its post-reboot reconnect.
- **Gap:** task completion delivery is at-most-once; there is no redelivery of
  terminal states after reconnect and no Border-side reconciliation (poll of
  in-flight tasks) when a member/peer channel is re-established.
- **Plan:** on channel re-establish, (a) the submitter SHOULD reconcile its
  non-terminal outbound tasks via `n2n/tasks/status`, and/or (b) the executor
  SHOULD re-announce unacknowledged terminal states (at-least-once with
  idempotent apply). Applies to both iN2N member channels and eN2N peer channels.
- **Draft:** `-02` async-tasks section should state that completion notifications
  are advisory and pollable state is authoritative: a submitter MUST NOT treat a
  missing completion as failure, and SHOULD reconcile in-flight tasks after a
  channel re-establish.

### H14. Tier asymmetry on dialer-initiated channels — *FIXED (found live 2026-07-18)*
- **Reality:** `channel.attestation` was only ever set on the ACCEPTOR side
  (`_on_hello` verifies the dialer's possession proof). On a channel the local claw
  dialed, the LISTENER never received an attestation, so its `endpoint_update` /
  execution requests were denied at tier-0 forever — observed as a 33-second denial
  loop against both live mesh peers, silently disabling `endpoint_reannounce` on
  every dialed channel (the lowest-AS claw dials everyone, so the hub saw it for all
  peers).
- **Fix (shipped):** on the dialer side, after `_secure_dial` verifies the
  listener's certificate (pin / domain SAN), the TLS handshake itself constitutes
  the listener's possession proof for that certificate; the channel now records
  `attestation="possession"` + the listener's leaf. Cleartext channels are
  unchanged (still self-asserted).
- **Draft:** `-02`'s admission-tier prose should state explicitly that on an
  encrypted channel the acceptor's tier at the initiator is established by the TLS
  server authentication (certificate verification + the handshake's key-possession
  property), while the initiator's tier at the acceptor is established by the
  `n2n/hello` possession proof — the two proofs are asymmetric by construction.

### Cutting `-02` (supervised)
**CUT 2026-07-17 at John's direction** (ahead of H12/mesh-TLS, which `-02` documents
honestly as staged/optional rather than claiming done): `draft-capobianco-ncfed-02.md`
folds in H10 (new §"Observable metadata"), H11 (PQ prose with the corrected
attest-or-report-unknown nuance), H13 (poll-authoritative task-state reconciliation),
the H12 honest mesh-trust-boundary statement (§seccons-port), and an H9 operational
note (endpoint persistence) plus a "Changes from -01" appendix. Rendered via `kdrfc
--v3` (0 over-length lines; idnits authoritative server-side at Datatracker, per the
`-01` checklist precedent) into `rendered/draft-capobianco-ncfed-02.{txt,xml}`.
A future `-03` (or pre-submission refresh of `-02`) picks up H12 once mesh-TLS ships.

## `-01` (next submission) seed — knowledge capability cards (spec 064, 2026-07-19)

Spec 064 (implemented) adds a **knowledge** surface to the A2A capability card and a
dedicated retrieval method. The next NCFED submission after `-00` should document it
in the draft (FR-010):

- **§11 Capability Cards:** add a `knowledge` array alongside `skills`/`mcp_servers` —
  one content-free A2A-skill-shaped entry per RAG collection (`collection_id`, name,
  semantic `description` of topics/titles, `tags`, doc/page/chunk counts,
  `retrieval` = `n2n/knowledge/query`). MUST NOT contain document content, embeddings,
  or source paths; per-peer visibility applies (item_type `knowledge`).
- **§9 Method families / Appendix C:** add `n2n/knowledge/query` — a dedicated method
  (NOT the MCP `tools/call` proxy) taking `{collection_id, query, k}` and returning an
  agent-composed, cited answer `{answer, provenance:{peer, collection_id, citations}}`.
  Default-deny + possession tier; unknown/hidden `collection_id` answered as
  "no such collection" (no existence oracle); audited with peer + collection + GAIT.
- **Framing note:** this is the on-wire form of *federated query* (knowledge stays
  home, only the answer travels) — the sovereignty-preserving counterpart to the
  deferred RAG2RAG *replication* idea (spec 065, out of scope).
- Selection (which peer collection answers) is deterministic embedding-cosine over the
  advertised descriptions with a configurable threshold — an implementation/agent
  concern, not a wire element, so it need not appear in the draft beyond a sentence.

## `-01` seed — IETF landscape reconciliation (roadmap R23, 2026-08-04)

From the survey in [`IETF-MCP-LANDSCAPE-2026-08.md`](./IETF-MCP-LANDSCAPE-2026-08.md). Ordered by
value-per-effort; every item traces to a verified draft state.

### Tier 1 — cheap, high-credibility

- **Fill in the `draft-bu-agentproto-security-principal-binding-04` claims matrix** for NCFED (user
  authority · agent instance identity · tool identity · delegation state · session continuity · action
  evidence; for each: carrying field, verifier, binding/freshness rule, failure behaviour). NCFED already has
  the mechanisms — this is tabulation, and it demonstrates engagement with `agentproto` rather than the
  expiring MCP corner. **Highest value per unit of effort identified by the survey.**
- **Promote revocation from lifecycle footnote to explicit argument.** `-00` treats severing as an operator
  action ({{prior-art}} / §"Lifecycle"). The agentproto BOF minutes flag *"continued discussion on trust
  boundaries, revocation, and authorization frameworks"*, and it is the **first question** this audience
  asks. NCFED's answer is genuinely stronger than the DNS-based alternatives' — Morrison
  `-05` concedes *"Revocation status cannot presently be established from DNS alone"* — so this is a win
  currently being left on the table.
- **Fix the Related Work citations.** Add `draft-akhavain-moussa-dawn-problem-statement-05` as the framing
  NCFED answers; cite `draft-serra-mcp-discovery-uri-04` (no key pinning, auth deferred to OAuth) and
  `draft-morrison-mcp-dns-discovery-05` (DNS-rooted pinning, admits no revocation) as **contrast**; cite
  `draft-yang-nmrg-mcp-nm-03` for MCP-in-network-management. **Do NOT cite
  `draft-zw-opsawg-mcp-network-mgmt` — it is expired.**

### Tier 2 — real writing

- **Reconcile with WIMSE/SPIFFE.** `draft-klrc-aiagent-auth-03` (Kasselman, Lombardo, Rosomakho, Campbell,
  Steele, Parecki) mandates one WIMSE identifier with **short-lived** SVID credentials rather than static
  keys. Add a paragraph explaining why a pinned long-lived key suits a BGP-adjacent peering session that must
  survive control-plane restarts. Expect to be asked; better to answer first.
- **Compare against `draft-abbott-mcp-ax-00`** (hierarchical tool-namespace delegation across MCP servers) —
  the closest thing to a federation story in MCP-land, and adjacent to iN2N's hub-and-spoke.

### Timing constraints

- **`draft-serra-mcp-discovery-uri-04` expires 2026-09-25.** If `-01` cites it, either submit before then or
  note the revision explicitly.
- **`draft-zeng-nmrg-mcp-usecases-requirements-00` expires 2026-08-18** — two weeks after the survey. Likely
  to lapse before `-01`.
- **Watch the `agentproto` charter.** Scope was rejected 38–124 and is being rewritten toward *context
  propagation across trust boundaries*, which is **closer to NCFED's contribution** than the original
  session-layer framing. NCFED's fit improves if it lands there.

---

## Addendum (spec 189, issue #343): peer limit semantics

The -00 text left what counts toward BUDGET_EXHAUSTED/RATE_LIMITED, per-peer vs global scope, the over-limit action and counter recovery unspecified. Section "Peer Limits" now specifies them (refuse default, warn, teardown with a persisted restart timer, optional aggregate cap, warning threshold). No wire change. Open for -01: whether a global rate cap and a wire-visible hold-down signal are wanted; both were deliberately left out.

## Seed from the 2026-11-22 two-Border evidence run (H15–H23)

Source: [`evidence/2026-11-ncfed-two-border/README.md`](evidence/2026-11-ncfed-two-border/README.md), live tests of
`-00` between two Borders at implementation `a5e7c3a3`. Section numbers below refer to that README. Its §5 items 8–11
(broad inventory advertisement, access-class naming, endpoint announcement overriding the dialled address, and a BGP
NOTIFICATION nuance) are documentation-only and are not repeated here.

### H15. Pinned key change is flagged by a log line only — *OPEN*
- **Reality (T3b, §5.1):** a changed pinned key is correctly refused and not re-pinned, but `notify_key_change` only
  writes a WARNING line. Nothing goes to audit, posture or `rotation_event`, and no operator notification is sent.
- **Plan:** write an audit/alert record and surface it in posture, or relax the draft (§6.2 "flagged to the operator",
  §14.3 "security alert") to "logged".

### H16. `-32002 APPROVAL_PENDING` is never sent for `tools/call` — *OPEN*
- **Reality (T4e, §5.2):** the callee holds the call for up to 900 s; the caller times out at 125 s with `-32006`
  while the approval is still pending. The approval can still be granted and then executes with no caller waiting.
- **Plan:** return `-32002` immediately with a poll/retry path, or bound the approval window by the caller deadline.
  The draft must state which.

### H17. Error-code semantics drift (`-32003`, `-32007`) — *OPEN*
- **Reality (§5.3–5.4):** `-32003 APPROVAL_EXPIRED` is also returned for an explicit operator deny. `-32007 SEVERED` is
  returned for "peer_unreachable: awaiting inbound (higher AS)" when nothing was severed.
- **Plan:** add distinct codes (approval denied; peer unreachable) or widen the draft's definitions.

### H18. No operator surface for domain-verified trust — *OPEN*
- **Reality (T1, T3c, §5.5):** setting `trust_model=domain-verified` and `claw_domain` needed direct SQL on the test
  Border, although the draft describes it as an operator choice.
- **Plan:** add an HTTP/CLI operation, with audit, to set and clear the trust model and `claw_domain` per peer.

### H19. TLS-layer refusal is not recorded in `verify_state` — *OPEN*
- **Reality (T3c, §5.6):** a SAN/hostname mismatch fails inside the TLS handshake and bypasses `_cert_refuse`. The peer
  still shows `verified` while every dial fails, and a redial drops the existing good channel first.
- **Plan:** map TLS verification failures onto the same refusal path, and keep the good channel until the new one is
  admitted.

### H20. An unauthenticated handshake creates a peer row — *FIXED (branch `fix/ncfed-stranger-peer-row`)*
- **Reality (§5.7):** `accept_channel` → `upsert_peer` runs before the consent check, so a stranger's handshake adds a
  `federation_peer` row. Nothing is sent back, but the table grows from unauthenticated input.
- **Fix:** `accept_channel` now checks local consent first and calls `upsert_peer` only for a consented peer. A
  stranger is closed with nothing persisted. `local_consent()` still creates the row when the operator consents, so
  consenting to a new peer works as before.
- **Test:** `tests/n2n/test_en2n_auth_baseline_060.py::test_unconsented_stranger_leaves_no_peer_row`.
- **Existing rows:** rows already created this way (e.g. production's `as65123-203.0.113.99`, `not_federated`) are not
  removed by the fix. They hold no consent or grants; an operator can delete them.

### H21. Stale gateway token shadows the config token — *FIXED (branch `fix/gateway-ws-token-reresolve`)*
- **Reality (T6b, §10):** `OPENCLAW_GATEWAY_TOKEN` in `~/.openclaw/.env` overrode `gateway.auth.token`. The daemon's
  cached gateway client kept presenting the rejected token for the life of the process, and the failure surfaced only
  as one failed delegated task with a generic handshake error.
- **Fix (§11):** `gateway_ws.py` logs the token source and a sha256 fingerprint (never the value). After an auth
  rejection it marks the cached client stale and resolves the token again, so a corrected config needs no daemon
  restart. Tests: `mcp-servers/protocol-mcp/tests/test_gateway_ws_token_reresolve.py`. Deployed on the production
  Border on 2026-11-22.

### H22. Skill load cap silently drops delegated skills — *RESOLVED on production (main agent and all iN2N members)*
- **Reality (T6b, §10–§11):** OpenClaw loads at most 200 skills per source, sorted by name. With 249 workspace skills,
  `subnet-calculator` was never loaded, so a correctly authorised delegated task returned "skill not available".
- **Fix (§11):** the spec-188 policy (`config/skill-limits.json`) was applied to the production main agent. The
  second re-run then passed end to end.
- **Members (§11, change 10):** the same policy was applied to all five iN2N member configs on 2026-11-22, with
  backups. viz no longer depends on its partial override of 300 for three scoped skills.
- **Remaining hardening (optional):** a startup check that fails loudly when a granted or scoped skill is not loaded,
  so a future cap breach is not silent.

### H23. Border leaves a completed member task at `submitted` — *OPEN (pull-only status, not H13)*
- **Reality (§13.2):** production delegated task `1a5ec57f-18d6-4e74-9421-de66259ab806` (skill
  `threejs-network-viz`) to the `byrns-risk/viz` member at 2026-11-22T23:22:43Z. The member completed it at 23:23:26Z
  and stored the result (the tool itself failed, a separate issue). The Border's `delegated_task` row stayed
  `submitted`, with no `updated_at` change and no `result_ref`.
- **Log check (read-only, 23:20–23:40Z):** the channel did not bounce. Neither the mesh daemon nor the viz member logged
  a disconnect, reconnect or error, and the member runs with `--idle-exit 0`. So this is not the H13 trigger.
- **Cause:** completion is pull-only. The executor never announces a terminal state (`tasks.py` has no completion
  notice), and the Border writes its outbound row only in `poll_member_task`, which runs only when something calls
  `GET /n2n/tasks/{id}` (n2n-mcp or the operator API) or the operator path in `operator.py`. Nothing polled this task,
  so the row stays `submitted` indefinitely. That GET path is not logged, so "nothing polled" is inferred from the row.
- **Plan:** the Border reconciles its own non-terminal outbound iN2N tasks: on member channel (re-)establish and
  periodically for rows past a deadline, using `n2n/tasks/result`. Optionally the executor also announces terminal
  states (H13's re-announce). The draft should state whether a submitter must poll or may expect a completion notice.
