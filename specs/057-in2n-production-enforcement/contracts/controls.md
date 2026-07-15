# Contract: Enforcement Control Probes & Application

`controls.py` provides the probes; `gateway.py` applies sandbox + guard at member execution. All fail-closed in production.

## Probes (`controls.py`)

```python
async def openshell_available() -> tuple[bool, str]:
    """(True, "") if the openshell sandbox is usable; else (False, reason).
    Probe: shutil.which('openshell') present AND a cheap `openshell` health/version
    exec returns 0. Cached ~3s."""

async def defenseclaw_available() -> tuple[bool, str]:
    """(True, "") if DefenseClaw guarding is reachable AND actually in effect;
    else (False, reason). Probe: shutil.which('defenseclaw') present AND guard/proxy
    health check (CLI status; falls back to a cheap inspect probe) AND
    security.mode == 'defenseclaw' in ~/.openclaw/openclaw.json. A merely-installed
    CLI with security.mode=hobby is NOT available (prevents a false 'enforced'
    claim — analyze finding I1). Cached ~3s."""

def gait_recording() -> tuple[bool, str]:
    """(True, "") if the GAIT repo at ~/.openclaw/n2n/gait is initialized and
    writable; else (False, reason)."""
```

## Member confinement (host-level systemd sandbox)

The member **process** is confined at launch (not per model turn) via systemd
sandboxing directives — so `run_agent_turn(local=True)` runs the member's real
command unchanged, contained by its unit:

```ini
# always-on member unit (scripts/in2n-services.py _hardening_block), portable set:
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ReadWritePaths=%h
InaccessiblePaths=-%h/.openclaw/.env
# + on a native-Linux manager (auto-detected): ProtectKernelModules, RestrictNamespaces,
#   RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6, SystemCallFilter=@system-service, …
```

```python
# on-demand cold-start (controls.confined_cold_start): transient hardened unit
systemd-run --user --collect --unit netclaw-coldmember-<slug> \
  -p NoNewPrivileges=yes -p ProtectSystem=strict -p InaccessiblePaths=-%h/.openclaw/.env … \
  /bin/sh -c "<launch_cmd>"
```

- `controls.sandbox_available()` → available iff `systemctl --user` reachable AND
  member units carry the confinement directives. If unavailable in production →
  refuse cold-start, posture `degraded(sandbox)` (FR-005, SC-002).
- WSL2/other managers that reject capability/namespace directives (`218/CAPABILITIES`)
  get the portable set; the full kernel set is added where supported.
- *(OpenShell containers were evaluated and rejected — empty, egress-denied; see
  research R2. OpenShell is not the member sandbox.)*

## Model-I/O guard + component scan (`gateway.py` / member (cold-)start, production only)

- **Component scan** (once per member start, cached in `member.component_scan`): `defenseclaw skill scan <each scoped skill/mcp>`; any flag → block that member, report (FR-008). *(Verified real: returns CLEAN/exit 0 for a benign skill.)*
- **Model-I/O guard = the DefenseClaw LLM guardrail PROXY**, not a per-call CLI. `defenseclaw setup guardrail` stands up a Go proxy (`:4000`) and patches OpenClaw to route the model through it for prompt/response inspection; `defenseclaw-gateway start` runs it. `controls.defenseclaw_available()` → available iff `defenseclaw` present AND the proxy reachable (`_guard_proxy_up()` → TCP `:4000`). *(There is NO `defenseclaw tool inspect` — that was a bug in 056/early-057; the per-tool block-list gate in `invocation.py` was corrected to `defenseclaw tool status`.)* The Border's own model turns are guarded because the gateway routes through the proxy; per-member proxy routing is a defined tightening.
- If `defenseclaw_available()` is false in production (proxy down) → the delegation **fails closed** (no unguarded provider), posture `degraded(model-guard)` (FR-009, SC-003).

## Acceptance mapping

- FR-004/005/006, SC-002 (sandbox = host confinement); FR-007/008/009, SC-003 (guard proxy + scan). Tests stub `sandbox_available`/`defenseclaw_available`/`confined_cold_start` deterministically (no live systemd/proxy needed).
