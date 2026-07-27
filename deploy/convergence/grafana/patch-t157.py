#!/usr/bin/env python3
"""T157 — restore the pilot's firewall-detail panels on structured fields.

The pilot's pfsense-security-overview / network-syslog boards had "Top Blocked
Source IPs", "Blocks by Interface (VLAN)" and "WAN Inbound Blocks by Protocol".
Consolidating to three boards dropped them — a real capability regression, since
the data was there the whole time.

The pilot built them at QUERY time with positional extraction:

    | json | line_format "{{.body}}" | regexp "(?P<src>[0-9]+[.]...),..."
    | pattern `<_>,<_>,<_>,<_>,<_>,match,block,<dir>,...,<src>,<dst>,<_>`
    ... and `|= "lagg0.100"` substring matching for interfaces

which bakes CSV offsets into every panel and false-positives when an IP or port
contains the interface string. The collector now parses filterlog at ingest
(T157), so these panels select real fields instead.

Cardinality: src_ip/dst_ip are FIELDS, never Loki labels — external scanner IPs
are unbounded (FR-042). Grouping happens at query time, which is safe.

Run from repo root:  python3 deploy/convergence/grafana/patch-t157.py
Idempotent.
"""
from __future__ import annotations

import json
import pathlib
import sys

BOARD = (
    pathlib.Path(__file__).resolve().parent
    / "provisioning"
    / "dashboards"
    / "json"
    / "convergence-security.json"
)

FILTERLOG = '{job="device-syslog"} | json | attributes_appname="filterlog"'
BLOCKED = f'{FILTERLOG} | attributes_action="block"'

ROW_ID = 210
PANELS = [
    (
        90,
        "table",
        0,
        12,
        "Top blocked source IPs",
        f"topk(15, sum by (attributes_src_ip) (count_over_time({BLOCKED} [$__range])))",
        "{{attributes_src_ip}}",
        "short",
        "External IPs are a structured field, not a label — unbounded values cannot "
        "explode Loki stream count. Enrichment (AbuseIPDB/GreyNoise/OTX) is done by "
        "NetClaw's pfsense-threat-intel skill at investigation time, deliberately "
        "not at ingest, so rate-limited APIs are only spent on IPs that survive triage.",
    ),
    (
        91,
        "timeseries",
        12,
        12,
        "Blocks by interface (VLAN)",
        f"sum by (attributes_fw_interface) (rate({BLOCKED} [5m]))",
        "{{attributes_fw_interface}}",
        "logs/s",
        "Selects the parsed interface field. The pilot substring-matched the "
        "interface name anywhere in the raw line, which false-positives when an IP "
        "or port contains the same digits.",
    ),
    (
        92,
        "timeseries",
        0,
        12,
        "WAN inbound blocks by protocol",
        f'sum by (attributes_protocol) (rate({BLOCKED} | attributes_direction="in" '
        f'| attributes_fw_interface=~"$wan_interface" [5m]))',
        "{{attributes_protocol}}",
        "logs/s",
        "Protocol case is normalised at ingest (v4 sends `tcp`, v6 sends `TCP`), so "
        "one protocol does not split across two series.",
    ),
    (
        93,
        "timeseries",
        12,
        12,
        "Block vs pass rate",
        f"sum by (attributes_action) (rate({FILTERLOG} [5m]))",
        "{{attributes_action}}",
        "logs/s",
        "Verdict accounting. Parse coverage is 100% of live filterlog lines; a gap "
        "here means the CSV layout changed.",
    ),
]


def ts_panel(pid, ptype, x, y, title, expr, legend, unit, desc) -> dict:
    p = {
        "id": pid,
        "type": ptype,
        "title": title,
        "description": desc,
        "datasource": {"type": "loki", "uid": "loki"},
        "gridPos": {"h": 8, "w": 12, "x": x, "y": y},
        "targets": [
            {
                "refId": "A",
                "datasource": {"type": "loki", "uid": "loki"},
                "expr": expr,
                "legendFormat": legend,
                "queryType": "range",
            }
        ],
        "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
    }
    if ptype == "timeseries":
        p["fieldConfig"]["defaults"]["custom"] = {
            "lineWidth": 1,
            "fillOpacity": 10,
            "showPoints": "never",
        }
        p["options"] = {
            "legend": {"displayMode": "list", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"},
        }
    else:
        p["targets"][0]["instant"] = True
        p["targets"][0]["queryType"] = "instant"
        p["options"] = {"showHeader": True, "sortBy": [{"displayName": "Value", "desc": True}]}
        p["transformations"] = [
            {"id": "labelsToFields", "options": {}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": {"Time": True},
                    "renameByName": {
                        "attributes_src_ip": "Source IP",
                        "Value": "Blocks",
                    },
                },
            },
        ]
    return p


def main() -> int:
    d = json.loads(BOARD.read_text())
    panels = d["panels"]

    if any(p.get("id") == ROW_ID for p in panels):
        print("firewall detail row: already present")
        return 0

    base_y = max(p.get("gridPos", {}).get("y", 0) + p.get("gridPos", {}).get("h", 0) for p in panels)
    panels.append(
        {
            "id": ROW_ID,
            "type": "row",
            "title": "Firewall detail (parsed filterlog)",
            "collapsed": False,
            "gridPos": {"h": 1, "w": 24, "x": 0, "y": base_y},
            "panels": [],
        }
    )
    for i, (pid, ptype, x, _w, title, expr, legend, unit, desc) in enumerate(PANELS):
        y = base_y + 1 + (i // 2) * 8
        panels.append(ts_panel(pid, ptype, x, y, title, expr, legend, unit, desc))

    # WAN interface is site-specific; make it a variable rather than hardcoding.
    templating = d.setdefault("templating", {}).setdefault("list", [])
    if not any(v.get("name") == "wan_interface" for v in templating):
        templating.append(
            {
                "name": "wan_interface",
                "label": "WAN interface",
                "type": "textbox",
                "query": "igc0.201",
                "current": {"text": "igc0.201", "value": "igc0.201"},
                "options": [],
                "hide": 0,
            }
        )

    BOARD.write_text(json.dumps(d, indent=2) + "\n")
    print(f"firewall detail row added: {len(PANELS)} panels + wan_interface variable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
