# R07 — Single-region recovery and transport lifecycle gate

- **Roadmap item:** gate before multi-region
- **Depends on:** R03, R04, R05, R06
- **Gate:** no multi-region work starts until this passes

## Specify input

Before adding Borders, prove the single-region system recovers safely from
transport and runtime failures. Every failure either recovers to the same
authenticated state or fails closed. Nothing falls back to a weaker transport and
nothing replays an uncertain action. Operators get a runbook for each scenario.

User stories:
- P1: Border and member restarts (plus optional tunnel/agent restarts) recover without re-enrollment.
- P1: Revoked tokens, certificates and members stop working immediately.
- P1: Lost replies, duplicate submissions and cancellations reconcile correctly.

## Clarify: decisions (recommended default first)

1. Recovery-time objectives per scenario: measure first, then set. [HUMAN]
2. Fallback to another transport during an outage: never automatic; an operator
   may switch transport explicitly through configuration.

## Acceptance evidence

| Scenario | Required outcome |
|---|---|
| Direct Border service restart | Same stable provider address; members reattach; no re-enrollment |
| Optional ngrok agent restart | Same reserved address; members reattach; no re-enrollment |
| Provider network/address unavailable | Fail closed; status shows the cause; no insecure fallback |
| Optional ngrok service/account unavailable | Affects only those deployments; no insecure fallback |
| Endpoint replacement | Members move to the new address through the registry; identity unchanged |
| Optional ngrok authtoken revocation | Tunnel stops; no NetClaw identity affected |
| Border restart | Pending work becomes reconciliation items; no replay |
| Member restart | Reattaches; in-flight work reconciled |
| Member key or certificate revocation | Immediate refusal on reconnect and on any open channel |
| Model provider outage | Refused at the guard with a clear status |
| Lost reply or acknowledgement | Reconciliation, no duplicate effect |
| Duplicate submission, cancellation | Exactly one effect or none, recorded |
| Runbook | One documented operator procedure per row |
