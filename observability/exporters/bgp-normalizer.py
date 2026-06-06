#!/usr/bin/env python3
"""Normalize BMP Kafka messages into netclaw_bgp_* Prometheus metrics.

Phase 1: SNMP metrics are emitted by bgp_snmp_exporter.py (canonical).
Phase 3: Kafka consumer for gobmp parsed topics → prefix + RIB metrics.
"""

from __future__ import annotations

import json
import logging
import os
import signal
import threading
import time
from dataclasses import dataclass
from typing import Any, Literal

from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from prometheus_client import Counter, Gauge, start_http_server

log = logging.getLogger("bgp-normalizer")

Source = Literal["snmp", "gnmi", "bmp"]

BGP_ESTABLISHED = 6

GOBMP_TOPICS = (
    "gobmp.parsed.unicast_prefix_v4",
    "gobmp.parsed.unicast_prefix_v6",
    "gobmp.parsed.statistics",
)

DEFAULT_ROUTER_MAP = {
    "192.168.220.11": "rr1",
    "100.0.254.5": "rr1",
    "2001:db8:100:254::5": "rr1",
    "192.168.220.6": "pe1",
    "192.168.220.7": "pe2",
    "192.168.220.8": "pe3",
}


@dataclass(frozen=True)
class PeerLabels:
    device_name: str
    neighbor: str
    peer_as: str = ""
    vrf: str = ""
    afi: str = "ipv4"
    safi: str = "unicast"
    source: Source = "snmp"

    def prometheus_labels(self) -> dict[str, str]:
        return {
            "device_name": self.device_name,
            "neighbor": self.neighbor,
            "peer_as": self.peer_as,
            "afi": self.afi,
            "safi": self.safi,
            "source": self.source,
        }


def normalize_peer_state(raw_state: int | str, labels: PeerLabels) -> tuple[str, dict[str, str], float]:
    """Map router-native peer state to netclaw_bgp_peer_state."""
    value = float(int(raw_state))
    return "netclaw_bgp_peer_state", labels.prometheus_labels(), value


def normalize_prefix_count(count: int, labels: PeerLabels) -> tuple[str, dict[str, str], float]:
    """Map accepted prefix count to netclaw_bgp_peer_prefixes_received."""
    return "netclaw_bgp_peer_prefixes_received", labels.prometheus_labels(), float(count)


def normalize_counter(name: str, value: int, labels: PeerLabels) -> tuple[str, dict[str, str], float]:
    """Map monotonic SNMP/BMP counters to netclaw_bgp_*_total gauges."""
    allowed = {
        "in_updates": "netclaw_bgp_peer_in_updates_total",
        "out_updates": "netclaw_bgp_peer_out_updates_total",
        "fsm_transitions": "netclaw_bgp_peer_established_transitions_total",
        "announcements": "netclaw_bgp_prefix_announcements_total",
        "withdrawals": "netclaw_bgp_prefix_withdrawals_total",
    }
    metric = allowed.get(name)
    if not metric:
        raise ValueError(f"unknown counter: {name}")
    return metric, labels.prometheus_labels(), float(value)


def afi_safi_from_mib(afi: str, safi: str) -> tuple[str, str]:
    """Convert CISCO-BGP4-MIB afi/safi indices to contract strings."""
    afi_map = {"1": "ipv4", "2": "ipv6"}
    safi_map = {"1": "unicast", "2": "multicast", "128": "vpn"}
    return afi_map.get(str(afi), str(afi)), safi_map.get(str(safi), str(safi))


prefix_announcements = Counter(
    "netclaw_bgp_prefix_announcements_total",
    "BGP prefix announcements from BMP route monitor (add)",
    ["device_name", "prefix", "neighbor", "peer_as", "afi", "source"],
)
prefix_withdrawals = Counter(
    "netclaw_bgp_prefix_withdrawals_total",
    "BGP prefix withdrawals from BMP route monitor (del)",
    ["device_name", "prefix", "neighbor", "peer_as", "afi", "source"],
)
rib_routes = Gauge(
    "netclaw_bgp_rib_routes_total",
    "RIB route count from BMP statistics report",
    ["device_name", "afi", "source"],
)
consumer_up = Gauge(
    "netclaw_bmp_consumer_up",
    "BMP Kafka consumer ready (1=connected and subscribed)",
)
kafka_messages = Counter(
    "netclaw_bmp_kafka_messages_total",
    "BMP Kafka messages processed by type",
    ["topic", "result"],
)


def parse_router_map(raw: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for part in raw.split(","):
        part = part.strip()
        if not part or "=" not in part:
            continue
        ip, name = part.split("=", 1)
        mapping[ip.strip()] = name.strip().lower()
    return mapping or DEFAULT_ROUTER_MAP


def topic_names(prefix: str) -> tuple[str, ...]:
    p = prefix.strip().strip(".")
    if not p:
        return GOBMP_TOPICS
    return tuple(f"{p}.{t}" for t in GOBMP_TOPICS)


def device_from_router_ip(router_ip: str, router_map: dict[str, str]) -> str:
    if not router_ip:
        return "unknown"
    return router_map.get(router_ip, router_ip.replace(".", "-"))


def cidr(prefix: str, prefix_len: int | str | None, is_ipv4: bool | None = None) -> str:
    if not prefix:
        return ""
    if "/" in prefix:
        return prefix
    if prefix_len is None:
        return prefix
    return f"{prefix}/{int(prefix_len)}"


def unwrap_payload(raw: bytes | str) -> dict[str, Any]:
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    if "msg_data" in data and isinstance(data["msg_data"], dict):
        return data["msg_data"]
    return data


def handle_unicast_prefix(payload: dict[str, Any], router_map: dict[str, str]) -> None:
    action = str(payload.get("action", "")).lower()
    if action not in {"add", "del"}:
        return
    prefix = cidr(
        str(payload.get("prefix", "")),
        payload.get("prefix_len"),
        payload.get("is_ipv4"),
    )
    if not prefix:
        return
    device = device_from_router_ip(str(payload.get("router_ip", "")), router_map)
    neighbor = str(payload.get("peer_ip", ""))
    peer_as = str(payload.get("peer_asn", payload.get("peer_as", "")))
    afi = "ipv4" if payload.get("is_ipv4", True) else "ipv6"
    labels = dict(
        device_name=device,
        prefix=prefix,
        neighbor=neighbor,
        peer_as=peer_as,
        afi=afi,
        source="bmp",
    )
    if action == "add":
        prefix_announcements.labels(**labels).inc()
    else:
        prefix_withdrawals.labels(**labels).inc()


def rib_count_from_stats(payload: dict[str, Any]) -> tuple[str, int] | None:
    per_afi = payload.get("per_afi_loc_rib") or []
    if per_afi:
        total_v4 = 0
        total_v6 = 0
        for entry in per_afi:
            if not isinstance(entry, dict):
                continue
            afi = int(entry.get("afi", 0))
            count = int(entry.get("count", 0))
            if afi == 1:
                total_v4 += count
            elif afi == 2:
                total_v6 += count
        if total_v4:
            return "ipv4", total_v4
        if total_v6:
            return "ipv6", total_v6
    local_rib = payload.get("local_rib")
    if local_rib is not None:
        return "ipv4", int(local_rib)
    adj_in = payload.get("ads_rib_in")
    if adj_in is not None:
        return "ipv4", int(adj_in)
    return None


def handle_statistics(payload: dict[str, Any], router_map: dict[str, str]) -> None:
    rib = rib_count_from_stats(payload)
    if not rib:
        return
    afi, count = rib
    device = device_from_router_ip(str(payload.get("router_ip", "")), router_map)
    rib_routes.labels(device_name=device, afi=afi, source="bmp").set(count)


def dispatch_message(topic: str, raw: bytes | str, router_map: dict[str, str]) -> None:
    payload = unwrap_payload(raw)
    if "unicast_prefix" in topic:
        handle_unicast_prefix(payload, router_map)
    elif topic.endswith("statistics"):
        handle_statistics(payload, router_map)


class BmpConsumer:
    def __init__(self) -> None:
        self.bootstrap = os.environ.get("KAFKA_BOOTSTRAP", "redpanda:9092")
        self.group = os.environ.get("BMP_CONSUMER_GROUP", "netclaw-bgp-normalizer")
        self.topic_prefix = os.environ.get("KAFKA_TOPIC_PREFIX", "")
        self.router_map = parse_router_map(os.environ.get("BMP_ROUTER_IP_MAP", ""))
        self._stop = threading.Event()
        self._consumer: KafkaConsumer | None = None

    def stop(self) -> None:
        self._stop.set()
        if self._consumer:
            self._consumer.close()

    def run(self) -> None:
        topics = list(topic_names(self.topic_prefix))
        while not self._stop.is_set():
            try:
                self._consumer = KafkaConsumer(
                    *topics,
                    bootstrap_servers=self.bootstrap,
                    group_id=self.group,
                    auto_offset_reset="latest",
                    enable_auto_commit=True,
                    consumer_timeout_ms=1000,
                    value_deserializer=lambda v: v,
                )
                consumer_up.set(1)
                log.info("subscribed to %s via %s", topics, self.bootstrap)
                while not self._stop.is_set():
                    for record in self._consumer:
                        try:
                            dispatch_message(record.topic, record.value, self.router_map)
                            kafka_messages.labels(topic=record.topic, result="ok").inc()
                        except Exception as exc:
                            kafka_messages.labels(topic=record.topic, result="error").inc()
                            log.warning("message parse failed on %s: %s", record.topic, exc)
            except NoBrokersAvailable:
                consumer_up.set(0)
                log.warning("kafka unavailable at %s, retrying in 5s", self.bootstrap)
                time.sleep(5)
            except Exception as exc:
                consumer_up.set(0)
                log.error("consumer error: %s", exc)
                time.sleep(5)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [bmp] %(levelname)s %(message)s")
    port = int(os.environ.get("BMP_EXPORTER_PORT", "9100"))
    start_http_server(port)
    log.info("metrics on :%s/metrics", port)

    consumer = BmpConsumer()

    def _shutdown(_signum: int, _frame: Any) -> None:
        consumer.stop()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    consumer.run()


if __name__ == "__main__":
    main()