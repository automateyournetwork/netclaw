# otel-collector component (Phase 11 / T156)

Device telemetry hub for K3s: syslog **and** SNMP in one workload, matching the
Docker path.

```text
devices --syslog RFC3164--> hostPort 1514 udp+tcp ──┬──> Loki          (14d)
                                                     └──> VictoriaLogs  (365d)
devices <--SNMP poll------- receivers ──────────────┬──> Prometheus     (15d)
                                                     └──> VictoriaMetrics (365d)
```

## What this replaced, and why it was broken

| Retired component | Why |
|---|---|
| `components/device-syslog` | promtail's syslog target parses **RFC5424 only**. Cisco IOS-XE and pfSense emit RFC3164, so it silently discarded every device log line — port open, packets arriving, Loki empty. The syslog-ng sidecar existed purely to work around that. |
| `components/device-snmp` | snmp_exporter needed a recording-rule layer to synthesise `interface_*` names. The OTel SNMP receiver emits them directly, and adds `interface_admin_status`. |

Both are deleted, not deprecated. Anyone applying the old overlay got the silent
log drop plus unbounded `app` label cardinality from Cisco mnemonics.

Also fixed here, because K3s would otherwise have been quietly broken:

- **`--web.enable-remote-write-receiver` on Prometheus.** Both the collector's SNMP
  metrics and the Loki ruler's derived pfSense metrics arrive by remote-write.
  Without the flag, K3s has **no device metrics at all**.
- **Loki ruler + rules ConfigMap.** T143's log-derived block/DNS metrics existed
  only on Docker.
- **`base/configs/device.rules.yml`** had drifted 210 lines from its Docker
  original and still selected retired metric names (`ifOperStatus`, `ifInErrors`),
  so those alerts would never have fired.

## Config is a copy, checked by a script

`configs/otel-config.yaml` is a **copy** of
`deploy/convergence/otel/otel-config.yaml`. The same file works in both runtimes
because compose service names and K8s Service names are identical (`loki`,
`victorialogs`, `prometheus`, `victoriametrics`).

A symlink would be better, but Kustomize refuses to load files outside its root and
requiring `--load-restrictor LoadRestrictionsNone` is worse than a copy. So:

```bash
deploy/convergence/k8s/check-config-drift.sh          # report
deploy/convergence/k8s/check-config-drift.sh --fix    # copy Docker → K8s
```

Run it before applying. A "keep in sync" comment is what let the previous copies
drift for weeks.

## Generating device blocks

Do not hand-edit the SNMP receivers or the syslog device map — they are generated
from `convergence.yaml` inventory:

```bash
scripts/render-convergence-telemetry.py \
  --config ~/.openclaw/convergence.yaml \
  --inject-otel deploy/convergence/otel/otel-config.yaml
deploy/convergence/k8s/check-config-drift.sh --fix
```

## Apply

```bash
kubectl apply -f deploy/convergence/k8s/secret.yaml      # SNMP_COMMUNITY
kubectl apply -k deploy/convergence/k8s/overlays/greenfield-device-telemetry
```

## Verify

```bash
kubectl -n netclaw-convergence port-forward svc/otel-collector 8888:8888 &
curl -s localhost:8888/metrics | grep -E \
  '^otelcol_(receiver_(accepted|refused)|exporter_send_failed)_log_records'

kubectl -n netclaw-convergence port-forward svc/prometheus 9090:9090 &
curl -sG localhost:9090/api/v1/query --data-urlencode \
  'query=count by (device_name) (interface_status{job="device_snmp"})'
```

## Known non-issue

`HostLogShipDown` (`up{job="promtail"} == 0`) ships in the shared alert rules but
is **inert on K3s** — there is no promtail scrape job here, so the series never
exists and the alert cannot fire. It is kept rather than forked so the rules stay
byte-identical to the Docker copy and the drift guard keeps working.

## Not covered

Host-side agent logs (OpenClaw files, systemd journal) have no K3s equivalent —
promtail handles those on the Docker/host path. See T150.
