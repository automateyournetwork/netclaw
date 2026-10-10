# Runtime execution contract

Local selection controls execution. Received harness names are never executable selectors. `run_agent_turn` retains `(reply_text, tokens_used)` compatibility (usage may be unavailable) and accepts trusted context from ingress. Errors distinguish pre-dispatch refusal from possibly-executed failure; tasks preserve this distinction.

## Private Hermes bridge

A separate federation stdio MCP server provides status, conversation open/history, submit, request status and stop against the federation namespace. Official SDK lifecycle is mandatory. It is not registered with any agent. Caller supplies selected installation and backend-created execution scope; the private ledger validates/fingerprints it with the body and conversation before POST. Native request ID/run ID mapping and tool evidence survive process interruption. No retry submits uncertain work.

The companion shares pinned protected source but separate profile/session/ledger/key/port from HUD. Per-request allowed tools are a frozen intersection of local qualification, target dependency closure and member scope. Capture scope before the upstream thread handoff. Each tool verifies source/schema/handler, scope/deadline and current authorization, records dispatch durably, then executes. Peer chat gets no tools; subnet skill gets only subnet_calculator IPv4/24…/30; incoming federation never gets n2n orchestration.

## Private execution broker

Installation-owned loopback endpoint and private discovery/auth material. Receiver permits are created only at authenticated NCFED ingress. A check binds permit, request and exact tool arguments to still-valid authorization/scope. Operator effect permits are issued only to the private local companion using installation credentials, bound to conversation/request/tool-call/body. MCP process environment carries the opaque permit, never a model field. Calls are bounded and non-redirecting; failure denies before execution.

Allowlisted operator MCP operations: status, Risk/member health/list, peer capabilities, named invoke/delegate, route with qualified target, peer chat and owned task status/result. Initial executable target set is the qualified subnet tool/skill. No consent/grant/approval/trust/kill/member-admin/replication-mutation tools. No arbitrary local task reads. Store returned task/chat associations before returning; persistence failure leaves uncertainty and never authorizes a retry.

## Existing federation contracts

Keep wire methods and legacy readers. Add optional caller request UUID/body digest and origin fields; derive authenticated caller from channel, never the submitted text. Member trust caps origin rather than upgrading external input. New receivers deduplicate owner/request/body; old receivers are never assumed idempotent. Every outbound effect has local durable intent before send, whether or not remote deduplication is negotiated.

Revalidate admission after waits and consume exact approval once. Session identity includes installation+authenticated peer+chat session, or installation+owner+task for a skill. Internal empty scope denies. Direct Hermes tool execution uses the same selected/qualified registration policy and official MCP lifecycle, with timeout/cancel cleanup. Existing OpenClaw controls remain; no new trust in its prompt markers.

Unknown execution does not become failed/cancelled merely because the waiter or channel stopped. Cancellation responses identify request versus confirmation. Task result reads remain owner-bound. Post-dispatch inability to persist results must leave a durable uncertain task.

## Permit and scope validation details

Broker binds only loopback and a private installation discovery record (owner-only, no symlink); authentication secrets are random at least256bits. Receiver permit life is at most the admitted deadline; operator effect permits expire after30s and authorize one exact normalized operation/body. Readiness/authentication calls cap5s; broker body cap64KiB; peer/operator text cap64KiB; one run retains max30 agent iterations/16tools per batch. Expired tokens and restarted-broker tokens cannot dispatch. Never follow redirects or trust ambient HTTP proxies. Store only token hashes in durable records.

The initial executable names are exactly skill `subnet-calculator` and tool `subnet-calc-mcp/subnet_calculator`; arguments are one CIDR IPv4/24…/30. Member profile `subnet` provisions that closure. Model/provider selection remains member-specific. Peer chat is contextual text-only with no operational tools. No recursive external delegation is enabled in a Hermes receiver.

Operator effect admission is keyed by installation+conversation+request+tool-call with a canonical operation digest. A matching completed duplicate returns retained evidence; a mismatched duplicate is refused; a previously dispatched unresolved effect returns uncertainty without dispatch. Returned task/chat handles must be durably assigned to that conversation before exposure; reads require that assignment. Bound authorizer callbacks evaluate live channel/consent/grant/member scope and permit deadline at effect time. Approved grant consumption is not repeated on every tool but the consumed exact request and still-current grant must match each subsequent effect.

The broker is an internal authorization/control endpoint; actual agent tool integration stays the existing n2n MCP server with an official client. Never register private runtime control tools on an agent. Per-call server environment contains only required process/runtime bindings and the opaque permit. Prompt text and tool arguments carry no credentials or trust claims.
