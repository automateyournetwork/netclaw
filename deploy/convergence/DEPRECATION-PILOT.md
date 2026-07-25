# Pilot external stack — deprecation path (067 T057)

## What is “pilot”

| Artifact | Location | Role during dual-run |
|----------|----------|----------------------|
| Full OBS + Grafana + VM + Loki | `~/k3s-observability-stack/` (external repo) | Live metrics + dashboards |
| Network Guardian Web | `network-guardian-web` Deployment in `observability` NS | Pilot diary + API |
| Pilot convergence-api k8s | `netclaw/ui/convergence-api/k8s/` | Deploys Guardian Web into pilot NS |

## Product path (in-repo)

| Artifact | Location |
|----------|----------|
| Docker Home | `netclaw/deploy/convergence/docker-compose.yml` |
| K3s Home | `netclaw/deploy/convergence/k8s/` |
| convergence-api source | `netclaw/ui/convergence-api/` |
| HUD | `netclaw/ui/netclaw-visual/` |
| Install profile | `./scripts/install.sh --profile convergence` |

## Migration order

1. **Dual-run** — HUD `HOME_API_URL` may still point at pilot Guardian.
2. **Docker or K3s Convergence** — stand up `netclaw-convergence` / compose; smoke.
3. **Point HUD** — `HOME_API_URL` + `HOME_API_TOKEN` to product convergence-api.
4. **Ensure guardian-claw** — `python3 scripts/ensure-guardian-claw.py` (idempotent).
5. **Alertmanager** — webhook stays on host alert-receiver (`:8099`).
6. **Decommission pilot Guardian Deployment only** after diary + HOME tab parity.
7. **Pilot Prometheus scrapes** can remain until Home metrics replace WAN/UniFi jobs.

Do **not** delete pilot Longhorn PVCs or Grafana until operators accept dashboards elsewhere (out of scope for 067 v1).

## Skill / config hardcodes

Skills under `workspace/skills/` may still mention pilot hostnames as **examples**. Prefer env:

- `PROMETHEUS_URL`, `HOME_API_URL` / `NETWORK_GUARDIAN_URL`, `ALERTMANAGER_URL`
- `DISCORD_ALERT_CHANNEL_ID` (not hard-coded channel ids in new docs)

`ensure-guardian-claw.py` and install profile `convergence` are the supported enrollment path; external-stack-only install is legacy dual-run.
