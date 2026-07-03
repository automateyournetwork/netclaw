# OpenClaw Token/Cost Exporter (pull)

A zero-dependency Prometheus exporter that surfaces NetClaw's LLM token and cost
usage for a **persistent** OpenClaw host, so the OBS-stack Prometheus can
**scrape** it directly.

This is the pull counterpart to the ephemeral demo VMs, which *push* via Vector
`prometheus_remote_write` because they have dynamic IPs and a 4-hour TTL. This
gateway is persistent on a stable IP (`192.168.3.252`), so scraping is simpler:
no Vector, no remote-write receiver.

## Data source

OpenClaw has no native `/metrics` endpoint and writes no token log. Usage lives
in the session logs — every assistant turn in
`~/.openclaw/agents/<agent>/sessions/*.jsonl` carries a `usage` block. The
exporter sums those per `(agent, provider, model)`.

- Checkpoint / reset / deleted session files are skipped (no double counting).
- Per-file results are cached by `(mtime, size)`; unchanged files aren't re-read.

## Metrics

Same names as the demo dashboard, with `instance="netclaw"`:

| Metric | Type | Labels |
|--------|------|--------|
| `netclaw_model_input_tokens_total` | counter | model, provider, agent, instance |
| `netclaw_model_output_tokens_total` | counter | model, provider, agent, instance |
| `netclaw_model_cache_read_tokens_total` | counter | model, provider, instance |
| `netclaw_model_cache_write_tokens_total` | counter | model, provider, instance |
| `netclaw_model_cost_usd_total` | counter | model, provider, agent, instance |
| `netclaw_model_calls_total` | counter | model, provider, agent, instance |
| `netclaw_model_call_duration_ms` | gauge | model, provider, instance |
| `netclaw_token_exporter_sessions` | gauge | instance |

> **Cost note:** `cost_usd_total` reflects the per-token prices in OpenClaw's
> model definitions. Cloud models currently have cost 0 in `openclaw.json`, so
> cost reads 0 until real prices are set (per-model `cost`, or
> `NETCLAW_TOKEN_PRICING_OVERRIDE`). Token counts are always accurate.

## Install (this host)

```bash
cp scripts/openclaw-metrics/openclaw-token-exporter.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now openclaw-token-exporter
curl -s localhost:9110/metrics | grep netclaw_model_calls_total
```

Config via env in the unit: `NETCLAW_INSTANCE`, `EXPORTER_PORT` (9110),
`OPENCLAW_HOME`.

## Scrape config (on the OBS VM Prometheus)

Add to `prometheus.yml`, then reload:

```yaml
scrape_configs:
  - job_name: netclaw-openclaw
    scrape_interval: 30s
    static_configs:
      - targets: ['192.168.3.252:9110']
        labels:
          instance: netclaw
```

```bash
# reload Prometheus (if --web.enable-lifecycle is set)
curl -X POST http://192.168.3.250:9090/-/reload
```

No `--web.enable-remote-write-receiver` needed for pull.

## Dashboard

The demo dashboard (`grafana-dashboard-netclaw-tokens.json`) works as-is; point
its variables at `instance="netclaw"` instead of `instance="netclaw-demo"`, or
duplicate the panels for both instances.

## Useful PromQL

```promql
# Tokens/min by model (last 5m)
sum by (model) (rate(netclaw_model_input_tokens_total{instance="netclaw"}[5m]) + rate(netclaw_model_output_tokens_total{instance="netclaw"}[5m])) * 60

# Calls by model
sum by (model) (netclaw_model_calls_total{instance="netclaw"})

# Cost/hour (once model prices are set)
sum(rate(netclaw_model_cost_usd_total{instance="netclaw"}[5m])) * 3600
```

## Quota-watch dashboard + alerts

`grafana-dashboard-netclaw-quota.json` and `prometheus-rules-netclaw-quota.yml`
give you a DeepSeek weekly-quota early-warning, since routine triage is now on
free local qwen and DeepSeek is the metered path.

Import the dashboard:

```bash
curl -X POST http://admin:admin@192.168.3.250:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d "{\"dashboard\": $(cat scripts/openclaw-metrics/grafana-dashboard-netclaw-quota.json), \"overwrite\": true}"
```
UID: `netclaw-quota-watch`. On import, pick your Prometheus datasource and set
the `weekly_token_budget` variable (see calibration below).

Install the alert rules on the OBS Prometheus (into its `rule_files:` dir), then
`curl -X POST http://192.168.3.250:9090/-/reload`.

### Calibrating the budget (important)

The Ollama Pro weekly cap is **GPU-time / usage based, not a token count**, so
the token totals are a *proxy*. Calibrate once:

1. Read DeepSeek's rolling 7-day tokens:
   `sum(increase(netclaw_model_input_tokens_total{model=~"deepseek.*"}[7d])) + sum(increase(netclaw_model_output_tokens_total{model=~"deepseek.*"}[7d]))`
2. Read the matching weekly usage % from the Ollama dashboard.
3. `budget = observed_tokens / (observed_percent / 100)`.
   (Data point: ~one heavy day of DeepSeek ≈ 9.3% of weekly, so a full week at
   that rate ≈ 200M tokens — the placeholder default.)

Set `weekly_token_budget` in the dashboard and replace `200000000` in the three
rule expressions with your calibrated value. Always treat the Ollama dashboard
as the authoritative quota figure; these are trend + early-warning.
