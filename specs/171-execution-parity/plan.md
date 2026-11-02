# Implementation Plan: R02 execution parity

**Branch**: `171-execution-parity` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

## Summary

An explicitly selected protected profile adds exact owner-reviewed approvals,
member-enforced one-use execution, guarded credential separation, signed durable
results and recovery without replay over existing iN2N. Existing profiles retain
their behavior and qualification limits. R02 concludes with actual local pyATS
acceptance and a human evidence review before R03.

## Technical context

- Languages: isolated Python 3.12; existing Node 24.19 and React 18 HUD.
- Dependencies: existing cryptography 50/P-256, SQLite, stdlib asyncio,
  MCP 2.3/FastMCP 4 and Express; pinned official OpenClaw and DefenseClaw.
- Storage: additive tables in federation.db, private immutable artifacts, existing
  GAIT Git trail, private owner SQLite database. Files 0600; directories 0700.
- Testing: pytest and Node suites, independent adversarial/crash/concurrency
  fixtures, actual fresh Linux Docker OpenClaw/guard/MCP/browser acceptance.
- Platform: Mac-hosted Linux ARM64 Docker qualification. GCP AMD64 belongs to R03.
- Bounds: one operation, at most two inference calls and one tool call, 512 KiB
  output within a 1 MiB signed envelope, explicit deadlines.
- Scope: one configured owner, fresh Border/member, selected lab `show version`.
- Constraints: no cloud changes, legacy fallback, automatic replay, or provider/
  integration credentials in Border or agent. No release or rollout changes.

## Constitution check

Read-only observation is in scope. The exact proposed read receives owner UI
approval; no device writes or ServiceNow change request are needed. GAIT records
protected authority boundaries. Reuse MCP integration; the private operation
bridge is an internal control, not a general tool server. Test backward
compatibility and use fresh homes to preserve existing runtimes. Credentials stay
in owned private .env files loaded only by trusted processes. Keep descriptors
free of credentials. The owner's publication hold supersedes public rollout
requirements; keep maintainer evidence under this spec. No cloud apply before
exact review. Retain human R02 acceptance and explicit provider/device scope.

## Structure

- contracts/execution.md: signed wire, durable state, private bridge and runtime.
- contracts/hud.md: owner session and exact operation UI.
- Federation protected_contract/store/service/owner modules and additive lifecycle.
- protected_runtime.py and scripts/protected-* for agent, guard and broker.
- HUD owner routes, bridge client, components and tests; no new framework.
- tests/n2n/test_protected_*: independent negative, concurrency and recovery tests.
- Private qualification packet and sanitized evidence; no public deployment guide.

## Phases and ownership

1. Freeze contracts and requirement mapping. Independent analysis must have no
   unresolved CRITICAL/HIGH findings before implementation.
2. Backend agent owns protocol/signing/store/service/GAIT, owner authority,
   the trusted owner CLI and focused tests. HUD agent owns Node/React routes,
   client, components and focused tests. Coordinator owns runtime/guard/pyATS
   containment, runtime activation/setup and integration. Independent verifier
   owns separate test files and review, without production fix ownership.
   Use separate worktrees; coordinate shared API changes.
3. Run focused tests, integrate and independently challenge boundaries, races
   and crashes. Count optional implementation/test/review passes, at most five
   across R02–R05. Never replay an unknown real operation to improve a test.
4. Prepare the exact fresh local packet: pins, homes, devices, guard policy,
   model/tool limits, baseline, preservation, stop procedure and commands.
   Existing authorized read-only scope permits this work; no runtime upgrades
   or device writes are inferred.
5. Qualify browser-approved pyATS, bypass refusals, signed result and lost-ACK
   recovery with actual invocation counts. Verify provider/device credentials
   are absent from Border and agent. Missing evidence stays unqualified.
6. Run relevant regressions/builds and independent final review. Complete the
   parity matrix and concrete evidence handoff before human R02 acceptance.
   R03 remains gated.

## Recovery

Unsupported profiles fail closed. Measure Docker isolation; labels alone do not
prove it. Durable claims and required GAIT precede runtime effects. Record which
atomic claim wins a revocation race. Unknown outcomes retain spent authority;
recovery only reads existing state or delivers an existing ACK. Historical
receipts use recorded trust without restoring old authority. Pin pyATS retry
semantics and independently count actual executions.
