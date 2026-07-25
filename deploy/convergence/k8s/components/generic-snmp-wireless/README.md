# Generic SNMP wireless — K3s component (T071)

K8s equivalent of the Docker `--profile generic-snmp-wireless` path. See the
Docker adapter docs for the full contract:
[`deploy/convergence/adapters/generic-snmp-wireless/README.md`](../../adapters/generic-snmp-wireless/README.md)

## Enable

Add to your overlay's `kustomization.yaml`:

```yaml
resources:
  - ../../base
components:
  - ../../components/generic-snmp-wireless
```

Then apply:

```bash
kubectl apply -k deploy/convergence/k8s/overlays/<your-overlay>
```

## Manual step: Prometheus scrape job

Kustomize's `configMapGenerator` embeds file *contents* verbatim — it does not
merge YAML keys across files. Add this job to
`deploy/convergence/k8s/base/configs/prometheus.yml` by hand (same convention as the
`blackbox_edge` target IP, which is also a manual edit):

```yaml
  - job_name: generic_snmp_wireless
    scrape_interval: 60s
    metrics_path: /snmp
    params:
      module: [if_mib]
    static_configs:
      - targets:
          - 192.168.1.20   # <-- set to your AP/controller IP
        labels:
          site: home
          role: wireless-generic-snmp
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: snmp-wireless-exporter:9116
```

After editing, re-apply so the `prometheus-config` ConfigMap updates, then
restart Prometheus (subPath-mounted config is not hot-reloaded — see the
observability steering rules for why):

```bash
kubectl apply -k deploy/convergence/k8s/overlays/<your-overlay>
kubectl -n netclaw-convergence rollout restart sts/prometheus
```
