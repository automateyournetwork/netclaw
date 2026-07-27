#!/usr/bin/env python3
"""Network board — interface table shows Device / Interface / Status only.

Drops the redundant identity columns: `ifIndex` is a wire-protocol detail and
`ifName` is the abbreviated form of the same string already shown as Interface
(`Gi1/0/13` vs `GigabitEthernet1/0/13`). `ifDescr` is likewise the source of
`interface_name`, so it is dropped too.

Status is IF-MIB ifOperStatus (RFC 2863), rendered as text instead of a bare
integer:

    1 up   2 down   3 testing   4 unknown   5 dormant
    6 notPresent    7 lowerLayerDown

Rows sort DOWN-first so problems surface without scrolling.

Run from repo root:  python3 deploy/convergence/grafana/patch-interface-status.py
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
    / "convergence-network.json"
)

# ifOperStatus value → (display text, colour)
OPER_STATUS = {
    "1": ("UP", "green"),
    "2": ("DOWN", "red"),
    "3": ("TESTING", "yellow"),
    "4": ("UNKNOWN", "text"),
    "5": ("DORMANT", "blue"),
    "6": ("NOT PRESENT", "text"),
    "7": ("LOWER LAYER DOWN", "orange"),
}

DROP_COLUMNS = [
    "Time",
    "__name__",
    "job",
    "site",
    "instance",
    "role",
    "vendor",
    "snmp_module",
    # redundant interface identity — interface_name already carries the name
    "ifIndex",
    "ifName",
    "ifDescr",
]


def build_panel(existing: dict) -> dict:
    grid = existing.get("gridPos", {"h": 7, "w": 12, "x": 12, "y": 22})
    return {
        "id": existing["id"],
        "title": "Interface status",
        "description": (
            "IF-MIB ifOperStatus per switch interface. UP/DOWN is the operational "
            "state; an admin-down port also reports DOWN. Sorted DOWN first."
        ),
        "type": "table",
        "gridPos": grid,
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {
                "refId": "A",
                "expr": 'interface_status{job="device_snmp"}',
                "format": "table",
                "instant": True,
                "datasource": {"type": "prometheus", "uid": "prometheus"},
            }
        ],
        "options": {
            "showHeader": True,
            "sortBy": [{"displayName": "Status", "desc": True}],
        },
        "fieldConfig": {
            "defaults": {
                "custom": {
                    "align": "auto",
                    "cellOptions": {"type": "auto"},
                    "filterable": True,
                }
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Status"},
                    "properties": [
                        {
                            "id": "mappings",
                            "value": [
                                {
                                    "type": "value",
                                    "options": {
                                        value: {
                                            "text": text,
                                            "color": colour,
                                            "index": i,
                                        }
                                    },
                                }
                                for i, (value, (text, colour)) in enumerate(
                                    OPER_STATUS.items()
                                )
                            ],
                        },
                        {
                            "id": "custom.cellOptions",
                            "value": {"type": "color-text"},
                        },
                        {"id": "custom.width", "value": 170},
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "Device"},
                    "properties": [{"id": "custom.width", "value": 160}],
                },
            ],
        },
        "transformations": [
            {"id": "labelsToFields", "options": {}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": {c: True for c in DROP_COLUMNS},
                    "indexByName": {
                        "device_name": 0,
                        "interface_name": 1,
                        "Value": 2,
                    },
                    "renameByName": {
                        "device_name": "Device",
                        "interface_name": "Interface",
                        "Value": "Status",
                    },
                },
            },
        ],
    }


def main() -> int:
    d = json.loads(BOARD.read_text())
    panels = d["panels"]
    for i, p in enumerate(panels):
        if p.get("id") == 23:
            new = build_panel(p)
            if p == new:
                print("interface status panel: already current")
                return 0
            panels[i] = new
            BOARD.write_text(json.dumps(d, indent=2) + "\n")
            print("interface status panel: updated (Device / Interface / Status)")
            return 0
    print("panel id 23 not found", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
