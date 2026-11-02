#!/usr/bin/env bash
# Exact reviewed R01 activation, run as root on the newly created pilot VM only.
# Arguments are non-secret hashes and a Secret Manager version resource name.
set -euo pipefail
umask 077
[[ $EUID -eq 0 && $# -eq 4 ]] || { echo 'Expected root and SOURCE_ARCHIVE SOURCE_SHA SECRET_VERSION SECRET_SHA' >&2; exit 2; }
archive=$1
source_sha=$2
secret_version=$3
secret_sha=$4
[[ "$source_sha" =~ ^[a-f0-9]{64}$ && "$secret_sha" =~ ^[a-f0-9]{64}$ ]] || exit 2
[[ "$secret_version" =~ ^projects/netclaw-506315/secrets/netclaw-r01-20261101-runtime/versions/[0-9]+$ ]] || exit 2
[[ -f "$archive" && ! -L "$archive" ]] || exit 2
[[ "$(sha256sum "$archive" | cut -d' ' -f1)" == "$source_sha" ]] || { echo 'Source hash mismatch' >&2; exit 1; }
[[ ! -e /opt/netclaw-r01/source && ! -e /var/lib/netclaw-r01/claw ]] || {
  echo 'Pilot material already exists; reconcile the prior outcome, do not replay activation.' >&2; exit 1;
}
python3 - <<'PY'
import urllib.request
request = urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/name', headers={'Metadata-Flavor': 'Google'})
with urllib.request.urlopen(request, timeout=10) as response:
    if response.read().decode() != 'netclaw-r01-20261101':
        raise ValueError('Unexpected VM identity')
PY
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y curl xz-utils python3.12-venv ca-certificates
install -d -m 0755 /opt/netclaw-r01/source
python3 - "$archive" <<'PY'
import sys, tarfile
from pathlib import Path, PurePosixPath
with tarfile.open(sys.argv[1], 'r:gz') as archive:
    members = archive.getmembers()
    for entry in members:
        path = PurePosixPath(entry.name)
        if path.is_absolute() or '..' in path.parts or not (entry.isfile() or entry.isdir()) or '.env' in path.parts:
            raise ValueError('Unsafe source archive entry')
    archive.extractall('/opt/netclaw-r01/source', members=members, filter='data')
for path in Path('/opt/netclaw-r01/source').rglob('*'):
    path.chmod(0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644)
PY
curl -fsS https://nodejs.org/dist/v24.19.0/node-v24.19.0-linux-x64.tar.xz -o /opt/netclaw-r01/node.tar.xz
echo '14b342e71204f811bde6153be8e04b62aef63c236fef92b55f9c83154b409647  /opt/netclaw-r01/node.tar.xz' | sha256sum -c -
install -d -m 0755 /opt/netclaw-r01/node
tar -xJf /opt/netclaw-r01/node.tar.xz --strip-components=1 -C /opt/netclaw-r01/node
python3.12 -m venv /opt/netclaw-r01/venv
/opt/netclaw-r01/venv/bin/python -m pip install -r /opt/netclaw-r01/source/mcp-servers/protocol-mcp/requirements.txt
# The root-created dependency environment contains no runtime secrets. Grant the
# service group read/execute without granting it package-write permission.
chgrp -R netclaw-r01 /opt/netclaw-r01/venv
chmod -R g+rX /opt/netclaw-r01/venv
chown -R netclaw-r01:netclaw-r01 /opt/netclaw-r01/source/ui/netclaw-visual
sudo -u netclaw-r01 env PATH=/opt/netclaw-r01/node/bin:/usr/bin:/bin \
  npm --prefix /opt/netclaw-r01/source/ui/netclaw-visual ci --no-audit --no-fund
sudo -u netclaw-r01 env PATH=/opt/netclaw-r01/node/bin:/usr/bin:/bin \
  npm --prefix /opt/netclaw-r01/source/ui/netclaw-visual run build
install -d -m 0700 -o netclaw-r01 -g netclaw-r01 \
  /opt/netclaw-r01/source/ui/netclaw-visual/node_modules/.vite \
  /opt/netclaw-r01/source/ui/netclaw-visual/node_modules/.vite-temp
# Workload identity retrieves only the approved version; check its payload digest
# before writing any private runtime file. The OAuth token stays in memory.
python3 - "$secret_version" "$secret_sha" <<'PY'
import base64, hashlib, io, json, os, sys, tarfile, urllib.request
from pathlib import Path, PurePosixPath
request = urllib.request.Request('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token', headers={'Metadata-Flavor': 'Google'})
with urllib.request.urlopen(request, timeout=10) as response:
    token = json.load(response)['access_token']
request = urllib.request.Request('https://secretmanager.googleapis.com/v1/' + sys.argv[1] + ':access', headers={'Authorization': 'Bearer ' + token})
with urllib.request.urlopen(request, timeout=15) as response:
    payload = base64.b64decode(json.load(response)['payload']['data'], validate=True)
if len(payload) > 65536 or hashlib.sha256(payload).hexdigest() != sys.argv[2]:
    raise ValueError('Secret payload digest mismatch')
home = Path('/var/lib/netclaw-r01/claw'); home.mkdir(mode=0o700)
with tarfile.open(fileobj=io.BytesIO(payload), mode='r:gz') as archive:
    members = archive.getmembers()
    if sum(entry.size for entry in members) > 4 * 1024 * 1024:
        raise ValueError('Runtime payload exceeds bound')
    for entry in members:
        path = PurePosixPath(entry.name)
        if path.is_absolute() or '..' in path.parts or not (entry.isfile() or entry.isdir()):
            raise ValueError('Unsafe runtime archive entry')
    archive.extractall(home, members=members, filter='data')
for item in home.rglob('*'):
    item.chmod(0o700 if item.is_dir() else 0o600)
PY
install -d -m 0700 /var/lib/netclaw-r01/claw/python-runtimes/records
echo /opt/netclaw-r01/venv/bin/python > /var/lib/netclaw-r01/claw/python-runtimes/records/n2n
chown -R netclaw-r01:netclaw-r01 /var/lib/netclaw-r01/claw
for service in federation hud; do
  install -m 0644 "/opt/netclaw-r01/source/specs/168-ngrok-transport-contract/pilot/gcp/netclaw-r01-${service}.service" "/etc/systemd/system/netclaw-r01-${service}.service"
done
systemctl daemon-reload
systemctl enable --now netclaw-r01-federation.service netclaw-r01-hud.service
systemctl is-active netclaw-r01-federation.service netclaw-r01-hud.service
# Capture listener and selected-service status separately from application admission.
ss -ltnp
