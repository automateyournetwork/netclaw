# Contract: limit semantics (normative text source for the draft)

Counted ("limited operation"): n2n/tools/call, skill invocation, n2n/tasks/submit, n2n/chat/message, n2n/knowledge/query, n2n/knowledge/replicate_manifest and each n2n/knowledge/replicate_batch page. One unit each.
Not counted: hello/handshake, heartbeat, card/inventory exchange, tasks/status|result|cancel, chat/open|close.

Scope: per-peer always; optional aggregate (all peers) daily request/token caps.
Limits: rate (sliding 60 s), daily requests, daily tokens (UTC day).

Exceed actions (receiver-local policy, not negotiated, invisible on the wire except via the refusal and the channel closing):
- refuse (default): -32005 RATE_LIMITED / -32004 BUDGET_EXHAUSTED, channel kept.
- warn: request proceeds; receiver records the event. No wire signal.
- teardown: the refusal above, then the receiver closes the channel and refuses new channels from that peer until the restart timer expires (peer sees SEVERED -32007 or connection closure). Consent is not revoked.

Warning threshold: fraction of the daily request/token limit, default 0.8, once per limit per UTC day (receiver-local, audit only).
Recovery: rate window slides; budgets reset at UTC 00:00 on the receiver clock; hold-down ends at timer expiry or operator clear; operator reset clears counters, rate window, latch, hold-down.
Sender guidance: SHOULD treat -32004/-32005 as backpressure and not retry before the window/day; MUST NOT assume a closed channel means de-federation.

Config surface (reference implementation): env defaults N2N_RATE_PER_MIN, N2N_DAILY_REQUESTS, N2N_DAILY_TOKENS (unchanged), new N2N_LIMIT_ACTION (refuse), N2N_LIMIT_WARN_THRESHOLD (0.8), N2N_LIMIT_RESTART_S (300), N2N_GLOBAL_DAILY_REQUESTS / N2N_GLOBAL_DAILY_TOKENS (unset=off); per-peer overrides in peer_limit_policy via Authorizer.set_policy.

Python API (stable): Authorizer.set_policy(peer, **fields), get_policy(peer)->effective dict, clear_policy(peer), limit_status(peer)->dict, reset_limits(peer, actor), clear_hold_down(peer), hold_down_remaining(peer)->seconds, teardown_hook attribute. Decision gains `teardown: bool = False`.
