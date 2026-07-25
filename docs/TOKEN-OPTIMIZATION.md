# Token optimization & HUD metrics

## Why `tokenOptimization` is not in `openclaw.json`

OpenClaw’s config schema **rejects unknown root keys**. Putting NetClaw’s
`tokenOptimization` block into `~/.openclaw/openclaw.json` causes:

```text
Gateway failed to start: Invalid config … status=78/CONFIG
```

That is why live homes often appeared to have “tokenOptimization turned off”:
the feature was never a first-class OpenClaw setting. The block lived only in
the **repo template** `config/openclaw.json` as documentation.

### Canonical live location

| File | Role |
|------|------|
| `~/.openclaw/netclaw-token-optimization.json` | NetClaw-owned flags (GCF default, footer, HUD) |
| `~/.openclaw-byrns-risk-*/netclaw-token-optimization.json` | Same for Risk of Claws members |
| `config/openclaw.json` (repo) | Template / docs only |

Example:

```json
{
  "enabled": true,
  "libraryPath": "src/netclaw_tokens",
  "gcfSerializationDefault": true,
  "footerDisplay": "always",
  "sessionTracking": true,
  "pricingOverrideEnvVar": "NETCLAW_TOKEN_PRICING_OVERRIDE",
  "hudMetrics": true
}
```

## What actually counts tokens

| Path | What it does | Visible where |
|------|----------------|---------------|
| **openclaw-token-exporter** `:9110` | Sums `usage` from session `.jsonl` | Prometheus / Grafana / **HUD footer** |
| **HUD** `/api/tokens/summary` | Scrapes exporter + last chat turn | Footer strip (Tokens / Last turn / GCF·opt) |
| **Chat reply footer** | Appends `Tokens: X in / Y out` when OpenAI-compat `usage` is present | Terminal message |
| **`src/netclaw_tokens` GCF/TOON** | Compresses *tool results* when MCP servers call `gcf_dumps` / serializers | Only if MCP implements it |
| **token-tracker skill** | Agent instruction to print footers | Only if the model follows the skill |

The HUD “Token Tracker” 3D orb is a **catalog card**, not a live meter.

## Keeping config rewrites from clobbering NetClaw flags

Scripts that rewrite `openclaw.json` must **not** invent OpenClaw-invalid keys.
Prefer updating `netclaw-token-optimization.json` separately.

## Related

- `scripts/openclaw-metrics/` — exporter unit
- `ui/netclaw-visual` — footer strip + `/api/tokens/summary`
- `docs/CONVERGENCE-ALERT-SAFETY.md` — investigation fan-out (token burn multiplier)
