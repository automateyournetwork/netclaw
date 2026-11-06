#!/usr/bin/env python3
"""ExecStart helper for defenseclaw-sidecar.service (spec 177).

Starts the gateway with `defenseclaw-gateway start`, so DefenseClaw writes its own
PID record (pid, executable, start identity). The DefenseClaw CLI needs that record
to reach the gateway: `defenseclaw skill enable`, audit recording and status. A
foreground gateway never writes it.

systemd needs the gateway's PID as a bare number, so this copies the `pid` field
from DefenseClaw's record into $RUNTIME_DIRECTORY/gateway.pid for PIDFile=. It
never writes DefenseClaw's own record.
"""
import json
import os
from pathlib import Path
import subprocess
import sys


def record_path() -> Path:
    home = os.environ.get("DEFENSECLAW_HOME") or os.path.expanduser("~/.defenseclaw")
    return Path(home) / "gateway.pid"


def main(argv) -> int:
    if len(argv) != 2:
        print("usage: defenseclaw-sidecar-start.py /path/to/defenseclaw-gateway", file=sys.stderr)
        return 2
    gateway = argv[1]
    code = subprocess.run([gateway, "start"], stdin=subprocess.DEVNULL).returncode
    if code:
        return code
    try:
        record = json.loads(record_path().read_text())
        pid = record["pid"]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"defenseclaw-gateway started but its PID record is unreadable: {exc}", file=sys.stderr)
        return 1
    if not isinstance(pid, int) or pid <= 1:
        print("defenseclaw-gateway PID record has no valid pid", file=sys.stderr)
        return 1
    runtime = os.environ.get("RUNTIME_DIRECTORY")
    if not runtime:
        print("RUNTIME_DIRECTORY is unset; run this from the systemd unit", file=sys.stderr)
        return 1
    Path(runtime, "gateway.pid").write_text(f"{pid}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
