> Integration amendment2026-11-02: source commit/push/main merge authorized; no
> release/version bump or rollout documentation until the full roadmap is done.
> Prior no-commit statements below record their original session boundary.
> See [main integration](main-integration.md); source and lab evidence remain valid.

# R01 verification — direct cloud pilot

**Roadmap:** R01 · **Spec:**168 · **Branch:** `168-ngrok-transport-contract`
**Baseline:** `9ba12ffc8d1033a0130dd8544aa54d95471afcbb`
**Current status:**40/40 tasks complete for the owner-amended R01 lab scope.
T028 live transport, T040 full HUD/Chat/Canvas/RAG and T038 reconciliation are
complete. Stop after R01; R02/R03 remain unstarted.

The owner fully delegated the R01 DNS/HTTPS, activation and relocation work, then
requested the full open lab workspace and their Anthropic Sonnet for a real
question delegated to the fresh on-prem member. The previous two-view status-only
restriction is superseded. No R02/R03, device operation, existing owner-runtime
upgrade, commit, push or publication is included.

Live full HUD: **https://r01-gcp-montreal.lobsternet.automateyournetwork.com/**.
Public DNS A34.95.60.45/TTL600 and publicly trusted Let's Encrypt HTTPS verified.
GCP project netclaw-506315, Montréal northamerica-northeast1-a, isolated VM
netclaw-r01-20261101. Cloud installation f03c0a7c-5444-4cd6-b745-394471cf328a.
Private administrator access remains through IAP;127.0.0.1 is the local tunnel
end, not the public cloud address. Users/SSO/RBAC remain R15–R17.

Private receipts: `~/.local/share/netclaw/spec168-direct-cloud-pivot-20261101/`.
Actual [Sonnet cloud-to-on-prem answer evidence](onprem-answer-evidence.md) includes
matching cloud/member task IDs and the Mac's actual calculator tool call/result.
The member is a **Mac subnet calculator**, not an existing pyATS claw.

## Current acceptance matrix

| Group | Actual evidence and limit |
|---|---|
| Positive | `live-positive.json`: real Mac→GCP iN2N enrollment; both `bgp-daemon-v2.py` and `in2n-member.py` authenticated, then durable daemon reconnected. Cloud members receipts match `r01-20261101/onprem`. `live-external.json`: independent fresh external Border AS64519 admitted by cloud AS64520 over TLS NCFED with bilateral consent; separate from member admission. |
| Identity | `live-negatives.json`: wrong TLS name/CA, Border identity/anchor, altered exporter, forged possession, unknown member, expired/replayed token, cross-connection proof replay, repeated authentication and revoked open/new channel all refused. Fresh exporter differs while member key remains unchanged. `live-external.json`: wrong peer key/name/CA and withdrawn consent refused; consent recovery passes. |
| Downgrade | Real cloud iN2N rejects cleartext, PROXY and TLS1.2; real NCFED endpoint rejects raw BGP, NCTUN, HTTP and PROXY. TLS/socket unit suite covers both direct and optional forwarded profiles. |
| Exposure | Actual cloud `ss` and firewall receipts:42101/42102 on private NIC with reviewed source `/32`; BGP/API/HUD loopback, SSH IAP-only. Both actual Mac member entrypoints have zero TCP listeners; no direct member-to-member listener. Member-as-Border refusal is a local socket test, not a second physical member test. Public ingress tests allow the reviewed full workspace/Chat/RAG routes and reject raw credentials/configuration, device writes, WebSockets, traversal and arbitrary proxy/query forwarding. |
| Recovery | Actual cloud owned-unit restarts and both local entrypoint reconnects preserve the member key. NCFED consent restoration passes. Address-only CAS/explicit recovery and no work replay pass local socket tests. `live-relocation.json` verifies the actual move34.47.13.89→34.95.60.45, stale-CAS refusal, unavailable prior address/no fallback, explicit recovery and both peers reconnecting with the same enrolled key. |
| Operations | Foundation and budget-only recovery applied under exact delegation; refreshed no-change plan. Workload identity reads only the fresh pilot secret. CAD50 alerts, expiry, cost and teardown documented. Public DNS/HTTPS and the full HUD navigation are browser-verified with zero JS errors; Caddy certificate renewal state is private and persistent. Frozen v4 activation and current no-drift receipts are retained. |

The on-prem member's application-key fingerprint is
`a7ab031e1da2b63f1317e72a58cf7e4db5329bddb89af6b3f659dbadf007bd08`.
Its single-use token was consumed and removed from its private environment.
Transport qualification ran with zero delegated tasks. The subsequent owner-requested
Sonnet example is an actual completed task, with prior failed attempts preserved.
Pilot posture is testing; no production or device-workload acceptance is implied.

## Current automated and browser evidence

| Evidence | Result / private receipt |
|---|---|
| Direct pivot suite |867 passed,5 skipped; `federation-final-junit.xml` (19:26:53–19:27:50 UTC). Preserved historical run. |
| Strict readiness regression |Five tests failed before the fix, then passed. Full suite872 passed,5 skipped; `federation-readiness-final.log/.xml`. A strict Border now needs both current listeners before readiness. |
| Incoming direct transport label |New assertion reproduced legacy `ngrok` label on accepted direct channel; six direct/forwarded NCFED cases pass after correction. `direct-inbound-transport-red.log`, `direct-inbound-transport-green.log`. Final full rerun:872 passed,5 skipped,69 warnings in59.16s; `federation-public-final.log/.xml/.json`,20:19:32–20:20:31 UTC. |
| HUD |408 tests pass after full workspace/freshness and RAG serialization changes; `full-hud-rag-final-tests.log`. Production build passes; `full-hud-final-build.log`. Existing chunk-size advisory retained. |
| Public ingress |Three real HTTP tests pass; `full-hud-ingress-tests.log`. Fixed origin/routes, cookie ownership, credentials excluded from inventory, private routes refused, bounded bodies and replies. |
| Browser |`full-hud-browser.json`: public HTTPS200, Chat/Canvas/RAG/Risk/neighbours navigation, zero JS errors. Earlier two-view/IAP screenshots remain historical; final functional receipts below. |
| VS Code |150 passed,3 skipped; typecheck/build pass. Deployment-choice card opens the selected source guide. |
| Installer |23 passed plus23 subtests,1 skip; effect/deploy/engine32 passed plus3 subtests. Catalog/effects/artifact/coverage checks pass again after the final documentation changes. |

## Full-workspace functional receipts

Normal public browser Chat: HTTP200, zero JavaScript errors, cloud and Mac task
`845cd3b1-2848-4873-b67e-d1589528cefa` completed. The Mac's actual tool call/result
IDs match and calculate192.0.2.0/28. Earlier API proof task
`23f0a74f-0d54-4926-8938-eaa4482fced0` also completed. Both use Sonnet4.6;
this is an isolated Mac subnet-calculator member, not the owner's existing pyATS.
See [correlated answer evidence](onprem-answer-evidence.md).

RAG: `browser-rag-canvas.json` records a real public browser upload, one ready
chunk, HTTP200 retrieval and a citation transferred into the actual Canvas draft.
Cloud-local BAAI/bge-small-en-v1.5 and ms-marco-MiniLM-L-6-v2 models use their
preloaded offline cache. Only harmless public lab text was uploaded. Screenshots
were visually inspected. Retrieval took25.864s and37.024s on this small pilot;
no production throughput or concurrency qualification is implied.

`browser-rag-canvas-answer.json` also records a normal Canvas send after cited
retrieval/handoff: HTTP200 from the gateway, correct member/range and lab-guide
citation, zero JavaScript errors. `full-hud-canvas-answer.png` was visually
inspected. This source-context answer is separate from the real member tool proof.

`r01-final-public-check.json` at21:20:27Z verifies all four DNS resolvers, trusted
TLS1.3/SAN/expiry, HTTP308 redirect,16 positive/refusal HTTP observations and zero
credential matches. Private environment, testbed, operator logs, device mutation
and cross-origin Chat requests were refused. `r01-final-runtime.json` records all
five owned units active, private/public listener placement and installed RAG
versions. `r01-final-member-key.json` and `r01-final-member-listeners.json` confirm
unchanged enrolled key, authenticated member and zero inbound TCP listeners.
`r01-closure-no-drift.json/.log`: OpenTofu detailed exit0,21:15:56–21:15:58Z.
The final applied description-only firewall plan changed no network rules.

Final federation run: **873 passed,5 skipped,69 warnings in57.88s**;
`federation-hud-final.log/.xml`, including native member tool-filter projection.
The five retained real-runtime skips are not qualifications. HUD: **408 passed**,
zero failures/skips; public ingress: **3 passed**. The last frontend build remains
valid; subsequent fixes affect server-side request handling only.

## Pilot corrections and preserved outcomes

Original foundation apply created10 resources; budget creation failed because user
OAuth needed an explicit quota project. The separately approved budget-only plan
succeeded. Local backend state was preserved and moved privately; never recreate
an empty state or replay stale plans. The authoritative state is `pilot.tfstate`.

Runtime activation preserved its original receipts. Two omitted public JSON imports
were transferred before the Linux HUD build passed. The dependency venv needed
service-group read/execute access; private home/secret permissions stayed0700/0600.
A wrong pilot stack setting (`in2n,en2n` rather than `both`) exposed a real false
readiness result, fixed with red/green regression tests. Frozen Secret version1
is initial bootstrap material; the active persistent environment has the corrected
stack value. Do not restore bootstrap data over the active home.

The fresh external fixture initially used AS64521, which does not initiate toward
AS64520 under NCFED's deterministic ordering. It was corrected to AS64519, without
changing cloud/member identities or weakening ordering. A consent request using
`peer_as` was rejected400; the documented API uses `as`, and the corrected call
succeeded. The first immediate external retry preceded listener readiness; the
subsequent positive/refusal/recovery run passed. Failed harness attempts remain
in their own logs. Temporary binding-proof members were retired after evidence;
the durable on-prem member remains enrolled and running.

The owner-authorized Sonnet5.5 attempt was rejected because the pinned runtime's
thinking format is unsupported by that model. Account-available Sonnet4.6 was
verified and used successfully. Fresh member MCP startup initially failed until
the existing source-hash-checked FastMCP migration was applied. Cloud MCP needed
its explicit loopback federation API binding. All failed task/provider receipts
remain; only actual completed task/tool records count as evidence.

The first browser request timed out before model dispatch while starting the
settings CLI. A native diagnostic succeeded after69.98s; the scoped bounded120s
CLI-startup override fixed it. RAG installation uses its own venv, not the
protocol environment. Model preload initially used an inaccessible cwd; the owned
home fixed it. Concurrent per-call RAG startup overloaded the host and could
race its interrupted-ingest sweep. Serializing HUD RAG calls with coalesced
status reads fixed that path; three regression tests and actual browser ingestion/
retrieval passed. Independently launched RAG clients still require coordination.
No VM resize or additional cloud service was needed.

## G1–G11 and portfolio

| Invariant | Evidence / boundary |
|---|---|
| G1 | Actual outbound-only member, both entrypoints, zero member listeners; Border identity enforcement and member-as-Border local refusal. Multi-Border clusters later. |
| G2 | Separate direct cloud iN2N/NCFED ports; application TLS1.3, exporter/member proof, CA/name/application identity separation. No ngrok token or TLS termination proxy on federation. Optional ngrok retains schema1 and local tests; its account deployment remains unqualified. |
| G3 | No public Ollama/MCP/broker/gateway/etcd or routing/admin API. Full public lab workspace is the owner-approved scoped exception; no raw gateway/admin port is public. |
| G4 | New cloud-only secrets, workload identity and scoped secret access. Owner explicitly authorized Anthropic; provider-only Secret Manager delta verified through workload identity. Device credentials remain outside pilot. |
| G5 | Transport tests had zero work/replay; subsequent scoped model/task receipts are recorded separately. R02 broker parity/R08 quorum remain later. |
| G6 | Principal propagation starts R02; users R15, SSO R16, RBAC R17. No account feature added here. |
| G7 | Source, local sockets, fixtures, real Mac/cloud admission and browser evidence explicitly separated. |
| G8 | Existing profiles preserved; no existing runtime/device changed. GAIT branches `spec168-direct-cloud-pivot-20261101` and `spec168-dns-https-closure-20261101`; scoped private baseline/repair receipts. |
| G9 | Isolated IaC VPC/VM/IPs/secret/IAM/firewalls/budget, expiry2026-12-01, US$24.96 base720h estimate before traffic/secrets/model usage/tax. Budget is an alert; stopped VM retains disk/IP costs. Teardown requires its own review. |
| G10 | Matrix below retains all platform limits. |
| G11 | Owner-authorized Sonnet/subnet example and local RAG functional checks; no device/system configuration. Later R03–R14 retain their own read-only/approval boundaries. |

| Surface | Current qualification |
|---|---|
| Apple Silicon Mac→Ubuntu24.04 GCP direct | Actual iN2N/NCFED authenticated positive/refusal/reconnect evidence. Actual IP relocation/recovery and public DNS/HTTPS verified. |
| Optional ngrok | Local forwarder, config and lifecycle regressions retained. Free account inventory API works; zero reserved TCP addresses observed. No paid plan required for direct cloud. Live ngrok remains unqualified. |
| WSL/native Windows/Intel Mac strict transport | Unqualified. WSL manager skip and Intel crypto wheel limitations retained. |
| Direct LAN/cloudflared108 | Regression-retained; no new physical-network qualification. |
| OpenClaw single-user | Selected transport/runtime paths retained; pilot has a separate pinned OpenClaw gateway and Sonnet4.6. Existing owner installations untouched. |
| Hermes/mixed runtime | Local/unit compatibility retained; five real-runtime cases skipped. No live strict-cloud Hermes claim. |
| HUD Chat/Canvas/RAG |408 tests pass; production build and full public workspace deployed. Actual browser Chat delegates and returns the member tool answer. Real document upload/index/search and cited Canvas draft handoff pass. |
| Gateway/skills/MCP | Catalog/setup/gateway regressions retained; no MCP schema/tool addition; scoped Sonnet/subnet demonstration only; no device workload qualification. |
| Zoom/Mobile | Automated edge/resource cases retained; real meetings/physical mobile unqualified. |
| VS Code |150 passing/3 skipped plus typecheck/build; source guide card. Real remote-editor/cloud installation acceptance remains later. |

## Artifact coherence and closure

README, SOUL, TOOLS, USER, environment example, protocol MCP docs, existing
federation skill, setup.sh/peering/setup catalog, VS Code wizard/guide, deployment
choices and roadmap reflect direct cloud, optional home/NAT ngrok, on-prem internal
members, private/air-gapped topology and later hybrid/multi-region/multi-cloud work.
No component/tool count changed:112 components,239 skills,126 registered+52 external
integrations. `r01-final-coherence.json` records passing catalog/effects coverage,
152-spec artifact check (4 legacy exceptions), whitespace/shell/JS syntax and the
3 public-ingress tests. `r01-source-secret-scan.json`:125 changed/untracked files,
zero credential matches. Final Risk/neighbour browser capture returns200 with
zero JS errors and the clear member/model/live/retired labels. Private
runtime/state/keys and original roadmap ZIP remain unstaged.

T028 is complete against actual cloud relocation and recovery. T040 includes
normal browser Chat, actual member tool execution, RAG indexing/search and a
Canvas answer from the retrieved context. T038 reconciles the artifacts and audit.
The [review packet](public-hud-review.md) names the exact
saved plan and frozen artifacts. Security review of the TLS adapter is not implied
by tests. Full runtime migration, production workloads, HA and multi-user access
remain later work. Human acceptance of the completed R01 evidence gates R03.

Daily memory and GAIT closure are recorded under
`spec168-dns-https-closure-20261101`; the full audit log is retained privately as
`gait-r01-closure-full-log.json`. No commit/PR/push/publication or R02/R03 occurred.

## Historical source-only evidence (superseded checkpoint)

The following records preserve earlier commands and their original limits. Their
then-open blockers and source-only/no-cloud statements do not describe current
state; use the current acceptance matrix above.

## Initial evidence

- 2026-11-01T17:36:48.765364+00:00: `ngrok api reserved-addrs list` exited 1,
  API key required. Account limits/reservations: UNQUALIFIED.
- 2026-11-01T17:37:45.066068Z: isolated public exporter API measured matching
  32-byte bindings per connection, fresh across connections; SAN/CA/TLS1.2
  refusals. SYNTHETIC IN-MEMORY evidence only; see research.md and private receipts.
- Pre-implementation artifact analysis: 28/28 coverage, no HIGH/CRITICAL findings;
  requirements checklist 11/11. This is not code or live qualification.

## Brief acceptance evidence

| Group | Evidence and remaining qualification |
|---|---|
| Positive | E1: actual local TLS and application enrollment/reconnect through byte forwarding; both launcher paths; separate NCFED TLS/key/consent success. Separate-network admission through real reservations remains UNQUALIFIED. |
| Identity | E1/E7: wrong SAN/CA/application identity/pin, altered exporter, forged key, unknown/expired/replayed enrollment, repeated authentication and revoked new/open channel refused. E7 additionally proves bounded Border denial audit and revocation before outbound calls/notifications. Wrong Border anchor refused before token disclosure. Live-ngrok repetition UNQUALIFIED. |
| Downgrade | E1 exporter socket cases refuse TLS1.2, cleartext and PROXY before application callback; no legacy fallback. Live public paths UNQUALIFIED. |
| Exposure | E1 public listener refuses BGP/NCTUN/HTTP/PROXY without peer mutation; reachable TCP does not admit unknown members. Member admission refusal and no-listener daemon control flow are FIXTURE-ONLY. Actual member firewall/listener and member-to-member network qualification UNQUALIFIED. |
| Lifecycle | E1/E7 real local address relocation preserves keys and schedules no delegated tasks; registry CAS/concurrent update/recovery/bundle rebinding pass. E7 rejects duplicate JSON keys in CLI register/import before writes. Fake agents prove owned stop/restart isolation and foreign-PID refusal; synthetic daemon observations gate activation (FIXTURE-ONLY). Real agent/reservation restart and live replacement UNQUALIFIED. |
| Regression | E7 reruns direct/internal TLS, cloudflared108, consent/STARTTLS, gateway, Mobile, Zoom and Hermes unit cases; E8 setup/coherence and E9 HUD pass. E1–E6 remain historical local receipts. Real Hermes/mixed-runtime skips and remote-platform limits remain below. |

Human review of completed evidence remains required before R03.

## Local adapter checkpoint

2026-11-01T17:54:20.602343+00:00: private Python3.12 test environment;
`python -m pytest -q tests/n2n/test_exporter_tls_168.py -o asyncio_default_fixture_loop_scope=function`: **8 passed in0.59s**.
Actual loopback TLS sockets, not ngrok. Equal32-byte exporters per connection, fresh
across connections; bidirectional/fragmented traffic, clean close, wrong SAN/CA,
TLS1.2/cleartext/PROXY, handshake timeout/cancellation, abrupt EOF and output bounds.
Initial red run failed because exporter_tls module did not exist, as intended.

## Final commands, UTC and excerpts

Date: 2026-11-01. Local Apple Silicon Mac; isolated Python3.12.12 with
pyOpenSSL26.4.0, cryptography50.0.2, service-identity26.1.0. Receipts below live
privately in `~/.local/share/netclaw/spec168-tls-research-20261101/`.
`python` in E1/E2 means that directory's `venv-current/bin/python`.

| ID | Exact command / result | UTC and receipt |
|---|---|---|
| E1 | `python -m pytest -q -rs tests/n2n -o asyncio_default_fixture_loop_scope=function`: **814 passed,5 skipped,51 warnings in50.41s**, exit0 | Started18:25:16.083731Z, finished18:26:06.785461Z; `federation-final.json` and `.log`. Includes57 R01 cases in the four new files. |
| E2 | `python -m pytest -q -rs tests/test_setup_catalog.py tests/test_setup_risk.py tests/test_setup_systemd.py tests/test_setup_service_binding.py -o asyncio_default_fixture_loop_scope=function`: **23 passed,1 skipped,23 subtests passed**, exit0 | Exact command UTC in `coherence-final.json`; disposable WSL manager skipped. |
| E3 | `npm test` in `ui/netclaw-visual`: **404 tests passed**, zero failures/skips | Log completion18:20:36.689006Z, `hud-tests.log`. |
| E4 | `npm run build` in `ui/netclaw-visual`: exit0, built in1.46s | Log completion18:22:06.206547Z, `hud-build.log`; existing large-chunk advisory. No browser visual qualification. |
| E5 | `ngrok config check --config <rendered private synthetic config>` with installed3.36.1: exit0, “Valid configuration file” | 18:24:08.547000Z, `ngrok-config-check-fixed.json`; FIXTURE-ONLY addresses, no agent/endpoint started. |
| E6 | Coherence commands below: all exit0 | Exact per-command UTC/output in `coherence-final.json`. |

E6:

```sh
node scripts/build-catalog.mjs --check
python3 scripts/build-catalog.py --check
python3 scripts/check-catalog-metadata.py
python3 scripts/verify-catalog-coverage.py
python3 scripts/verify-spec-artifacts.py
git diff --check
bash -n scripts/netclaw scripts/peering-setup.sh scripts/lib/install-steps.sh
node --check ui/netclaw-visual/server.js
```

E1's new cases are in `tests/n2n/test_exporter_tls_168.py`,
`test_endpoint_registry_168.py`, `test_ngrok_lifecycle_168.py` and
`test_ngrok_transport_168.py`. Every acceptance row above maps to E1's command,
timestamp and passing excerpt. Socket tests use real loopback TLS; fake process,
registry and daemon fixtures do not constitute live ngrok qualification.
Additional adapter coverage: equal32-byte exporters at both ends, connection
freshness, bidirectional4MiB transfers, one-byte fragmentation, clean close,
abrupt EOF, bounded output, stalled handshake timeout and cancellation.

Initial full federation run:791 passes/17 failures/5 skips; all17 failures needed
absent ChromaDB in the isolated environment. Installing the RAG project's declared
test dependency resolved them:808/5, then final814/5 after readiness cases. Setup
checks caught stale generated artifacts and two deliberately changed description
fixtures; regeneration and targeted fixture edits passed E2/E6. Installed ngrok
rejected documented `tcp://` upstream origins at18:23:23Z; bare loopback host:port
under reserved TCP endpoints passed E5. Both receipts retained. No security check
or negative test was weakened. Earlier in-memory research remains synthetic.

E1 skips: one `test_hermes_external_149`, two `test_hermes_lifecycle_149`, one
`test_hermes_mobile_149` require real pinned Hermes fixtures; one
`test_mixed_runtime_149` requires a real mixed runtime. Existing `utcnow()`
deprecation warnings remain. These skips are not qualifications.

## Resume reconciliation — 2026-11-01

The checkpoint correctly reported only16/31 checked tasks and missing T030 files.
The earlier XI claim that the drafts existed was unsupported at that checkpoint.
Both drafts now exist and are linked below; previous receipts are retained.

Private resumed receipts: `~/.local/share/netclaw/spec168-r01-completion-20261101/`.
The isolated Python is unchanged from E1. HUD tests/build use the existing
Node24.19.0 binary at `~/.local/share/netclaw/spec155-native-tests/node-standalone/bin/node`;
ambient Node25.3.0 was not used to qualify HUD execution.

| ID | Command / actual result | UTC / receipt |
|---|---|---|
| E7 | `python -m pytest -q -rs tests/n2n -o asyncio_default_fixture_loop_scope=function --junitxml=<private>/federation-closure-junit.xml`: **822 passed,5 skipped,57 warnings in53.77s**, exit0;65 R01 cases | 18:48:09.918111Z–18:49:04.077787Z; `federation-closure.json`, `.log`, `federation-closure-junit.xml` |
| E8 | E2 setup command: **23 passed,1 skipped,23 subtests passed**; E6 catalog/artifact/shell/JS syntax commands all pass | 18:45:50.628068Z–18:45:52.959829Z; `coherence.json`; disposable WSL manager still skipped |
| E9 | `npm test`: **404 passed**, no skips; `npm run build`: exit0 in1.39s | 18:47:55.058441Z–18:48:03.234944Z; `hud.json`, `hud-tests.log`, `hud-build.log`; existing large-chunk advisory retained |
| E10 | Fresh `ngrok api reserved-addrs list` and `ngrok api endpoints list`: both exit1, API key required | 18:42:30.706938Z–18:42:30.777514Z; separate private JSON receipts; no account facts inferred |

Baseline rerun before source changes:814 passed/5 skipped at18:42:54–18:43:48Z
(`federation.json`). Four new denial-audit cases first failed because the Border
had no matching durable denial row; two outbound-revocation cases first failed
because removed members still received calls/notifications on open channels.
All six then passed. Two CLI duplicate-key cases first failed because decoding
silently selected the last value; both then passed before the final E7 run.
Red logs are `denial-red.log`, `revocation-red.log`, `ambiguous-json-red.log`.

The source fixes use one fixed refusal reason per channel, existing SQLite/GAIT
audit, and closure even if recording fails. Strict handler error logs omit caller
parameters/exception text. Before a Border sends a call or notification it checks
current membership. Unknown outcomes from already-sent work remain unchanged.
CLI register/import now apply the registry's duplicate-key rejection before any
configuration write. No approval, trust or transport test was weakened.

| Task | Reconciled evidence |
|---|---|
| T017 | E7 `test_strict_identity_refusals`, `test_cross_connection_proof_and_enrollment_replay`, `test_external_strict_trust_refusal`, repeated-auth case; real local sockets |
| T018 | E7 expired/replay/revoked cases; exporter `test_refusals_before_callback`; public-listener protocol refusal cases; real local sockets |
| T019 | E7 `test_border_denial_is_audited_without_submitted_secrets` (4), `test_revoked_member_receives_no_new_work_on_open_channel` (2), repeated-auth/revocation; `InternalChannel.refuse` and service audit binding inspected |
| T020 | E7 both launchers actually dial local TLS; member admission/no-listener control-flow fixtures; local unavailable/relocation path and empty task ledgers; actual remote listener/firewall gate remains T028 |
| T021 | E7 `test_atomic_address_change_and_explicit_recovery`, `test_concurrent_revision_change_has_one_winner`, local relocation and foreign-installation refusal |
| T022 | Inspected CLI address/recover and registry atomic/CAS receipts; E7 registry/lifecycle tests, including duplicate-key register/import refusal before writes |
| T023 | [Operator guide](../../specs/168-ngrok-transport-contract/deferred-docs/NGROK-TRANSPORT.md) covers coordinated profile migration, identity move versus clone, fencing and transport-only scope |
| T024 | Inspected existing README/SOUL/TOOLS/environment/federation-skill changes; examples retain operator-owned identities and explicit evidence limits |
| T025 | E8 catalog/effects parity and zero unexplained coverage gaps;112 components,239 skills,126 registered+52 external integrations; existing OpenClaw registration reviewed, no new tools/servers |
| T026 | E7–E9 current regression evidence; E1–E6 preserved with their original scopes |
| T027 | [Live runbook](live-runbook.md) refreshed using E10 and installed CLI help; exact read commands, activation sequence and missing review-packet fields recorded; no mutation executed |
| T028 | **OPEN**: no actual reservation, separate-network admission, live refusal/restart or live relocation evidence |
| T029 | Six evidence groups, G1–G11, portfolio/platform matrix and XI checklist reviewed; UNQUALIFIED does not pass a security gate |
| T030 | [Milestone draft](milestone-draft.md) and [PR draft](pr-draft.md) created locally, unpublished |
| T031 | Daily memory and GAIT session `spec168-r01-completion-20261101`; final audit log retained privately; resume checkpoint updated; R02 not started |

Project setup: existing Git ignores cover private environment, Python/Node build
outputs, audit state and memory. No new Docker image, npm publication, Terraform
or Helm artifact is introduced. Spec Kit checklist11/11 passes. Optional
`speckit.git.commit` hooks were not invoked; no staging/commit was needed to
continue the existing authorized local work. The original roadmap ZIP and all
pre-existing work are preserved.
