#!/usr/bin/env python3
"""Apply IP SLA (PE) and BMP (RR1) stanzas to CSR lab routers via SSH."""

from __future__ import annotations

import subprocess
import sys
import time

USER = "admin"
PASS = "admin"

PE_DEVICES = {
    "PE1": "192.168.220.6",
    "PE2": "192.168.220.7",
    "PE3": "192.168.220.8",
}

RR1 = "192.168.220.11"

PE_SLA = {
    "PE1": """\
ip sla responder
ip sla 10
 udp-jitter 100.0.254.12 16384 num-packets 100
 frequency 60
 threshold 3000
 owner netclaw-jitter-10
ip sla schedule 10 life forever start-time now
ip sla 20
 udp-jitter 100.0.254.13 16384 num-packets 100
 frequency 60
 threshold 3000
 owner netclaw-jitter-20
ip sla schedule 20 life forever start-time now
ip sla 30
 icmp-echo 100.0.254.111
 frequency 30
 threshold 5000
 owner netclaw-icmp-echo-30
ip sla schedule 30 life forever start-time now
""",
    "PE2": """\
ip sla responder
ip sla 10
 udp-jitter 100.0.254.11 16384 num-packets 100
 frequency 60
 threshold 3000
 owner netclaw-jitter-10
ip sla schedule 10 life forever start-time now
ip sla 20
 udp-jitter 100.0.254.13 16384 num-packets 100
 frequency 60
 threshold 3000
 owner netclaw-jitter-20
ip sla schedule 20 life forever start-time now
ip sla 30
 icmp-echo 100.0.254.112
 frequency 30
 threshold 5000
 owner netclaw-icmp-echo-30
ip sla schedule 30 life forever start-time now
""",
    "PE3": """\
ip sla responder
ip sla 10
 udp-jitter 100.0.254.11 16384 num-packets 100
 frequency 60
 threshold 3000
 owner netclaw-jitter-10
ip sla schedule 10 life forever start-time now
ip sla 20
 udp-jitter 100.0.254.12 16384 num-packets 100
 frequency 60
 threshold 3000
 owner netclaw-jitter-20
ip sla schedule 20 life forever start-time now
ip sla 30
 icmp-echo 100.0.254.112
 frequency 30
 threshold 5000
 owner netclaw-icmp-echo-30
ip sla schedule 30 life forever start-time now
""",
}

BMP_BLOCK = """\
router bgp 65000
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
"""


def ssh_config(host: str, lines: str, label: str) -> bool:
    script = f"configure terminal\n{lines}\nend\nwrite memory\n"
    cmd = [
        "sshpass", "-p", PASS,
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=20",
        f"{USER}@{host}",
    ]
    print(f"Applying {label} to {host}...")
    proc = subprocess.run(
        cmd,
        input=script,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        print(proc.stderr or proc.stdout, file=sys.stderr)
        return False
    if "% Invalid" in proc.stdout or "ERROR" in proc.stdout:
        print(proc.stdout, file=sys.stderr)
        return False
    print(f"  OK: {label}")
    return True


def main() -> int:
    ok = True
    for name, ip in PE_DEVICES.items():
        if not ssh_config(ip, PE_SLA[name], f"IP SLA ({name})"):
            ok = False
        time.sleep(3)
    if not ssh_config(RR1, BMP_BLOCK, "BMP (RR1)"):
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())