"""Benchmark: GCF graph profile vs generic profile on network topology data.

Network data is inherently graph-structured: devices are nodes, links/sessions
are edges. The generic profile encodes them as flat tables. The graph profile
uses local IDs and edge arrows, eliminating repeated identifiers.

This benchmark generates realistic network topologies and compares token counts
between generic profile (current NetClaw integration) and graph profile.

Usage:
    pip install gcf-python tiktoken
    python benchmarks/gcf_graph_benchmark.py
"""

import json
import random
import tiktoken

from gcf import encode, encode_generic, Payload, Symbol, Edge

enc = tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(enc.encode(text))


# ---------------------------------------------------------------------------
# Network topology generators
# ---------------------------------------------------------------------------

def generate_bgp_topology(n_devices: int, n_sessions: int):
    """BGP topology: devices as nodes, peering sessions as edges.

    Each device has a router ID, AS number, role, and location.
    Each session connects two devices with state and prefix counts.
    """
    roles = ["spine", "leaf", "border", "route-reflector", "pe", "ce"]
    locations = ["dc-east", "dc-west", "dc-central", "pop-nyc", "pop-lax", "pop-ord"]

    devices = []
    for i in range(n_devices):
        devices.append({
            "router_id": f"10.0.{i // 256}.{i % 256 + 1}",
            "hostname": f"rtr-{random.choice(['spine','leaf','border','rr'])}-{i+1:03d}",
            "as_number": random.choice([64512, 64513, 64514, 65000, 65001]),
            "role": random.choice(roles),
            "location": random.choice(locations),
            "vendor": random.choice(["cisco", "arista", "juniper", "nokia"]),
            "os_version": f"{random.randint(15,20)}.{random.randint(0,9)}.{random.randint(0,9)}",
        })

    sessions = []
    for _ in range(n_sessions):
        src = random.randint(0, n_devices - 1)
        tgt = random.randint(0, n_devices - 1)
        while tgt == src:
            tgt = random.randint(0, n_devices - 1)
        sessions.append({
            "source": devices[src]["hostname"],
            "target": devices[tgt]["hostname"],
            "state": random.choice(["Established", "Active", "Idle"]),
            "prefixes_received": random.randint(0, 50000),
            "prefixes_sent": random.randint(0, 10000),
            "session_type": random.choice(["ebgp", "ibgp", "ebgp-multihop"]),
        })

    return devices, sessions


def generate_ospf_topology(n_routers: int, n_adjacencies: int):
    """OSPF topology: routers as nodes, adjacencies as edges."""
    routers = []
    for i in range(n_routers):
        routers.append({
            "router_id": f"10.0.{i // 256}.{i % 256 + 1}",
            "hostname": f"ospf-{i+1:03d}",
            "area": f"0.0.0.{random.choice([0, 1, 2, 10])}",
            "role": random.choice(["dr", "bdr", "drother", "abr", "asbr"]),
            "lsa_count": random.randint(10, 5000),
            "spf_runs": random.randint(1, 200),
        })

    adjacencies = []
    for _ in range(n_adjacencies):
        src = random.randint(0, n_routers - 1)
        tgt = random.randint(0, n_routers - 1)
        while tgt == src:
            tgt = random.randint(0, n_routers - 1)
        adjacencies.append({
            "source": routers[src]["hostname"],
            "target": routers[tgt]["hostname"],
            "state": random.choice(["Full", "2-Way", "ExStart"]),
            "interface": f"Ethernet{random.randint(1,48)}",
            "cost": random.choice([1, 10, 100, 1000]),
        })

    return routers, adjacencies


def generate_fabric_topology(n_switches: int, n_links: int):
    """Data center fabric: switches as nodes, physical links as edges."""
    tiers = ["spine", "leaf", "superspine", "border-leaf"]
    switches = []
    for i in range(n_switches):
        tier = tiers[min(i % 4, 3)]
        switches.append({
            "hostname": f"{tier}-{i+1:03d}",
            "mgmt_ip": f"172.16.{i // 256}.{i % 256 + 1}",
            "model": random.choice(["DCS-7050CX3", "QFX5120", "N9K-C93180YC", "SR-1"]),
            "tier": tier,
            "pod": f"pod-{(i % 4) + 1}",
            "serial": f"SN{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=10))}",
            "uptime_days": random.randint(1, 365),
        })

    links = []
    for _ in range(n_links):
        src = random.randint(0, n_switches - 1)
        tgt = random.randint(0, n_switches - 1)
        while tgt == src:
            tgt = random.randint(0, n_switches - 1)
        links.append({
            "source": switches[src]["hostname"],
            "target": switches[tgt]["hostname"],
            "link_type": random.choice(["uplink", "downlink", "peer-link", "isl"]),
            "speed_gbps": random.choice([10, 25, 40, 100, 400]),
            "state": random.choice(["up", "down"]),
        })

    return switches, links


# ---------------------------------------------------------------------------
# Encoding functions
# ---------------------------------------------------------------------------

def encode_as_json(devices, sessions):
    """Encode as JSON (baseline)."""
    return json.dumps({"devices": devices, "sessions": sessions}, indent=2)


def encode_as_generic(devices, sessions):
    """Encode as GCF generic profile (current NetClaw integration)."""
    return encode_generic({"devices": devices, "sessions": sessions})


def encode_as_graph(devices, sessions, device_kind="svc", edge_type_key="session_type"):
    """Encode as GCF graph profile with local IDs and edge arrows."""
    symbols = []
    hostname_to_idx = {}

    for i, device in enumerate(devices):
        hostname = device.get("hostname", device.get("router_id", f"device-{i}"))
        hostname_to_idx[hostname] = i

        # Build qualified name from hostname + key attributes
        qname = hostname
        kind = device_kind
        score = 0.0
        provenance = "network"

        # Determine distance/grouping based on role if available
        role = device.get("role", device.get("tier", ""))
        if role in ("spine", "superspine", "dr", "route-reflector", "border"):
            distance = 0  # core/important
        elif role in ("leaf", "bdr", "pe", "abr"):
            distance = 1  # related
        else:
            distance = 2  # extended

        symbols.append(Symbol(
            qualified_name=qname,
            kind=kind,
            score=score,
            provenance=provenance,
            distance=distance,
        ))

    edges = []
    for session in sessions:
        src_hostname = session.get("source", "")
        tgt_hostname = session.get("target", "")

        src_idx = hostname_to_idx.get(src_hostname)
        tgt_idx = hostname_to_idx.get(tgt_hostname)
        if src_idx is None or tgt_idx is None:
            continue

        src_qname = symbols[src_idx].qualified_name
        tgt_qname = symbols[tgt_idx].qualified_name

        etype = session.get(edge_type_key, session.get("link_type", session.get("state", "connected")))

        edges.append(Edge(
            source=src_qname,
            target=tgt_qname,
            edge_type=etype,
        ))

    payload = Payload(
        tool="network_topology",
        symbols=symbols,
        edges=edges,
    )

    return encode(payload)


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

TOPOLOGIES = {
    "BGP Topology": {
        "generator": generate_bgp_topology,
        "edge_type_key": "session_type",
        "kind": "svc",
    },
    "OSPF Topology": {
        "generator": generate_ospf_topology,
        "edge_type_key": "state",
        "kind": "svc",
    },
    "DC Fabric": {
        "generator": generate_fabric_topology,
        "edge_type_key": "link_type",
        "kind": "svc",
    },
}

SIZES = [
    (10, 8),
    (20, 30),
    (50, 80),
    (100, 200),
    (200, 500),
]


def benchmark():
    random.seed(42)

    print("=" * 100)
    print("NetClaw Benchmark: GCF Graph Profile vs Generic Profile vs JSON")
    print("Token counts via cl100k_base")
    print("=" * 100)
    print()

    for topo_name, config in TOPOLOGIES.items():
        gen = config["generator"]
        edge_key = config["edge_type_key"]
        kind = config["kind"]

        print(f"--- {topo_name} ---")
        print(f"{'Nodes':>6} {'Edges':>6}  {'JSON':>8}  {'Generic':>8}  {'Graph':>8}  {'Gen%':>7}  {'Graph%':>7}  {'Graph vs Gen':>13}")
        print("-" * 100)

        for n_nodes, n_edges in SIZES:
            devices, sessions = gen(n_nodes, n_edges)

            json_str = encode_as_json(devices, sessions)
            generic_str = encode_as_generic(devices, sessions)
            graph_str = encode_as_graph(devices, sessions, device_kind=kind, edge_type_key=edge_key)

            json_tok = count_tokens(json_str)
            generic_tok = count_tokens(generic_str)
            graph_tok = count_tokens(graph_str)

            gen_pct = (1 - generic_tok / json_tok) * 100
            graph_pct = (1 - graph_tok / json_tok) * 100
            graph_vs_gen = (1 - graph_tok / generic_tok) * 100

            print(f"{n_nodes:>6} {n_edges:>6}  {json_tok:>8}  {generic_tok:>8}  {graph_tok:>8}  {gen_pct:>6.1f}%  {graph_pct:>6.1f}%  {graph_vs_gen:>+12.1f}%")

        print()

    print("=" * 100)
    print("'Gen%' = generic profile savings vs JSON")
    print("'Graph%' = graph profile savings vs JSON")
    print("'Graph vs Gen' = additional savings from graph profile over generic")
    print("=" * 100)


if __name__ == "__main__":
    benchmark()
