#!/bin/bash
set -euo pipefail
umask 077
archive=/tmp/netclaw-r01-public-hud-v2.tar.gz
expected=27cf46f45f10c57a328db90fde06475eae31cde8e36fb89ff7db3d54ef563635
[ "$(hostname)" = netclaw-r01-20261101 ]
[ ! -e /opt/netclaw-r01/public-hud ]
[ ! -e /etc/systemd/system/netclaw-r01-public-hud.service ]
[ ! -e /etc/systemd/system/netclaw-r01-https.service ]
if getent passwd netclaw-r01-web >/dev/null; then exit 1; fi
printf '%s  %s\n' "$expected" "$archive" | sha256sum --check
ss -ltnp
install -d -m 0755 /opt/netclaw-r01/public-hud
tar --no-same-owner -xzf "$archive" -C /opt/netclaw-r01/public-hud
chmod -R a+rX /opt/netclaw-r01/public-hud
chmod 0755 /opt/netclaw-r01/public-hud/caddy
useradd --system --home-dir /var/lib/netclaw-r01-web --shell /usr/sbin/nologin --no-create-home netclaw-r01-web
install -d -m 0700 -o netclaw-r01-web -g netclaw-r01-web /var/lib/netclaw-r01-web /var/lib/netclaw-r01-web/data /var/lib/netclaw-r01-web/config
sudo -u netclaw-r01-web env XDG_DATA_HOME=/var/lib/netclaw-r01-web/data XDG_CONFIG_HOME=/var/lib/netclaw-r01-web/config /opt/netclaw-r01/public-hud/caddy validate --config /opt/netclaw-r01/public-hud/Caddyfile --adapter caddyfile
install -m 0644 /opt/netclaw-r01/public-hud/netclaw-r01-public-hud.service /etc/systemd/system/netclaw-r01-public-hud.service
install -m 0644 /opt/netclaw-r01/public-hud/netclaw-r01-https.service /etc/systemd/system/netclaw-r01-https.service
systemctl daemon-reload
systemctl enable --now netclaw-r01-public-hud.service
systemctl enable netclaw-r01-https.service
systemctl is-active netclaw-r01-public-hud.service
# Start HTTPS only after authoritative DNS points at the approved public address.
