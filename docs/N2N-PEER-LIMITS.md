# NCFED peer limits (max-prefix-style)

Spec 189, issue #343. Normative text: `docs/ietf/draft-capobianco-ncfed-00.md`, section "Peer Limits".
The BGP maximum-prefix practice (warn threshold, hard limit, discard or teardown with a restart timer) is used only as an analogy.

## What counts

Counted (one request unit and one rate slot each): tool call, skill invocation, task submit, chat message, knowledge query, and every knowledge-replication request (manifest and each batch page).

Not counted: hello, heartbeat, capability-card/inventory exchange, task status/result/cancel, chat open/close.

A refused request never debits the budget. Tokens are charged after execution to a separate daily token budget.
Each batch page of a replication is a request, so replicating a large collection needs generous limits for that peer.

## Limits and scope

| Limit | Scope | Window | Default |
|---|---|---|---|
| `rate_per_min` | per peer | sliding 60 s | 10 (`N2N_RATE_PER_MIN`) |
| `daily_requests` | per peer | UTC day | 200 (`N2N_DAILY_REQUESTS`) |
| `daily_tokens` | per peer | UTC day | 500000 (`N2N_DAILY_TOKENS`) |
| global `daily_requests` / `daily_tokens` | all peers combined | UTC day | off (`N2N_GLOBAL_DAILY_REQUESTS`, `N2N_GLOBAL_DAILY_TOKENS`, or the `*` policy row) |

Precedence: per-peer override, then node-wide `*` row (action, warn threshold, restart timer; global caps), then environment.
The global cap has no rate component.

## Exceed actions (`N2N_LIMIT_ACTION`, per-peer `limit_action`)

| Action | Behavior |
|---|---|
| `refuse` (default) | Refuse with -32005 RATE_LIMITED or -32004 BUDGET_EXHAUSTED; channel stays up. Identical to behavior before spec 189. |
| `warn` | Allow the request, keep counting, write an audit record `limit_exceeded_warned`. Rate is advisory too. |
| `teardown` | Refuse, then close the peer's channel about 0.25 s later and refuse its channel attempts for the restart timer (`N2N_LIMIT_RESTART_S`, default 300 s). Consent is NOT revoked; the peer stays federated. The hold-down is stored in the database and survives a restart. |

Teardown applies to eN2N peers only. iN2N (internal member) channels are never torn down by a limit.
When the global cap is crossed, only the peer whose request crossed it is acted on.

## Warning threshold (`N2N_LIMIT_WARN_THRESHOLD`, default 0.8)

One audit record `limit_warning` per peer, per limit, per UTC day when daily requests or tokens reach the threshold (and for the global caps). Never visible to the peer.

## Recovery

Rate window slides. Budgets reset at 00:00 UTC (receiver clock). Hold-down ends at timer expiry or `clear_hold_down`. Operator `reset_limits` clears today's counters, the rate window, the warning latch and the hold-down.

## Configure (n2n_config tool or daemon `POST /n2n/config`)

```text
n2n_config(peer="as65007-7.7.7.7", daily_requests=500, limit_action="teardown",
           warn_threshold=0.9, restart_timer_s=600)
n2n_config(peer=..., reset_limits=True)       # audited reset
n2n_config(peer=..., clear_hold_down=True)    # end teardown early
```

Invalid values (negative numbers, threshold outside (0,1], unknown action) return HTTP 400 and change nothing. Setting a field to null in Python (`Authorizer.set_policy(peer, field=None)`) returns it to inheritance. Node-wide defaults and global caps use the peer identity `*` through `Authorizer.set_policy("*", ...)`.

## Visibility

`GET /n2n/status` adds a compact `limits` block per peer; `GET /n2n/peers/<id>` adds the full `limits` status (policy, usage, rate use, warnings, hold-down remaining, global usage). Audit rows use `target_type='limit'` with decisions `limit_warning`, `limit_exceeded_warned`, `limit_teardown`, `limit_hold_down_refused`, `limit_reset`, `limit_config` and are mirrored to GAIT by the existing auditor. Under `refuse` the existing denied-request audit row is the record.

## Relationship to issue #344 (read/write grants)

Spec 190 adds an access class to grants (`docs/N2N-GRANT-ACCESS-CLASS.md`). The class check sits after the grant lookup and before the counted-operation gates above: reads and writes are counted identically, and a request refused by the class check is not debited, takes no rate slot and never starts a warn or teardown action. Separate per-class budgets are not provided.
