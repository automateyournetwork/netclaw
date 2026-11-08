# Hosted-model protected profile (T015-T020)

Owner decision (2026-11-08): HA Borders use a hosted foundation model (`claude-sonnet-5-5`, Anthropic API).
No Ollama and no local model on Borders. This note records the coupling found in the source, the design that
was implemented, and the **gaps that remain**. Nothing here is "qualified": R08 qualification evidence does not
transfer and a REAL run is still required.

## 1. Exact Ollama coupling points (all under `mcp-servers/protocol-mcp/bgp/federation/`)

| Where | Coupling |
|---|---|
| `protected_docker.py` `validate_runtime_fields` | accepts `_MCP_RUNTIME_FIELDS` or `... | {'ollama'}` only |
| `protected_docker.py` `runtime_profile_revision` | `'ollama' in config` branch pins provider/model/profile id; the non-Ollama branch pins `claude-sonnet-4-6` (spec 171) |
| `protected_docker.py` `validate_execution_bindings` | operation limits (2 inference calls, 1 tool call, timeouts) enforced only when `'ollama' in config` |
| `protected_docker.py` `DockerExecutor.__init__` | `self.ollama`, `RunnerLatch` bound to the Ollama profile |
| `protected_docker.py` `DockerExecutor.run` | `ha_admission is not None and not self.ollama` -> `ha_runtime_unqualified` |
| `protected_docker.py` `DockerExecutor.forward` | HA (`'cluster' in payload`) is reachable only inside the `self.ollama is not None` branch and calls `ha.model_transport.ha_model_forward` |
| `ha/model_transport.py` | requires `guard_url == docker-exec://<ollama model_container_id>/127.0.0.1:4000`, forwards to `X-DC-Target-URL: http://127.0.0.1:11434` through a helper executed inside the model container |
| `ha/member.py` lines 18 and 61 | `executor.ollama` must be truthy |
| `protected_ollama.py` | pinned runner digests, store closure, nftables confinement proof, container inspection (unchanged; its source hash is pinned by `_OLLAMA_SOURCE_PIN`, so it is NOT edited) |

Already hosted-capable and reused unchanged: the spec 171 path starts the DefenseClaw guard on a bridge network
with a loopback-published port (`--publish 127.0.0.1::4000`), mounts the guard env file read-only (the provider
credential lives only there, never in the Border process), and `forward()` already POSTs to
`<guard_url>/v1/chat/completions` with `X-DC-Auth`.

## 2. Design

New config key `hosted` (mutually exclusive with `ollama`), strictly validated by
`federation/protected_hosted.py`:

```
{schema_version:1, provider:"anthropic", model:"claude-sonnet-5-5", egress_host:"api.anthropic.com",
 max_output_tokens, call_timeout_seconds, task_timeout_seconds}
```
- Exact field set (no extras), type and bound checks; `model` and `egress_host` are single pinned constants.
- **No key material is accepted**: any field resembling a credential (`key`, `token`, `secret`, `authorization`,
  or a value matching `sk-`/`sk-ant-`) is refused. The API key reaches only the guard container through the
  existing read-only `guard.env`; it is never in the manifest, profile, audit rows, logs or error text.
- Profile id `hosted-anthropic-claude-sonnet-5-5`; `profile_binding()` hashes the profile, limits and prompt
  version into the runtime revision (`runtime_profile_revision` gains a `hosted` branch and
  `hosted_source_sha256`, mirroring `ollama_source_sha256`).
- Limits: 2 inference calls, 1 tool call, `inference_timeout_ms <= call_timeout_seconds*1000`,
  `expires_at_ms - issued_at_ms <= task_timeout_seconds*1000` (parity with `validate_execution_bindings`).
- `DockerExecutor` gets `self.hosted`; `run()` admits HA when `ollama or hosted`; `forward()` routes
  `'cluster' in payload` with `self.hosted` to `ha/hosted_model_transport.ha_hosted_model_forward`.
  `ha/member.py` accepts `ollama or hosted`. The Ollama path is byte-for-byte unchanged in behaviour.
- `ha_hosted_model_forward` (host-side, one clock domain, so no cross-clock helper is needed):
  consumes the existing `EffectScope('model')`; refuses before handoff unless the remaining admission budget
  exceeds the clock allowance; calls `permit.handoff('model')` immediately before the single send; **one
  request, no retry, no redirects, `trust_env=False`**; deadline = min(remaining, inference timeout);
  response capped at 1 MiB and must be JSON; after handoff every failure (timeout, reset, non-200, oversize,
  invalid JSON) raises `RuntimeUnknown('model_handoff_unknown')` so the caller keeps the fence and never
  retries; before handoff failures raise `RuntimeRefused`. Error text is fixed vocabulary only.
- **Independent request counter**: `count_guard_requests()` counts `POST /v1/chat/completions` lines in the
  guard container's own `json-file` log (log driver already pinned for `'cluster'` payloads), read by the
  qualification harness with `docker logs`, never by the Border process under test.

## 3. Gaps (explicit; no parity claimed)

1. **DefenseClaw upstream target is unverified.** The Ollama path forwards with `X-DC-Target-URL` to a local
   port. For a hosted upstream the guard's pinned config (`config_sha256`) must name the Anthropic provider;
   this was not exercised (no guard/Docker/network in this stream). Prompt/completion inspection coverage for
   the hosted path is therefore **unproven** until a REAL run shows guard ingress counts and inspections.
2. **Egress allowlist is not enforced by product code.** `egress_host` is a pinned declaration validated in the
   profile, but nothing here blocks other destinations. Needed on the VM: a host rule limiting the guard
   container's egress to `api.anthropic.com` (resolved IP set or an egress proxy); GCP firewall rules cannot
   filter by FQDN without a paid feature. Tracked as a deploy task.
3. **No confinement proof/container-inspection parity** for the hosted guard on a bridge network (the Ollama path
   verifies network namespace, nftables and read-only mounts). `inspect_guard` for the bridge guard is the
   existing spec 171 check only.
4. **Sonnet 5.5 is not in the spec 171 qualified harness list** (that path pins `claude-sonnet-4-6` for the
   OpenClaw/Hermes harnesses). The hosted branch pins `claude-sonnet-5-5`, but the agent harness behaviour
   with that model (tool-call format, 2-call limit) is unverified.
5. **Provider charge cap**: the Ollama profile has `provider_charge_microusd: 0`; hosted calls cost money. A
   per-operation token cap is enforced (`max_output_tokens`), but no spend meter exists.
6. **No REAL evidence.** Unit tests use controlled in-process guards only. R08 qualification rows must be re-run
   on the hosted profile before any HA-protected-effect claim.

## 4. Implementation status (stream C, 2026-11-08)

Files: `federation/protected_hosted.py` (new), `federation/ha/hosted_model_transport.py` (new),
`tests/n2n/test_ha_model_transport_182.py` (new). Minimal guarded edits: `federation/protected_docker.py`
(`validate_runtime_fields`, `runtime_profile_revision`, `validate_execution_bindings`, `__init__`, `run` gate,
`forward` routing, hosted source pin) and `federation/ha/member.py` (accept `ollama or hosted`).
`protected_ollama.py` is untouched, so `_OLLAMA_SOURCE_PIN` is unchanged. Not committed.

Tests: `python3.10 -m pytest tests/n2n/test_ha_model_transport_182.py` -> 56 passed, 1 skipped (the member test
skips here because `service_identity` is not installed; it must run on Linux CI). Regression check on the
existing suites (`test_ha_*_179.py`, `test_protected_*.py`, python3.10, this macOS env,
`--continue-on-collection-errors`): **identical before and after** (849 passed, 32 failed, 165 errors, 1 skipped on
BOTH a pristine HEAD worktree and the edited tree; same 197-name failure/error set). Those failures and errors are
pre-existing in this environment (missing `service_identity`, python3.10 vs the 3.12 contract env, macOS
differences) and are NOT evidence either way for Linux CI. The contract env `.contract-test-envs/n2n` (3.12)
lacks `pytest-asyncio` and `service_identity` on this machine, so it could not run the async suites.

## 5. Additional gaps found while implementing

7. **Member tests could not be collected locally** (`service_identity` missing), so `ClusterMemberOperations`
   behaviour with a hosted executor is covered only by a test that skips here. Run it on Linux CI.
8. **Combined (multi-member) requests remain Ollama-only** (`protected_contract.py` and `protected_calculator.py`
   select model profiles with `provider == 'ollama'`). Hosted HA covers single-operation protected requests only.
9. **Native tool contract for hosted**: `validate_tool` only applies the summary calculator contract to the
   Ollama provider; a hosted profile falls through to the legacy `subnet_calculator` argument rules. The HA
   config path still demands `mcp.kind == 'subnet_summary'`. This pairing is unexercised end to end.
10. **Transport was only exercised against loopback fakes.** HTTP parsing is hand-written (content-length and
    chunked, 1 MiB cap, 16 KiB header cap, 200 only, no redirects); it has never talked to the real DefenseClaw
    guard. Real response framing (streaming/SSE, compression) is untested.
11. **Admission upper bound** in the hosted transport is the manifest maximum (10000 ms), unlike the Ollama
    helper's hard 3000 ms. A larger `admission_ms` (planned for WAN, research D2) widens the stale-proof window;
    this must be justified by the measured RTT and recorded.
12. **Independent counter** is a log parser only; the guard's actual log format was not observed, so the regex is
    an assumption to be confirmed against a real guard log before it is trusted as evidence.
13. `.env.example` was not changed (shared file). The Border process holds no provider key; the key goes into the
    guard env file (`guard.env`), whose creation/pinning is a deploy task.
