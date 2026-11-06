# Plan: optional read-only VM Security panel

**Status:** scope proposal only; no implementation in this PR. Implementation starts
after the maintainer agrees to the scope.

## Access path

```text
Owned NetClaw HUD session
  → GET /api/hud/convergence/vm-security        (new, same guards as the flow routes)
    → convergence_vm_security()                  (new tool, no arguments)
      → GET /api/security/vms?site=<fixed site>  (existing service route, viewer key)
        → Convergence VM Security analysis       (service-owned)
```

The tool reuses `settings.py` (endpoint, site, viewer key, loopback opt-in) and the
transport in `client.py` (deadline, size limit, no redirects). Only the path and the
response validation are new.

## Proposed change inventory for the implementation PR

| Surface | Files | Change |
|---|---|---|
| Connector | `mcp-servers/convergence-read-mcp/{server.py,client.py,README.md}` | One tool and a strict projection of the VM Security contract; drop `hostTelemetry` |
| HUD server | `ui/netclaw-visual/src/hud-server/convergence.js` (+ test) | Add `vm-security` to the fixed tool map and mount one route |
| HUD view | `ui/netclaw-visual/src/dashboard/Convergence.jsx` or a new `ConvergenceVmSecurity.jsx` (+ tests) | Panel with findings, evidence and coverage; synthetic banner |
| Skill and docs | `workspace/skills/convergence-observations/SKILL.md`, `docs/CONVERGENCE.md` | How to read findings and their limits; setup is unchanged |
| Counts and catalog | `README.md`, `TOOLS.md`, `mcp-servers/README.md`, catalog metadata | Tool count 2 → 3 |
| Tests | `tests/convergence-read/`, `ui/netclaw-visual/integration/` | Fixtures and negative cases below |

No new component, dependency, credential or setting. The connector's isolated
Python environment and pins are unchanged.

## Validation the implementation must add

- **Fixtures:** each pattern; truncated findings; stale and unknown sources;
  null counter changes; stopped, unsupported and UUID-less VMs; a synthetic source.
- **Rejections:** wrong site; unknown pattern or state; examples not attributed to a
  listed VM interface; counts that disagree; timestamps outside the window;
  oversized or malformed bodies; timeout; redirect.
- **Access:** no session, wrong installation, cross-origin request. No credential in
  browser responses, logs or errors.
- **Side effects:** only `GET /api/security/vms` is requested.
- **Real run:** synthetic demo end to end in the HUD, and one live finding from a
  Proxmox VE observer, recorded with the service revision.
- **Compatibility:** an older service without the route leaves the flow view working.

## Sequence after agreement

1. Service: add the synthetic source and its label; publish a pinned revision.
2. NetClaw: tool and validation with fixtures (no HUD yet).
3. NetClaw: HUD route and panel.
4. Qualification on Linux, docs, counts and release metadata (minor version).

## Release and rollback

No version change for this proposal. The implementation is a minor release.
Disabling the integration removes the panel and the tool's requests, as today.
Rolling back the connector touches nothing in the service.
