#!/usr/bin/env bash
# R09 (spec 182) Border VM bootstrap. Run as root on a fresh Debian 12 nc182-border-* VM.
# Idempotent. Installs only what a Border needs; no secrets are handled here.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq docker.io chrony curl ca-certificates iptables tar xz-utils jq >/dev/null
systemctl enable --now docker chrony >/dev/null 2>&1

id nc182 >/dev/null 2>&1 || useradd --system --home-dir /var/lib/nc182 --shell /usr/sbin/nologin nc182
install -d -m 0755 /opt/nc182
install -d -m 0700 -o nc182 -g nc182 /var/lib/nc182
echo 'net.ipv4.ip_unprivileged_port_start=443' >/etc/sysctl.d/90-nc182.conf
sysctl --system >/dev/null

# Python 3.12 (contract environments use 3.12) via uv, into an immutable-able root-owned prefix.
if [ ! -x /opt/nc182/venv/bin/python ]; then
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/opt/nc182/uv UV_NO_MODIFY_PATH=1 sh >/dev/null
  export UV_PYTHON_INSTALL_DIR=/opt/nc182/uv-python UV_CACHE_DIR=/root/.cache/uv
  /opt/nc182/uv/uv python install 3.12 >/dev/null
  /opt/nc182/uv/uv venv --python 3.12 /opt/nc182/venv >/dev/null
  /opt/nc182/uv/uv pip install --python /opt/nc182/venv/bin/python -q \
    cryptography==50.0.2 pyOpenSSL==26.4.0 service-identity==26.1.0 \
    'httpx>=0.27' 'websockets>=12.0,<17' 'qrcode>=7.4' 'PyYAML>=6.0' 'h2>=4.1' >/dev/null
fi

# Node 24 LTS for the HUD ingress (checksum verified against nodejs.org SHASUMS).
if [ ! -x /opt/nc182/node/bin/node ]; then
  base=https://nodejs.org/dist/latest-v24.x
  line=$(curl -fsSL "$base/SHASUMS256.txt" | grep 'linux-x64.tar.xz$')
  file=$(echo "$line" | awk '{print $2}'); want=$(echo "$line" | awk '{print $1}')
  curl -fsSL "$base/$file" -o /tmp/node.tar.xz
  echo "$want  /tmp/node.tar.xz" | sha256sum -c - >/dev/null
  mkdir -p /opt/nc182/node && tar -xJf /tmp/node.tar.xz -C /opt/nc182/node --strip-components=1
  rm -f /tmp/node.tar.xz
fi

# etcd image (official), recorded by digest for the evidence record.
docker pull -q gcr.io/etcd-development/etcd:v3.6.16 >/dev/null
docker image inspect gcr.io/etcd-development/etcd:v3.6.16 --format '{{index .RepoDigests 0}}' >/var/lib/nc182/etcd-image.digest

echo "python: $(/opt/nc182/venv/bin/python --version) node: $(/opt/nc182/node/bin/node --version) docker: $(docker --version)"
echo "chrony: $(chronyc tracking 2>/dev/null | head -1)"
