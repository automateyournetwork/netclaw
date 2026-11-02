# Spec 169: Timed-out member turns record why

Created 2026-11-02; branch `169-task-timeout-error` from upstream main (1.18.1);
status: implementation and verification. Follow-up recorded in spec168's verification:
a member turn that hits its time budget leaves an empty task error.

## Problem

`gateway.run_agent_turn(local=True)` bounds the embedded `openclaw agent --local` process
with `asyncio.wait_for`. On expiry it kills the process and re-raises `wait_for`'s own
`TimeoutError`, which has no message. `TaskManager.run` stores `str(e)` as the task's
error, so the member's task result, and the Border's `GET /n2n/tasks/<id>`, report
`failed` with an empty error, and the member's log reads "Task <id> failed: " with
nothing after it. An operator cannot tell a timeout from any other failure. The gateway
(non-embedded) path already raises a `TimeoutError` with a message.

## User scenarios and acceptance

1. P1: An embedded member turn that exceeds `timeout_s` fails with "agent turn for
   session '<session>' timed out after <timeout_s>s"; the process is still killed and
   reaped first.
2. P1: Any task worker exception without a message records the exception's type name
   (for example `TimeoutError`) as the task error and in the failure log line, instead
   of an empty string. Exceptions with a message are recorded unchanged.

## Boundaries

Time budgets, task states (`failed` vs `outcome_unknown`), cancellation and the gateway
path are unchanged. The visualization member's token use (the cause of the timeout seen
in spec168) is a model and skill matter, not addressed here.
