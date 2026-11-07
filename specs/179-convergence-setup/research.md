# Research

- **Service contract** (convergence-platform `v0.1.2`, `1e7900f`; the VM Security contract is unchanged since `v0.1.0`):
  `GET /api/security/vms` returns the assessment from `src/lib/vmSecurity.js` plus a
  `hostTelemetry` block. v0.1.0 adds `synthetic` (top level) and `kind` per source
  (`proxmox` or `synthetic`); `VM_SECURITY_DEMO=1` serves a synthetic assessment that
  passes the same validation as live data. The connector's test fixture is that
  service's real demo output.
- **Upstream integration conventions:** spec 162 (connector, HUD, member policy,
  installer access, catalog), the generated catalog (`config/components/catalog.json`
  canonical; `build-catalog.py` writes `scripts/lib/catalog.sh`) and standalone skills
  (19 catalog skills have no component).
- **DefenseClaw:** its skill scanner quarantined an earlier version of the setup skill
  that bundled Python helpers (a false-positive CRITICAL on a `docker inspect` format
  template). Keeping helpers in the service repository leaves a text-only skill.
- **Proxmox access:** the community [mcp-proxmox](https://github.com/gilby125/mcp-proxmox)
  covers discovery but cannot set cloud-init and disables TLS verification; provisioning
  uses the release's `proxmox.py` (verified TLS, range/prefix/tag guardrails).
