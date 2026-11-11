import os
import sys
from pathlib import Path

import pytest

SRV = Path(__file__).resolve().parents[2] / "mcp-servers" / "result-analysis-mcp"
sys.path.insert(0, str(SRV))


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    d = tmp_path / "results"
    monkeypatch.setenv("NETCLAW_RESULTS_DIR", str(d))
    for k in ("NETCLAW_RESULT_INLINE_BUDGET", "NETCLAW_RESULT_MAX_BYTES",
              "NETCLAW_RESULT_STORE_MAX_BYTES", "NETCLAW_RESULT_TTL_SECONDS",
              "NETCLAW_RESULT_MAX_SCAN"):
        monkeypatch.delenv(k, raising=False)
    return d


def interface_table(n_tunnel_up=300, n_tunnel_down=120, n_other=1500):
    """Genie-shaped `show ip interface brief`: {"interface": {name: {...}}}, > 170 KB."""
    ifs = {}
    for i in range(n_tunnel_up):
        ifs[f"Tunnel{i}"] = {"ip_address": f"10.{i // 250}.{i % 250}.1", "status": "up",
                             "protocol": "up", "method": "manual", "interface_ok": "YES"}
    for i in range(n_tunnel_down):
        ifs[f"Tunnel{1000 + i}"] = {"ip_address": "unassigned", "status": "administratively down",
                                    "protocol": "down", "method": "unset", "interface_ok": "YES"}
    for i in range(n_other):
        ifs[f"GigabitEthernet0/0/{i}"] = {"ip_address": "unassigned", "status": "up",
                                          "protocol": "up", "method": "unset",
                                          "interface_ok": "YES"}
    return {"status": "completed", "device": "r1", "command": "show ip interface brief",
            "output": {"interface": ifs}, "parsed": True}
