# Plan

- Connector: `convergence_vm_security` in `server.py`; `validate_vm_security` and
  `ConvergenceClient.vm_security` in `client.py`. Member policy and installer access list
  the tool.
- HUD: `vmSecurity` in the fixed tool map, `GET /api/hud/convergence/vm-security` (no
  query arguments), `ConvergenceVmSecurity.jsx` inside the Convergence view, loaded on
  request.
- Skills: new `convergence-setup` (text only, pins `v0.1.2`); `convergence-observations`
  gains VM Security guidance. Catalog entries and digests; HUD integration prefixes.
- Docs: `docs/CONVERGENCE.md` (VM Security, setup, release pin), `docs/CONVERGENCE-LINUX.md`
  (release clone, `setup/` helpers, `--vm-security-demo`), README, SOUL, TOOLS, MCP READMEs.
- Integration test and its workflow pin convergence-platform `v0.1.2` and enable the
  demo bundle's VM Security source.
- Release 1.19.0 (new capability).
