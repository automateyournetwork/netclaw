# NetBox HA member on the hosted Sonnet profile (stream N)

Status: source + tests only. Nothing here ran against Anthropic, NetBox, Docker or a Border. It is NOT qualified:
the hosted guard path has no REAL evidence yet (see `model-transport.md` gaps 1-13, plus the new ones below).

## What changed in product source (3 small edits, all under `mcp-servers/protocol-mcp/bgp/federation/`)

1. `protected_docker.validate_runtime_fields`: a `hosted` runtime may now bind `mcp.kind` in
   `{subnet_summary, netbox}` (was `subnet_summary` only; unknown kinds -> `hosted_mcp_kind_refused`). `ollama` is unchanged and
   still calculator-only (`ollama_native_summary_required`). Every other check still applies via `validate_mcp_binding`:
   exact https origin, `credential_file` (private, `NETBOX_TOKEN=` form), source closure incl. `netclaw_http.py`, tool
   `netbox_get_object_by_id` only, schema/selection/endpoint hashes, exact arguments, skill pin, immutable Python env.
   The tool-effect admission fence is the existing one: `invoke_mcp(..., ha_required=True, ha_admission=...)`.
2. `protected_hosted.py`: `ALLOWED_MODELS = (claude-sonnet-5-5, claude-sonnet-4-6)`, `profile_id` and `limits` follow the profile's
   model; `protected_docker.runtime_profile_revision` compares against the profile's own model. Reason: the DefenseClaw guard
   image copies `scripts/lib/protected_provider.py` at build time and refuses to start unless the operation model equals its
   `MODEL` (`claude-sonnet-4-6` in the existing R05 image). Sonnet 5.5 therefore needs a rebuilt, re-pinned guard image
   (change `MODEL`, build, new digest, review). 4.6 is the only model the current image can run.
3. `ha/hosted_model_transport.py`: documented and tested freshness window, plus `read_provider_fence()`.

## Window: why hosted is not subject to the 2.75 s band

Ollama handoff (`ha/model_transport.py`, in-container helper) needs `250 < admission_ms - elapsed <= 3000`. The hosted forward runs in the
member's own clock domain and needs only `250 < remaining <= 10000`. With a signed `admission_ms` of 4500 any elapsed time in
[0, 4250) hands off (tests: remaining 4400, 4300, 3001, 3000, 1500, 251 accepted; 250, 0, 10001 refused before connecting).
Also: the hosted path has no runner latch, so a refusal does not strand the member the way the Ollama latch did.

## Independent counter

`read_provider_fence(<operation_root>)` reads the guard's own durable `guard/provider.sqlite` (ProviderFence: one row per upstream
request with ordinal, state and upstream attempt count) read-only, counts only. This replaces the log regex as the primary
independent counter. The real file format is from `scripts/lib/protected_provider.py`; unobserved on a real run.

## Where the credentials go (no value is ever printed, logged, put in state/profile/contract or committed)

| Variable | Read by | Written to | Mode | Reaches |
|---|---|---|---|---|
| `ANTHROPIC_API_KEY` | `r09_member.py artifacts`, from the shell environment | `<member root>/artifacts/guard.env` | 0600, create-only | the guard container only (read-only bind mount at `/guard/guard.env`; the DefenseClaw child process gets only a placeholder `DEFENSECLAW_LLM_KEY`), then `api.anthropic.com:443` via the guard's fixed-host proxy |
| `NETBOX_TOKEN` | same step | `<member root>/artifacts/netbox-credential` (`NETBOX_TOKEN=...`) | 0600, create-only | the member host process, passed in env to the NetBox MCP subprocess, then `NETBOX_URL` (https origin pinned in the binding) |
| `NETBOX_URL` | same step | profile `mcp.origin` (not secret) | | |

Shell use: `( set -a; . ~/.openclaw/.env; set +a; python -m labs.ha.r09_member artifacts --root $M )`. The builder refuses a missing,
short, non-ASCII or equal credential and names only the variable. A pytest greps the whole member root: the (fake) values appear only
in those two files.

## Unqualified / unverified (explicit)

- Derived hosted guard config: transformed from the pinned R05 DefenseClaw v9 config; passes `protected-guard.verify_config` and
  `load_guard_env` in tests, but has not been accepted by the real DefenseClaw gateway binary. A rejection fails at guard start,
  before any model call.
- Network egress is NOT filtered: the hosted guard runs on Docker's default bridge; only the guard's proxy code pins
  `api.anthropic.com:443` (default TLS context, proxy env removed). A compromised guard container could reach any host.
- No spend meter (per-operation caps only: 2 inference calls, 1 tool call, `max_output_tokens` 1024).
- Sonnet 4.6 harness behaviour with this tool schema is the spec 171 qualified path; 5.5 is untested end to end.
- `mcp-servers/netbox-mcp-server` is an ignored nested git clone (`.gitignore: mcp-servers/*`), not part of this repository. Only its
  `netbox_client.py` is hash-gated (by `scripts/netbox-compat.py`); the whole copied tree is pinned at freeze time.
- The fastmcp<3 env is built from unpinned ranges over the network (PyPI); it is immutable and hashed afterwards, not reproducible.
- Combined multi-member requests stay Ollama-only (model-transport.md gap 8).

## Live runbook (parent runs these; PY = the scratchpad venv python, G = current deployment root)

```
cd /Users/john.capobianco/netclaw
PY=/private/tmp/claude-503/-Users-john-capobianco-netclaw/8e4f7aba-bfb3-4565-9ae8-2535153d5ff0/scratchpad/r09venv/bin/python
G=~/.local/share/netclaw/r09-gen4-20261109   M=~/.local/share/netclaw/r09-member-netbox-20261109
$PY -m labs.ha.r09_member identity    --root $M --deployment $G --flavor netbox
$PY -m labs.ha.r09_member freeze      --root $M
$PY -m labs.ha.r09_member python-env  --root $M                       # reuses the R04A member env
$PY -m labs.ha.r09_member netbox-env  --root $M --build --yes-network # uv + brew python@3.12; PyPI only
( set -a; . ~/.openclaw/.env; set +a; $PY -m labs.ha.r09_member artifacts --root $M )
$PY -m labs.ha.r09_member materialize --root $M
$PY -m labs.ha.r09_member validate    --root $M                       # expect role_validate=valid, closure_import=ok
# enroll exactly as for the calculator member: scripts/ + labs/ha/r09_vm_enroll.py with $M/identity/member.json
# (stop 3 Borders, wait for lease expiry, enroll as Border 0, restart Montreal first), then start the member with the
# production launcher (cwd = $M/home, env -i PATH=/usr/bin:/bin HOME=$M/home) on the Mac; verify attachments == 3.
# Then prepare/approve netbox_get_object_by_id dcim.device 27 from the HUD or VS Code (two members now: pick by member_id).
# After the run: read_provider_fence(<member runtime>/<operation_id>) for the independent count; compare the NetBox object's
# last_updated before/after (a read changes nothing).
```

## Live finding 1 (hosted NetBox member, gen4): two causes, both fixed in source

Symptom: Border stuck at `dispatch_claimed`, member `protected_executor` then silence, `ha-admission.sqlite3` empty, `cleanup.json` lists only the guard.
1. **Wrong guard management port.** `protected_docker.guard_health_probe(None)` (every non-Ollama guard) queries the guard's management API on
   **4001**. The hosted guard config was derived from the R05 Ollama DefenseClaw config whose `gateway.api_port` is **18970** (the Ollama probe
   port). Every probe was refused, `start_guard` gave up after 40 tries (~15 s) with `guard_not_ready`, before any relay/agent container, model or
   tool admission existed. Evidence: guard `config.yaml` has `api_port: 18970`, no `qualified-health.json`, timing 13:28:54 -> 13:29:09.
   Fix: the builder rewrites `gateway.api_port` to 4001 (`HOSTED_GUARD_API_PORT`); a test pins it to the probe's port.
2. **Silence on executor failure (product gap).** `run()` raised the refusal inside `async with mcp.session_manager.run()`, an anyio task group, so
   it left as an `ExceptionGroup`. `ProtectedOperations._execute` then saw a non-`ProtectedError`, recorded `outcome_unknown`
   (`effect_outcome_unknown`) and sent no result although the effect was never claimed (member store: effect_claimed 0). Reproduced in the member
   env (Python 3.12, mcp 2.x). Fix, hosted path only: re-raise the lone `RuntimeRefused`/`RuntimeUnknown` from a single-member group
   (`_single_protected_error`), so an unclaimed effect becomes a signed refusal and an unknown stays unknown.
   NOT changed: the Ollama path has the same wrapping and was therefore also silent on refusals (it likely explains the earlier stranded
   operations whose member state was `outcome_unknown`). Extending the fix to Ollama needs your review of a qualified path.

## Live finding 2: hosted guard config must be the qualified Anthropic file (fixed)
The real guard answered `finish_reason content_filter: provider "" is not supported by DefenseClaw guardrail - traffic blocked` because the config
derived from the Ollama config lacked `llm_role: judge_and_agent`, the llm/api_key_env/forward_custom_headers shape, `gateway.fleet_mode/token_env`
and `ai_discovery`, and set `allow_empty_providers`/`allow_unknown_llm_domains` false. `r09_member.py` (netbox and pyats flavors) now loads the
qualified file `roadmap-r04a-20261103/cloud-plan/member-inputs/guard-config.yaml`, refuses it unless its sha256 is
`1fdc7ab5...fa26b` (the hash that directory's manifest.json pins), and uses it byte for byte for `claude-sonnet-4-6` (only the model string is
swapped for another model, which also needs a rebuilt guard image). `gateway.api_port` is 4001, matching the health probe. Policy pinning:
the R04A `official-policy-manifest.json` hash is `0c9ad2c8...` = the R05 template's `policy_manifest_sha256`, so the pin is unchanged;
`guard_policy_sha256` is recomputed from the new `config_sha256` at materialize. `protected_hosted.py` references no config values.
