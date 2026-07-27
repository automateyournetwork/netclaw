#!/usr/bin/env python3
"""T142 — move Loki panels off message-content regex onto label selectors.

Context: the NetClaw board selected mesh/N2N streams as
`{job=~"openclaw-gateway|netclaw-journal"} |~ "(?i)(n2n|mesh|peer|...)"` because
the journal `job`/`unit` labels were believed to be broken. They are not — the
promtail journal relabel chain produces `job=netclaw-mesh` /
`unit=netclaw-mesh.service` correctly; those panels looked empty only because the
units were idle beyond promtail's max_age window. Regex-over-message selection is
brittle (it silently drops matching lines as wording changes) and violates
spec FR-034.

Security panels move onto the `app` label now published by the syslog gateway
(T141), which is both precise and cheap, and gain block/DNS rate panels — the
log-shaped half of the T143 gap.

Run from repo root:  python3 deploy/convergence/grafana/patch-t142.py
Idempotent.
"""
from __future__ import annotations

import json
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parent / "provisioning" / "dashboards" / "json"

NETCLAW_QUERIES = {
    "OpenClaw gateway logs": '{job="openclaw-gateway"}',
    "N2N / mesh / member logs": '{job=~"netclaw-mesh|netclaw-member"}',
    "Errors across NetClaw plane": (
        '{job=~"openclaw-gateway|netclaw-mesh|netclaw-member|netclaw-agent'
        '|netclaw-hud|netclaw-journal"} '
        '|~ "(?i)(error|fail|exception|oom|crash|timeout)"'
    ),
}

SECURITY_QUERIES = {
    81: (
        "Firewall blocks (filterlog / IDS)",
        '{job="device-syslog", app=~"filterlog|snort|suricata"} '
        '|~ "(?i)(,block,|,reject,|blocked|denied)"',
    ),
    82: (
        "Auth / login events",
        '{job="device-syslog", app=~"sshd|sudo|su|login|nginx|openvpn"} '
        '|~ "(?i)(fail|invalid|accepted|authenticat)"',
    ),
}


def patch_netclaw(path: pathlib.Path) -> int:
    d = json.loads(path.read_text())
    changed = 0
    for p in d.get("panels", []):
        want = NETCLAW_QUERIES.get(p.get("title"))
        if not want:
            continue
        for t in p.get("targets", []) or []:
            if t.get("expr") != want:
                t["expr"] = want
                changed += 1
    if changed:
        path.write_text(json.dumps(d, indent=2) + "\n")
    return changed


def patch_security(path: pathlib.Path) -> int:
    d = json.loads(path.read_text())
    panels = d.get("panels", [])
    changed = 0

    for p in panels:
        spec = SECURITY_QUERIES.get(p.get("id"))
        if not spec:
            continue
        title, expr = spec
        if p.get("title") != title:
            p["title"] = title
            changed += 1
        for t in p.get("targets", []) or []:
            if t.get("expr") != expr:
                t["expr"] = expr
                changed += 1

    if not any(p.get("id") == 83 for p in panels):
        # Insert activity rates directly under the syslog row, push logs down.
        for p in panels:
            y = p.get("gridPos", {}).get("y", 0)
            if y >= 23:
                p["gridPos"]["y"] = y + 7
        panels.extend([_rate_panel(83, 0), _dns_panel(84, 12)])
        panels.sort(key=lambda p: (p.get("gridPos", {}).get("y", 0), p.get("gridPos", {}).get("x", 0)))
        changed += 2

    if changed:
        path.write_text(json.dumps(d, indent=2) + "\n")
    return changed


def _base_ts(pid: int, x: int, title: str, expr: str, legend: str, unit: str) -> dict:
    return {
        "id": pid,
        "type": "timeseries",
        "title": title,
        "datasource": {"type": "loki", "uid": "loki"},
        "gridPos": {"h": 7, "w": 12, "x": x, "y": 23},
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "custom": {"lineWidth": 1, "fillOpacity": 10, "showPoints": "never"},
            },
            "overrides": [],
        },
        "options": {
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "targets": [
            {
                "refId": "A",
                "datasource": {"type": "loki", "uid": "loki"},
                "expr": expr,
                "legendFormat": legend,
                "queryType": "range",
            }
        ],
    }


def _rate_panel(pid: int, x: int) -> dict:
    return _base_ts(
        pid,
        x,
        "Firewall block rate by device",
        'sum by (device_name) (rate({job="device-syslog", app=~"filterlog|snort|suricata"} '
        '|~ "(?i)(,block,|,reject,|blocked|denied)" [5m]))',
        "{{device_name}}",
        "logs/s",
    )


def _dns_panel(pid: int, x: int) -> dict:
    return _base_ts(
        pid,
        x,
        "DNS resolver activity (unbound)",
        'sum by (device_name) (rate({job="device-syslog", app="unbound"}[5m]))',
        "{{device_name}}",
        "logs/s",
    )


def main() -> int:
    n = patch_netclaw(BASE / "convergence-netclaw.json")
    s = patch_security(BASE / "convergence-security.json")
    print(f"netclaw: {n} change(s)")
    print(f"security: {s} change(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
