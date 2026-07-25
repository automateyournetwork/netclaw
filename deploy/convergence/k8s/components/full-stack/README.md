# Full stack — K3s component (T072)

K8s equivalent of `docker-compose.full.yml` (`--profile full` / `--profile speedtest`).
Adds Loki, VictoriaMetrics, Grafana, and a speedtest CronJob + Pushgateway on
top of the base minimal stack.

## Enable

Add to your overlay's `kustomization.yaml`:

```yaml
resources:
  - ../../base
components:
  - ../../components/full-stack
```

```bash
kubectl apply -k deploy/convergence/k8s/overlays/<your-overlay>
```

| Service | K8s object | Port |
|---------|------------|------|
| loki | StatefulSet + PVC | 3100 |
| victoriametrics | StatefulSet + PVC | 8428 |
| grafana | Deployment + PVC, ClusterIP + NodePort **30300** | 3000 |
| pushgateway | Deployment | 9091 |
| speedtest | CronJob (hourly, `17 * * * *`) | — |

Open Grafana at `http://<node-ip>:30300` or port-forward:

```bash
kubectl -n netclaw-convergence port-forward svc/grafana 3300:3000
```

## Manual steps (not automated by kustomize)

Kustomize `configMapGenerator` embeds file *contents* verbatim — it cannot
merge YAML keys across separate files. Two wiring steps are left manual, same
convention as the `blackbox_edge` target IP in the base Prometheus config:

### 1. Scrape the Pushgateway (to see speedtest metrics)

Add to `deploy/convergence/k8s/base/configs/prometheus.yml`:

```yaml
  - job_name: pushgateway
    scrape_interval: 60s
    honor_labels: true
    static_configs:
      - targets: ["pushgateway:9091"]
        labels:
          site: home
```

### 2. Long-term retention via remote_write (optional)

If you want Prometheus to forward samples into VictoriaMetrics for 365d
retention (rather than just querying VM separately in Grafana), add under
`global:` in the same file:

```yaml
remote_write:
  - url: "http://victoriametrics:8428/api/v1/write"
```

After either edit, re-apply and restart Prometheus (subPath-mounted config is
never hot-reloaded):

```bash
kubectl apply -k deploy/convergence/k8s/overlays/<your-overlay>
kubectl -n netclaw-convergence rollout restart sts/prometheus
```

## Resource footprint

This component is heavier than the base stack — expect roughly:
- +256Mi–1Gi memory (Loki)
- +128Mi–512Mi memory (VictoriaMetrics)
- +128Mi–512Mi memory (Grafana)
- +15Gi combined PVC storage (Loki 5Gi + VM 10Gi + Grafana 1Gi)

Only enable on a node/cluster with headroom for this in addition to the base
stack's postgres + prometheus PVCs.
