# Spec 167: Production-mode Risk qualification with the DefenseClaw model guard

Created 2026-11-01; branch `167-production-mode-qualification` (stacked on spec166 /
upstream PR #313); status: research and qualification. Owner asked to keep working
after #313; this closes the gap both #312 and #313 record: production mode end to end.

## Problem

`N2N_RISK_MODE=production` refuses every delegation unless the sandbox, model-guard
and audit controls pass. Model-guard requires DefenseClaw, `security.mode`
`defenseclaw`, a reachable guardrail proxy on loopback :4000 and every model
(primary, override, fallbacks) using a `defenseclaw/<model>` provider that targets
that port. Production cold start (spec166) and the member hardening (spec165) have
only unit-test evidence in production mode. The test VM's provider is Ollama Cloud,
which NetClaw's DefenseClaw docs do not list.

## User scenarios and acceptance

1. P1: On the dedicated VM, an operator following NetClaw's documented DefenseClaw path
(pinned, reviewed installer; no unreviewed remote script execution) reaches posture
`production - enforced` with the Convergence member, or the exact blocking gap is
recorded with evidence and, where it is NetClaw's, fixed under this spec.
2. P1: In production mode a delegated Convergence task cold-starts the on-demand member
as a confined system instance, the model I/O of Border and member passes through the
guardrail (observable in DefenseClaw audit), and the answer meets the spec165 R1-R6
rubric. Component scan runs before the member.
3. P1: Removing or stopping a control (proxy down, template removed) degrades the
posture and refuses delegation fail-closed, without an unconfined or unguarded run.

## Boundaries

Test VM only; no production NetClaw changes. Third-party installers are fetched, read
and pinned to a reviewed release before running. Provider runs are counted; Ollama
Cloud support through DefenseClaw is a research question, not an assumption.
