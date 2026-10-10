# Data model: Hermes NCFED federation

## InstallationContext

Local immutable kind (`openclaw`/`hermes`), canonical home/config/env/skills paths, installation UUID, N2N base, selected API and recorded interpreters. Created by local selection, never a peer card. A private ownership record fences an explicitly relocated base. Preserve default OpenClaw legacy state.

## HarnessDescriptor

`type`: safe bounded name or null; `version`: safe bounded software version or null; `source`: local-observation/peer-advertised/member-advertised/unknown; `observed_at`: bounded timestamp or null; `status`: known/unknown/unrecognized. Card freshness is retained separately at receipt. Invalid extension fields do not invalidate the legacy inventory. `runtime_kind` retains deployment meaning. External Border card contains no per-member enumeration.

## ExecutionContext and permit

Installation, local runtime, authenticated requester, origin (operator/internal/external), request/task and conversation identity, target type/name, body digest, grant/approval identity, qualified profile, deadline and parent correlation. Persist before admission. A private opaque permit authenticates current authorization checks and one exact tool call; cannot be modified by model input. Owner/task associations persist; raw permit secrets do not appear in cards/logs/results. Permit expiration/revocation or service restart prevents new effects.

## DelegatedTask migration

Keep existing task_id/direction/peer/target/result fields. Add nullable context, installation/runtime, request deduplication key/body digest, dispatch_started_at, execution_ref, cancel_requested_at and usage_status; preserve legacy records. Active states submitted/working/awaiting_approval/stopping; settled completed/failed/cancelled; outcome_unknown represents potentially executed work without a confirmed result. Lookup unknown continues to mean unknown/not-owned task and is distinct.

Persist dispatch before external effect. Pre-dispatch denial/failure is known not executed. Cancellation after dispatch is stopping then outcome_unknown unless actual adapter confirms cessation. Restart never recreates workers from tasks. Known execution references may be reconciled read-only. Retention never sweeps active or uncertain records. Null usage stays unavailable; actual0 is measured only with supporting evidence.

## ExactApproval

Existing invocation approval bound to authenticated requester, installation, target, request/body digest and original grant. Approval expires even after the human resolves it. Atomically consume one approved decision at dispatch, only after current grant/consent/scope/budget checks. Reuse/mismatch/replacement/expiry fails closed.

## OperatorEffect and owned handles

Private broker admission keyed by installation+conversation+request+tool-call, canonical operation digest, dispatch state and result evidence. Duplicate identical completed calls may return stored evidence; unfinished/unknown effects are not replayed. Scope-owned remote task/chat references bind retrieval to the initiating conversation. A lost upstream submission response retains the caller-generated intent and uncertainty.
