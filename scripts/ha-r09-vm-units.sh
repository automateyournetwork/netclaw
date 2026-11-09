#!/usr/bin/env bash
# R09 (spec 182): systemd units for one Border (role launcher) and its public HUD ingress. Run as root.
set -euo pipefail
S=/var/lib/nc182
cat >/etc/systemd/system/nc182-border.service <<UNIT
[Unit]
Description=nc182 NetClaw HA Border (protected role launcher)
After=network-online.target nc182-net.service docker.service
Wants=network-online.target
[Service]
User=nc182
WorkingDirectory=$S/home
Environment=PATH=/usr/bin:/bin HOME=$S/home
ExecStart=/opt/nc182/venv/bin/python -I -B /opt/nc182/source/scripts/protected-role.py --contract $S/contract.json run
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
cat >/etc/systemd/system/nc182-hud.service <<UNIT
[Unit]
Description=nc182 NetClaw Border HUD ingress (public HTTPS)
After=nc182-border.service
[Service]
User=nc182
WorkingDirectory=$S/hud
Environment=PATH=/usr/bin:/bin HOME=$S/hud
ExecStart=/opt/nc182/node/bin/node /opt/nc182/hud-source/labs/ha/hud_ingress_r09.mjs serve $S/hud/ingress.json
Restart=on-failure
RestartSec=5
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
case "${1:-}" in
  border) systemctl enable --now nc182-border.service ;;
  hud) systemctl enable --now nc182-hud.service ;;
esac
