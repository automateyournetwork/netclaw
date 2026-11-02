#!/usr/bin/env bash
# Infrastructure bootstrap only. No NetClaw listener starts at VM creation.
set -euo pipefail
umask 077
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y python3.12-venv python3-pip ca-certificates
id netclaw-r01 >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/netclaw-r01 --shell /usr/sbin/nologin netclaw-r01
install -d -m 0700 -o netclaw-r01 -g netclaw-r01 /var/lib/netclaw-r01
install -d -m 0755 -o root -g root /opt/netclaw-r01
# The reviewed source archive, pinned Python environment, exact configuration and
# system unit are installed separately through IAP. Nothing accepts traffic yet.
