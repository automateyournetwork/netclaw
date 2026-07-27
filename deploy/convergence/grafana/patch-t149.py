#!/usr/bin/env python3
"""T149 — Security board queries structured OTel fields, not labels or regex.

Before (promtail + syslog-gateway): `app` was a Loki *label*, derived by syslog-ng
from the first token before the colon. On Cisco that token is the mnemonic
(%SEC_LOGIN-5-LOGIN_SUCCESS), so every new message type minted a new stream —
unbounded label cardinality.

After (OTel): appname / mnemonic / facility / priority are structured fields
inside the log record. Labels stay a bounded set (device_name, site, job,
service_name, level). Queries use `| json` and filter on `attributes_*`, verified
against live data:

    attributes_appname, attributes_facility, attributes_priority,
    attributes_message, attributes_mnemonic, attributes_sev_level

Cisco gets `attributes_mnemonic` from the vendor regex operator in the collector
config, because IOS syslog is not RFC3164-compliant.

Run from repo root:  python3 deploy/convergence/grafana/patch-t149.py
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

# T157: filterlog is parsed at ingest, so select the action FIELD instead of
# keyword-matching the raw CSV. `,block,` also matched pass lines whose payload
# happened to contain the string.
FIREWALL_SEL = (
    '{job="device-syslog"} | json '
    '| attributes_appname=~"filterlog|snort|suricata" '
    '| attributes_action=~"block|reject"'
)

AUTH_SEL = (
    '{job="device-syslog"} | json '
    '| attributes_appname=~"sshd|sudo|su|login|nginx|openvpn" or '
    'attributes_mnemonic=~"SEC_LOGIN.*|SYS-\\\\d-LOG(IN|OUT).*|AAA.*" '
    '|~ "(?i)(fail|invalid|accepted|authenticat|login|logout)"'
)

PANELS = {
    81: ("Firewall blocks (filterlog / IDS)", FIREWALL_SEL),
    82: ("Auth / login events", AUTH_SEL),
    83: (
        "Firewall block rate by device",
        'sum by (device_name) (rate({job="device-syslog"} | json '
        '| attributes_appname=~"filterlog|snort|suricata" '
        '| attributes_action=~"block|reject" [5m]))',
    ),
    84: (
        "DNS resolver activity (unbound)",
        'sum by (device_name) (rate({job="device-syslog"} | json '
        '| attributes_appname="unbound" [5m]))',
    ),
}


def main() -> int:
    d = json.loads(BOARD.read_text())
    changed = 0
    for p in d.get("panels", []):
        spec = PANELS.get(p.get("id"))
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
    if changed:
        BOARD.write_text(json.dumps(d, indent=2) + "\n")
    print(f"security board: {changed} change(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
