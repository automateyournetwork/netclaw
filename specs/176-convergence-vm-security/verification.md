# Verification

This is a documentation-only scope proposal. No runtime result is claimed.

## Sources checked (2026-11-06)

- Upstream `main` `db0c9682` (1.18.6): `convergence-read-mcp` (`server.py`,
  `client.py`, `settings.py`), `ui/netclaw-visual/src/hud-server/convergence.js`,
  `src/dashboard/Convergence.jsx`, `docs/CONVERGENCE.md` and specs 161 and 162.
  The connector has two tools, and the HUD mounts three fixed routes behind the
  trusted-origin and owned-session checks.
- Upstream spec 091 and the `nsm-ids-triage` skill: offline capture analysis only.
- Convergence service at `024821c8`: `VM-SECURITY-CONTRACT.md`, `vm_security.py`,
  `routes/security.js`, `lib/vmSecurity.js`, `server.js` and `middleware/auth.js`.
  `/api/security` is mounted with the same `authMiddleware` as `/api/flows`, which
  scopes API keys to their sites.
- The fork is public, and the contract and tree links at `024821c8` return HTTP 200.

## Checks

- `scripts/verify-spec-artifacts.py`: PASS.
- `git diff --check`: clean.
- No version change, by the same rule as spec 161.

## Not verified

- Any NetClaw implementation; there is none.
- A live VM Security run or a synthetic demo source; the second does not exist yet.
- The service's tests were not rerun for this proposal.
