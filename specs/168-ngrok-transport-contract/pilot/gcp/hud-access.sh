#!/usr/bin/env bash
# Operator command: run only after the reviewed pilot and HUD are provisioned.
# gcloud may register the operator's SSH key through OS Login. No public HUD port.
set -euo pipefail
if [[ $# -ne 3 ]]; then
  echo "Usage: $0 PROJECT ZONE INSTANCE" >&2
  exit 2
fi
for value in "$@"; do
  [[ "$value" =~ ^[a-z][a-z0-9-]+$ ]] || { echo 'Invalid target identifier' >&2; exit 2; }
done
echo 'After authentication, open http://127.0.0.1:13000/ while this tunnel stays open.'
exec gcloud compute ssh "$3" --project "$1" --zone "$2" \
  --tunnel-through-iap --strict-host-key-checking=yes -- \
  -N -o ExitOnForwardFailure=yes -o ForwardAgent=no \
  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:13000:127.0.0.1:13000 \
  -L 127.0.0.1:13001:127.0.0.1:13001
