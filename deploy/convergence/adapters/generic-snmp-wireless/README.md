# Generic SNMP wireless adapter (Home Docker / K3s)

Second wireless vendor path (T071) for APs/controllers that expose standard
SNMP MIBs but have no UniFi-style REST API — e.g. TP-Link Omada (via its
controller SNMP agent), Aruba Instant On, MikroTik, or any AP that answers
`IF-MIB` / `DOT11-MIB` style OIDs.

Uses the standard Prometheus `snmp_exporter` — no custom code, matches the
`wireless.type: generic-snmp` option already defined in
[`contracts/adapters.md`](../../../specs/067-convergence/contracts/adapters.md).

## Enable

Set in `config/convergence.yaml`:

```yaml
wireless:
  type: generic-snmp
  generic_snmp:
    target: 192.168.1.20      # AP or controller IP
    community: public         # SNMPv2c community (or configure v3 in snmp.yml)
```

Bring up the exporter:

```bash
cd deploy/convergence
# in .env:
#   SNMP_WIRELESS_TARGET=192.168.1.20
#   SNMP_WIRELESS_COMMUNITY=public
docker compose --env-file .env --profile generic-snmp-wireless up -d snmp-wireless-exporter
```

Core Prometheus already scrapes `snmp-wireless-exporter:9116` (job
`generic_snmp_wireless`) using the module-based Prometheus SNMP exporter
pattern (target passed as a query param). If the profile is off, the target
is simply down — no alert wired by default since coverage varies per vendor.

## Metrics

Exposed metric names follow the upstream `snmp_exporter` `if_mib` module
convention (`ifOperStatus`, `ifHCInOctets`, `ifHCOutOctets`, client counts via
vendor-specific MIB modules where configured). This is intentionally generic:
per-vendor MIB walks (client count, radio retries, channel utilization) must
be added to `snmp.yml` per deployment — there is no universal SNMP client-count
OID across vendors.

## What this stub does NOT do (yet)

- No per-radio band/retry metrics (vendor MIB dependent — extend `snmp.yml`)
- No Wi‑Fi client breakdown in the Home Wi‑Fi view (`wifi.js` still reads
  `unifi_*` series only — see "Wiring into convergence-api" below)
- No install-wizard credential prompt yet (UniFi remains the only prompted
  wireless adapter in `setup.sh`; add a `home-noc-wireless-snmp` catalog
  component when a real vendor MIB set is validated)

## Wiring into convergence-api (future work)

To surface generic-SNMP wireless health in the Home Wi‑Fi view, add fallback
PromQL in `ui/convergence-api/src/routes/wifi.js` for a `generic_snmp_wireless`
job's series once a specific vendor MIB is chosen, e.g.:

```promql
ifOperStatus{job="generic_snmp_wireless"} == 1
```

## Secrets

SNMPv2c community strings are low-security by design (SNMP itself). Treat
`SNMP_WIRELESS_COMMUNITY` as a secret anyway — never commit real values, only
set them in `deploy/convergence/.env` (gitignored).
