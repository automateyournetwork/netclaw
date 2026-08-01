# T041 — Overlay notes: NetClaw Convergence k8s vs pilot OBS

Pilot source of truth (this host / fork):

| Path | Role |
|------|------|
| `~/k3s-observability-stack/k8s/observability/` | Full OBS: Prometheus, AM, blackbox, UniFi exporter, VM, Loki, Grafana, … |
| `netclaw/ui/convergence-api/k8s/` | Pilot Network Guardian Web + `guardian-postgres` in `observability` |
| `deploy/convergence/k8s/` (this tree) | Productized Home minimal stack (080 Phase 4) |

## Namespace and naming

| Concern | Pilot OBS | Home k8s base (greenfield) |
|---------|-----------|----------------------------|
| Namespace | `observability` | `netclaw-convergence` |
| Postgres | `guardian-postgres` (db/user `guardian`) | `postgres` (db/user `home`) |
| convergence-api / web | `network-guardian-web` Service port **80** → 3000 | `convergence-api` Service port **3000**; NodePort **30080** |
| Prometheus | `prometheus` ClusterIP | same name, **different namespace** |
| Alertmanager | `alertmanager` | same name, different NS |
| Blackbox | Service **`blackbox-exporter`**, often `hostNetwork` | Service **`blackbox`** (Docker-aligned DNS); no hostNetwork |
| UniFi exporter | `unifi-exporter` + embedded ConfigMap script | same name; script from `deploy/convergence/adapters/unifi/exporter.py` |
| Image | `ghcr.io/byrn-baker/network-guardian-web:…` + node pin | `netclaw-convergence-api:local` (build from `ui/convergence-api`) |
| Storage | Longhorn PVCs (large TSDB) | default StorageClass; small PVCs (15d Prom retention) |
| Alert webhook | `http://192.168.3.252:8099/webhook` | same default in `base/configs/alertmanager.yml` — edit for your agent |

Because names collide only **within a namespace**, greenfield Home can run **beside** pilot OBS without kubectl name conflicts. DNS is different (`prometheus.netclaw-convergence.svc` vs `prometheus.observability.svc`).

## Dual-run strategies

### A — Prefer pilot Guardian (status quo)

HUD keeps pointing at pilot:

```bash
# ~/.openclaw/.env  (backup has prior pilot values)
HOME_API_URL=https://guardian.example.com   # or ClusterIP / tunnel URL
HOME_API_TOKEN=<pilot API key>
```

Do **not** apply `deploy/convergence/k8s` until cutover. Docker Home (`deploy/convergence/docker-compose.yml`) can still run on the NetClaw host for local trials.

### B — Greenfield Home stack alongside pilot (recommended product path)

1. Apply secrets + greenfield overlay into `netclaw-convergence`.
2. Leave pilot `observability` untouched.
3. Point HUD at Home NodePort or port-forward:

```bash
# From a node IP reachable by the HUD host:
HOME_API_URL=http://<node-ip>:30080
# or:
kubectl -n netclaw-convergence port-forward svc/convergence-api 3080:3000
HOME_API_URL=http://127.0.0.1:3080
HOME_API_TOKEN=<key from home-secrets API_KEYS>
```

4. Cut traffic over when Overview/Wi‑Fi/Devices look good; then decommission pilot Guardian Deployment (optional).

### C — convergence-api only, reuse pilot Prometheus/AM

Avoid running two Prometheuses if you only need API + diary:

1. Deploy only `namespace`, `postgres`, `convergence-api` (and secrets) into `netclaw-convergence`.
2. Patch convergence-api env:

| Env | Pilot value |
|-----|-------------|
| `PROMETHEUS_URL` | `http://prometheus.observability.svc:9090` |
| `ALERTMANAGER_URL` | `http://alertmanager.observability.svc:9093` |
| Optional VM/Loki | `http://victoriametrics.observability.svc:8428`, `http://loki.observability.svc:3100` |

3. Do **not** deploy Home prometheus/alertmanager/blackbox/unifi-exporter (pilot already has them).
4. Pilot scrape jobs already cover WAN + UniFi; Home `home.rules.yml` is for the **minimal** stack only.

`overlays/pilot/kustomization.yaml` is a stub for this path — start from base resources and strategic-merge patches rather than applying full greenfield.

## Config parity (Docker Home ↔ k8s base)

| Artifact | Docker | K8s base |
|----------|--------|----------|
| Prometheus scrape/rules | `deploy/convergence/prometheus/` | `k8s/base/configs/` (copied; keep in sync when editing Docker) |
| Blackbox modules | `deploy/convergence/blackbox/blackbox.yml` | `k8s/base/configs/blackbox.yml` |
| Alertmanager webhook | `render-config.sh` → `host.docker.internal` | static file — set agent LAN IP |
| UniFi exporter | compose profile `unifi` | always in base; empty `UNIFI_API_KEY` leaves target down |
| Nautobot SoT (T070) | `SOT_TYPE`/`NAUTOBOT_*` in `deploy/convergence/.env` | `configMapGenerator` literals + `home-secrets.NAUTOBOT_TOKEN` |
| Generic SNMP wireless (T071) | compose profile `generic-snmp-wireless` | Component `k8s/components/generic-snmp-wireless/` |
| Full stack (T072) | `docker-compose.full.yml` `--profile full`/`speedtest` | Component `k8s/components/full-stack/` |
| Ports on host | 3080 / 9090 / 9093 / 9115 / 9899 / 9116 / 3300 / 8428 / 3100 / 9091 | ClusterIP + NodePort **30080** (convergence-api), **30300** (grafana, if full-stack component enabled) |

## StorageClass (this pilot cluster)

Pilot OBS PVCs set `storageClassName: longhorn`. Home base leaves StorageClass empty (cluster default).  
This pilot currently advertises **two** defaults (`local-path` and `longhorn`). If Home PVCs stay Pending:

```bash
kubectl -n netclaw-convergence get pvc
# patch or re-apply with storageClassName: longhorn (match pilot OBS)
```

Optional strategic-merge patch (add under `overlays/greenfield` when needed):

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: prometheus
spec:
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        storageClassName: longhorn
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
```

(Same idea for `postgres`.)

## Name / behavior deltas vs pilot OBS (do not “fix over” blindly)

1. **Blackbox DNS**: pilot scrape configs use `blackbox-exporter:9115`; Home uses `blackbox:9115`.
2. **Job names**: Home UniFi job is `unifi` (Docker); pilot uses `unifi_exporter`. Alert `UniFiExporterDown` in Home rules matches job `unifi`.
3. **Postgres credentials / DB name**: pilot `guardian` vs Home `home` — events are not shared unless you migrate.
4. **Node affinity**: pilot Guardian pins `k3s-worker-macmini-1` for amd64 image; Home base has no pin (add overlay patch if needed).
5. **remote_write / VictoriaMetrics**: pilot Prometheus writes to VM; Home base does not (minimal parity with Docker).
6. **Existing `ui/convergence-api/k8s/`**: remains the pilot deploy path for `network-guardian-web`. Product path is `deploy/convergence/k8s/`.

## Cutover checklist (pilot → Home)

- [ ] Secrets created in `netclaw-convergence` (API key rotated or matched to HUD token)
- [ ] `kubectl apply -k deploy/convergence/k8s/overlays/greenfield` (or convergence-api-only path)
- [ ] Smoke checklist green (`SMOKE.md` / `./smoke-k8s.sh`)
- [ ] HUD `HOME_API_URL` / `HOME_API_TOKEN` updated and HUD restarted
- [ ] Confirm Overview KPIs + Devices/Wi‑Fi against Home stack
- [ ] Optional: scale down pilot `network-guardian-web` only after dual-run verified
- [ ] Leave pilot Prometheus scrapes until Home metrics parity accepted (or accept dual scrape cost)

## References

- Docker Home: `deploy/convergence/README.md`, `docker-compose.yml`
- Pilot deploy: `~/k3s-observability-stack/k8s/observability/deploy.sh`
- Pilot Guardian: `ui/convergence-api/k8s/deploy.sh`
- Spec: `specs/080-convergence/`
