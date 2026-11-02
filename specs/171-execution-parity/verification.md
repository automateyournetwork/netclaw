# R02 implementation and qualification evidence

## Current status

Design analysis passed after six corrections. Implementation pass 1 is active.
No actual R02 runtime/provider/device/browser qualification has completed.
Do not count fixtures as live acceptance or mark R02 complete before T036.

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
