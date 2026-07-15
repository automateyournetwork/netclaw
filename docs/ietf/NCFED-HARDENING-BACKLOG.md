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
