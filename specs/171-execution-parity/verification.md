# R02 implementation and qualification evidence

## Current status

**Technical acceptance complete: T001–T035 pass; T036 human review is pending.**
Corrected source `8c178ff8` passed both actual local OpenClaw and Hermes operations
with guarded Sonnet, one approved `show version`, **zero setup commands**, signed
results/ACKs and independently checked IOS-XE 17.18.2 output. The authoritative
run is `live-qualification/run-20261102T155125-625aeb/` under the private R02 work
root. Original runtime and independent reports both pass; no reconstruction was
needed for this final run. Earlier authentic runs with an extra implicit Unicon
read retain that limitation and were not replayed.

The [parity matrix](parity-matrix.md) is ready for human review. The
[R02 roadmap brief](../../docs/roadmap/issue-310/briefs/R02-execution-parity.md)
requires that review before R03. R03–R05 have not started.

Current automated regression evidence: 311 protected Python tests; 219 relevant
legacy federation/installer tests; 436 HUD tests with serialized file execution;
eight independent Node boundary checks and the HUD build. Earlier failures,
synthetic fixtures and their limits below are historical checkpoints, not current
acceptance claims. Source is 1.18.3, extension 1.5.0; no release or cloud change.

## Bounded passes

| Pass | Scope | Status |
|---|---|---|
| 1 of at most 5 across R02–R05 | Implement, test and independently review R02 | Completed with an exact-command scope finding |
| 2 of at most 5 across R02–R05 | Remove implicit Unicon connection read; independently qualify exact command scope | Passed actual acceptance and independent review |

These are explicitly counted implementation passes. The Claude Code Ralph
stop-hook plugin is not running in this Codex session.

## Early implementation evidence (synthetic, not live acceptance)

- Independent runtime boundary tests: 32 passed before Docker-inspection expansion.
- Actual official OpenClaw 2026.7.1-2 Linux ARM64 image and native MCP projection
  completed a synthetic operation: exactly two inference callbacks and one tool
  callback. Operation 6298d06d-96ef-4ad4-8055-ff23eef994d3. Provider and device
  responses were fixtures; no Anthropic or device operation occurred.
- Initial OpenClaw allowlist named the tool incorrectly. Actual runtime logs
  identified `approved__pyats_run_show_command`; fixed and reran a fresh fixture.
- Docker Desktop cannot forward arbitrary bind-mounted host Unix sockets
  (Errno95). The fixed-route relay uses host loopback TCP instead, with a second
  network available only to the relay. Isolated agent probe could not resolve
  host/gateway Docker names or connect directly to 1.1.1.1:443. Full bypass
  qualification remains pending.
- Independent review found root-UID aliases, extra security options and unchecked
  tmpfs settings accepted by the first inspect validator. Fixed exact UID,
  security options and bounded tmpfs checks; independent recheck is pending.
- Official DefenseClaw 1.0.4 ARM64 archive downloaded and SHA256 verified against
  31460eaa944d29f31473cec5a29a0992f305432d053020a2244215a133ba78e8.
  Binary is defenseclaw-gateway, not defenseclaw; fresh image built accordingly.

Hermes was added by the owner during this pass. Its separate pinned image and
qualification are in progress. Both harnesses require actual acceptance evidence.

- Actual pinned Hermes v0.21.6 (818c13be1dc4fd28987e1e881a9408224afd4535)
  on Linux ARM64/Python 3.14.6 passed the same synthetic sequence: two guarded
  inference callbacks and one native MCP callback. Operation
  78bf1102-03a0-4e12-8f81-7c8cb34c220b. No real provider/device call.
- Docker default subnet pools were exhausted by existing networks. Protected
  operations now require a reviewed explicit local benchmarking address pool
  (198.18.0.0/15), with one internal isolated /28 per operation; any collision
  refuses before starting the model. Existing networks remain untouched.
- Runtime and containment independent subset now passes 67 tests. Full independent
  suite against protocol worktree plus root runtime passes 154 tests (verifier).
- Fresh private pinned pyATS runtime installed successfully; device reachability
  and actual pyATS acceptance remain pending.
- Official DefenseClaw image currently needs its shipped strict policy assets;
  binary-only config validation was insufficient for runtime startup. Guard
  worker is qualifying official pinned assets and upstream retry semantics.

## Integrated backend and boundary verification

Backend integrated at 421b8bf4, runtime hardening at d03f24d9, independent follow-up
tests at 62247933 and 079082b9. The independent suite reached 208 passing tests.
It covers real separate-process claims, ticket races and GAIT Git serialization,
with synthetic provider/device boundaries. Full deadline, resolved endpoint,
strict SSH options/host-key bytes, frozen upstream/adapter/testbed files and
unknown cleanup/summary outcomes are now explicitly enforced.

The actual strict-wire run run-20261102T135025-35739d passed ten checks using
separate fresh Border and two member processes, TLS 1.3 exporters, native
enrollment, owner CLI/HTTP bridge, signed approvals/results/ACKs and GAIT. The
executor was explicitly synthetic: no provider/device calls. A deliberately
lost ACK response and complete process restart retained identical operation,
approval, attempt, receipt and ACK identities, with one synthetic effect each.
Independent cryptography verification passed both receipts. All nine owned
worker processes exited successfully.

Official DefenseClaw 1.0.4 action mode with the pinned strict pack was exercised
against a local stub: authentication refusals, prompt-injection blocking and
ordinary forwarding passed. The strict pack has 255 enabled rules. An accepted
POST followed by response EOF exposed four internal SDK retry attempts despite
a zero-retry configuration value. Consequently the original facade-only counter
is insufficient for live qualification. An operation-bound upstream proxy is
being added inside the guard's credential domain. Actual guard→proxy→stub proof
now shows four retries produce one upstream dispatch; a third distinct request
after two is refused. Unknown accepted dispatch remains spent across proxy
restart, without another upstream call. This remains synthetic upstream evidence.

Hermes uses the official guard's OpenClaw-compatible HTTP proxy adapter plus the
protected MCP broker. Official native Hermes connector hooks are not qualified:
that connector is hooks-only and does not bind the HTTP proxy listener. Do not
claim native Hermes hook coverage from the successful protected HTTP path.

The source testbed's invalid defaults.arguments was preserved. A fresh selected
R1 inventory loaded successfully but its SSH address and the saved CML controller
were unreachable. The owner said they would start CML at the saved address.
No device authentication or command has been attempted in this session. CML
account credentials were briefly placed in an unused private device environment;
corrected to the original testbed's device credential references before any
authentication attempt. Never equate controller and device credentials.

Actual browser qualification is in progress. It identified Vite replacing the
protected entry's no-store header; final server/preview headers now enforce it.
The protected profile now excludes the repository .env and rejects legacy APIs
and WebSockets, with navigation limited to its reviewed operations. Unselected
profiles and the existing R01 lab retain their behavior.

## Pre-live integration checkpoint

The final official guard image is
`sha256:72a1523116eecfe7edde18f316af9064c7f8111e87036f962dc6d6de0489a284`.
Its actual runner bootstrapped and verified all 80 pinned policy files, started
action-mode enforcement, blocked an injection prompt with zero provider claims,
kept the real key out of the official child's environment/log, and stopped with
exit 0. Repeating retry/drop/restart checks using the final provider module
confirmed the durable dispatch limit. All upstream responses were local stubs.
Guard fixture containers were stopped; existing resources were preserved.

Actual Chrome qualification reached 16 passing checks: private owner ticket and
HttpOnly/Strict cookie, both enrolled member catalogs, immutable review, signed
synthetic results/ACKs, reload without replay, native revocation, logout, legacy
API/WebSocket refusal, no legacy automatic polling, final no-store/anti-framing
headers, safe discard of definitively unsubmitted reviews, and recovery of an
admitted review whose HTTP reply was deliberately dropped. Provider/device calls
were zero. The selected-profile header now reports configuration availability
instead of an unobserved legacy connection status. UX integration: `1453778b`.
The independent suite previously reached 210 Python + 8 Node checks; the focused
UX suite passed 36 checks and Vite built. Final combined totals remain pending.

After the owner restored CML, authenticated inventory confirmed the original
R1/R2/SW1/SW2 nodes booted. Exact-node console reads of interface state and the
RSA public key matched R1's SSH endpoint key. A fresh strict R1-only inventory
and native Unicon SSH argument generation passed without connecting. Global
known-host trust and ambient SSH configuration are disabled. The qualified
Unicon class is checked by object identity after native loading. Commit
`ef53e606` adds these corrections; 78 targeted tests passed. Both original
testbeds were re-hashed unchanged. No R02 `show version` or provider call yet.

Independent implementation review identified a signed revision-binding gap:
the runtime had compared two supplied profiles without deriving the approved
revision from actual images, guard configuration/policies and tool sources.
Correction and independent recheck are required before live activation.

The exact initial local scope is in [runtime-review.md](runtime-review.md), and
the control-by-control status is in [parity-matrix.md](parity-matrix.md).
Private evidence is retained under the work root in `browser-qualification/`,
`guard-qualification/`, `wire-qualification/`, `r1-host-verification/` and
`live-qualification/`. No cloud resource or existing R01 runtime was changed.

## Actual native integration attempts (not acceptance)

Integrated revision/containment/raw-MCP fixes at `aedf4277`, truthful supported
profile labels at `6c57ccd2`, guard HOME inspection at `05430447`, and the empty
nested secret-bind mountpoint at `d6750cba`. The last full protected suite passed
288 tests; later guard/cleanup subset passed 62. The unchanged complete HUD suite
passed 436 tests with serialized file execution; its first parallel run had two
fixed-delay avatar/UI timing failures, and both files passed in isolation. Eight
independent HTTP boundary checks and the HUD production build passed.

The first private bootstrap attempt `run-20261102T144824-da682e` refused a
qualification-helper risk-name mismatch before enrollment; corrected only that
helper and retained the failed run. `run-20261102T144902-9ea3de` then passed all
26 actual HTTP refusal checks, but its OpenClaw approval stopped before guard
start because the new inspector expected the wrong image HOME. The operation
`6109ae81-c450-4837-b78a-00034657b40e` remains conservatively unknown/spent,
with no effect claim, provider ledger or started guard; it was never replayed.

Guard-only preflights subsequently exposed Docker Desktop's nested bind mountpoint
requirement and root-private public policy asset modes. Fixed the mountpoint
without copying a credential, and rebuilt only public policy file/directory
permissions (0444/0555). Earlier standalone guard evidence did not establish this
non-root fresh-home startup; the new evidence below supersedes that assumption.
No fallback to root or weaker policy enforcement was introduced.

Current immutable guard image:
`sha256:5aec2081925656378df61a978c634f266e743dc5f77bb08cad07bee37a406aa1`.
Actual production guard preflight `guard-preflight-be2f0fb0-adb3-4522-9118-42487a177335`
passed and was independently inspected: UID503, exact containment/mounts,
DefenseClaw1.0.4 action/running health, all80 bootstrapped policy hashes and source
hashes correct, stopped exit0. Provider receipt and SQLite independently show
zero requests/dispatch claims. Old images, failed preflights and unused profile
bindings remain preserved as evidence.

The next native run `run-20261102T145948-e065ce` again passed26 actual HTTP refusal
checks. Its OpenClaw operation `a0b69c48-f9e7-4eaf-b3a8-c1ce2727b7de` reached the
isolated agent and guard, but the guard's local upstream returned403 before any
provider ledger claim or tool. One outer inference claim remains unknown/spent;
there was no automatic replay. All owned workers/HUD/containers stopped. Native
request translation is under investigation (OpenClaw emits
max_completion_tokens; the guarded provider contract uses max_tokens).

There have still been **zero actual R02 Anthropic dispatches and zero pyATS
show-version reads**. Do not label these failed attempts as execution acceptance.

The token translation cause was subsequently proven with the actual official
guard and a local stub: native max_completion_tokens2048 became vendor
max_tokens64000 and was refused; explicit max_tokens2048 passed. Commitab728b2d
normalizes the supported fields before the inference claim, rejects ambiguity
and invalid/out-of-range values, and preserves the4096 provider-fence ceiling.
Independent review passed; the complete protected suite now passes301 tests.

Native run `run-20261102T151005-bf2245` passed26 HTTP refusal checks and performed
one real Anthropic request (HTTP200). Sonnet proposed the exact reviewed R1
show-version arguments and the broker claimed the tool. The SSH connection then
timed out before a result could be captured. Operation
`1a7a0400-d272-4d68-80ff-cb1d6efaa205` remains unknown/spent with effect_claimed1,
effect_finished0 and no tool evidence; it is not a successful read. Independent
native SSH and CML HTTPS diagnostics both timed out before authentication. The
owner subsequently restored CML; HTTPS200 returned and R1 identity recheck is
pending. All owned failed-run workers/HUD/containers stopped.

Independent actual restart/reconciliation of that uncertain operation passed
14 checks: three fresh native worker processes re-established strictTLS1.3
channels, authenticated the same owner and performed status/reconcile only.
Approval/attempt records, provider/inference counters, every retained tool
artifact and original failed report stayed unchanged; no containers started.
The operation correctly remained unknown. All three workers stopped exit0.
Private report: the failed run's
`independent-unknown-recovery-20261102T152238-336534/report.json`.

## First native read evidence — exact-command qualification failed

After the second owner restoration, authenticated exact-node CML interface/key
reads matched the existing R1 identity and pinned SSH host key. No inventory or
trust relaxation was needed. Fresh run `run-20261102T152632-4e16f6` used the actual
source at `ab728b2d`, native enrolled TLS 1.3 channels, the private owner HUD,
OpenClaw 2026.7.1-2 / Hermes v0.21.6, official DefenseClaw 1.0.4 action mode,
Anthropic Sonnet 4.6 and the dedicated strict pyATS adapter.

| Native member | Operation | Captured tool execution | Model/provider |
|---|---|---|---|
| OpenClaw | `af612982-7348-4835-9216-2d120cf4177b` | One `show version`, one attempt, parsed captured output | Two finished guarded inference/provider calls; verified answer |
| Hermes | `24eaa3a1-a5f5-45b3-be08-bc053db4348d` | One `show version`, one attempt, parsed captured output | Two finished guarded inference/provider calls; verified answer |

Both independent raw/parsed inspections matched the observed hostname and
IOS-XE 17.18.2. Empty initialization command lists were retained. The identical
raw SHA256 was `c40c8ad1acf529dc85fed97b35c4d647ef00fe285375f25f9929a8f4a4120e22`;
separate operation identities, claims and receipts establish the two reads.
The earlier timed-out operation remains uncertain; these successful counts do
not retroactively establish zero effects for that earlier attempt.

Actual Chrome 156 passed 13 checks: both exact reviews, two approvals, verified
answers, refresh without resubmission, native owner revocation/relogin/logout,
owner cookies, protected navigation and legacy API/WebSocket refusal. Browser
artifacts retain the complete verified receipt payloads and screenshots. Hermes
correctly displayed a durable verified ACK with delivery still pending after the
deliberate reply loss. OpenClaw's submit reply was deliberately lost after
admission, while the channel remained open for authorization; the original
operation completed through reconciliation. There were two prepare and two
approve POSTs, with zero refresh mutation requests.

The run also retained 26 actual owner HTTP checks and 12 strict-channel
refusal/replay checks. Unknown devices, changed commands/arguments/profile/tool,
missing/used tickets, forged client principal, cross-origin/CSRF violations,
stale catalogs and denied reviews refused. Wire checks covered missing approval,
signature/argument/device tampering, validly signed already-expired specimens and
concurrent replay of each **completed** approval. Runtime artifact hashes stayed
unchanged. The expiry specimen was constructed already expired; first-admission
concurrency is separately covered by process-level tests, not this wire replay.

The private qualification driver completed its restart/reconciliation and wire
checks, but its final aggregate serialization failed in the strict protocol
encoder. Independently saved browser, tool, provider, wire and cleanup artifacts
remain intact. Missing in-memory pre-restart snapshots/exit-code maps are not
fabricated. A separately recorded reconciliation-only restart subsequently
passed 20 checks with before/after snapshots and zero additional effects. The
original two approvals were not repeated to obtain a new test report.

Independent credential-byte inspection scanned 84 fresh Border/model artifacts
and found no actual provider/device credential values. Both original inventory
SHA256 values still match their pre-test baselines. Actual containment records
show non-root UID503, read-only roots, dropped capabilities, no-new-privileges,
internal isolated agent networks and only the reviewed agent mount/environment.
Both guard health records show action mode; all six operation containers stopped.
Agent/guard exits were zero; relay shutdown required termination (137), and the
owned HUD API/Vite were deliberately terminated. Cleanup is confirmed, not a
claim that every process exited normally.

Private evidence in this run: `browser-1793651221024/browser-report.json`,
`verified-evidence-{openclaw,hermes}.json` in that browser directory,
`negative-http-before.json`, `negative-wire-after.json`,
`independent-parsed-monitor.json`, per-operation tool/provider/containment/cleanup
records, `independent-credential-absence.json`,
`original-inventory-preservation.json` and
`independent-success-recovery-20261102T153444-460bcb/report.json`.
Final signature/GAIT inspection and targeted isolated bypass probes are recorded
separately when complete; they do not authorize another real operation.

### Final-review finding: implicit Unicon setup read

The independent receipt inspector verified the actual signatures, authority,
result/ACK, provider budgets and GAIT correlations for both operations. Full
connection transcripts additionally showed `show version | include operating
mode` before the approved command. Empty init-exec/config lists did not suppress
this native Unicon platform-discovery read. The adapter's `execute_calls:1`
counts its approved callback, not every command sent during connection setup.

This extra command is read-only but exceeds the exact reviewed packet. These
runs prove real guarded execution/result/recovery, **not exact-command acceptance**.
Retain their receipts and the finding. Pass2 fixes the connection policy, tests
it against the actual installed Unicon plugin and requires fresh reviewed
operations with a complete command-transcript check; never replay prior approvals.

## Pass2 correction and independent boundary evidence

Commit `8c178ff8` suppresses the implicit IOS-XE discovery path using fixed,
internal connection settings, qualified package versions and a 580-file Unicon
source/native-module digest. It refuses other plugin profiles, unapplied settings,
a non-enable initial state and reconnection. The signed tool revision changes;
old runtime profiles/approvals remain preserved. There is no testbed override
or exposed bypass flag. This native dependency pin is deliberately Mac-specific,
not full Python dependency attestation or general pyATS platform support.

The actual installed pyATS/Unicon local mock independently proved that MIT alone
still probes, while the corrected adapter emits zero setup commands and exactly
one requested read, parses captured output, and refuses disconnected execution
without reconnecting. Final native adapter proof is
`live-qualification/unicon-full-adapter-mock-20261102T155036/report.json`.
Six transcript-verifier self-tests reject both prior real extra-probe logs and
additional command/echo mutations. No provider or device was used in those tests.
Final protected regression: **311 passed**, two existing utcnow warnings.

Separate actual network probes used both pinned images with the same container
security flags and isolated network topology; only entrypoint, dummy capability,
owned names and copied nonsecret config changed. Bridge positive controls reached
internet TCP443 and the owned host tripwire. Both isolated probes failed internet
and declared gateway TCP and host/gateway DNS, sent zero application bytes, and
had no provider/device environment or Docker socket. Three probe containers exited
zero and stopped; host listener closed. `/root/.ssh` was inaccessible, not proven
absent. Docker Desktop host/gateway literal addresses learned by the positive
control were not directly attempted. Evidence: `agent-boundary-probe-20261102/receipt.json`.

The production DockerExecutor ASGI/Uvicorn/official MCP SDK path also passed
17 negative HTTP cases plus two discovery checks, with missing/wrong capability,
headers/routes/queries, altered tool/device/command/timeout, extra or missing
arguments, coercion values, batch and duplicate JSON. Gate/effect/provider/inference
counts remained zero, and825 real evidence files stayed unchanged. External
Docker/guard/pyATS seams were synthetic; this proves the actual HTTP/MCP boundary,
not live tool execution or first-admission concurrency. Evidence:
`mcp-negative-http-qualification/report.json`.

## Final corrected acceptance and human gate

Fresh source `8c178ff8`, run `run-20261102T155125-625aeb`, completed successfully:

| Harness | Operation | Independently verified outcome |
|---|---|---|
| OpenClaw | `ff22d921-951b-4024-8eaa-b5547417c980` | One exact R1 read, zero setup commands; two guarded provider calls; signed result/ACK; submit-loss recovery |
| Hermes | `dc674dfe-5af0-46ce-a5dc-9091fb0bd0d1` | One exact R1 read, zero setup commands; two guarded provider calls; signed result/ACK; ACK-loss recovery |

The actual Chrome run passed15 checks, including the complete native command
transcript before allowing the next harness approval. Owner HTTP26 and wire12
refusal/replay checks passed. The native driver passed7 grouped checks and exited
zero; its final report retained the genuine pre/post restart snapshots. Both
approved operations preserve their approval, attempt, receipt and ACK identities
and provider/inference/tool hashes across full process restart/reconciliation.
All owned execution containers, native workers and HUD processes stopped.

The independent verifier used the exact bytes frozen before activation and
passed both operations' domain-separated P-256 signatures, trusted enrollment
bindings, raw-to-parsed evidence, exact single-command transcript, provider/tool
budgets, GAIT commit linkage, restart invariants and cleanup. No additional
runtime, model or device calls were made by the verifier. The final credential
scan covered86 Border/model/provider-body files with zero actual credential-byte
matches. Both original inventories still match their baselines.

Authoritative private evidence, relative to the final run:

- `report.json` — original complete driver report, source/pins/restart snapshots.
- `browser-1793652734808/browser-report.json` and verified-evidence JSON/screenshots.
- `independent-native-receipts-20261102T155405.json` — independent strict acceptance.
- `negative-http-before.json`, `negative-wire-after.json`.
- `independent-credential-absence.json`, `original-inventory-preservation.json`.
- Per-operation native logs, raw/parsed tool evidence, provider ledger/receipt,
  guard health, containment and cleanup;14 frozen helper sources/manifests.

T001–T035 are complete for the two pinned Mac/Docker ARM64 harnesses, Sonnet4.6
and this IOS-XE/IOL read. This does not qualify arbitrary providers/models,
Linux/WSL/cloud native execution, other device plugins, writes, physical mobile,
native Hermes hooks or multi-user/SSO/RBAC. Trusted host/Docker and the trusted
guard process domain remain explicit. Earlier failed/unknown/limited runs are
preserved; none was silently replayed or rewritten as acceptance.

**T036 remains open:** the human must review this evidence and the completed
parity matrix before R03, as required by the R02 brief and FR016. No new cloud
resources, deployment changes, version bump, release or public rollout material
were made. The total later GCP lab ceiling remains conservatively CAD100/month,
including R01; exact resource/spend review is still required.
