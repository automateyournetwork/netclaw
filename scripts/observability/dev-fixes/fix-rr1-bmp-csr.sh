#!/usr/bin/env bash
# CSR1000v BMP fix: Gi1 must be global (no clab-mgmt VRF); no bmp update-source.
set -euo pipefail

HOST="${RR1_HOST:-192.168.220.11}"
PASS="${CSR_PASS:-admin}"

CFG=$(cat <<'EOF'
configure terminal
interface GigabitEthernet1
 no vrf forwarding clab-mgmt
 ip address 192.168.220.11 255.255.255.0
 no shutdown
ip route 0.0.0.0 0.0.0.0 GigabitEthernet1 192.168.220.1
no logging host 192.168.3.252 vrf clab-mgmt
logging host 192.168.3.252 transport udp port 1514
router bgp 65000
 no bmp server 1
 bmp initial-refresh delay 30
 neighbor BACKBONE-RR-IPV4-PEERS bmp-activate server 1
 neighbor BACKBONE-RR-IPV6-PEERS bmp-activate server 1
 neighbor NETCLAW-MGMT-PEERS bmp-activate server 1
 bmp server 1
  address 192.168.3.252 port-number 5000
  description netclaw-gobmp
  initial-delay 5
  failure-retry-delay 5
  flapping-delay 30
  activate
 exit-bmp-server-mode
end
EOF
)

echo "Applying BMP fix to RR1 ($HOST)..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=20 "admin@${HOST}" <<< "$CFG"
sleep 15
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "admin@${HOST}" \
  'show ip bgp bmp server summary' | tail -5