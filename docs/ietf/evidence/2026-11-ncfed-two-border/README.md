# NCFED two-Border evidence run — 2026-11-22

Live tests of draft-capobianco-ncfed-00 between two NetClaw Borders. Both Borders ran the same
implementation commit. Every result below has a UTC timestamp, and its raw output is in `raw/`.

| | |
|---|---|
| Draft under test | draft-capobianco-ncfed-00 (published text) |
| Implementation | `a5e7c3a3e07d8c8c4f2f26d22b4bd854dd1ba42e` on both Borders |
| Run window | 2026-11-22 20:42Z – 20:59Z |
| Operator / author | run by Claude Code on behalf of the draft co-author |

## 1. Environment

| | Production Border | Test Border |
|---|---|---|
| Host | `198.51.100.10` (hostname `Netclaw`) | `198.51.100.20` (`netclaw-ncfed-test`, Proxmox VM 127, cloned from template 8000) |
| Identity | `as65099-10.255.255.1` | `as65010-10.255.250.1` |
| Build | `~/netclaw-production-candidate` @ a5e7c3a3 | `git archive` of a5e7c3a3 → `~/netclaw-ncfed-test` (+`COMMIT` file) |
| Python deps | production venv, Python 3.12.3 | `~/ncfed-venv`: production's exact 143-package freeze (cryptography 50.0.2, mcp 2.3.0, fastmcp 4.0.11, websockets 16.1.1) |
| NCFED listener | TCP 1179 (API 127.0.0.1:8179) | TCP 1179 on 0.0.0.0 (API 127.0.0.1:8179) |
| Mode | `N2N_CERT_MODE=enforce` | `N2N_CERT_MODE=enforce`, `N2N_ROLE=border`, `N2N_ENABLED_STACKS=en2n`, `NETCLAW_BGP_PEERS=[]`, `NETCLAW_DRY_RUN=true` |
| TLS server cert | CN/SAN `border.example.com`, SPKI sha256 `540da1ef9b9acdb5…` | self-signed host cert, `9163d6e5a206eebb…` |
| Possession key (`keys/self.crt`) | — | `131fe7117555cc67…` |
| Process | daemon PID 504509 (not restarted) | systemd user unit `netclaw-ncfed-test.service`, PID 33258 |

The test VM's SSH host key (ED25519 `SHA256:W6ICoDnpEsUC0cxchKd8lkgcktNHwFRcu+cDy7AkcOg`) was accepted on first
use through a temporary known_hosts file. This was a VM created minutes earlier for this run.
`qm guest exec` returned nothing, so the fingerprint could not be cross-checked out of band.

Fingerprints are truncated to 16 hex digits throughout. Nonces, private keys, tokens and the public ngrok endpoint are
redacted or were never logged.

LAN addresses and the production Border's DNS name are replaced with documentation values throughout, including
the raw files: production `198.51.100.10`, test VM `198.51.100.20`, Proxmox host `198.51.100.2` (RFC 5737), and the
production TLS name `border.example.com` (RFC 2606). NCFED identities such as `as65099-10.255.255.1` are lab
router IDs, not host addresses, and are kept.

### Tools

- `tools/ncfed_wire_probe.py` is a raw-wire probe (stdlib plus `cryptography`). The repository's
  `scripts/ncfed-conformance-test.py` is not present at a5e7c3a3 and hardcodes 127.0.0.1 and a single identity, so this
  run used an adapted, parameterised version. Subcommands: `discriminate`, `timeouts`, and
  `handshake --hello none|keyless|forged|badsig [--tls12]`.
- `tools/ncfed_probe_mcp.py` is a stdlib stdio MCP server, registered on the test VM only as `ncfed-probe` in
  `~/.openclaw/openclaw.json`. It provides the invocation targets `echo_info` and `approval_info` (read) and
  `touch_marker` (classified as write, but it performs no write). No tool touches the filesystem or the network.
- Each Border's API was called with `curl` against `127.0.0.1:8179` over SSH. Helper: `api METHOD PATH [JSON]`.

## 2. Results summary

| # | Test | Result | Time (UTC) | Raw |
|---|---|---|---|---|
| 1 | Consent gate | **PASS** | 20:45:20 – 20:46:06 | `t1-*.txt`, `prod-change-1-consent.txt` |
| 2 | Port discrimination (test VM port; production cross-check) | **PASS**, with a BGP note | 20:44:16 – 20:45:32 | `t2-*.txt`, `t1-t2-production-log.txt` |
| 3a | Pinned tier: changed key refused | **PASS** | 20:46:37 | `t3-pinned-impersonation.txt` |
| 3b | Pinned tier: changed key *flagged to the operator* | **PARTIAL**: log line only | 20:46:37 | same |
| 3c | Domain-verified tier: SAN ≠ claw_domain refused | **PASS**, with a state-recording gap | 20:47:03 | `t3-domain-verified-negative.txt` |
| 3d | Possession proof: bad signature and keyless peer refused | **PASS** | 20:46:37 | `t3-pinned-impersonation.txt` |
| 4a | Tool invocation default-deny (`NOT_ALLOWLISTED`) | **PASS** | 20:49:44 | `t4-grants.txt` |
| 4b | Read tool succeeds after a per-peer grant | **PASS** | 20:49:52, 20:50:03 | `t4-grants.txt` |
| 4c | Access class: a write-class tool under a read grant is refused | **PASS** | 20:50:03 | `t4-grants.txt` |
| 4d | Approval: approve → success; deny → `-32003` | **PASS** | 20:50:33 – 20:50:45 | `t4-approval.txt` |
| 4e | `APPROVAL_PENDING (-32002)` on the wire | **NOT OBSERVED** (the implementation holds the call) | 20:50:55 – 20:54:20 | `t4-approval.txt` |
| 4f | `RATE_LIMITED (-32005)` | **PASS** | 20:54:36 | `t4-limits.txt` |
| 4g | `BUDGET_EXHAUSTED (-32004)` | **PASS** | 20:54:37 | `t4-limits.txt` |
| 5 | Revocation: sever, refused redial, recovery only after re-consent | **PASS** | 20:54:59 – 20:55:34 | `t5-revocation.txt` |
| 6a | Delegation default-deny (skill task) | **PASS** | 20:55:47 | `t6-delegation.txt` |
| 6b | Delegated task end to end | **PARTIAL** in the run: protocol path works, but production's agent gateway refused execution. **PASS** at the NCFED layer on re-run after the gateway fix (§10), though the skill was not loaded on production. **PASS end to end** on the second re-run after the skill limit raise (§11): the skill ran and returned the correct answer | 20:56:15 – 20:58:47; re-runs 21:20:35 – 21:21:30 and 22:03:35 – 22:04:21 | `t6-delegation-positive.txt`, `t6-rerun-after-gateway-fix.txt`, `t6-rerun-after-skill-limits.txt` |

## 3. Tests, commands and redacted outputs

### Test 2 — §4 port discrimination (test VM port, then production cross-check)

```
# from production → test VM
python3 /tmp/ncfed_wire_probe.py discriminate 198.51.100.20 1179
python3 /tmp/ncfed_wire_probe.py timeouts     198.51.100.20 1179
# from the test VM → production (no 0xFF probe against production BGP)
python3 /tmp/ncfed_wire_probe.py discriminate 198.51.100.10 1179 --no-bgp
```

| Input | Test VM (20:44:16Z) | Production (20:45:32Z) |
|---|---|---|
| `0x00` | 0 bytes, closed | 0 bytes, closed (log: "Unknown protocol byte") |
| TLS ClientHello `0x16…` | 0 bytes, closed | 0 bytes, closed |
| `NXXXX` | 0 bytes, closed | 0 bytes, closed (log: "Invalid N-magic") |
| `NCTUX` (near miss) | 0 bytes, closed | 0 bytes, closed |
| `0xFF`×16 + KEEPALIVE | handed to BGP, then closed silently (see note) | not run |
| Silence | closed after **30.0 s** | — |
| `N` then silence | closed after **10.0 s** | — |

The probe's own heuristic marked `0xFF` as FAIL, because it expected a BGP NOTIFICATION. The daemon log
shows the octet *was* replayed into the BGP parser: `expected OPEN (1), got type 4`. A follow-up full BGP OPEN
from AS65020 at 20:44:30Z received OPEN plus KEEPALIVE, and the FSM moved OpenSent→OpenConfirm. §4 dispatch is therefore
confirmed. The BGP engine sends **no NOTIFICATION** for an FSM error before OPEN; RFC 4271 §6.6 expects one. This
is BGP-engine behaviour, not an NCFED claim.

### Test 1 — consent gate

1. Before consent, a raw handshake to production claiming `as65010-10.255.250.1`
   (`handshake 198.51.100.10 1179 65010 10.255.250.1`) got **0 reply bytes** and no nonce. Production log:
   `NCFED from as65010-10.255.250.1 but no local consent — closing (FR-003)`. The symmetric probe to the test VM also got 0 bytes.
2. The test VM's daemon dialled production through `/n2n/connect` and stayed in `consent_pending_remote`. Its log shows
   `0 bytes read on a total of 5 expected bytes`.
3. **PRODUCTION CHANGE 1** (20:45:51Z): `POST /n2n/consent {"as":65010,"router_id":"10.255.250.1","display_name":"ncfed-test-vm (VM 127, safe to destroy)"}`.
4. After consent (20:46:06Z), the same raw handshake got the 13-octet NCFED reply (acceptor `as65099-10.255.255.1`),
   then in-place TLS **TLSv1.3 TLS_AES_256_GCM_SHA384**, then a 32-octet nonce. A client capped at TLS 1.2 was refused
   (production log `UNSUPPORTED_PROTOCOL`). The daemon redial brought both sides to `federated`, with the channel up and
   inventory exchanged.

### Test 3 — admission tiers

Before the test, the test VM operator set production's trust to `domain-verified` with `claw_domain=border.example.com`.
**No HTTP or CLI surface exists for this**, so it was done with direct SQL on the test VM's `federation.db`. The result was:

- Production's view of the test VM: `pinned`, `verified`, pin `131fe7117555cc67…`, which equals the test VM's `self.crt`.
- The test VM's view of production: `domain-verified`, `verified`.

Possession-tier negatives ran from the test VM against production while the real channel stayed up (20:46:37Z):

| Probe `--hello` | Production reply | Production log |
|---|---|---|
| `forged` (fresh key, valid signature, claims the pinned identity) | `-32010 pinned key mismatch` | `eN2N ALERT: pinned key changed … rejected` |
| `badsig` (signature from a different key) | `-32010 possession proof failed` | — |
| `keyless` | `-32010 peer requires certificate-secured federation…` | — |

After each probe the real channel was still up and the pin was unchanged; no silent re-pin occurred. The flag
appears **only as a log line**. Nothing was written to audit, posture or rotation-event records, and
`approval_notifier` is `None`, so no operator notification fires.

Domain-verified negative (test VM, 20:47:03Z): `claw_domain` was set to `wrong-domain.example.net` and the test VM redialled.
The dial was refused with `CERTIFICATE_VERIFY_FAILED: Hostname mismatch`, and the channel went to `reconnecting`. However,
`verify_state` stayed `verified`, because the TLS-layer failure bypasses `_cert_refuse`. The redial also tore down
the healthy channel before the new dial failed. The setting was restored at 20:47:08Z and the channel came back.

### Test 4 — per-peer tool grants

All grants, classifications and limits were set **on the test VM** (the callee). Production only invoked
`POST /n2n/invoke {"peer":"as65010-10.255.250.1","target_name":"ncfed-probe/<tool>"}`.

| Step | Callee config | Caller result |
|---|---|---|
| 4a 20:49:44Z | no grant | `-32001 tool 'ncfed-probe/echo_info' not allowlisted` (callee audit `not_allowlisted/denied`) |
| 4b 20:49:51Z | classify `echo_info`=read; `POST /n2n/grants {peer, tool, echo_info, access_class:"read"}` | success, `trust: remote-untrusted`, result from host `netclaw-ncfed-test` |
| 4c 20:50:03Z | `touch_marker` classified write, granted read | `-32001` (callee audit `access_class_denied`) |
| 4c' 20:50:14Z | `approval_info` granted read, **unclassified** | `-32001` (`access_class_denied`): unclassified tools default to write; MCP `readOnlyHint` is not used automatically |
| 4d 20:50:33Z | `approval_info` classified read, grant `requires_approval:true` | call held; the callee listed pending approval id 1; operator **approve** → success |
| 4d 20:50:39Z | same | operator **deny** → `-32003 approval not granted` |
| 4e 20:52:15Z | same; nobody resolves | after **125 s** the caller got `-32006 n2n/tools/call timed out; operation outcome may be unknown`. The callee approval was still `pending` with expiry at +15 min |
| 4f 20:54:35Z | `POST /n2n/config {peer, rate_per_min:2, limit_action:"refuse", reset_limits:true}` | calls 1–2 succeed; call 3 → `-32005 per-minute rate limit exceeded` |
| 4g 20:54:37Z | `{rate_per_min:null, daily_requests:2, reset_limits:true}` | calls 1–2 succeed (audit also logs a `limit_warning` at the 0.8 threshold); call 3 → `-32004 daily budget exhausted` |
| restore 20:54:37Z | all overrides set to `null`; `reset_limits`, `clear_hold_down` | three calls succeed |

Approval timing: the caller-side timeout is `N2N_TOOL_TIMEOUT_S` (120) + 5 s, and the callee's approval window is
`N2N_APPROVAL_WINDOW_S` (900 s). In one run (20:50:55Z), the operator approved after the local HTTP client had already
given up at 60 s. The tool still executed, and the result reached the production daemon at 20:51:56Z. In the 4e run, an
operator who approved after 125 s would cause execution with no caller waiting. The orphaned request was denied as
cleanup.

### Test 5 — revocation

1. 20:54:59Z, test VM: `POST /n2n/kill {"peer":"as65099-10.255.255.1"}` → `severed:true`. Local consent was revoked,
   cached inventory purged, the channel closed and the state set to `severed`. No sever message is sent (§13 design).
2. 20:55:01Z, production `invoke` → `-32007 peer_unreachable: awaiting inbound (higher AS)`. Production's own view
   stays `federated`, and its consent rows are unchanged; it only sees the channel close.
3. 20:55:01Z, a raw handshake to the test VM claiming production's identity got **0 bytes**. Test VM log:
   `NCFED from as65099-10.255.255.1 but no local consent — closing (FR-003)`.
4. 20:55:23Z, test VM: `POST /n2n/consent {"as":65099,"router_id":"10.255.255.1","host":"198.51.100.10","port":1179}`.
   It reached `federated` within 10 s, with `domain-verified` and `verified` kept. At 20:55:34Z, the production invoke succeeded again.

Grants on the callee survive a sever and become effective again after re-consent. This is worth stating in the draft if intended.

### Test 6 — task delegation

- 6a, 20:55:47Z: the test VM submitted `POST /n2n/tasks {peer:"as65099-…", target_type:"skill", target_name:"healthcheck"}`
  and got `-32001 skill 'healthcheck' not allowlisted`. Production audit: `not_allowlisted/denied`.
- **PRODUCTION CHANGE 2** (20:56:15Z): `POST /n2n/grants {"peer":"as65010-10.255.250.1","target_type":"skill","target_name":"subnet-calculator","requires_approval":true}` → grant 61.
- 6b: the test VM submitted a subnet-calculator task for `192.0.2.77/27` and got task `780b5128…`, `submitted`.
  - Production listed a pending approval for that skill, and the operator approved it at 20:56:24Z.
  - Production's task worker then failed at its own OpenClaw gateway:
    `gateway connect handshake failed … AUTH_TOKEN_MISMATCH`.
  - The test VM's polling (`n2n/tasks/result` every ~10 s) reports `outcome_unknown, may_have_executed: true`.
- **PRODUCTION CHANGE 2 reverted** (20:58:47Z): `DELETE /n2n/grants/61`. The same submit then got `-32001`.

So the NCFED parts all worked end to end: submit, authorize, hold for approval, run the async task and poll the
result. The skill itself never ran, because **production's federation daemon cannot authenticate to its local OpenClaw
gateway**. That is a pre-existing production configuration fault, independent of this run, and was not changed here
(credential change). The reverse direction could not run either: the test VM has no agent gateway.

This gateway fault was fixed after the run, and 6b was re-run; see [§10](#10-follow-up-production-gateway-fix-and-6b-re-run).

## 4. Claims matrix

| Draft claim (§) | Verdict | Evidence |
|---|---|---|
| §4 first octet `0xFF` → BGP with the octet replayed | Confirmed | T2 log + OPEN follow-up |
| §4 `N`+`NCFED` → federation; `N`+other magic → close silently | Confirmed | T2 (`NXXXX`, `NCTUX`) |
| §4 any other first octet (incl. TLS `0x16`) → close silently | Confirmed | T2 |
| §4 30 s first-octet / 10 s magic budgets | Confirmed (30.0 s / 10.0 s) | T2 timeouts |
| §5 acceptor answers with a 13-octet handshake only for a consented identity; otherwise closes before the nonce | Confirmed | T1, T5 |
| §5 deterministic initiator = lower (AS, router-id) | Consistent: production (higher) reports "awaiting inbound (higher AS)" | T5 step 2 |
| §6.1 in-place TLS 1.3 after the handshake; lower versions refused | Confirmed | T1 |
| §6.2 domain-verified: SAN must equal claw_domain | Confirmed (refused on mismatch) | T3c |
| §6.2 pinned: a changed key MUST be refused | Confirmed | T3a |
| §6.2 changed key MUST be *flagged to the operator* | Partially met: one WARNING log line, no alert, audit, posture or notification record | T3b |
| §6.2 MUST NOT silently re-pin | Confirmed | T3a (pin unchanged) |
| §6.3 possession proof over nonce ‖ SHA-256(acceptor cert) | Confirmed (bad signature refused; real peer admitted) | T3d, T1 |
| §6.4 enforcing mode refuses keyless peers | Confirmed | T3d |
| §14.3 fingerprint mismatch surfaced as a security alert | Partially met (log "ALERT" only) | T3b |
| Invocation default-deny until a per-peer grant | Confirmed (tools and skills) | T4a, T6a |
| `-32001 NOT_ALLOWLISTED` | Confirmed | T4a/c, T6a/c |
| `-32002 APPROVAL_PENDING` | Not observed: tools/call holds open; never sent on the wire for tools | T4d/e |
| `-32003 APPROVAL_EXPIRED` | Confirmed for an operator *deny* (message "approval not granted"); expiry not waited for (900 s) | T4d |
| `-32004 BUDGET_EXHAUSTED` | Confirmed | T4g |
| `-32005 RATE_LIMITED` | Confirmed | T4f |
| `-32006 EXECUTION_TIMEOUT` | Confirmed (caller-side, during a held approval) | T4e |
| `-32007 SEVERED` | Observed, but used for "peer_unreachable", not only for a sever | T5 |
| `-32010 NOT_FEDERATED` | Confirmed for admission failures | T3 |
| Sever is local and needs no peer cooperation; redials refused until re-consent | Confirmed | T5 |
| Async task delegation (submit → status/result polling) | Confirmed end to end: the protocol path and agent turn on the first re-run (§10), and the granted skill executing with a correct result on the second re-run (§11) | T6b |
| Task-owner binding (a third identity cannot poll another's task) | Not testable (needs a third federated identity) | — |
| `-32008 GUARDRAIL_BLOCKED` | Not testable (both Borders in `hobby` security mode; DefenseClaw inspection off) | — |

## 5. Spec-versus-implementation differences

1. **Key-change flag is log-only** (§6.2 "flagged to the operator", §14.3 "security alert"). `notify_key_change` writes a
   WARNING line. Nothing goes to audit, posture or `rotation_event`, and no operator notification is sent. Recommend
   writing an audit/alert record, or relaxing the draft wording to "logged".
2. **`-32002 APPROVAL_PENDING` is never sent for tools/call.** The callee holds the request for up to 900 s and the caller
   times out at 125 s with `-32006`, while the approval is still pending and can still be approved. The orphaned
   approval can execute with no caller waiting. Either return `-32002` immediately (with a retry/poll path), or bound
   the approval window by the caller deadline and say so in the draft.
3. `-32003` is returned for an explicit **deny** as well as for expiry. The name `APPROVAL_EXPIRED` reads as expiry only.
4. `-32007` (`SEVERED`) is returned for "peer_unreachable: awaiting inbound (higher AS)" even when the local side never
   severed.
5. **No operator surface for domain-verified trust.** Setting `trust_model=domain-verified` and `claw_domain` needed direct
   SQL. The draft describes it as an operator choice.
6. **TLS-layer refusal is not recorded in `verify_state`.** A SAN/hostname mismatch fails inside the TLS handshake and
   bypasses `_cert_refuse`, so the peer still shows `verified` while every dial fails. A redial also drops the existing
   good channel first.
7. **A stranger's handshake creates a peer row** on the acceptor (`accept_channel` → `upsert_peer`) before consent is
   checked. Nothing is sent, but the table grows from unauthenticated input.
8. **Inventory is advertised broadly on federation.** The test VM received production's full card (252 skills, 27 MCP servers,
   68 knowledge collections) with zero grants. Advertisement is not authorization (T4a/T6a confirm default-deny), but
   operators should know visibility defaults are permissive.
9. **Access-class model.** Unclassified tools are treated as write. MCP `readOnlyHint` is not imported automatically,
   although `POST /n2n/classifications {"server": …}` can import it. The grant API takes `read|read_write`, while the
   classification API takes `read|write`.
10. **Endpoint announcement overrides the dialled address.** Production advertises an ngrok endpoint, so the test VM
    recorded `transport: ngrok` and production's ngrok host as the redial target, although the channel was opened on the LAN.
    Cosmetic for this run.
11. BGP engine: no NOTIFICATION is sent before closing on an FSM error that arrives before OPEN (RFC 4271 nuance; outside NCFED).

## 6. Production change log

Backup taken before any production-affecting step: `~/.local/state/ncfed-two-border-20261122/federation.db.pre-test`
on production (0600, SQLite backup API, `integrity_check` ok, sha256 `f0554c15…a80cac1fc`, 20:43:55Z).

| # | Time (UTC) | Change | Status |
|---|---|---|---|
| 1 | 20:45:51 | `POST /n2n/consent` for `as65010-10.255.250.1` (the test VM only) → consent rows 7/8 and peer row `as65010-…` | **Severed** 23:21:33 at teardown (§13); consent rows 7/8 revoked 23:21:22 |
| 2 | 20:56:15 | Grant 61: skill `subnet-calculator` to `as65010-…`, `requires_approval` | **Revoked** 20:58:47 |
| — | 20:56:24 | Approved production approval id 1 (that task) | consumed; the task failed at the gateway |
| 3 | 21:17:28 | `~/.openclaw/.env` backed up to `.env.bak-gwtoken-20261122T211728Z`; `OPENCLAW_GATEWAY_TOKEN` aligned to `gateway.auth.token` (§10) | **Active** (the fix) |
| 4 | 21:17:42 | `openclaw-gateway.service` restarted (PID 676625 → 833981) | done |
| 5 | 21:20:35 | Grant 62: skill `subnet-calculator` to `as65010-…`, `requires_approval` (6b re-run) | **Revoked** 21:21:30 |
| — | 21:20:45 | Approved production approval id 2 (re-run task) | consumed; task `completed` |
| 6 | 21:58:58 | `bgp/federation/gateway_ws.py` patched in the production working tree (token re-resolve and source logging); backup `gateway_ws.py.bak-reresolve-20261122T215858Z` (§11) | **Active** |
| 7 | 21:59:03 | `netclaw-mesh.service` restarted to load the patch (PID 504509 → 852849) | done |
| 8 | 22:01:00 | `~/.openclaw/openclaw.json` `skills.limits` raised to the spec-188 policy; backup `openclaw.json.bak-skilllimits-20261122T220100Z` (§11) | **Active** (hot-reloaded; gateway PID 833981 unchanged) |
| 9 | 22:03:35 | Grant 63: skill `subnet-calculator` to `as65010-…`, `requires_approval` (second 6b re-run) | **Revoked** 22:04:21 |
| — | 22:03:44 | Approved production approval id 3 (second re-run task) | consumed; task `completed` |
| 10 | 22:54:59 | `skills.limits` raised to the spec-188 policy in all five iN2N member configs (`~/.openclaw-byrns-risk-{cml,guardian-claw,pyats,secops,viz}/openclaw.json`); backups `openclaw.json.bak-skilllimits-20261122T225459Z` beside each (§11) | **Active** (no restart; read by each new per-task agent process) |
| 11 | 2026-11-23 00:57:53 | Deleted the stale, pre-existing peer row `as65123-203.0.113.99` (`not_federated`, transport ngrok, created 2026-07-18; not part of this run); backup `federation.db.pre-delete-as65123-20261123T005753Z` (§13) | **Done** (no restart) |
| 12 | 2026-11-23 01:01:07 | Deleted its 7 leftover `budget_counter` rows (days 2026-11-13, -14, -15, -17, -19, -21, -22; all 0 requests and 0 tokens); backup `federation.db.pre-delete-as65123-budget-20261123T010107Z` (§13) | **Done** (no restart) |
| 13 | 2026-11-23 01:39:09 | H23 reconcile: one `GET /n2n/tasks/1a5ec57f-18d6-4e74-9421-de66259ab806` on the loopback operator API moved the Border's outbound `delegated_task` row from `submitted` to `completed` (result stored); `completed_at` was left empty, a Border bug fixed in upstream PR #376; backup `federation.db.pre-h23-reconcile-20261123T013904Z` (§13.4) | **Done** (no restart) |
| — | 20:44 / 20:49 | `/tmp/ncfed_wire_probe.py`, `/tmp/ncfed_api.sh` copied to production | `/tmp/ncfed_api.sh` removed from both hosts 22:05 (§11); `/tmp/ncfed_wire_probe.py` removed at teardown (§13) |

Automatic side effects on production: audit/GAIT entries for every probe and invoke; `federation_peer`/
`consent_record`/`invocation_grant` rows for as65010; inventory cache for as65010.

Verified unchanged at 20:59Z by a read-only comparison with the backup:

- The retired peers `as65001-4.4.4.4`, `as65007-7.7.7.7` and `as64512-10.0.0.1` are still `severed`, with consent rows 1–6 still revoked at 2026-11-13T03:12:29Z.
- Grants 1–60 are untouched: grant 1 was already revoked on 2026-07-10, and grants 2–60 are still active, as before.
- The daemon was not restarted (PID 504509 throughout).

The HUD, mobile enrollment, BGP config and Stage 8 checks were not touched. John (`as65001-4.4.4.4`) was not re-consented.

## 7. Current state (after teardown, 2026-11-22T23:21Z)

- Test VM: VM 127 has been destroyed (`qm destroy --purge`); its config no longer exists on Proxmox. Template 8000
  (`ubuntu-24-04-cloud`) is present and stopped, unchanged.
- Production: the as65010 peer is `severed`; consent rows 7/8 are revoked; grants 61–63 are revoked; the helper
  scripts are gone from `/tmp`. The deliberate repairs (changes 3–4, 6, 8 and 10) remain active.
- Production federation peers: `as64512`, `as65001`, `as65007` and `as65010` are `severed`; `as65099-10.255.255.1`
  is `not_federated`. The stale `as65123` row was removed (changes 11–12).
- Production's outbound row for the viz task `1a5ec57f…` is `completed` after the H23 reconcile (change 13), but its
  `completed_at` is empty (§13.4).
- Mesh daemon PID 852849 and gateway PID 833981 are unchanged since §11; nothing in §13 needed a restart.

## 8. Teardown and full production revert

```bash
# 1. production — sever the test peer (local kill switch; revokes consent rows 7/8, purges its inventory)
ssh ubuntu@198.51.100.10 'curl -s -X POST -H "Content-Type: application/json" \
  -d "{\"peer\":\"as65010-10.255.250.1\"}" http://127.0.0.1:8179/n2n/kill'
# 2. production — confirm no active grants for as65010 (grants 61, 62 and 63 are already revoked)
ssh ubuntu@198.51.100.10 'curl -s http://127.0.0.1:8179/n2n/grants' | grep -c as65010   # expect 0 (the list omits revoked grants)
# 3. production — remove helper files
ssh ubuntu@198.51.100.10 'rm -f /tmp/ncfed_wire_probe.py /tmp/ncfed_api.sh'
# 4. Proxmox — destroy the test VM (VM 127 only)
ssh root@198.51.100.2 'qm stop 127 && qm destroy 127'
```

The §10 gateway token fix (changes 3–4) and the §11 changes (6, 8 and 10) are deliberate repairs and are not part of
this teardown; their rollbacks are in §10 and §11. Steps 1–4 leave production's federation state functionally identical to before the run. Its `federation.db` keeps a severed
`as65010` peer row plus audit history, in the same way the retired peers remain. For a byte-for-byte revert, restore the backup.
That needs the daemon stopped, and it discards the audit rows from this run:

```bash
# production — ONLY with operator approval; stops the federation daemon briefly
systemctl --user stop netclaw-mesh.service
cp ~/.openclaw/n2n/federation.db ~/.local/state/ncfed-two-border-20261122/federation.db.post-test
cp ~/.local/state/ncfed-two-border-20261122/federation.db.pre-test ~/.openclaw/n2n/federation.db
systemctl --user start netclaw-mesh.service
```

## 9. Limitations

- One test peer and one production peer. Task-owner binding and multi-peer isolation need a third identity.
- The test VM runs `NETCLAW_DRY_RUN=true` with no BGP peers and no OpenClaw gateway, so it cannot execute skills.
- Approval expiry (900 s) and teardown/hold-down limit actions were not exercised.
- Grok Build was not used. Every step needed live production access and credential context, which falls outside
  its sanitized-input rule.

## 10. Follow-up: production gateway fix and 6b re-run

Done after the run on the same day (21:05–21:22Z), at the operator's request. Raw output:
`raw/t6-rerun-after-gateway-fix.txt`. Tokens are identified only by sha256 prefix.

**Root cause of the 6b failure.** Production's daemon authenticates to its local OpenClaw gateway with
`gateway.auth.token` from `~/.openclaw/openclaw.json` (`cf699848aa…`). That value has been unchanged in every config
backup since 2026-10-25. But `~/.openclaw/.env` still set `OPENCLAW_GATEWAY_TOKEN` to an older token (`e8d5d2bcb6…`).
The `.env` file was last written at 2026-11-14 14:07:31Z, ten seconds before the running gateway started.

Evidence:
- The gateway log rejected the daemon with `reason=token_mismatch`.
- A single, operator-approved connect-then-close test with the `.env` token was **accepted**.
- The same mismatch had already hit OpenClaw's own agent clients on 2026-11-14 (03:35–05:37Z) under the previous
  gateway process. So the fault predates this run.

OpenClaw documents that its managed gateway prefers `gateway.auth.token` and flags an `.env` override like this as a
conflict (`gateway.env_token_overrides_config`). Yet the running gateway accepted the `.env` token. Why it was used is
not explained further here.

**Fix applied** (production changes 3 and 4 in the table below):
1. 21:17:28Z: backed up `~/.openclaw/.env` to `~/.openclaw/.env.bak-gwtoken-20261122T211728Z` (0600).
2. Set `OPENCLAW_GATEWAY_TOKEN` in `.env` to the `gateway.auth.token` value. One line changed; no keys added or removed.
3. 21:17:42Z: restarted `openclaw-gateway.service`. The new PID is 833981, and it was ready about 52 s later.
   - The mesh daemon was not restarted (PID 504509 throughout).
4. Verified with the daemon's own client (`gateway_ws.get_gateway_ws_client`):
   - The token `cf699848aa…` was **accepted**. The first two attempts timed out while the gateway was still busy starting.
   - There were no `token_mismatch` rejections after the restart.
   - `openclaw health` was OK.
   - The only processes with a gateway token in their environment held the new value.

Rollback: `cp -p ~/.openclaw/.env.bak-gwtoken-20261122T211728Z ~/.openclaw/.env`, then restart
`openclaw-gateway.service`.

**6b re-run** (21:20–21:22Z):
- **PRODUCTION CHANGE 5** (21:20:35Z): temporary grant 62, the same shape as grant 61.
- The test VM submitted task `fc02d436…`. Production queued approval 2, and the operator approved it at 21:20:45Z.
- The test VM polled `working` ×4, then got `completed` at 21:21:25Z with `usage_available: true` and `tokens_used` 56953.
- **Result:** submit, authorize, approve, the production agent turn through the gateway, and async result retrieval
  now all work end to end. **6b is PASS at the NCFED layer.**
- The agent's answer, though, was `Error: Skill "subnet-calculator" is not available to this agent.`
  - That is a separate production OpenClaw fault, not an NCFED one.
  - Production's workspace holds 249 skills, but OpenClaw loads at most 200 per source
    (`DEFAULT_MAX_SKILLS_LOADED_PER_SOURCE`). It keeps the first 200 by sorted directory name.
  - So `subnet-calculator` and about 49 other skills (mostly S–Z) are never loaded.
  - Fix: raise `skills.limits.maxSkillsLoadedPerSource` (applied later; see §11).
- **PRODUCTION CHANGE 5 reverted** (21:21:30Z): `DELETE /n2n/grants/62`. The same submit then got `-32001`, and
  no approvals were left pending.

**Suggested daemon hardening** (`bgp/federation/gateway_ws.py`):
- On `AUTH_TOKEN_MISMATCH`, drop the cached client so the token is resolved again.
- Log the token source and its fingerprint at startup.
- Today this fault surfaces only as a single failed task with a generic handshake error.
- Implemented and deployed; see §11.

## 11. Follow-up: gateway_ws patch, skill limit raise and second 6b re-run

Done later the same day (21:58–22:05Z), at the operator's request. Raw output:
`raw/t6-rerun-after-skill-limits.txt`. Tokens are identified only by sha256 prefix.

**gateway_ws.py hardening** (production changes 6 and 7):
- Source change: commit `a4cc75d4` on branch `fix/gateway-ws-token-reresolve`, with
  `tests/test_gateway_ws_token_reresolve.py` (6 tests, passing).
- The daemon now logs where its gateway token came from (`env:OPENCLAW_GATEWAY_TOKEN`, `config:<path>` or
  `secretref-env:<VAR>@<path>`) and the token's fingerprint. It never logs the value.
- On an auth rejection (`AUTH_TOKEN_MISMATCH` and similar), the cached client is marked stale. The next call resolves
  the token again, so a corrected config takes effect without a daemon restart. If the token comes from the process
  environment and is unchanged, the log says that a restart is needed.
- Production: the patched file was copied into the working tree of `~/netclaw-production-candidate` (no commit on the
  server). The original was backed up to `gateway_ws.py.bak-reresolve-20261122T215858Z` beside it.
  `netclaw-mesh.service` was restarted at 21:59:03Z (PID 504509 → 852849).
- Verified in the daemon log: `gateway ws token resolved: source=config:~/.openclaw/openclaw.json fp=cf699848aa`,
  then `gateway ws connected`.
- Rollback: copy the backup over `gateway_ws.py`, then restart `netclaw-mesh.service`.

**Skill load limit raise** (production change 8):
- `skills.limits` in `~/.openclaw/openclaw.json` was set from the repository policy `config/skill-limits.json`
  (spec 188), using `scripts/lib/skill_limits.raise_limits`: `maxSkillsLoadedPerSource` 400,
  `maxCandidatesPerRoot` 400, `maxSkillsInPrompt` 400, `maxSkillsPromptChars` 122000. No other keys changed.
- The gateway hot-reloaded the config; it was not restarted (PID 833981 throughout).
- `subnet-calculator` is now `ready`. The ready skill count went from 187 of 298 to 227 of 347.
- Rollback: `cp -p ~/.openclaw/openclaw.json.bak-skilllimits-20261122T220100Z ~/.openclaw/openclaw.json`.

**Second 6b re-run** (22:03–22:05Z):
- **PRODUCTION CHANGE 9** (22:03:35Z): temporary grant 63, the same shape as grants 61 and 62.
- The test VM submitted task `0551d62e…`. Production queued approval 3, and the operator approved it at 22:03:44Z.
- The test VM polled `working` ×3, then got `completed` at 22:04:15Z with `usage_available: true` and
  `tokens_used` 149489.
- The answer was correct for 192.0.2.77/27: network 192.0.2.64/27, broadcast 192.0.2.95, usable hosts
  192.0.2.65–192.0.2.94, mask 255.255.255.224.
- The production agent's trajectory shows `skills_read subnet-calculator`, then a call to
  `subnet-calculator-mcp__subnet_calculator`. So the delegated task used the granted skill.
- **Result: 6b is PASS end to end**, both at the NCFED layer and in the delegated agent turn.
- **PRODUCTION CHANGE 9 reverted** (22:04:21Z): grant 63 revoked. The same submit then got `-32001`, and no
  approvals were left pending. Helper `/tmp/ncfed_api.sh` was removed from both hosts.

**iN2N members (checked read-only first; limits applied afterwards as change 10).** None of the five active member configs
(`~/.openclaw-byrns-risk-<name>/openclaw.json`, generated 2026-11-14) has the spec-188 limits, except viz, which sets
only `maxSkillsLoadedPerSource` 300. No member loses a scoped skill today:
- cml, pyats and secops: all scoped skills sort within the first 200.
- viz: three scoped skills (`threejs-network-viz`, `ue5-network-viz`, `uml-diagram`) sort past 200. They load only
  because of the 300 override.
- guardian-claw: uses its own 7-skill workspace.
- No member logged a "cannot load scoped skill" warning in the previous 3 days.

**PRODUCTION CHANGE 10** (22:54:59Z): the same raise-only `raise_limits()` and `config/skill-limits.json` were applied to
all five member configs, so viz no longer depends on its partial override. Before: no `skills.limits` (viz: only
`maxSkillsLoadedPerSource` 300). After: 400 / 400 / 400 / 122000. Each file was backed up first
(`openclaw.json.bak-skilllimits-20261122T225459Z`, mode 0600) and replaced atomically, staying `ubuntu:ubuntu` 0600.
A re-serialisation of each original reproduced it byte for byte, so the only diff is the `skills.limits` block. No
member service was restarted: a member runs no gateway and starts a fresh `openclaw agent --local` per delegated
task, which reads `openclaw.json` at start. All five services stayed active on their original PIDs.

```bash
# rollback for one member
cp -p ~/.openclaw-byrns-risk-<name>/openclaw.json.bak-skilllimits-20261122T225459Z \
      ~/.openclaw-byrns-risk-<name>/openclaw.json
```

## 12. Evidence file index

Every file in this folder, and the test it supports. All times are UTC on 2026-11-22.

| File | Test | Contents |
|---|---|---|
| `raw/t1-preconsent.txt` | T1, T2 | Production port 1179 discrimination cross-check (no `0xFF`/BGP probe) and the pre-consent handshake refusal |
| `raw/t1-preconsent-daemon-dial.txt` | T1 | Test VM operator marks production as domain-verified (direct SQL; no HTTP/CLI surface), then the daemon's pre-consent dial |
| `raw/t1-postconsent.txt` | T1 | Raw handshake to production after mutual consent: the 13-octet NCFED reply |
| `raw/prod-change-1-consent.txt` | T1 | Production change 1: `POST /n2n/consent` for the test VM identity only |
| `raw/t1-t2-production-log.txt` | T1, T2 | Production daemon log for the T1/T2 window |
| `raw/t2-discriminate-testvm.txt` | T2 | First-octet and magic discrimination against the test VM, with its daemon log |
| `raw/t2-timeouts-testvm.txt` | T2 | 30 s first-octet and 10 s magic timeout measurements |
| `raw/t3-pinned-impersonation.txt` | T3a, T3b, T3d | Forged, keyless and bad-signature hellos; changed pinned key refused and logged |
| `raw/t3-domain-verified-negative.txt` | T3c | Wrong `claw_domain` set on the test VM; TLS SAN mismatch refused on redial |
| `raw/t3-trust-state-after-federation.txt` | T3 | Production's read-only view of the test peer's trust state after federation |
| `raw/t4-grants.txt` | T4a–T4c | Default-deny, read grant, and a write-class tool refused under a read grant |
| `raw/t4-approval.txt` | T4d, T4e | Approve and deny paths; the held call that never returns `-32002` |
| `raw/t4-limits.txt` | T4f, T4g | `RATE_LIMITED` and `BUDGET_EXHAUSTED` |
| `raw/t5-revocation.txt` | T5 | Sever on the test VM, refused redial, recovery after re-consent |
| `raw/t6-delegation.txt` | T6a | Skill task submitted with no grant: refused |
| `raw/t6-delegation-positive.txt` | T6b | Production change 2 (grant 61): the first delegated task, which failed at production's gateway |
| `raw/t6-rerun-after-gateway-fix.txt` | T6b (§10) | Grant 62 re-run after the gateway token fix: NCFED path passes; the skill was not loaded |
| `raw/t6-rerun-after-skill-limits.txt` | T6b (§11) | Grant 63 re-run after the skill limit raise: the skill runs; daemon token-source log; agent trajectory |
| `tools/ncfed_wire_probe.py` | T1–T3 | Raw-wire probe: `discriminate`, `timeouts`, `handshake --hello none\|keyless\|forged\|badsig [--tls12]` |
| `tools/ncfed_probe_mcp.py` | T4 | Stdio MCP server registered on the test VM only as `ncfed-probe` (`echo_info`, `touch_marker`, `approval_info`) |

Related source changes, outside this folder:

- `mcp-servers/protocol-mcp/bgp/federation/gateway_ws.py` and
  `mcp-servers/protocol-mcp/tests/test_gateway_ws_token_reresolve.py`: the gateway token re-resolve fix from §11, on
  branch `fix/gateway-ws-token-reresolve`.
- `config/skill-limits.json` and `scripts/lib/skill_limits.py` (spec 188): the skill limit policy applied in §11.

Findings that need follow-up work are tracked as H15–H23 in
[`../../NCFED-HARDENING-BACKLOG.md`](../../NCFED-HARDENING-BACKLOG.md).

## 13. Teardown performed and member viz check

### 13.1 Teardown (2026-11-22, §8 steps 1–4)

A pre-teardown backup was taken first: `~/.local/state/ncfed-two-border-20261122/federation.db.pre-teardown-20261122T232112Z`
(0600, SQLite backup API).

| Step | Result (read-only verification afterwards) |
|---|---|
| 1. Sever `as65010-10.255.250.1` | Peer `severed`, `updated_at` 23:21:33Z. Consent rows 7 (`local_grant`, granted 20:46:00Z) and 8 (`remote_grant`, granted 20:46:06Z) both revoked at 23:21:22Z |
| 2. No active grants for as65010 | Grants 61, 62 and 63 revoked at 20:58:47, 21:21:30 and 22:04:21; none active |
| 3. Remove helper files | `/tmp/ncfed_wire_probe.py` and `/tmp/ncfed_api.sh` absent on production |
| 4. Destroy VM 127 | Destroyed with `--purge`; `qm config 127` reports no such VM. Template 8000 present and stopped; no other VM touched |

Not re-consented: John (`as65001-4.4.4.4`) and every other retired peer stay `severed`. The HUD, mobile enrollment,
BGP config and Stage 8 checks were not touched. Rollback: restore `federation.db.pre-teardown-…` with the daemon stopped
(same procedure as §8); VM 127 itself cannot be restored and would be re-cloned from template 8000.

### 13.2 Member viz check (change 10 follow-up)

To confirm that the raised `skills.limits` (change 10) reach an iN2N member, production delegated one task to the
`byrns-risk/viz` member:

- Task `1a5ec57f-18d6-4e74-9421-de66259ab806`, skill `threejs-network-viz`, created 23:22:43Z.
- The member's agent reported that it **could see the skill**, so the member-side limits load as intended.
- **Tool execution failed**: the member answered that the "executable tool corresponding to this skill was not found or
  failed to resolve during the execution attempt". The member's tool config is `null`, so it runs on defaults; no
  visualization was produced. Not diagnosed further.
- **Border status mismatch**: the member finished the task, but production's `delegated_task` row stayed `submitted`
  (progress `None`, `updated_at` 23:22:43Z). The Border does not pull the member's result back. Tracked as H23 and
  reconciled by hand in §13.4.

Result: change 10 is confirmed for skill visibility only. Skill execution on the viz member is not demonstrated.

### 13.3 Stale as65123 cleanup (changes 11–12)

The peer `as65123-203.0.113.99` predates this run (created 2026-07-18, transport ngrok, never federated). It was removed
together with its 7 empty `budget_counter` rows, after a backup each time (see §6). Neither deletion needed a restart;
daemon PID 852849 is unchanged. Rollback: restore the matching `federation.db.pre-delete-as65123-*` backup with the daemon
stopped.

### 13.4 H23 Border task record reconcile (change 13)

**Cause.** iN2N task status is pull-only. A member never announces that a task has finished, and the Border updates its
outbound `delegated_task` row only in `poll_member_task`, which runs when something calls `GET /n2n/tasks/{id}`. Nothing
polled task `1a5ec57f…` after 23:22:43Z, so the row stayed `submitted` although the member had completed it (H23 in
[`../../NCFED-HARDENING-BACKLOG.md`](../../NCFED-HARDENING-BACKLOG.md)).

**Backup.** `~/.local/state/ncfed-two-border-20261122/federation.db.pre-h23-reconcile-20261123T013904Z` (SQLite backup
API, `integrity_check` ok). In the backup the row is `submitted`.

**Reconcile.** One read call on production's loopback operator API (`127.0.0.1`), at 01:39:09Z:
`GET /n2n/tasks/1a5ec57f-18d6-4e74-9421-de66259ab806`. It returned HTTP 200 with state `completed` and `tokens_used`
132186. The call made the Border poll the member, and it wrote the row.

| Field | Before | After |
|---|---|---|
| `state` | `submitted` | `completed` |
| `updated_at` | 2026-11-22T23:22:43Z | 2026-11-23T01:39:09Z |
| result | none | stored |
| `completed_at` | None | **None** |

**Second defect: `completed_at` stays empty.** A member's result reply carries no `completed_at`, and
`poll_member_task` stores the value it receives, so a reconciled row is terminal with no completion time. The row was
left as it is; no hand-written timestamp was added.

**Fix (not deployed).** Upstream PR [#376](https://github.com/automateyournetwork/netclaw/pull/376) makes the Border
reconcile its own non-terminal outbound iN2N tasks: when a member channel registers or reconnects, and on a 60 s loop
(`N2N_MEMBER_TASK_RECONCILE_S`). It only checks members that are already connected and never cold-starts one. It also
falls back to the Border's clock for `completed_at`. Four tests cover it (`tests/n2n/test_member_task_reconcile.py`).
Deploying it needs a `netclaw-mesh.service` restart, which has not been done.

The daemon was not restarted for the reconcile (PID 852849 unchanged). Rollback: restore
`federation.db.pre-h23-reconcile-*` with the daemon stopped.
