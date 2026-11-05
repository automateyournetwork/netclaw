# Ollama execution profile contract

Status: design for implementation; no current NetClaw qualification claim.

## Identity and immutable selection

Add explicit revisioned `ollama-cpu-ipv4` and `ollama-cpu-ipv6` profiles. Bind member
installation/generation, runtime image/version, model manifest+layers, prompt
adapter digest, native tool schema/source digest, guard policy, limits and placement
in `profile_revision`. Existing hosted profiles/historical serializations are unchanged.
No capability may select an arbitrary provider, URL, path, model or command.

| Field | ARM64 on-prem | AMD64 GCP |
|---|---|---|
| Runner/model | Ollama0.40.11 / qwen3:0.6b Q4_K_M | Same |
| Context/output/turns/tool calls | 16,384 /1,024 /2 /1 | Same |
| Model CPU/RAM | 2 /2,048MiB | 1 /2,048MiB |
| Agent RAM | 1,536MiB; swap disabled | Same |
| Cache | q8_0 + flash attention | Same |
| Per-call / task deadline | 60s /180s | 120s /180s |
| Idle retention | 30s | 120s |
| Provider charge ceiling | 0 | 0 |

Use the complete architecture image/manifests/layers in Thermidor's hashed
`labs/ollama/model-lock.json`, including license provenance; verify bytes before
admission. Model manifest `7df6b6e09427a769808717c0a93cadc4ae99ed4eb8bf5ca557c90846becea435`;
weights `7f4030143c1c477224c5434f8272c662a8b042079a0a584f0a27a1684fe2e1fa`,522,640,096bytes.
Fresh NetClaw prompt/schema/guard revision hashes are required after adaptation.

## Guard and confinement

Thermidor qualified DefenseClaw source `46f444a78a88de6b4c25e8f7fa67562873a4b242`.
Probe the actual selected NetClaw binary for the same narrow capability. The
trusted admission layer injects fixed `X-DC-Target-URL: http://127.0.0.1:11434` only
for this profile and the signed two-turn capability. Reject caller-supplied target,
model, routing headers, inference controls, provider credentials and arbitrary tools.
Keep strict/action/closed inspection; no dummy API key or general private-upstream grant.
Readiness fails closed if capability/identity/integrity cannot be established.

Only guard UID may initiate the model API connection in the owned member namespace.
Model UID may reach its owned internal worker endpoints in32768–65535, excluding
all broker/guard/service ports (Thermidor excluded49171; discover actual NetClaw
assignments). Agent, tool broker, sibling member, Border and external namespaces
cannot reach11434 or use a forwarded alternative. No published port, host networking,
Docker socket mount, unbounded egress or model management API. Inspect kernel/container
state and test admitted positive controls beside every negative probe.

## Prompt and native MCP result

Port calculator-v4's immutable two-turn pattern, adapting only the exact native
tool/schema/argument names. Bind template bytes to the profile. Set trusted
`reasoning_effort=none`; preserve actual assistant/tool messages and IDs. Prose,
bare JSON, no tool call, extra calls, altered arguments and invented tool output
fail. The guard/broker revalidate the signed exact CIDR and one tool call.

First qualify/pin corrected existing subnet MCP source or apply the tracked bounded
summary/IPv6 patch. The inspected clone lacks IPv6 and has unbounded IPv4 iteration.
Only then discover native `subnet_calculator` and `subnet_calculator_v6` from the
actual source-pinned process; installer application must verify source/patch hashes. Preserve the old R04 IPv4 profile; the new summary profile
uses strict canonical CIDRs of its family over prefix0–32 or0–128. No host iteration.
Normalize tool output into bounded factual JSON and independently compare against
integer address arithmetic. Exact address/subnet counts travel as decimal strings;
absent optional neighbor fields at address-space edges are explicit. Native approximate
notation is validated and normalized, never trusted as an exact integer.

The scoped model-facing facade emits one compact JSON text content block, with no
duplicate structuredContent. Retain original native result digest in private evidence.
Bound native result1MiB and normalized output32KiB; enforce existing stricter bounds
where applicable. A mismatch or unrecognized native shape fails; it cannot be filled
by model narration. Maintain wire tests over real OpenClaw requests.

## Durable accounting and recovery

Persist a claim before forwarding each inference request; bind exact canonical
request digest, ordinal, operation/profile and expiry. Maximum2 dispatches total.
Completed identical request may return the stored response; claimed/unknown may
not forward again. Never reset a claim after timeout/restart or rotate operation
IDs automatically. A new operation needs a new reviewed approval.

Maintain a second member/provider-instance busy/uncertain latch with operation
attribution, shared across all operation IDs. Persist it before dispatch. A fresh
ID or process restart cannot bypass an uncertain runner. Clear that latch only
after verified termination/recovery of its owned process tree; prior request
claims remain spent.

Successful child: two measured inference turns, exactly one native MCP invocation,
verified arithmetic, actual tokens/time/resource observations, no hosted provider
key or call, signed result and durable ACK in the existing NetClaw ledger. Missing
metrics are unknown, not zero. Evidence export/reconciliation and process recovery
are separate checks. Verified owned-process termination is required to clear a busy
provider for fresh work; it never authorizes replay of an old child.
