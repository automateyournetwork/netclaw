#!/usr/bin/env bash
# Runs ON a new GCP node (sent over IAP SSH by netclaw-gcp.py bootstrap). Re-runnable. No secrets involved.
# Prepares the host: prerequisites the NetClaw installer preflight requires + a NetClaw checkout. It does NOT run install.sh:
# that needs a real TTY and your own provider choices/keys (openclaw onboard), so it stays an interactive step.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get install -y -qq git python3 python3-venv curl xz-utils pipx >/dev/null
export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"
command -v uv >/dev/null || pipx install uv >/dev/null
node_ok() { command -v node >/dev/null && node -e 'const [a,b]=process.versions.node.split(".").map(Number);process.exit((a==24&&b>=16)||(a==26&&b>=1)||a>26?0:1)'; }
if ! node_ok; then
  arch=$(uname -m); case "$arch" in x86_64) arch=x64;; aarch64) arch=arm64;; esac
  ver=$(curl -fsS https://nodejs.org/dist/index.json | python3 -c "import json,sys;print(next(x['version'] for x in json.load(sys.stdin) if x['version'].startswith('v24.')))")
  tmp=$(mktemp -d); cd "$tmp"
  curl -fsSO "https://nodejs.org/dist/$ver/node-$ver-linux-$arch.tar.xz"
  curl -fsSO "https://nodejs.org/dist/$ver/SHASUMS256.txt"
  grep " node-$ver-linux-$arch.tar.xz\$" SHASUMS256.txt | sha256sum -c -   # checksum-verified download
  sudo tar -xJf "node-$ver-linux-$arch.tar.xz" -C /usr/local --strip-components=1
  cd "$HOME"; rm -rf "$tmp"
fi
hash -r
if [ -d netclaw/.git ]; then git -C netclaw pull -q --ff-only; else git clone -q --depth 1 https://github.com/automateyournetwork/netclaw.git; fi
echo "READY node=$(node -v) uv=$(uv --version | cut -d' ' -f2) checkout=$HOME/netclaw"
