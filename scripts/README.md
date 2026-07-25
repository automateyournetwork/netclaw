# Scripts directory

Installer, risk/iN2N helpers, and utilities. **Product deployables** for
Convergence live under `deploy/` and `services/` — not everything under
`scripts/` is day-to-day ops.

## Start here (Convergence)

| What | Where |
|------|--------|
| Product overview | [`docs/CONVERGENCE.md`](../docs/CONVERGENCE.md) |
| Env layout | [`docs/ENV-AND-LAYOUT.md`](../docs/ENV-AND-LAYOUT.md) |
| Stack (Docker/K3s) | [`deploy/convergence/`](../deploy/convergence/) |
| Alert / Nautobot webhooks | [`services/alert-receiver/`](../services/alert-receiver/) |
| Install | `./install.sh --profile convergence` then `./setup.sh` |

## Layout

```text
scripts/
├── install.sh / setup.sh / clean-slate.sh
├── lib/                 # catalog.sh, install-steps.sh
├── systemd/             # unit templates (HUD, alert-receiver, …)
├── ensure-guardian-claw.py
├── in2n-*.py            # risk border/member helpers
├── mcp-call.py          # MCP tool smoke
├── docs-site-to-pdf.py  # optional RAG site crawl
└── … historical lab / enablement helpers …
```

### Moved out of scripts/

| Path | Role |
|------|------|
| `services/alert-receiver/` | Alertmanager + Nautobot webhooks (host systemd) |

Install the unit from `scripts/systemd/netclaw-alert-receiver.service` (or the
copy under `services/alert-receiver/`).

## Historical / lab tooling

Many scripts under this tree were for **Part 15 BGP lab**, vendor enablement
(`*-enable.sh`), scans, and one-off migrations. They are not required for
Convergence site ops. Prefer `docs/CONVERGENCE.md` over running random
root-level scripts.

If you are specifically working BGP route-stability lab material, see
`specs/031-bgp-route-observability/` (if present) and related `docs/blogs/`.
