# Tasks: NCFED/N2N Certificate-Based Channel Security ("Claw Certification")

**Input**: Design documents from `/specs/060-claw-cert-security/`
**Prerequisites**: plan.md, spec.md (clarified 2026-07-15), research.md (R1–R10), data-model.md, contracts/wire-protocol.md, contracts/operator-api.md, quickstart.md

**Tests**: Included — the spec defines an Independent Test per story and measurable SCs (SC-001/002/004/009/010/011), and Constitution VIII requires verification; integration tests reuse the 056/057 two-claw loopback pattern.

**Organization**: Grouped by user story (priority order from spec.md: US1 → US2 → US5 → US6 → US3 → US4), each independently testable.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

**Purpose**: Constants, key-material layout, dependency fetch, config surface

- [x] T001 Add 060 constants to `mcp-servers/protocol-mcp/bgp/constants.py`: `TLS_FIRST_BYTE = 0x16`, `NCFED_ALPN = "ncfed/1"`, `TLS_EXPORTER_LABEL = "EXPORTER-ncfed-claw-auth"`, default lifetimes/threshold env parsing (`N2N_CERT_RENEW_FRACTION=0.667`, `N2N_CERT_MEMBER_DAYS=90`, `N2N_CERT_CA_DAYS=730`), JSON-RPC error codes `-32060 LEGACY_REFUSED` / `-32061 CERT_VERIFY_FAILED` (contracts/wire-protocol.md §1–3)
- [x] T002 [P] Create keys-directory helper in `mcp-servers/protocol-mcp/bgp/federation/certs.py` (module skeleton): `keys_dir()` returning `~/.openclaw/n2n/keys/` with `host/`, `acme/`, `risk-ca/`, `members/` subdirs created `0700`, files written `0600` (data-model.md §6)
- [x] T003 [P] Add lego fetch helper `scripts/lib/fetch-lego.sh`: download the pinned lego release for the host arch into `~/.openclaw/n2n/bin/lego`, verify SHA-256 checksum, idempotent (research.md R2)
- [x] T004 [P] Document all new environment variables in `.env.example`: `N2N_CLAW_DOMAIN`, `N2N_ACME_DNS_PROVIDER`, `N2N_ACME_EMAIL`, `GODADDY_API_KEY`/`GODADDY_API_SECRET`, `CLOUDFLARE_DNS_API_TOKEN`, `ACME_DNS_API_BASE`/`ACME_DNS_STORAGE_PATH`, `N2N_CERT_RENEW_FRACTION`, `N2N_CERT_MEMBER_DAYS`, `N2N_CERT_CA_DAYS` — names + descriptions only (data-model.md §7; Constitution XIII)

---

## Phase 2: Foundational (blocking all user stories)

**Purpose**: X.509 primitives, schema migration, audit event kinds — every story builds on these

- [x] T005 Implement X.509 primitives in `mcp-servers/protocol-mcp/bgp/federation/certs.py`: `generate_keypair()` (ECDSA P-256), `create_self_signed(cn, days)` (host-pinned model), `create_risk_ca(risk_name, days)` (CA basicConstraints pathlen=0), `issue_cert(ca_key, ca_cert, subject_cn, san, days)` (member/hub issuance), `fingerprint(cert)` (SHA-256 over DER hex), `verify_chain(leaf_pem, anchor_pem, expected_san)`, `load_or_create_host_credential()` — using the existing `cryptography` dependency (research.md R5)
- [x] T006 Schema migration v3 in `mcp-servers/protocol-mcp/bgp/federation/manager.py`: additive, transactional — new tables `credential`, `rotation_event`, `auth_failure_bucket`; new `federation_peer` columns `trust_model`/`claw_domain`/`pinned_fp`/`pinned_fp_next`/`peer_cred_fp`/`peer_cred_not_after`/`peer_renew_state`/`verify_state`; new `member` columns `credential_state`/`cred_fp`/`cred_not_after`/`renew_state`/`enroll_fingerprint_logged`; backfill `trust_model='legacy'` for existing peers and `credential_state='legacy'` for existing members (data-model.md §1–5, FR-020)
- [x] T007 [P] Add rotation/refusal event kinds to `mcp-servers/protocol-mcp/bgp/federation/audit.py` (`renewed`, `rotated`, `overlap-opened`, `overlap-closed`, `renewal-failed`, `emergency-rekey`, `verify-refused`) writing both `rotation_event` rows and the existing audit+GAIT trail (FR-016; Constitution IV)
- [x] T008 [P] Unit tests for certs.py primitives in `tests/protocol/test_certs.py`: self-signed round-trip, CA issue + chain verify, SAN mismatch fails, fingerprint stability, expiry math for `renew_after` at 2/3 lifetime

**Checkpoint**: `pytest tests/protocol/test_certs.py` green; migration applies cleanly to a copy of a live `federation.db` with row counts unchanged.

---

## Phase 3: User Story 1 — Authenticated, Encrypted External Federation (P1) 🎯 MVP

**Goal**: eN2N channels are TLS on the shared port; peers verified domain-verified or pinned; cleartext refused in production with actionable reason.

**Independent Test**: Two-claw loopback federation in each trust model; wire capture shows TLS; wrong-key impersonation refused + audited (SC-001/002).

- [x] T009 [US1] Listener discrimination in `mcp-servers/protocol-mcp/bgp-daemon-v2.py`: peek first byte — `0x16` → server-side TLS wrap with active host credential then existing `NCFED` magic path inside TLS; `0xFF` → BGP unchanged; `N` → legacy path gated on `N2N_RISK_MODE != production`, else send `-32060` refusal frame (contracts/wire-protocol.md §1/§3, FR-001/001a/021, research.md R4)
- [x] T010 [US1] TLS dial path in `mcp-servers/protocol-mcp/bgp/federation/channel.py` `open_channel`: client SSLContext per trust model — domain-verified: `create_default_context()` + `check_hostname` against `claw_domain` (server_hostname=claw_domain via SNI even though TCP target is the tunnel host); pinned: `CERT_NONE` + post-handshake fingerprint check against `pinned_fp`/`pinned_fp_next`; offer ALPN `ncfed/1` (research.md R1/R4)
- [x] T011 [US1] NCFED hello v2 in `mcp-servers/protocol-mcp/bgp/federation/channel.py`: listener nonce in hello response; new `n2n/hello.auth` handler verifying dialer cert (WebPKI+SAN or pin) and ECDSA signature over `nonce || tls_exporter` (`SSLObject.export_keying_material`, label from T001); dialer-side signing with host credential; TOFU pin-on-first-contact for consented pinned peers; all failures → `-32061` + `verify-refused` audit (contracts/wire-protocol.md §2, FR-002/005/006/007)
- [x] T012 [US1] Peer trust records in `mcp-servers/protocol-mcp/bgp/federation/service.py` + `manager.py`: persist/read `trust_model`, `claw_domain` (verified attribute — identity key unchanged per FR-003a), `verify_state`; extend `/n2n/connect` in `bgp-daemon-v2.py` with optional `claw_domain`; add a **local-only** trust-model change surface (`POST /n2n/config` accepts `{peer, trust_model, claw_domain?}`) that the remote side can never trigger (FR-007) and that provides the domain-loss → pinned fallback path (spec Edge Case "Domain loss"); reject any remote-initiated downgrade (contracts/operator-api.md)
- [x] T013 [US1] ACME issuance in new `mcp-servers/protocol-mcp/bgp/federation/acme.py`: drive `~/.openclaw/n2n/bin/lego` (`run` for first issuance) with `N2N_ACME_DNS_PROVIDER` env passthrough incl. `acme-dns` delegation path; parse lego cert tree into a `credential` row; expose `ensure_domain_credential()` used at daemon startup when `N2N_CLAW_DOMAIN` set (research.md R2/R3, FR-004/004a)
- [x] T014 [P] [US1] Unit tests in `tests/protocol/test_discrimination.py`: first-byte routing (0x16/0xFF/N/other), production vs lab legacy gating, refusal frame content
- [x] T015 [US1] Integration test in `tests/protocol/test_tls_federation.py`: two in-process claws federate loopback in pinned model (TOFU → reconnect → pin match), including the both-sides-pinned first-contact sequence completing in one exchange with neither side seeing a "changed key" (spec Edge Case); wrong-key impersonation refused (SC-001); a remote-initiated trust-model downgrade attempt refused (FR-007); domain-verified path with a test CA injected via `SSL_CERT_FILE` (SC-002 asserted via socket-level TLS check)

**Checkpoint**: US1 independently shippable — pinned-model secured federation works claw-to-claw with no domain required.

---

## Phase 4: User Story 2 — Hub Attestation for Members (P2)

**Goal**: Border is the risk CA; members verify the hub's chain at dial; legacy members keep working flagged.

**Independent Test**: Enroll member → mutual verification recorded; non-CA hub credential → member refuses (auditable); pre-060 member still connects, flagged `legacy`.

- [x] T016 [US2] Risk CA lifecycle in `mcp-servers/protocol-mcp/bgp/federation/risk.py`: `ensure_risk_ca()` (create on first run, `credential` row); replace `_generate_self_signed` with `certs.issue_cert` at enrollment (member cert + key delivered in enrollment reply with `risk_ca_pem` + `enroll_fingerprint`); issue hub credential; keep pin table authoritative for `credential_state='legacy'` members (research.md R5, FR-008/009/011)
- [x] T017 [US2] Hub-side presentation in `mcp-servers/protocol-mcp/bgp/federation/internal_channel.py`: `build_ssl_contexts` server context loads hub credential + risk-CA chain; add member-side verify mode `build_member_client_context(risk_ca_path)` with chain verification and app-layer SAN check == risk name (FR-010)
- [x] T018 [US2] Member-side anchor handling in `scripts/in2n-member.py`: store `risk_ca_pem` + issued credential from enrollment reply under the member's `N2N_MEMBER_BASE`; verify hub chain at every dial when anchor present; abort + log on failure; legacy members (no anchor) keep pin behavior (FR-010/011)
- [x] T019 [P] [US2] Integration test in `tests/protocol/test_hub_attestation.py`: enroll under CA → mutual verify recorded; imposter hub (self-signed non-CA cert) → member aborts dial; legacy member connects and is flagged

**Checkpoint**: risk-internal mutual authentication complete; unpatched members unaffected.

---

## Phase 5: User Story 5 — Trust Hardening from the 059 Review (P2)

**Goal**: Quarantine-DoS closed; enrollment fingerprints logged both sides.

**Independent Test**: Foreign-source failing auth spam leaves member standing untouched (SC-010); enrollment logs matching fingerprints both ends, mismatch hard-aborts.

- [x] T020 [US5] Per-source failed-auth accounting in `mcp-servers/protocol-mcp/bgp/federation/service.py` + `risk.py`: token-bucket per source via `auth_failure_bucket` (default 5/min then drop+audit); member quarantine counters increment only from the member's own authenticated origin (data-model.md §5, FR-022)
- [x] T021 [US5] Enrollment fingerprint logging in `mcp-servers/protocol-mcp/bgp/federation/risk.py` + `scripts/in2n-member.py`: Border records + audits `enroll_fingerprint`; member recomputes over received cert DER, prints it, confirms in enrollment ack; mismatch → hard abort with full state rollback, `enroll_fingerprint_logged=1` on success; no interactive pause (FR-023, Clarification Q5)
- [x] T022 [P] [US5] Integration test in `tests/protocol/test_trust_hardening.py`: 50 failing auths from a foreign source → member state unchanged + bucket audit rows (SC-010); tampered enrollment reply → abort with no member row remaining

**Checkpoint**: 059 §seccons-tofu hazards closed.

---

## Phase 6: User Story 6 — Install, Patch, and Heartbeat Coverage (P2)

**Goal**: Fresh installs come up certified; existing claws upgrade with one idempotent command; heartbeats carry credential health.

**Independent Test**: Fresh install → credentialed + enforcing; patch on a live-state claw → zero lost rows, enforcement on, unpatched peers listed (SC-009); heartbeat reflects a mid-session rotation (SC-011).

- [x] T023 [US6] Heartbeat credential payload in `mcp-servers/protocol-mcp/bgp/federation/channel.py` (`_heartbeat_loop` + handler) and `internal_channel.py`: add `cred: {fp, not_after, renew_state}` both directions; persist to `peer_cred_*` / member `cred_*` columns; state the inherited heartbeat interval as a named constant so SC-011 ("staleness ≤ one heartbeat interval") is measurable; liveness logic untouched (FR-024/026, SC-011)
- [x] T024 [US6] Patch installer `scripts/patch-claw-certs.sh`: git-pull → stop services → transactional schema migration (T006) → `load_or_create_host_credential()` + `ensure_risk_ca()` → re-issue service-managed member certs (cold members lazily at next contact) → optional `--domain`/`--dns-provider` wizard calling `acme.ensure_domain_credential()` → restart services in the 057 order (gateway → mesh → members) → print posture incl. refused-pending-patch peers → assert before/after state counts equal; exit codes per contracts/operator-api.md; idempotent (FR-028/029, research.md R9)
- [x] T025 [P] [US6] Fresh-install component: add `"claw-certs|Federation|Claw Certification|TLS credentials, risk CA, ACME domain identity + rotation for N2N"` to `scripts/lib/catalog.sh` and `component_install_claw_certs()` to `scripts/lib/install-steps.sh` (fetch-lego, keygen, optional domain wizard, .env writes); run `scripts/verify-catalog-coverage.py` (FR-027; Constitution XI)
- [x] T026 [P] [US6] Patch test in `tests/protocol/test_patch_upgrade.py`: seed a federation.db copy with peers/members/grants → run migration + credential generation path → assert row counts identical, `trust_model='legacy'` backfill, re-run converges (idempotency)

**Checkpoint**: the whole mesh (Nick, Byrn, AB) has a one-command adoption path.

---

## Phase 7: User Story 3 — Automatic Rotation Before Expiry (P3)

**Goal**: Everything renews automatically at 2/3 lifetime with dual-trust overlap; failures escalate; emergency re-key exists.

**Independent Test**: Short-lifetime lab risk rotates hub/member/pinned credentials with zero channel drops (SC-004); killed renewal escalates amber→red.

- [x] T027 [US3] Rotation state machine in `mcp-servers/protocol-mcp/bgp/federation/certs.py` + `service.py`: `credential.state` transitions (active→overlap→retired, active→failed), successor issuance, dual-acceptance (`pinned_fp OR pinned_fp_next`, old-CA OR new-CA) with bounded overlap window, `n2n/cert/update` notify to pinned peers and members over live channels (FR-013, research.md R6)
- [x] T028 [US3] Renewal scheduler task in `mcp-servers/protocol-mcp/bgp/federation/acme.py` + startup hook in `bgp-daemon-v2.py`: hourly asyncio check of all `credential` rows past `renew_after` — ACME rows via `lego renew` (ARI honored), risk/host rows via local re-issue; backoff retry on failure + `renewal-failed` events + amber/red escalation fields (FR-012/014)
- [x] T029 [US3] Operator rotation surface: `/n2n/certs/rotate` (incl. `emergency: true` immediate-distrust path) and `/n2n/certs/renew` HTTP routes in `bgp-daemon-v2.py`; `n2n_cert_rotate` tool in `mcp-servers/n2n-mcp/` (FR-015; contracts/operator-api.md)
- [x] T030 [P] [US3] Integration test in `tests/protocol/test_rotation.py`: 2-minute-lifetime credentials rotate with a live loopback channel open — zero drops, overlap events emitted, offline-peer reconnect after overlap → re-verification path flagged (spec US3 scenario 4)

**Checkpoint**: no expiry outages possible without ≥14 days of visible warning.

---

## Phase 8: User Story 4 — Certificate Visibility in the HUD (P4)

**Goal**: Full trust state inspectable at a glance; posture carries channel-security counts.

**Independent Test**: HUD shows trust model/fingerprint/expiry/renewal per peer+member with amber/red thresholds; rotation + verify-refused events appear in posture/audit.

- [x] T031 [US4] `GET /n2n/certs` route in `bgp-daemon-v2.py` aggregating `credential` + peer/member trust columns per contracts/operator-api.md; extend `GET /n2n/posture` with `channel_security` block incl. `clock_suspect` (host clock plausibility check) (FR-017/019)
- [x] T032 [P] [US4] `n2n_certs` tool in `mcp-servers/n2n-mcp/` rendering trust model, identity, fingerprint, days remaining, amber/red flags (contracts/operator-api.md)
- [x] T033 [P] [US4] HUD certificate panel in `ui/netclaw-visual/`: per-row trust badges, truncated click-to-copy fingerprint, days-remaining with amber `<30` / red `<14`, posture strip counts, rotation/verify-refused event feed (FR-018; Constitution X/XI)

**Checkpoint**: SC-006 — trust facts for any channel in one view, under 10 seconds.

---

## Phase 9: Polish & Cross-Cutting

- [x] T034 [P] Update `docs/N2N-RISK.md`: trust models, enrollment fingerprint step, heartbeat credential health, rotation behavior — reference deployment `netclaw.automateyournetwork.ca` end to end (FR-030)
- [x] T035 [P] Update `docs/N2N-RISK-MIGRATION-FOR-PEERS.md`: patch instructions for existing peers (quickstart.md §A/B lifted), refusal-message explanation, GoDaddy + delegation + Cloudflare paths (FR-030)
- [x] T036 [P] Update `README.md` federation sections + `TOOLS.md` + `SOUL.md` capability summary; update `scripts/peering-setup.sh` for the certified flow (FR-030; Constitution XI/XII)
- [x] T037 [P] Add "superseded by 060 for channel trust" header notes to `specs/052-n2n-federation/spec.md`, `specs/053-n2n-ergonomics/spec.md`, `specs/056-in2n-internal-federation/spec.md`, `specs/057-in2n-production-enforcement/spec.md` (FR-031)
- [x] T038 Walk quickstart.md against the live reference deployment (`netclaw.automateyournetwork.ca`, GoDaddy — direct API or delegation per account access) and correct any step that fails first-attempt (SC-003/008)
- [x] T039 Run the Artifact Coherence Checklist (constitution §Checklist) — catalog coverage script green, HUD updated, .env.example complete, existing skills verified unbroken (Constitution XI/XV)
- [x] T040 Draft WordPress milestone blog post (Constitution XVII) — present to John for review before publishing

---

## Dependencies

```text
Phase 1 (T001–T004) → Phase 2 (T005–T008) → all user stories
US1 (T009–T015): needs Phase 2 only — MVP
US2 (T016–T019): needs Phase 2; independent of US1 (iN2N transport is separate)
US5 (T020–T022): needs US2's enrollment path (T016) for fingerprint logging; quarantine part (T020) needs Phase 2 only
US6 (T023–T026): T023 needs US1 channel code; T024 needs T005/T006/T016 (+T013 for --domain); T025 independent
US3 (T027–T030): needs US1 (peers) + US2 (members) credentials to rotate
US4 (T031–T033): needs data from US1/US2/US3 (render-only)
Phase 9: after all stories (T038 needs US1+US6 complete)
```

## Parallel Execution Examples

- Phase 1: T002, T003, T004 in parallel after T001
- Phase 2: T007, T008 parallel with each other after T005/T006
- After Phase 2: US1 (T009+) and US2 (T016+) can proceed in parallel — different modules (channel.py vs internal_channel.py/risk.py)
- Docs (T034–T037) all parallel

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + US1**: pinned-model TLS federation claw-to-claw — the crypto gap closed with zero external dependencies (no domain, no ACME). Ship, patch two claws (John + Nick), verify SC-001/002 live. Then US2+US5 (risk trust), US6 (mesh-wide adoption), US3 (rotation), US4 (visibility), polish.

**Total**: 40 tasks — Setup 4, Foundational 4, US1 7, US2 4, US5 3, US6 4, US3 4, US4 3, Polish 7.


## Completion notes (2026-07-15)

- **T038 validated on the real domain:** a production Let's Encrypt certificate for
  `netclaw.automateyournetwork.ca` was issued end-to-end via GoDaddy DNS-01 and
  installed under `~/.openclaw/n2n/keys/acme/` (valid to 2026-10-13). Discovered
  and handled GoDaddy's Bearer-PAT vs legacy-sso-key mismatch with an exec hook
  (`scripts/lib/godaddy-acme-hook.sh`) + authoritative-NS propagation resolvers;
  quickstart §B.1 updated to the validated path. Auto-renew via the daemon path
  verified against the live cert.
- **T039 artifact coherence:** README federation section updated; catalog.sh +
  install-steps.sh `claw-certs` component (verify-catalog-coverage.py PASS);
  .env.example variables; HUD channel-security panel; docs (peer guide + new
  N2N-FEDERATION-GUIDE.md); SOUL.md already covers n2n-federation. No new MCP
  server (extends the existing protocol-mcp daemon), so no config/openclaw.json
  change.
- **T040 blog:** milestone post drafted at `docs/blog/2026-07-15-claw-certification.md`
  — awaiting John's review before publishing to WordPress (Constitution XVII).
