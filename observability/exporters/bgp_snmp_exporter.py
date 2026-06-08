#!/usr/bin/env python3
"""Poll BGP4-MIB + CISCO-BGP4-MIB and expose netclaw_bgp_* Prometheus metrics."""

from __future__ import annotations

import logging
import os
import re
import subprocess
import time
from pathlib import Path

import yaml
from prometheus_client import Gauge, start_http_server

logging.basicConfig(level=logging.INFO, format="%(asctime)s [bgp-snmp] %(levelname)s %(message)s")
log = logging.getLogger("bgp-snmp")

# Devices with BGP — Phase 1: Cisco RR + PE
BGP_DEVICES = {
    "rr1": {"ip": "192.168.220.11", "vendor": "cisco", "role": "rr"},
    "pe1": {"ip": "192.168.220.6", "vendor": "cisco", "role": "pe"},
    "pe2": {"ip": "192.168.220.7", "vendor": "cisco", "role": "pe"},
    "pe3": {"ip": "192.168.220.8", "vendor": "cisco", "role": "pe"},
}

PATH_DEVICES = {
    "pe1": {"ip": "192.168.220.6"},
    "pe2": {"ip": "192.168.220.7"},
    "pe3": {"ip": "192.168.220.8"},
    "ce1": {"ip": "192.168.220.9"},
    "ce2": {"ip": "192.168.220.10"},
}

# Cisco IOL — sequential ifOperStatus poll (OTEL parallel scrapes time out on these).
INTERFACE_DEVICES = {
    "p1": {"ip": "192.168.220.2"},
    "p2": {"ip": "192.168.220.3"},
    "p3": {"ip": "192.168.220.4"},
    "p4": {"ip": "192.168.220.5"},
    **{k: {"ip": v["ip"]} for k, v in BGP_DEVICES.items()},
    **{k: {"ip": v["ip"]} for k, v in PATH_DEVICES.items()},
}

IF_OPER_OID = "1.3.6.1.2.1.2.2.1.8"
IF_NAME_OID = "1.3.6.1.2.1.2.2.1.2"
IF_ERR_IN_OID = "1.3.6.1.2.1.2.2.1.14"
IF_ERR_OUT_OID = "1.3.6.1.2.1.2.2.1.20"

DATASOURCE_ROOT = Path(os.environ.get(
    "NAUTOBOT_DATASOURCE",
    "/home/ubuntu/github-projects/Nautobot-Workshop-Datasource/config_contexts/devices",
))

RTT_OID = "1.3.6.1.4.1.9.9.42.1.2.10.1.1"
JITTER_OID = "1.3.6.1.4.1.9.9.42.1.5.2.1.4"
LOSS_SD_OID = "1.3.6.1.4.1.9.9.42.1.5.2.1.26"

COMMUNITY = os.environ.get("SNMP_COMMUNITY", "public")
PORT = int(os.environ.get("BGP_SNMP_EXPORTER_PORT", "9102"))
INTERVAL = int(os.environ.get("BGP_SNMP_POLL_INTERVAL", "60"))
SNMPWALK = os.environ.get("SNMPWALK_BIN", "snmpwalk")

# BGP4-MIB bgpPeerTable columns
COL_STATE = "1.3.6.1.2.1.15.3.1.2"
COL_IN_UPDATES = "1.3.6.1.2.1.15.3.1.10"
COL_OUT_UPDATES = "1.3.6.1.2.1.15.3.1.11"
COL_FSM_TRANS = "1.3.6.1.2.1.15.3.1.15"
COL_UPTIME = "1.3.6.1.2.1.15.3.1.16"
COL_REMOTE_AS = "1.3.6.1.2.1.15.3.1.9"

# CISCO-BGP4-MIB cbgpPeerPrefixAccepted (counter)
CISCO_PREFIX_ACCEPTED = "1.3.6.1.4.1.9.9.187.1.2.4.1.1"

IP_IN_OID = re.compile(r"(\d+\.\d+\.\d+\.\d+)$")


peer_state = Gauge(
    "netclaw_bgp_peer_state",
    "BGP peer FSM state (BGP4-MIB bgpPeerState enum; 6=established)",
    ["device_name", "neighbor", "peer_as", "source"],
)
peer_prefixes = Gauge(
    "netclaw_bgp_peer_prefixes_received",
    "Accepted prefix count per peer (CISCO-BGP4-MIB)",
    ["device_name", "neighbor", "peer_as", "afi", "safi", "source"],
)
peer_in_updates = Gauge(
    "netclaw_bgp_peer_in_updates_total",
    "BGP peer InUpdates counter (monotonic SNMP value)",
    ["device_name", "neighbor", "peer_as", "source"],
)
peer_out_updates = Gauge(
    "netclaw_bgp_peer_out_updates_total",
    "BGP peer OutUpdates counter (monotonic SNMP value)",
    ["device_name", "neighbor", "peer_as", "source"],
)
peer_fsm_transitions = Gauge(
    "netclaw_bgp_peer_established_transitions_total",
    "BGP peer FSM established transitions (monotonic SNMP value)",
    ["device_name", "neighbor", "peer_as", "source"],
)
peer_uptime = Gauge(
    "netclaw_bgp_peer_uptime_seconds",
    "BGP peer FSM established time seconds",
    ["device_name", "neighbor", "peer_as", "source"],
)

path_rtt = Gauge(
    "netclaw_path_rtt_ms",
    "IP SLA latest RTT milliseconds (RTTMON-MIB)",
    ["device_name", "probe_id", "probe_type", "destination", "source"],
)
path_jitter = Gauge(
    "netclaw_path_jitter_ms",
    "IP SLA average jitter milliseconds (RTTMON-MIB .1.5.2.1.4.{probe})",
    ["device_name", "probe_id", "probe_type", "destination", "source"],
)
path_loss = Gauge(
    "netclaw_path_loss_packets",
    "IP SLA source-to-destination packet loss (RTTMON-MIB .1.5.2.1.26.{probe})",
    ["device_name", "probe_id", "probe_type", "destination", "source"],
)

interface_oper_status = Gauge(
    "interface_status",
    "ifOperStatus (1=up, 2=down, …)",
    ["device_name", "interface_index", "interface", "device_role", "source"],
)
interface_errors_in = Gauge(
    "interface_errors_in_total",
    "ifInErrors SNMP counter",
    ["device_name", "interface_index", "interface", "device_role", "source"],
)
interface_errors_out = Gauge(
    "interface_errors_out_total",
    "ifOutErrors SNMP counter",
    ["device_name", "interface_index", "interface", "device_role", "source"],
)


def load_ip_sla_probes(device_name: str) -> list[dict]:
    """Load probe definitions from Nautobot datasource device context."""
    fname = device_name.upper()
    path = DATASOURCE_ROOT / f"{fname}.yml"
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text()) or {}
        return data.get("ip_sla", {}).get("probes", [])
    except Exception:
        return []


def snmp_get(host: str, oid: str) -> int | None:
    try:
        out = subprocess.run(
            ["snmpget", "-v2c", "-c", COMMUNITY, "-Os", host, oid],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        log.error("snmpget not found — install net-snmp")
        return None
    if out.returncode != 0:
        return None
    for line in out.stdout.splitlines():
        if "=" in line:
            return parse_int(line.partition("=")[2])
    return None


def snmp_walk(host: str, oid: str) -> list[tuple[str, str]]:
    """Run snmpwalk -Os; return list of (oid_suffix, value)."""
    try:
        out = subprocess.run(
            [SNMPWALK, "-v2c", "-c", COMMUNITY, "-Os", host, oid],
            capture_output=True,
            text=True,
            timeout=45,
        )
    except FileNotFoundError:
        log.error("snmpwalk not found — install net-snmp or set SNMPWALK_BIN")
        return []
    if out.returncode != 0:
        log.warning("snmpwalk %s %s failed: %s", host, oid, out.stderr.strip()[:200])
        return []
    rows = []
    for line in out.stdout.splitlines():
        if "=" not in line:
            continue
        left, _, right = line.partition("=")
        rows.append((left.strip(), right.strip()))
    return rows


def neighbor_from_oid_suffix(suffix: str) -> str | None:
    m = IP_IN_OID.search(suffix)
    return m.group(1) if m else None


def parse_int(val: str) -> int | None:
    val = val.strip()
    for prefix in ("Gauge32:", "Counter32:", "INTEGER:"):
        if val.startswith(prefix):
            try:
                return int(val.split(":", 1)[1].strip())
            except ValueError:
                return None
    try:
        return int(val)
    except ValueError:
        return None


def index_key_from_oid(full_oid_left: str, base_oid: str) -> str:
    """Return index portion after base OID."""
    if full_oid_left.startswith(base_oid):
        return full_oid_left[len(base_oid) :].lstrip(".")
    # snmpwalk -Os may use MIB name prefix
    parts = full_oid_left.split(".")
    base_parts = base_oid.split(".")
    if len(parts) >= len(base_parts):
        return ".".join(parts[len(base_parts) :])
    return full_oid_left


def poll_peer_table(device_name: str, host: str) -> dict[str, dict]:
    """Collect BGP4-MIB peer columns keyed by neighbor IP."""
    peers: dict[str, dict] = {}
    columns = {
        "state": COL_STATE,
        "in_updates": COL_IN_UPDATES,
        "out_updates": COL_OUT_UPDATES,
        "fsm_trans": COL_FSM_TRANS,
        "uptime": COL_UPTIME,
        "remote_as": COL_REMOTE_AS,
    }
    for field, oid in columns.items():
        for left, val in snmp_walk(host, oid):
            idx = index_key_from_oid(left, oid)
            neighbor = neighbor_from_oid_suffix(idx) or idx
            if not neighbor or neighbor == "0.0.0.0":
                continue
            peers.setdefault(neighbor, {})[field] = parse_int(val)
    return peers


def poll_cisco_prefixes(device_name: str, host: str) -> list[dict]:
    """Parse cbgpPeerPrefixAccepted — index peer.afi.safi after column OID."""
    results = []
    for left, val in snmp_walk(host, CISCO_PREFIX_ACCEPTED):
        idx = index_key_from_oid(left, CISCO_PREFIX_ACCEPTED)
        parts = idx.split(".")
        if len(parts) < 3:
            continue
        # suffix: 100.0.254.13.1.1 → neighbor + afi + safi (last two)
        safi = parts[-1]
        afi = parts[-2]
        neighbor = ".".join(parts[:-2])
        if not neighbor or neighbor == "0.0.0.0":
            continue
        count = parse_int(val)
        if count is None:
            continue
        results.append({"neighbor": neighbor, "afi": afi, "safi": safi, "count": count})
    return results


def parse_if_name(val: str) -> str:
    val = val.strip()
    if val.startswith('STRING:'):
        val = val.split(':', 1)[1].strip()
    return val.strip('"')


def poll_interface_status(device_name: str, host: str) -> None:
    """Walk ifName + ifOperStatus — one device at a time for IOL SNMP agent headroom."""
    role = BGP_DEVICES.get(device_name, {}).get("role") or (
        "pe" if device_name.startswith("pe") else
        "ce" if device_name.startswith("ce") else
        "rr" if device_name == "rr1" else
        "p" if device_name.startswith("p") else "unknown"
    )
    names: dict[str, str] = {}
    for left, val in snmp_walk(host, IF_NAME_OID):
        idx = index_key_from_oid(left, IF_NAME_OID)
        if idx:
            names[idx] = parse_if_name(val)

    oper_rows = snmp_walk(host, IF_OPER_OID)
    if not oper_rows:
        log.warning("No interface_status from %s (%s)", device_name, host)
        return

    err_in = {index_key_from_oid(l, IF_ERR_IN_OID): parse_int(v) for l, v in snmp_walk(host, IF_ERR_IN_OID)}
    err_out = {index_key_from_oid(l, IF_ERR_OUT_OID): parse_int(v) for l, v in snmp_walk(host, IF_ERR_OUT_OID)}

    for left, val in oper_rows:
        idx = index_key_from_oid(left, IF_OPER_OID)
        status = parse_int(val)
        if status is None or not idx:
            continue
        ifname = names.get(idx, f"ifIndex{idx}")
        labels = dict(
            device_name=device_name,
            interface_index=idx,
            interface=ifname,
            device_role=role,
            source="snmp",
        )
        interface_oper_status.labels(**labels).set(status)
        if err_in.get(idx) is not None:
            interface_errors_in.labels(**labels).set(err_in[idx])
        if err_out.get(idx) is not None:
            interface_errors_out.labels(**labels).set(err_out[idx])


def poll_path_device(device_name: str, info: dict) -> None:
    host = info["ip"]
    probes = load_ip_sla_probes(device_name)
    if not probes:
        return
    log.info("Polling path metrics for %s (%s)", device_name, host)
    for probe in probes:
        pid = str(probe.get("id", ""))
        if not pid:
            continue
        probe_type = str(probe.get("type", "unknown"))
        destination = str(probe.get("destination", ""))
        labels = dict(
            device_name=device_name,
            probe_id=pid,
            probe_type=probe_type,
            destination=destination,
            source="snmp",
        )
        jitter_val = snmp_get(host, f"{JITTER_OID}.{pid}")
        if jitter_val is not None and probe_type == "jitter":
            path_jitter.labels(**labels).set(jitter_val)
        rtt_val = snmp_get(host, f"{RTT_OID}.{pid}")
        if rtt_val is not None:
            path_rtt.labels(**labels).set(rtt_val)
        loss_val = snmp_get(host, f"{LOSS_SD_OID}.{pid}")
        if loss_val is not None and probe_type == "jitter":
            path_loss.labels(**labels).set(loss_val)


def poll_device(device_name: str, info: dict) -> None:
    host = info["ip"]
    log.info("Polling %s (%s)", device_name, host)
    peers = poll_peer_table(device_name, host)
    if not peers:
        log.warning("No BGP peers from %s", device_name)
        return

    remote_as_map = {n: p.get("remote_as") for n, p in peers.items()}

    for neighbor, data in peers.items():
        peer_as = str(data.get("remote_as") or remote_as_map.get(neighbor) or "")
        labels = dict(device_name=device_name, neighbor=neighbor, peer_as=peer_as, source="snmp")
        if data.get("state") is not None:
            peer_state.labels(**labels).set(data["state"])
        if data.get("in_updates") is not None:
            peer_in_updates.labels(**labels).set(data["in_updates"])
        if data.get("out_updates") is not None:
            peer_out_updates.labels(**labels).set(data["out_updates"])
        if data.get("fsm_trans") is not None:
            peer_fsm_transitions.labels(**labels).set(data["fsm_trans"])
        if data.get("uptime") is not None:
            peer_uptime.labels(**labels).set(data["uptime"])

    if info["vendor"] == "cisco":
        for row in poll_cisco_prefixes(device_name, host):
            peer_as = str(remote_as_map.get(row["neighbor"]) or "")
            peer_prefixes.labels(
                device_name=device_name,
                neighbor=row["neighbor"],
                peer_as=peer_as,
                afi=row["afi"],
                safi=row["safi"],
                source="snmp",
            ).set(row["count"])


def poll_loop() -> None:
    while True:
        for name, info in INTERFACE_DEVICES.items():
            try:
                poll_interface_status(name, info["ip"])
            except Exception as exc:
                log.exception("Interface poll failed for %s: %s", name, exc)
        for name, info in BGP_DEVICES.items():
            try:
                poll_device(name, info)
            except Exception as exc:
                log.exception("BGP poll failed for %s: %s", name, exc)
        for name, info in PATH_DEVICES.items():
            try:
                poll_path_device(name, info)
            except Exception as exc:
                log.exception("Path poll failed for %s: %s", name, exc)
        time.sleep(INTERVAL)


def main() -> None:
    log.info("Starting BGP SNMP exporter on :%s (interval=%ss)", PORT, INTERVAL)
    start_http_server(PORT)
    poll_loop()


if __name__ == "__main__":
    main()