# K3s component: device-snmp (Phase 8)

Campus switch IF-MIB via `snmp_exporter`.

## Include in an overlay

```yaml
# overlays/greenfield-device/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
components:
  - ../../components/device-snmp
```

Add Prometheus scrape job `device_snmp` (same as Docker
`prometheus/prometheus.yml`) via a ConfigMap patch on `prometheus-config`.

See `deploy/convergence/adapters/device-snmp/README.md`.
