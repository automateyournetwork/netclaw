#!/usr/bin/env python3
"""Stream OpenConfig BGP from Arista cEOS via gNMI → netclaw_bgp_* metrics."""

from __future__ import annotations

import logging
import os
import re
import signal
import threading
import time
from pathlib import Path
from typing import Any

import yaml
from prometheus_client import Gauge, start_http_server
from pygnmi.client import gNMIclient, telemetryParser

logging.basicConfig(level=logging.INFO, format="%(asctime)s [bgp-gnmi] %(levelname)s %(message)s")
log = logging.getLogger("bgp-gnmi")

CONFIG_PATH = Path(os.environ.get(
    "GNMI_SUBSCRIPTIONS",
    "/app/gnmi/subscriptions.yaml",
))

SESSION_STATE = {
    "IDLE": 1,
    "CONNECT": 2,
    "ACTIVE": 3,
    "OPENSENT": 4,
    "OPENCONFIRM": 5,
    "ESTABLISHED": 6,
}

NEIGHBOR_RE = re.compile(r"neighbor-address=([^]]+)")
AFI_RE = re.compile(r"afi-safi-name=([^]]+)")

peer_state = Gauge(
    "netclaw_bgp_peer_state",
    "BGP peer session state (OpenConfig session-state mapped to BGP4-MIB enum)",
    ["device_name", "neighbor", "peer_as", "source"],
)
peer_prefixes = Gauge(
    "netclaw_bgp_peer_prefixes_received",
    "BGP prefixes received per neighbor AFI/SAFI (OpenConfig)",
    ["device_name", "neighbor", "peer_as", "afi", "safi", "source"],
)

_peer_as_cache: dict[tuple[str, str], str] = {}
_state_cache: dict[tuple[str, str], float] = {}
_cache_lock = threading.Lock()
_stop = threading.Event()


def load_config() -> dict[str, Any]:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    if not data.get("targets"):
        raise RuntimeError(f"No gNMI targets in {CONFIG_PATH}")
    return data


def afi_safi_labels(afi_safi: str) -> tuple[str, str]:
    name = afi_safi.upper()
    if name.startswith("IPV6"):
        return "ipv6", "unicast"
    if "EVPN" in name:
        return "l2vpn", "evpn"
    return "ipv4", "unicast"


def peer_as_for(device: str, neighbor: str) -> str:
    with _cache_lock:
        return _peer_as_cache.get((device, neighbor), "")


def set_peer_as(device: str, neighbor: str, value: Any) -> str:
    pas = str(value)
    with _cache_lock:
        _peer_as_cache[(device, neighbor)] = pas
    return pas


def publish_state(device: str, neighbor: str, state_val: float) -> None:
    pas = peer_as_for(device, neighbor)
    if not pas:
        return
    peer_state.labels(
        device_name=device,
        neighbor=neighbor,
        peer_as=pas,
        source="gnmi",
    ).set(state_val)


def parse_path(path: str) -> dict[str, str]:
    out: dict[str, str] = {}
    m = NEIGHBOR_RE.search(path)
    if m:
        out["neighbor"] = m.group(1)
    m = AFI_RE.search(path)
    if m:
        out["afi_safi"] = m.group(1)
    return out


def handle_update(device: str, path: str, value: Any) -> None:
    meta = parse_path(path)
    neighbor = meta.get("neighbor")
    if not neighbor:
        return

    if path.endswith("/state/session-state"):
        state = float(SESSION_STATE.get(str(value).upper(), 0))
        with _cache_lock:
            _state_cache[(device, neighbor)] = state
        publish_state(device, neighbor, state)
        return

    if path.endswith("/state/peer-as"):
        pas = set_peer_as(device, neighbor, value)
        with _cache_lock:
            cached_state = _state_cache.get((device, neighbor))
        if cached_state is not None:
            peer_state.labels(
                device_name=device,
                neighbor=neighbor,
                peer_as=pas,
                source="gnmi",
            ).set(cached_state)
        return

    if path.endswith("/prefixes/received") and "afi_safi" in meta:
        afi, safi = afi_safi_labels(meta["afi_safi"])
        peer_prefixes.labels(
            device_name=device,
            neighbor=neighbor,
            peer_as=peer_as_for(device, neighbor),
            afi=afi,
            safi=safi,
            source="gnmi",
        ).set(float(value))


def subscribe_device(target: dict[str, Any], cfg: dict[str, Any]) -> None:
    defaults = cfg.get("defaults", {})
    device = target["device_name"]
    host = target["host"]
    port = int(target.get("port", defaults.get("port", 6030)))
    interval = int(target.get("sample_interval_ns", defaults.get("sample_interval_ns", 30_000_000_000)))

    subs = []
    for entry in cfg.get("subscriptions", []):
        subs.append({
            "path": entry["path"],
            "mode": entry.get("mode", "sample"),
            "sample_interval": interval,
        })

    subscribe = {"subscription": subs, "mode": "stream", "encoding": defaults.get("encoding", "json")}

    while not _stop.is_set():
        try:
            log.info("Subscribing %s (%s:%s)", device, host, port)
            with gNMIclient(
                target=(host, port),
                username=target.get("username", defaults.get("username", "admin")),
                password=target.get("password", defaults.get("password", "admin")),
                insecure=bool(defaults.get("insecure", True)),
                skip_verify=bool(defaults.get("tls_skip_verify", True)),
            ) as gc:
                for raw in gc.subscribe(subscribe):
                    if _stop.is_set():
                        break
                    parsed = telemetryParser(raw)
                    updates = parsed.get("update", {}).get("update", [])
                    if not isinstance(updates, list):
                        continue
                    for item in updates:
                        if not isinstance(item, dict):
                            continue
                        handle_update(device, item.get("path", ""), item.get("val"))
        except Exception as exc:  # noqa: BLE001
            log.warning("%s gNMI stream error: %s — retry in 15s", device, exc)
            time.sleep(15)


def main() -> None:
    cfg = load_config()
    port = int(os.environ.get("BGP_GNMI_EXPORTER_PORT", "9103"))
    start_http_server(port)
    log.info("BGP gNMI exporter listening on :%s", port)

    for target in cfg["targets"]:
        t = threading.Thread(
            target=subscribe_device,
            args=(target, cfg),
            name=f"gnmi-{target['device_name']}",
            daemon=True,
        )
        t.start()

    def _shutdown(*_args: object) -> None:
        _stop.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while not _stop.is_set():
        time.sleep(1)


if __name__ == "__main__":
    main()