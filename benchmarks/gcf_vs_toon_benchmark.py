"""Benchmark: GCF vs TOON vs JSON token costs on NetClaw network data.

Generates realistic network data matching NetClaw's actual MCP server payloads
and measures token counts across all three formats.

Usage:
    pip install gcf toon-format tiktoken
    python benchmarks/gcf_vs_toon_benchmark.py
"""

import json
import random
import string
import subprocess
import tempfile
import tiktoken

from gcf import encode_generic

# Use cl100k_base (GPT-4/Claude tokenizer approximation)
enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


def toon_encode(data) -> str:
    """Encode data using TOON's Node.js library (their flagship implementation)."""
    json_str = json.dumps(data)
    script = f"""
const {{ encode }} = require('@toon-format/toon');
const data = JSON.parse({json.dumps(json_str)});
process.stdout.write(encode(data, {{ keyFolding: 'safe' }}));
"""
    import os
    netclaw_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    result = subprocess.run(
        ["node", "-e", script],
        capture_output=True, text=True, timeout=30,
        cwd=netclaw_root,
    )
    if result.returncode != 0:
        raise RuntimeError(f"TOON encode failed: {result.stderr}")
    return result.stdout


# ---------------------------------------------------------------------------
# Realistic network data generators (matching NetClaw MCP server payloads)
# ---------------------------------------------------------------------------

def generate_bgp_peers(n: int) -> dict:
    """BGP peer sessions (protocol-mcp: get_peers)."""
    states = ["Established", "Active", "Idle", "Connect", "OpenSent", "OpenConfirm"]
    peers = []
    for i in range(n):
        peers.append({
            "neighbor": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "remote_as": random.randint(64512, 65534),
            "local_as": 65000,
            "state": random.choice(states),
            "uptime_seconds": random.randint(0, 864000),
            "prefixes_received": random.randint(0, 50000),
            "prefixes_sent": random.randint(0, 10000),
            "messages_received": random.randint(100, 1000000),
            "messages_sent": random.randint(100, 1000000),
            "description": f"Transit-Peer-{i+1}",
            "address_family": "ipv4-unicast",
            "hold_time": 180,
            "keepalive_interval": 60,
        })
    return {"peers": peers, "count": n}


def generate_route_table(n: int) -> dict:
    """BGP RIB entries (protocol-mcp: get_rib)."""
    origins = ["igp", "egp", "incomplete"]
    routes = []
    for i in range(n):
        prefix = f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.0/24"
        routes.append({
            "prefix": prefix,
            "next_hop": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "as_path": " ".join(str(random.randint(1, 65534)) for _ in range(random.randint(1, 6))),
            "local_pref": random.choice([100, 150, 200]),
            "med": random.randint(0, 1000),
            "origin": random.choice(origins),
            "communities": f"{random.randint(1,65534)}:{random.randint(1,65534)}",
            "valid": True,
            "best": random.random() > 0.3,
            "weight": random.choice([0, 100, 32768]),
        })
    return {"routes": routes, "count": n}


def generate_interfaces(n: int) -> dict:
    """Network interfaces (suzieq-mcp: query interfaces)."""
    types = ["ethernet", "loopback", "vlan", "port-channel", "management"]
    states = ["up", "down", "admin-down"]
    interfaces = []
    for i in range(n):
        itype = random.choice(types)
        interfaces.append({
            "hostname": f"switch-{random.randint(1,20):02d}",
            "ifname": f"{'Ethernet' if itype == 'ethernet' else itype.capitalize()}{random.randint(1,96)}",
            "state": random.choice(states),
            "adminState": random.choice(["up", "down"]),
            "type": itype,
            "mtu": random.choice([1500, 9000, 9214]),
            "speed": random.choice([1000, 10000, 25000, 40000, 100000]),
            "ipAddressList": [f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}/30"],
            "macaddr": ":".join(f"{random.randint(0,255):02x}" for _ in range(6)),
            "vlan": random.randint(1, 4094),
            "master": "",
            "description": f"Link-to-{''.join(random.choices(string.ascii_lowercase, k=6))}",
        })
    return {"interfaces": interfaces, "count": n}


def generate_ospf_neighbors(n: int) -> dict:
    """OSPF neighbor sessions (protocol-mcp: get_ospf_neighbors)."""
    states = ["Full", "2-Way", "ExStart", "Exchange", "Loading", "Init", "Down"]
    neighbors = []
    for i in range(n):
        neighbors.append({
            "router_id": f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
            "neighbor_address": f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}",
            "state": random.choice(states[:3]),  # mostly Full/2-Way
            "area": f"0.0.0.{random.choice([0, 1, 2, 10, 20])}",
            "interface": f"Ethernet{random.randint(1,48)}",
            "priority": random.choice([0, 1, 128]),
            "dead_timer": random.randint(30, 40),
            "uptime_seconds": random.randint(0, 864000),
            "dr": f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
            "bdr": f"10.0.{random.randint(0,255)}.{random.randint(1,254)}",
            "options": "0x12",
        })
    return {"neighbors": neighbors, "count": n}


def generate_nsg_rules(n: int) -> dict:
    """Azure NSG rules (azure-network-mcp: list_nsgs)."""
    actions = ["Allow", "Deny"]
    directions = ["Inbound", "Outbound"]
    protocols = ["TCP", "UDP", "ICMP", "*"]
    rules = []
    for i in range(n):
        rules.append({
            "name": f"Rule-{i+1:03d}",
            "priority": 100 + i * 10,
            "direction": random.choice(directions),
            "access": random.choice(actions),
            "protocol": random.choice(protocols),
            "source_address_prefix": random.choice(["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "*", "VirtualNetwork"]),
            "destination_address_prefix": random.choice(["10.0.0.0/8", "*", "AzureLoadBalancer", "Internet"]),
            "source_port_range": random.choice(["*", "1024-65535", "80", "443"]),
            "destination_port_range": random.choice(["80", "443", "22", "3389", "1433", "*"]),
            "description": f"{'Allow' if random.random() > 0.3 else 'Deny'} traffic for service-{i+1}",
            "provisioning_state": "Succeeded",
        })
    return {"nsg_name": "prod-web-nsg", "resource_group": "rg-networking", "rules": rules, "count": n}


# ---------------------------------------------------------------------------
# Benchmark runner
# ---------------------------------------------------------------------------

DATASETS = {
    "BGP Peers": generate_bgp_peers,
    "Route Table": generate_route_table,
    "Interfaces": generate_interfaces,
    "OSPF Neighbors": generate_ospf_neighbors,
    "NSG Rules": generate_nsg_rules,
}

SIZES = [10, 50, 100, 200, 500]


def benchmark():
    random.seed(42)

    print("=" * 90)
    print("NetClaw Benchmark: GCF vs TOON vs JSON (token counts via cl100k_base)")
    print("=" * 90)
    print()

    all_results = []

    for dataset_name, generator in DATASETS.items():
        print(f"--- {dataset_name} ---")
        print(f"{'Rows':>6}  {'JSON':>8}  {'TOON':>8}  {'GCF':>8}  {'TOON%':>7}  {'GCF%':>7}  {'GCF vs TOON':>12}")
        print(f"{'':>6}  {'tokens':>8}  {'tokens':>8}  {'tokens':>8}  {'saved':>7}  {'saved':>7}  {'delta':>12}")
        print("-" * 90)

        for size in SIZES:
            data = generator(size)

            json_str = json.dumps(data, indent=2)
            toon_str = toon_encode(data)
            gcf_str = encode_generic(data)

            json_tokens = count_tokens(json_str)
            toon_tokens = count_tokens(toon_str)
            gcf_tokens = count_tokens(gcf_str)

            toon_savings = (1 - toon_tokens / json_tokens) * 100
            gcf_savings = (1 - gcf_tokens / json_tokens) * 100
            gcf_vs_toon = (1 - gcf_tokens / toon_tokens) * 100

            all_results.append({
                "dataset": dataset_name,
                "rows": size,
                "json_tokens": json_tokens,
                "toon_tokens": toon_tokens,
                "gcf_tokens": gcf_tokens,
                "toon_savings_pct": round(toon_savings, 1),
                "gcf_savings_pct": round(gcf_savings, 1),
                "gcf_vs_toon_pct": round(gcf_vs_toon, 1),
            })

            print(f"{size:>6}  {json_tokens:>8,}  {toon_tokens:>8,}  {gcf_tokens:>8,}  {toon_savings:>6.1f}%  {gcf_savings:>6.1f}%  {gcf_vs_toon:>+10.1f}%")

        print()

    # Summary
    print("=" * 90)
    print("SUMMARY")
    print("=" * 90)

    avg_toon = sum(r["toon_savings_pct"] for r in all_results) / len(all_results)
    avg_gcf = sum(r["gcf_savings_pct"] for r in all_results) / len(all_results)
    avg_gcf_vs_toon = sum(r["gcf_vs_toon_pct"] for r in all_results) / len(all_results)

    gcf_wins = sum(1 for r in all_results if r["gcf_tokens"] < r["toon_tokens"])
    toon_wins = sum(1 for r in all_results if r["toon_tokens"] < r["gcf_tokens"])
    ties = sum(1 for r in all_results if r["gcf_tokens"] == r["toon_tokens"])

    print(f"  Average TOON savings vs JSON:  {avg_toon:.1f}%")
    print(f"  Average GCF savings vs JSON:   {avg_gcf:.1f}%")
    print(f"  Average GCF savings vs TOON:   {avg_gcf_vs_toon:.1f}%")
    print(f"  GCF wins: {gcf_wins}/{len(all_results)}, TOON wins: {toon_wins}/{len(all_results)}, Ties: {ties}/{len(all_results)}")
    print()

    # Total tokens across all tests
    total_json = sum(r["json_tokens"] for r in all_results)
    total_toon = sum(r["toon_tokens"] for r in all_results)
    total_gcf = sum(r["gcf_tokens"] for r in all_results)
    print(f"  Total JSON tokens:  {total_json:>10,}")
    print(f"  Total TOON tokens:  {total_toon:>10,}  ({(1 - total_toon/total_json)*100:.1f}% less than JSON)")
    print(f"  Total GCF tokens:   {total_gcf:>10,}  ({(1 - total_gcf/total_json)*100:.1f}% less than JSON)")
    print(f"  GCF vs TOON total:  {total_gcf - total_toon:>+10,} tokens ({(1 - total_gcf/total_toon)*100:.1f}% less)")


if __name__ == "__main__":
    benchmark()
