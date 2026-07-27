# OTel SNMP receiver block — reference for the generator (T151 → T154)

Hand-written for the Phase 11 PR3 cutover on this site's three switches. **T154
will generate this from `convergence.yaml` inventory**, so treat the shape here as
the contract, not as something operators should edit.

## Metric → OID map

Chosen so `prometheusremotewrite` emits *exactly* the names Convergence already
uses, which is why the cutover needs no dashboard or alert changes (measured in
T145).

| OTel metric | OID | Unit / type | Prometheus name emitted |
|---|---|---|---|
| `interface.octets.in` | 1.3.6.1.2.1.31.1.1.1.6 | `By`, monotonic sum | `interface_octets_in_bytes_total` |
| `interface.octets.out` | 1.3.6.1.2.1.31.1.1.1.10 | `By`, monotonic sum | `interface_octets_out_bytes_total` |
| `interface.errors.in` | 1.3.6.1.2.1.2.2.1.14 | `{errors}`, monotonic sum | `interface_errors_in_total` |
| `interface.errors.out` | 1.3.6.1.2.1.2.2.1.20 | `{errors}`, monotonic sum | `interface_errors_out_total` |
| `interface.status` | 1.3.6.1.2.1.2.2.1.8 | `{state}`, gauge | `interface_status` (ifOperStatus) |
| `interface.admin.status` | 1.3.6.1.2.1.2.2.1.7 | `{state}`, gauge | `interface_admin_status` (ifAdminStatus) |

`interface.name` is a resource attribute from ifDescr (1.3.6.1.2.1.2.2.1.2) →
label `interface_name`.

`interface_admin_status` is new. Together with `interface_status` it distinguishes
**administratively shut** (admin 2) from **link failed** (admin 1, oper 2), which
`SwitchLinkLost` currently has to infer from "was oper-up 15m ago".

## Label preservation

`prometheusremotewrite` derives `job` from `service.name` and `instance` from
`service.instance.id`. Setting those per device keeps every existing selector
working:

| Prometheus label | Resource attribute |
|---|---|
| `job` | `service.name` |
| `instance` | `service.instance.id` |
| `device_name`, `role`, `vendor`, `site` | set directly |

## Staged cutover (why `device_snmp_otel` first)

`snmp_exporter` is still emitting `interface_status{job="device_snmp"}`. Two
writers producing the same series with the same labels is a data-integrity
problem, not a cosmetic one, so the collector starts under
`service.name: device_snmp_otel`:

1. Both run. Compare `interface_status{job="device_snmp"}` against
   `interface_status{job="device_snmp_otel"}` per device/interface.
2. When parity holds, flip `service.name` to `device_snmp`, and in the same change
   remove the `device_snmp` scrape job and the `snmp-device-exporter` service.
3. Retire `device-recording.rules.yml` — OTel emits the final names directly, so
   the `label_replace` chain that synthesised them is redundant.

Never leave step 2 half-done.

## Retention

Both exporters are wired: `prometheusremotewrite/prometheus` (15d, what the boards
and alerts query) and `prometheusremotewrite/victoriametrics` (365d). VictoriaMetrics
had **zero series ever written** before this — the 365d retention claim in the docs
was fiction until this task.
