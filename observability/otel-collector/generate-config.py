#!/usr/bin/env python3
"""Generate otel-config.yaml — SNMP, IP SLA scalars, syslog with device enrichment."""

import os
from pathlib import Path

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

IP_TO_DEVICE = {info["ip"]: name for name, info in DEVICES.items()}

INTERFACE_INDEX = "interface.index"
INTERFACE_NAME = "interface.name"
IFACE_INDEX_ONLY = [INTERFACE_INDEX]
BGP_NEIGHBOR = "bgp.neighbor"
BGP_PEER_AS = "bgp.peer_as"

# Polled sequentially by bgp-snmp-exporter — skip OTEL parallel SNMP (IOL agents stall).
OTEL_SNMP_SKIP = frozenset({
    "p1", "p2", "p3", "p4",
    "pe1", "pe2", "pe3", "ce1", "ce2", "rr1",
})


def _iface_col(oid: str) -> list[dict]:
    return [{"oid": oid, "resource_attributes": IFACE_INDEX_ONLY}]


BASE_METRICS = {
    "interface.octets.in": {
        "unit": "By",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": _iface_col("1.3.6.1.2.1.31.1.1.1.6"),
    },
    "interface.octets.out": {
        "unit": "By",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": _iface_col("1.3.6.1.2.1.31.1.1.1.10"),
    },
    "interface.packets.in": {
        "unit": "{packets}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": _iface_col("1.3.6.1.2.1.2.2.1.11"),
    },
    "interface.packets.out": {
        "unit": "{packets}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": _iface_col("1.3.6.1.2.1.2.2.1.17"),
    },
    "interface.errors.in": {
        "unit": "{errors}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": _iface_col("1.3.6.1.2.1.2.2.1.14"),
    },
    "interface.errors.out": {
        "unit": "{errors}",
        "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
        "column_oids": _iface_col("1.3.6.1.2.1.2.2.1.20"),
    },
    "interface.status": {
        "unit": "{state}",
        "gauge": {"value_type": "int"},
        "column_oids": _iface_col("1.3.6.1.2.1.2.2.1.8"),
    },
}

DATASOURCE_ROOT = Path(os.environ.get(
    "NAUTOBOT_DATASOURCE",
    "/home/ubuntu/github-projects/Nautobot-Workshop-Datasource/config_contexts/devices",
))


def load_ip_sla_probe_ids(device_key: str, probe_type: str | None = None) -> list[int]:
    """Load IP SLA probe IDs from Nautobot datasource device context."""
    fname = device_key.upper().replace("WEST-", "West-").replace("EAST-", "East-")
    if fname.startswith("P") and not fname.startswith("PE"):
        fname = fname  # P1, P2, etc.
    path = DATASOURCE_ROOT / f"{fname}.yml"
    if not path.exists():
        path = DATASOURCE_ROOT / f"{device_key.upper()}.yml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text()) or {}
        probes = data.get("ip_sla", {}).get("probes", [])
        ids = []
        for p in probes:
            if "id" not in p:
                continue
            if probe_type and p.get("type") != probe_type:
                continue
            ids.append(int(p["id"]))
        return ids
    except Exception:
        return []


def build_ip_sla_scalar_metrics(all_probe_ids: list[int], jitter_probe_ids: list[int]) -> dict:
    """Per-probe scalar OIDs — avoids broken indexed sla.index resource mapping on IOL."""
    if not all_probe_ids:
        return {}
    metrics = {}
    rtt_oids = [{"oid": f"1.3.6.1.4.1.9.9.42.1.2.10.1.1.{pid}"} for pid in all_probe_ids]
    # RTTMON-MIB: avg jitter column .1.4.{probe} (not .1.46.{probe}.1)
    jitter_oids = [{"oid": f"1.3.6.1.4.1.9.9.42.1.5.2.1.4.{pid}"} for pid in jitter_probe_ids]
    loss_sd_oids = [{"oid": f"1.3.6.1.4.1.9.9.42.1.5.2.1.26.{pid}"} for pid in jitter_probe_ids]
    loss_ds_oids = [{"oid": f"1.3.6.1.4.1.9.9.42.1.5.2.1.27.{pid}"} for pid in jitter_probe_ids]

    metrics["netclaw.path.rtt"] = {
        "unit": "ms",
        "gauge": {"value_type": "int"},
        "scalar_oids": rtt_oids,
    }
    metrics["netclaw.path.jitter"] = {
        "unit": "ms",
        "gauge": {"value_type": "int"},
        "scalar_oids": jitter_oids,
    }
    metrics["netclaw.path.loss.sd"] = {
        "unit": "{packets}",
        "gauge": {"value_type": "int"},
        "scalar_oids": loss_sd_oids,
    }
    metrics["netclaw.path.loss.ds"] = {
        "unit": "{packets}",
        "gauge": {"value_type": "int"},
        "scalar_oids": loss_ds_oids,
    }
    return metrics


def build_bgp4_mib_metrics() -> dict:
    """Standard BGP4-MIB bgpPeerTable — indexed by bgpPeerRemoteAddr."""
    peer_idx = [BGP_NEIGHBOR]
    return {
        "netclaw.bgp.peer.state": {
            "unit": "{state}",
            "gauge": {"value_type": "int"},
            "column_oids": [{"oid": "1.3.6.1.2.1.15.3.1.2", "resource_attributes": peer_idx}],
        },
        "netclaw.bgp.peer.in.updates": {
            "unit": "{update}",
            "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
            "column_oids": [{"oid": "1.3.6.1.2.1.15.3.1.10", "resource_attributes": peer_idx}],
        },
        "netclaw.bgp.peer.out.updates": {
            "unit": "{update}",
            "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
            "column_oids": [{"oid": "1.3.6.1.2.1.15.3.1.11", "resource_attributes": peer_idx}],
        },
        "netclaw.bgp.peer.fsm.transitions": {
            "unit": "{transition}",
            "sum": {"value_type": "int", "aggregation": "cumulative", "monotonic": True},
            "column_oids": [{"oid": "1.3.6.1.2.1.15.3.1.15", "resource_attributes": peer_idx}],
        },
        "netclaw.bgp.peer.uptime": {
            "unit": "s",
            "gauge": {"value_type": "int"},
            "column_oids": [{"oid": "1.3.6.1.2.1.15.3.1.16", "resource_attributes": peer_idx}],
        },
        "netclaw.bgp.peer.remote.as": {
            "unit": "{as}",
            "gauge": {"value_type": "int"},
            "column_oids": [{"oid": "1.3.6.1.2.1.15.3.1.9", "resource_attributes": peer_idx}],
        },
    }


BGP_ROLES = frozenset({"rr", "pe"})


def build_snmp_receiver(name, info, device_index: int):
    metrics = dict(BASE_METRICS)
    resource_attrs = {
        INTERFACE_INDEX: {"oid": "1.3.6.1.2.1.2.2.1.1"},
        INTERFACE_NAME: {"oid": "1.3.6.1.2.1.2.2.1.2"},
    }
    add_bgp = info["role"] in BGP_ROLES or (
        info["vendor"] == "arista" and info["role"] in ("spine", "leaf")
    )
    if add_bgp:
        resource_attrs[BGP_NEIGHBOR] = {"oid": "1.3.6.1.2.1.15.3.1.7"}
        resource_attrs[BGP_PEER_AS] = {"oid": "1.3.6.1.2.1.15.3.1.9"}
        metrics.update(build_bgp4_mib_metrics())

    return {
        "collection_interval": "90s",
        "initial_delay": f"{device_index * 5}s",
        "endpoint": f"udp://{info['ip']}:161",
        "version": "v2c",
        "community": "public",
        "timeout": "45s",
        "resource_attributes": resource_attrs,
        "metrics": metrics,
    }


def build_interface_label_processor():
    """Promote interface_name → interface for agent/Grafana PromQL."""
    return {
        "metric_statements": [
            {
                "context": "datapoint",
                "statements": [
                    'set(attributes["interface"], attributes["interface_name"]) '
                    'where attributes["interface_name"] != nil',
                ],
            },
            {
                "context": "resource",
                "statements": [
                    'set(attributes["interface"], attributes["interface_name"]) '
                    'where attributes["interface_name"] != nil',
                ],
            },
        ]
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


def build_syslog_device_processor():
    """Map syslog source IP (net.peer.ip) to device_name for Loki correlation."""
    ottl = []
    for ip, device in sorted(IP_TO_DEVICE.items()):
        ottl.append(
            f'set(attributes["device_name"], "{device}") where attributes["net.peer.ip"] == "{ip}"'
        )
        ottl.append(
            f'set(attributes["device_ip"], "{ip}") where attributes["net.peer.ip"] == "{ip}"'
        )
    ottl.append(
        'set(attributes["loki.attribute.labels"], "device_name,device_ip") '
        "where attributes[\"device_name\"] != nil"
    )
    return {
        "log_statements": [
            {"context": "log", "statements": ottl},
        ]
    }


def build_syslog_resource_processor():
    """Promote device_name from log attributes to resource for Loki index labels."""
    return {
        "log_statements": [
            {
                "context": "log",
                "statements": [
                    'set(resource.attributes["device_name"], attributes["device_name"]) '
                    'where attributes["device_name"] != nil',
                    'set(resource.attributes["device_ip"], attributes["device_ip"]) '
                    'where attributes["device_ip"] != nil',
                ],
            },
        ]
    }


class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def main():
    config = {
        "receivers": {},
        "processors": {
            "batch": {"timeout": "15s", "send_batch_size": 512},
            "attributes/loki": {
                "actions": [
                    {
                        "key": "loki.attribute.labels",
                        "value": "device_name,device_ip",
                        "action": "insert",
                    },
                ]
            },
            "resource/syslog": {
                "attributes": [
                    {"key": "service.name", "value": "network-devices", "action": "upsert"},
                    {"key": "loki.resource.labels", "value": "device_name,service.name", "action": "insert"},
                ]
            },
            "transform/syslog_device": build_syslog_device_processor(),
            "transform/syslog_resource": build_syslog_resource_processor(),
            "transform/interface_labels": build_interface_label_processor(),
        },
        "exporters": {
            "prometheusremotewrite": {
                "endpoint": "http://victoriametrics:8428/api/v1/write",
                "resource_to_telemetry_conversion": {"enabled": True},
                "timeout": "30s",
            },
            "loki": {
                "endpoint": "http://loki:3100/loki/api/v1/push",
                "timeout": "30s",
            },
        },
        "service": {"pipelines": {}},
    }

    config["receivers"]["udplog"] = {
        "listen_address": "0.0.0.0:1514",
        "add_attributes": True,
    }

    otel_snmp_devices = [(n, i) for n, i in DEVICES.items() if n not in OTEL_SNMP_SKIP]
    for idx, (name, info) in enumerate(otel_snmp_devices):
        config["receivers"][f"snmp/{name}"] = build_snmp_receiver(name, info, idx)
        config["processors"][f"resource/{name}"] = build_resource_processor(name, info)

    config["service"]["pipelines"]["logs"] = {
        "receivers": ["udplog"],
        "processors": [
            "transform/syslog_device",
            "transform/syslog_resource",
            "attributes/loki",
            "resource/syslog",
            "batch",
        ],
        "exporters": ["loki"],
    }

    for name, _ in otel_snmp_devices:
        config["service"]["pipelines"][f"metrics/{name}"] = {
            "receivers": [f"snmp/{name}"],
            "processors": [f"resource/{name}", "transform/interface_labels", "batch"],
            "exporters": ["prometheusremotewrite"],
        }

    out = Path(__file__).parent / "otel-config.yaml"
    with open(out, "w") as f:
        yaml.dump(config, f, Dumper=NoAliasDumper, default_flow_style=False, sort_keys=False, width=120)

    print(f"Generated {out}")
    print(f"  {len(otel_snmp_devices)} SNMP receivers ({len(OTEL_SNMP_SKIP)} via bgp-snmp-exporter)")


if __name__ == "__main__":
    main()