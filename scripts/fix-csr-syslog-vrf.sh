#!/usr/bin/env bash
# Fix CSR syslog: Gi1 is in vrf clab-mgmt; logging must use the same VRF.
set -euo pipefail

PASS="${CSR_PASS:-admin}"
HOSTS=(
  192.168.220.2   # P1
  192.168.220.3   # P2
  192.168.220.4   # P3
  192.168.220.5   # P4
  192.168.220.6   # PE1
  192.168.220.7   # PE2
  192.168.220.8   # PE3
  192.168.220.9   # CE1
  192.168.220.10  # CE2
  192.168.220.11  # RR1
)

CFG=$(cat <<'EOF'
configure terminal
no logging host 192.168.220.200
logging host 192.168.220.200 vrf clab-mgmt transport udp port 1514
logging on
logging trap informational
end
EOF
)

for host in "${HOSTS[@]}"; do
  echo "=== $host ==="
  if sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15 \
      "admin@${host}" <<< "$CFG" 2>&1 | grep -E '% Invalid|ERROR' ; then
    echo "  FAIL"
    exit 1
  fi
  echo "  OK"
done

echo "Done: CSR syslog VRF fixed on ${#HOSTS[@]} routers"