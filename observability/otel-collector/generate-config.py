#!/usr/bin/env python3
"""Generate otel-config.yaml with proper syslog handling and IP SLA metrics."""

import yaml

DEVICES = {
    "p1":  {"ip": "192.168.220.2",  "vendor": "cisco", "role": "p"},
    "p2":  {"ip": "192.168.220.3",  "vendor": "cisco", "role": "p"},
    "p3":  {"ip": "192.168.220.4",  "vendor": "cisco", "role": "p"},
    "p4":  {"ip": "192.168.220.5",  "vendor": "cisco", "role": "p"},
    "pe1": {"ip": "192.168.220.6",  "vendor": "cisco", "role": "pe"},
    "pe2": {"ip": "192.168.220.7",  "vendor": "cisco", "role": "pe"},
    "pe3": {"ip": "192.168.220.8",  "vendor": "cisco", "role": "pe"},
    "ce1": {"ip": "192.168.220.9",  "vendor": "cisco", "role": "ce"},
    "ce2": {"ip": "192.168.220.10", "vendor": "cisco", "role": "ce"},
    "rr1": {"ip": "192.168.220.11", "vendor": "cisco", "role": "rr"},
    "west-spine01": {"ip": "192.168.220.12", "vendor": "arista", "role": "spine"},
    "west-spine02": {"ip": "192.168.220.13", "vendor": "arista", "role": "spine"},
    "west-leaf01":  {"ip": "192.168.220.14", "vendor": "arista", "role": "leaf"},
    "west-leaf02":  {"ip": "192.168.220.15", "vendor": "arista", "role": "leaf"},
    "east-spine01": {"ip": "192.168.220.16", "vendor": "arista", "role": "spine"},
    "east-spine02": {"ip": "192.168.220.17", "vendor": "arista", "role": "spine"},
    "east-leaf01":  {"ip": "192.168.220.18", "vendor": "arista", "role": "leaf"},
    "east-leaf02":  {"ip": "192.168.220.19", "vendor": "arista", "role": "leaf"},
}

# Base interface metrics (all devices)
BASE_METRICS = {
    "interface.octets.in": {
        "unit": "By",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.2.1.31.1.1.1.6", "resource_attributes": ["interface"]}],
    },
    "interface.octets.out": {
        "unit": "By",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.2.1.31.1.1.1.10", "resource_attributes": ["interface"]}],
    },
    "interface.packets.in": {
        "unit": "{packets}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.2.1.2.2.1.11", "resource_attributes": ["interface"]}],
    },
    "interface.packets.out": {
        "unit": "{packets}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.2.1.2.2.1.17", "resource_attributes": ["interface"]}],
    },
    "interface.errors.in": {
        "unit": "{errors}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.2.1.2.2.1.14", "resource_attributes": ["interface"]}],
    },
    "interface.errors.out": {
        "unit": "{errors}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.2.1.2.2.1.20", "resource_attributes": ["interface"]}],
    },
    "interface.status": {
        "unit": "{state}",
        "gauge": {"value_type": "int"},
        "column_oids": [{"oid": "1.3.6.1.2.1.2.2.1.8", "resource_attributes": ["interface"]}],
    },
}

# IP SLA metrics (PE/CE only)
IP_SLA_METRICS = {
    "ip_sla.rtt": {
        "unit": "ms",
        "gauge": {"value_type": "int"},
        "column_oids": [{"oid": "1.3.6.1.4.1.9.9.42.1.2.10.1.1", "resource_attributes": ["interface"]}],
    },
    "ip_sla.jitter.avg": {
        "unit": "ms",
        "gauge": {"value_type": "int"},
        "column_oids": [{"oid": "1.3.6.1.4.1.9.9.42.1.5.2.1.46", "resource_attributes": ["interface"]}],
    },
    "ip_sla.packet_loss.sd": {
        "unit": "{packets}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.4.1.9.9.42.1.5.2.1.26", "resource_attributes": ["interface"]}],
    },
    "ip_sla.packet_loss.ds": {
        "unit": "{packets}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": [{"oid": "1.3.6.1.4.1.9.9.42.1.5.2.1.27", "resource_attributes": ["interface"]}],
    },
}

# NOTE: Cisco CPU/Memory OIDs (cpmCPUTotal5minRev, ciscoMemoryPoolUsed/Free)
# are not available on IOL virtual devices. Omitted to avoid scrape errors.
# If running on real hardware, add scalar_oids for:
#   1.3.6.1.4.1.9.9.109.1.1.1.1.8.1 (CPU 5min)
#   1.3.6.1.4.1.9.9.48.1.1.1.5.1 (memory used)
#   1.3.6.1.4.1.9.9.48.1.1.1.6.1 (memory free)
CISCO_SYSTEM_METRICS = {}


def build_snmp_receiver(name, info):
    metrics = dict(BASE_METRICS)
    if info["vendor"] == "cisco":
        metrics.update(CISCO_SYSTEM_METRICS)
    if info["role"] in ("pe", "ce"):
        metrics.update(IP_SLA_METRICS)

    return {
        "collection_interval": "60s",
        "endpoint": f"udp://{info['ip']}:161",
        "version": "v2c",
        "community": "public",
        "timeout": "10s",
        "resource_attributes": {
            "interface": {"oid": "1.3.6.1.2.1.2.2.1.2"}
        },
        "metrics": metrics,
    }


def build_resource_processor(name, info):
    return {
        "attributes": [
            {"key": "device_name", "value": name, "action": "upsert"},
            {"key": "device_vendor", "value": info["vendor"], "action": "upsert"},
            {"key": "device_role", "value": info["role"], "action": "upsert"},
            {"key": "device_ip", "value": info["ip"], "action": "upsert"},
            {"key": "service.name", "value": "network-devices", "action": "upsert"},
        ]
    }


class NoAliasDumper(yaml.SafeDumper):
    """YAML dumper that never uses anchors/aliases."""
    def ignore_aliases(self, data):
        return True


def main():
    config = {
        "receivers": {},
        "processors": {
            "batch": {"timeout": "10s", "send_batch_size": 1000},
            "resource/syslog": {
                "attributes": [
                    {"key": "service.name", "value": "network-devices", "action": "upsert"},
                ]
            },
        },
        "exporters": {
            "prometheusremotewrite": {
                "endpoint": "http://192.168.220.201:8428/api/v1/write",
                "resource_to_telemetry_conversion": {"enabled": True},
            },
            "loki": {
                "endpoint": "http://192.168.220.202:3100/loki/api/v1/push",
            },
        },
        "service": {"pipelines": {}},
    }

    # Syslog receiver — use udplog (raw lines, no RFC3164 parsing)
    # Cisco IOS sends: *May 10 21:49:01.747: %FACILITY-SEV-MNEMONIC: message
    # Arista EOS sends: May 10 21:49:01 hostname FACILITY: message
    # We ingest raw and let Loki/Grafana handle parsing via LogQL
    config["receivers"]["udplog"] = {
        "listen_address": "0.0.0.0:1514",
    }

    # SNMP receivers + resource processors
    for name, info in DEVICES.items():
        config["receivers"][f"snmp/{name}"] = build_snmp_receiver(name, info)
        config["processors"][f"resource/{name}"] = build_resource_processor(name, info)

    # Service pipelines
    config["service"]["pipelines"]["logs"] = {
        "receivers": ["udplog"],
        "processors": ["resource/syslog", "batch"],
        "exporters": ["loki"],
    }

    for name in DEVICES:
        config["service"]["pipelines"][f"metrics/{name}"] = {
            "receivers": [f"snmp/{name}"],
            "processors": [f"resource/{name}", "batch"],
            "exporters": ["prometheusremotewrite"],
        }

    # Write YAML without anchors
    with open("/home/ubuntu/netclaw/observability/otel-collector/otel-config.yaml", "w") as f:
        yaml.dump(config, f, Dumper=NoAliasDumper, default_flow_style=False, sort_keys=False, width=120)

    print("Generated otel-config.yaml")
    print(f"  {len(DEVICES)} SNMP receivers")
    print(f"  IP SLA metrics on: {[n for n,i in DEVICES.items() if i['role'] in ('pe','ce')]}")
    print(f"  CPU/Memory: disabled (IOL doesn't expose cpmCPU/ciscoMemoryPool MIBs)")
    print(f"  Syslog: udplog receiver (raw lines, LogQL parsing)")


if __name__ == "__main__":
    main()
