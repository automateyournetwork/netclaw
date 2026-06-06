#!/usr/bin/env bash
# Recreate IP SLA jitter probes with frequency (IOL rejects adding frequency after udp-jitter exists).
set -euo pipefail
ANSIBLE_LAB="${ANSIBLE_LAB:-$HOME/Nautobot-Workshop/ansible-lab}"
cd "$ANSIBLE_LAB" && . .venv/bin/activate

fix_pe() {
  local host="$1" pe2="$2" pe3="$3" ce="$4"
  echo "Fixing IP SLA on $host..."
  ansible "$host" -m ios_config -a "lines='no ip sla schedule 10\nno ip sla 10\nno ip sla schedule 20\nno ip sla 20'" -o
  ansible "$host" -m ios_config -a "lines='ip sla 10\n udp-jitter ${pe2} 16384 num-packets 100\n frequency 60\n threshold 3000\n owner netclaw-jitter-10\nip sla schedule 10 life forever start-time now\nip sla 20\n udp-jitter ${pe3} 16384 num-packets 100\n frequency 60\n threshold 3000\n owner netclaw-jitter-20\nip sla schedule 20 life forever start-time now'" -o
}

fix_pe PE1 100.0.254.12 100.0.254.13 100.0.254.111
fix_pe PE2 100.0.254.11 100.0.254.13 100.0.254.112
fix_pe PE3 100.0.254.11 100.0.254.12 100.0.254.113
echo "Done. Wait 2 minutes for IP SLA SNMP metrics."