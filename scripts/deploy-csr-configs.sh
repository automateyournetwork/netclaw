#!/usr/bin/env bash
# Push lab configs to CSR1000v nodes one at a time (avoids SSH overload).
set -euo pipefail

ANSIBLE_DIR="${ANSIBLE_DIR:-/home/ubuntu/Nautobot-Workshop/ansible-lab}"
DEVICES=(P1 P2 P3 P4 PE1 PE2 PE3 CE1 CE2 RR1)
USER=admin
PASS=admin

wait_ssh() {
  local ip=$1 name=$2
  for i in $(seq 1 40); do
    if sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
      "${USER}@${ip}" 'show version | include Version' &>/dev/null; then
      echo "  $name ($ip) SSH ready"
      return 0
    fi
    sleep 15
  done
  echo "  $name ($ip) SSH timeout" >&2
  return 1
}

push_config() {
  local name=$1 ip=$2 cfg="${ANSIBLE_DIR}/configs/${name}.conf"
  [ -f "$cfg" ] || { echo "missing $cfg" >&2; return 1; }
  echo "Pushing $name..."
  sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "${USER}@${ip}" <<EOF
configure terminal
$(grep -v '^!' "$cfg" | grep -v '^$' | grep -v '^version ' | grep -v '^boot-start-marker' | grep -v '^boot-end-marker' | sed 's/^/ /')
end
write memory
EOF
}

declare -A MGMT=(
  [P1]=192.168.220.2 [P2]=192.168.220.3 [P3]=192.168.220.4 [P4]=192.168.220.5
  [PE1]=192.168.220.6 [PE2]=192.168.220.7 [PE3]=192.168.220.8
  [CE1]=192.168.220.9 [CE2]=192.168.220.10 [RR1]=192.168.220.11
)

echo "Waiting for CSR boot..."
for d in "${DEVICES[@]}"; do
  wait_ssh "${MGMT[$d]}" "$d"
done

echo "Deploying configs serially..."
for d in "${DEVICES[@]}"; do
  push_config "$d" "${MGMT[$d]}" || exit 1
  sleep 5
done

echo "Done."