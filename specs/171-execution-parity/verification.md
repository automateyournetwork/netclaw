# R02 implementation and qualification evidence

## Current status

Design analysis passed after six corrections. Implementation pass 1 is active.
Actual harnesses, official guard, browser and strict-wire checks have passed
with synthetic effects/upstreams. Fresh CML console reads verified R1's SSH
identity; the native pyATS inventory/SSH arguments passed offline checks.
Real R02 Sonnet/pyATS operations have not yet run. Do not count fixtures as live
acceptance or mark R02 complete before T036.

## Bounded passes

| Pass | Scope | Status |
|---|---|---|
| 1 of at most 5 across R02–R05 | Implement, test and independently review R02 | In progress |

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
