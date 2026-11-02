# R02 — Execution parity on NetClaw production mode

- **Roadmap item:** prerequisite for every remote workload
- **Depends on:** none (runs beside R01)
- **Gate:** human review of the parity matrix and verification.md before R03

## Specify input

The cloud program relies on the guarantees Thermidor qualified: the owner reviews
the operation, member and model; the service issues an exact, scoped, one-use
approval; the Border dispatches over the member's existing channel; the member's
model runs behind a guard and can only propose a tool call; a broker validates
the exact approved arguments and holds the integration credentials; signed,
durable result records support completion; and a lost reply produces
reconciliation work instead of a replay.

NetClaw already has production mode (`N2N_RISK_MODE=production`, the DefenseClaw
model guard, member confinement from specs 165–166, GAIT audit). This feature
produces a parity matrix (Thermidor control → NetClaw existing / partial /
missing) and implements the missing pieces so a dispatched read can be approved,
executed and evidenced end to end. Every request carries a principal; for now
that is the owner.

User stories:
- P1: The owner approves an exact read in the HUD; the member executes it; an
  altered argument, an expired approval or a reused approval is refused.
- P1: A member refuses a dispatch that lacks a valid approval for its own tools.
- P1: A lost reply produces a reconciliation item and never a second execution.
- P2: Maintainers can read the parity matrix and see what was reused and what
  was added.

## Clarify: decisions (recommended default first)

1. Approval object: signed, binding principal, operation, member, tool, hash of
   exact arguments, model profile, expiry and nonce; consumed once.
2. Result records: signed by the member, verified by the Border, acknowledged
   durably before the operation counts as complete.
3. ServiceNow CR: read-only operations need none; the approval object reserves a
   CR reference field for writes (R17).
4. Principal schema: `{issuer, subject, display_name, roles[]}`, with the owner as
   issuer `local`, forward-compatible with R16 identities.
5. Ollama under the DefenseClaw guard: out of scope here, but record the gap
   (spec 167 notes the provider list does not cover every runtime) for R05.

## Plan notes

- Thermidor's broker, model admission, approved execution and calculator
  execution modules are design references only (see the handoff); do not assume
  they exist in NetClaw, and do not import them wholesale.
- NetClaw starting points: `bgp/federation/risk.py`, `authorization.py`,
  `execution.py`, `controls.py`, `operator_policy.py`, `gait.py`, `audit.py`,
  and specs 056, 057, 165, 166, 167.
- Extend GAIT with principal attribution; do not build a second audit trail.

## Out of scope

Cloud deployment, multi-user, RBAC, write operations.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Parity matrix | Every Thermidor control mapped with status, file references and decision |
| Approved read | Local lab: approved pyATS `show version` through a member in production mode |
| Refusals | Altered arguments, expired approval, reused approval, missing approval, unknown device, disallowed command |
| Credentials | Provider key and device credentials absent from the Border and from model context |
| Guard | Direct agent or model call bypassing the guard is refused |
| Durability | Lost-acknowledgement drill yields reconciliation and no duplicate execution |
| Audit | GAIT entries carry the principal for approval, dispatch and result |
