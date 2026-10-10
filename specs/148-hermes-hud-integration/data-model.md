# Data model: selected runtime and owned conversations

All runtime files below are private (directories 0700, files 0600, owner checked, atomic replacement, no symlink traversal). Browser projections omit paths, credentials, upstream IDs and private reasoning. Existing retention limits remain unless explicitly tightened here.

## RuntimeSelection / RuntimeInstallation

Persisted selection schema 1: `kind: openclaw|hermes`, `home: absolute canonical path`, optional OpenClaw `configPath`, `schemaVersion:1`. Stored at `${XDG_CONFIG_HOME:-$HOME/.config}/netclaw/runtime.json`. No credential or executable supplied by the browser. A selected home's `netclaw-hud/installation.json` owns a generated immutable UUID; migration associates legacy OpenClaw bindings with this ID explicitly.

Resolved server object: `installationId`, `kind`, `home`, `configPath`, `envPath`, `workspacePath`, `skillsPath`, `statePath`, selected component/interpreter identity, upstream revision, capability snapshot and compatibility status. Browser receives only the opaque installation ID, runtime label, safe version/capabilities and status. Config selection is immutable until HUD restart; concurrent instances cannot change another instance's resolver.

## CapabilitySnapshot

Each named capability has `state: supported|unsupported|unconfigured|unverified|unavailable|failed`, `reasonCode`, `observedAt`, `source`, optional `verificationId`. Registration and actual execution are distinct fields. A supported capability does not claim every provider/tool is healthy. Usage additionally carries `quality: reported|derived|unknown`, counters nullable, source and time. Never fill absent counters with measured zero.

Required names include chat, history, canvas, localAvatar, tools, skills, terminalIntentRead, terminalIntentApply, modelSelection, effortSelection, attachments, nativeUi, hostedAvatar, federation, usage, logs and each configuration action. Readiness stages: selection → installed → compatible → bridgeDiscovered → companionAuthenticated → protectedPolicyReady → providerConfigured; execution verification is a separate timestamp/result from an explicit test or actual request.

## HudOwnerBinding / Conversation

Existing owner cookie stays HttpOnly with current access protections; only its hash is stored. Binding schema 2 adds `installationId` and `runtimeKind`. Expiry/revocation is checked on admission, every history/status/approval/stop lookup and again after asynchronous work, before disclosure. Limits stay 30-day owner lifetime and maximum 500 task bindings unless current policy is stricter.

Conversation: opaque `conversationId`, owner binding reference, installationId, optional Canvas branch and parent IDs, state `open|busy|uncertain|archived`, timestamps and context digest. The HUD owns authorization; bridge ledger owns upstream mapping. Neither incoming Hermes IDs nor a claimed owner field create authorization. No global session-list fallback.

Canvas branches each map to a distinct conversation/session. Seed context references a verified ancestor prefix and digest, is text-only and at most 1 MiB, and is recorded once before first admission. Clients may supply their current branch text, but cannot claim other owners' IDs or use stored content with a different installation marker. New turns remain per-branch isolated.

## BridgeConversation / AgentRequest

SQLite tables (foreign keys enabled): installation metadata, conversation/session mappings, requests, sanitized event cursor metadata and approval records. Authoritative backend authorization remains in HUD bindings; ledger receives trusted scope only through private stdio.

Request fields: opaque requestId; installation/conversation IDs; browser retry nonce unique within owner+conversation; immutable body digest; opaque upstream session/run IDs (server only); idempotency key; admission timestamps; deadline; state; companion invocation-ledger references; native transcript lineage/interval when available; actual model/provider metadata; recovery reason. Persist before HTTP submission. A uniqueness constraint/transaction grants one active turn per conversation; concurrent conversations may run up to four at once. A duplicate browser nonce returns the same local request or conflict on body mismatch; it never creates another upstream run.

Allowed transitions:

```text
prepared → submitting → running → waiting_approval → running
                         ├→ completed | failed | interrupted
                         └→ stopping → cancelled | completed | failed | unknown
submitting → unknown             (lost admission response)
running/waiting_approval → unknown (deadline/connection loss with no reliable status)
known run after restart → status reconciliation → observed terminal state or unknown
```

`unknown` is an outcome, never success or an instruction to replay. Restart reconciles known run IDs read-only; no automatic POST. Uncertain conversations block another submission until known status is terminal, or the owner explicitly acknowledges uncertainty and opens a new conversation. Acknowledgment does not assert rollback or end the original process. Keep minimal uncertainty/admission records until owner-reviewed resolution; do not expire them solely because upstream idempotency retention elapsed. Normal completed request metadata retention is 30 days, within existing owned-history retention policy; expired owner records are inaccessible regardless of physical retention.

## ApprovalRecord / ExecutionEvidence

Approval records include exact request/run approval ID, owner/conversation/installation scope, safe action summary, current state and expiry. Only `once` or `deny` may be forwarded; no session/always/bulk choice. It cannot grant a tool absent from the policy or stand in for ServiceNow/Local-Lab authorization.

Execution evidence includes installation, conversation, request, run/session lineage, actual invocation ID, qualified tool/server identity, observed status/result digest and optional enforcement/audit references. The companion records it at the guarded invocation/result boundary under a trusted request scope; native transcript intervals are corroborating references only. A result must match the companion's actual invocation record for this request, including after compression or row rewrite. Partial/unmatched events remain `unverified`; they are not promoted through UI heuristics. Browser receives bounded redacted summaries, not raw environment/configuration or hidden reasoning.

`UncertaintyAcknowledgment` stores owner hash, installation ID, uncertain request ID, new conversation ID and timestamp. It is created only by the explicit browser new-conversation confirmation and validated against an owned uncertain request. The original request remains uncertain and locked against resubmission. Acknowledgment permits independent new work; it grants no execution permission and does not settle the original outcome.

## Browser workspace migration

New storage keys are schema-versioned by installation UUID. Stored payloads also contain origin identity, guarding against accidental key reuse. Existing legacy OpenClaw stores are copied with a migration marker and rollback backup only in the selected matching OpenClaw context. Legacy data of unknown origin remains preserved/read-only and requires explicit origin association; never infer ownership merely from visibility in another authenticated browser session. Existing server cookie ownership is required to reopen runtime transcript content. Switching runtime shows a preserved-other-installation state and sends none of that content to the active agent.
