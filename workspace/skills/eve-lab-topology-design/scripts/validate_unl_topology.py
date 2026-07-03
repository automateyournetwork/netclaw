#!/usr/bin/env python3
"""
EVE-NG UNL Topology Validator

Parses a .unl lab file and validates:
  - Connectivity: orphan nodes, dangling interfaces, isolated networks
  - Role adjacency: hierarchy rules based on node name prefixes
  - Resilience: SPOF detection, asymmetric redundancy, dual-homing gaps
  - Design requirements: optional comparison against expected links (JSON)

Usage:
  python3 validate_unl_topology.py <lab.unl> [--reqs design_reqs.json] [--roles roles.json] [--verbose]

Design requirements JSON format:
  {
    "required_links": [
      {"from": "R1", "to": "R2", "type": "p2p"},
      {"from": "SW1", "to": "SW2", "type": "p2p"}
    ],
    "redundancy_groups": [
      {"nodes": ["DIST1", "DIST2"], "role": "distribution", "min_uplinks": 2},
      {"nodes": ["SPINE1", "SPINE2"], "role": "spine", "min_uplinks": 2}
    ],
    "forbidden_links": [
      {"from": "HOST1", "to": "CORE1"}
    ]
  }

Roles JSON format (override name-based heuristics):
  {
    "R1": "core",
    "R2": "core",
    "PE1": "pe",
    "SW1": "distribution",
    "SW3": "access",
    "HOST1": "host"
  }
"""

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Role inference from node names (heuristic, overrideable via --roles)
# ---------------------------------------------------------------------------

ROLE_PATTERNS = [
    (["spine", "sp-"],         "spine"),
    (["leaf", "lf-"],          "leaf"),
    (["border", "bl-"],        "border-leaf"),
    (["core", "cr-", "p-"],    "core"),
    (["pe-", "pe_"],           "pe"),
    (["rr-", "rr_"],           "rr"),
    (["dist", "distribution", "dr-", "agg"], "distribution"),
    (["access", "acc-", "sw-", "sw_"], "access"),
    (["fw", "firewall", "asa", "ftd", "palo"], "firewall"),
    (["wan", "edge", "ce-", "ce_"], "wan-edge"),
    (["host", "pc", "server", "srv", "endpoint"], "host"),
    (["mgmt", "oob"],          "mgmt"),
    (["internet", "cloud", "isp"], "internet"),
]

ROLE_HIERARCHY = {
    "internet":    0,
    "wan-edge":    1,
    "firewall":    1,
    "core":        2,
    "pe":          2,
    "rr":          2,
    "spine":       2,
    "distribution": 3,
    "leaf":        3,
    "border-leaf": 3,
    "access":      4,
    "host":        5,
    "mgmt":        5,
    "unknown":     3,
}

FORBIDDEN_ADJACENCY = [
    ("host", "core"),
    ("host", "spine"),
    ("host", "pe"),
    ("host", "wan-edge"),
    ("access", "core"),
    ("access", "internet"),
]


def infer_role(name: str, role_map: dict) -> str:
    if name in role_map:
        return role_map[name]
    lname = name.lower()
    for prefixes, role in ROLE_PATTERNS:
        for p in prefixes:
            if lname.startswith(p) or p in lname:
                return role
    return "unknown"


# ---------------------------------------------------------------------------
# UNL parser
# ---------------------------------------------------------------------------

def parse_unl(lab_path: Path):
    tree = ET.parse(lab_path)
    root = tree.getroot()
    lab_name = root.attrib.get("name", lab_path.stem)

    nodes = {}      # node_id -> {name, type, template, image, interfaces: [{id, name, network_id}]}
    networks = {}   # network_id -> {name, type}

    for node_el in root.findall(".//node"):
        nid = node_el.attrib.get("id")
        if not nid:
            continue
        ifaces = []
        for iface_el in node_el.findall("interface"):
            ifaces.append({
                "id":         iface_el.attrib.get("id"),
                "name":       iface_el.attrib.get("name", f"iface{iface_el.attrib.get('id')}"),
                "network_id": iface_el.attrib.get("network_id"),
            })
        nodes[nid] = {
            "id":        nid,
            "name":      node_el.attrib.get("name", f"node{nid}"),
            "type":      node_el.attrib.get("type", ""),
            "template":  node_el.attrib.get("template", ""),
            "image":     node_el.attrib.get("image", ""),
            "interfaces": ifaces,
        }

    for net_el in root.findall(".//network"):
        nid = net_el.attrib.get("id")
        if not nid:
            continue
        networks[nid] = {
            "id":   nid,
            "name": net_el.attrib.get("name", f"net{nid}"),
            "type": net_el.attrib.get("type", "bridge"),
        }

    return lab_name, nodes, networks


# ---------------------------------------------------------------------------
# Connectivity analysis
# ---------------------------------------------------------------------------

def build_connectivity(nodes: dict, networks: dict):
    """
    Returns:
      net_members: network_id -> list of (node_id, iface_name)
      node_nets:   node_id -> set of network_ids the node is connected to
      adjacency:   node_id -> set of neighbor node_ids
    """
    net_members = defaultdict(list)
    node_nets = defaultdict(set)
    dangling_ifaces = []          # (node_name, iface_name, network_id) where network_id unknown
    declared_net_ids = set(networks.keys())

    for nid, node in nodes.items():
        for iface in node["interfaces"]:
            netid = iface.get("network_id")
            if netid:
                node_nets[nid].add(netid)
                net_members[netid].append((nid, iface["name"]))
                if netid not in declared_net_ids:
                    dangling_ifaces.append((node["name"], iface["name"], netid))

    adjacency = defaultdict(set)
    for netid, members in net_members.items():
        for i, (nid_a, _) in enumerate(members):
            for nid_b, _ in members[i+1:]:
                adjacency[nid_a].add(nid_b)
                adjacency[nid_b].add(nid_a)

    return net_members, node_nets, adjacency, dangling_ifaces


# ---------------------------------------------------------------------------
# Graph utilities
# ---------------------------------------------------------------------------

def find_connected_components(node_ids: set, adjacency: dict) -> list:
    visited = set()
    components = []
    for start in node_ids:
        if start in visited:
            continue
        comp = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            comp.add(n)
            for nb in adjacency.get(n, set()):
                if nb in node_ids and nb not in visited:
                    stack.append(nb)
        components.append(comp)
    return components


def find_articulation_points(node_ids: set, adjacency: dict) -> set:
    """Tarjan's algorithm for articulation points (SPOF nodes)."""
    ids = list(node_ids)
    idx_map = {n: i for i, n in enumerate(ids)}
    n = len(ids)
    disc = [-1] * n
    low  = [-1] * n
    parent = [-1] * n
    ap = set()
    timer = [0]

    def dfs(u):
        children = 0
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        for nb in adjacency.get(ids[u], set()):
            if nb not in idx_map:
                continue
            v = idx_map[nb]
            if disc[v] == -1:
                children += 1
                parent[v] = u
                dfs(v)
                low[u] = min(low[u], low[v])
                if parent[u] == -1 and children > 1:
                    ap.add(ids[u])
                if parent[u] != -1 and low[v] >= disc[u]:
                    ap.add(ids[u])
            elif v != parent[u]:
                low[u] = min(low[u], disc[v])

    for i in range(n):
        if disc[i] == -1:
            dfs(i)

    return ap


def find_bridge_links(node_ids: set, adjacency: dict) -> list:
    """Find bridge edges (links whose removal disconnects the graph)."""
    ids = list(node_ids)
    idx_map = {n: i for i, n in enumerate(ids)}
    n = len(ids)
    disc = [-1] * n
    low  = [-1] * n
    parent = [-1] * n
    bridges = []
    timer = [0]

    def dfs(u):
        disc[u] = low[u] = timer[0]
        timer[0] += 1
        for nb in adjacency.get(ids[u], set()):
            if nb not in idx_map:
                continue
            v = idx_map[nb]
            if disc[v] == -1:
                parent[v] = u
                dfs(v)
                low[u] = min(low[u], low[v])
                if low[v] > disc[u]:
                    bridges.append((ids[u], ids[v]))
            elif v != parent[u]:
                low[u] = min(low[u], disc[v])

    for i in range(n):
        if disc[i] == -1:
            dfs(i)

    return bridges


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

class ValidationResult:
    def __init__(self):
        self.passed = []
        self.warnings = []
        self.failures = []

    def ok(self, msg):   self.passed.append(msg)
    def warn(self, msg): self.warnings.append(msg)
    def fail(self, msg): self.failures.append(msg)

    @property
    def score(self):
        total = len(self.passed) + len(self.warnings) + len(self.failures)
        if total == 0:
            return 100
        return int(100 * len(self.passed) / total)


def check_orphan_nodes(nodes, node_nets, result):
    orphans = [n["name"] for nid, n in nodes.items() if not node_nets.get(nid)]
    if orphans:
        result.fail(f"Orphan nodes (no connected interfaces): {', '.join(sorted(orphans))}")
    else:
        result.ok("No orphan nodes")


def check_dangling_interfaces(dangling_ifaces, result):
    if dangling_ifaces:
        for node_name, iface_name, netid in dangling_ifaces:
            result.fail(f"Dangling interface: {node_name}/{iface_name} references missing network_id={netid}")
    else:
        result.ok("No dangling interface references")


def check_isolated_networks(net_members, networks, result):
    for netid, members in net_members.items():
        net_name = networks.get(netid, {}).get("name", f"net{netid}")
        if len(members) < 2:
            result.warn(f"Isolated network '{net_name}' (id={netid}) has only {len(members)} endpoint(s) — possible dangling link")
        elif len(members) > 2:
            net_type = networks.get(netid, {}).get("type", "bridge")
            if net_type not in ("bridge", "ovs"):
                result.warn(f"Network '{net_name}' (id={netid}) has {len(members)} endpoints — verify this is intentional shared segment")


def check_connectivity(node_ids, adjacency, result):
    components = find_connected_components(node_ids, adjacency)
    if len(components) > 1:
        comp_names_list = []
        for comp in components:
            comp_names_list.append("{" + ", ".join(sorted(comp)[:5]) + ("..." if len(comp) > 5 else "") + "}")
        result.fail(f"Topology is partitioned into {len(components)} disconnected components: {', '.join(comp_names_list)}")
    else:
        result.ok(f"All {len(node_ids)} nodes are in one connected component")


def check_role_adjacency(nodes, adjacency, role_map, result):
    id_to_name = {nid: n["name"] for nid, n in nodes.items()}
    name_to_id = {n["name"]: nid for nid, n in nodes.items()}
    violations = []
    for nid, node in nodes.items():
        role_a = infer_role(node["name"], role_map)
        for nb_id in adjacency.get(nid, set()):
            nb_name = id_to_name.get(nb_id, nb_id)
            role_b = infer_role(nb_name, role_map)
            for fa, fb in FORBIDDEN_ADJACENCY:
                if (role_a == fa and role_b == fb) or (role_a == fb and role_b == fa):
                    pair = tuple(sorted([node["name"], nb_name]))
                    if pair not in violations:
                        violations.append(pair)
                        result.fail(f"Forbidden adjacency: {node['name']} ({role_a}) <-> {nb_name} ({role_b})")
    if not violations:
        result.ok("Role-based adjacency rules respected")


def check_spof(node_ids, adjacency, nodes, result):
    id_to_name = {nid: n["name"] for nid, n in nodes.items()}
    aps = find_articulation_points(node_ids, adjacency)
    bridges = find_bridge_links(node_ids, adjacency)

    if aps:
        ap_names = sorted(id_to_name.get(n, n) for n in aps)
        result.warn(f"SPOF nodes (articulation points — removal splits topology): {', '.join(ap_names)}")
    else:
        result.ok("No single-node SPOFs detected")

    if bridges:
        bridge_names = sorted(
            f"{id_to_name.get(a, a)} <-> {id_to_name.get(b, b)}"
            for a, b in bridges
        )
        result.warn(f"SPOF links (bridge links — loss splits topology): {'; '.join(bridge_names)}")
    else:
        result.ok("No single-link SPOFs detected")


def check_symmetry(nodes, adjacency, role_map, result):
    """Check that nodes sharing the same role have the same number of uplinks."""
    role_to_nodes = defaultdict(list)
    for nid, node in nodes.items():
        role = infer_role(node["name"], role_map)
        role_to_nodes[role].append(nid)

    id_to_name = {nid: n["name"] for nid, n in nodes.items()}

    for role, nids in role_to_nodes.items():
        if len(nids) < 2:
            continue
        degree_map = {nid: len(adjacency.get(nid, set())) for nid in nids}
        degrees = list(degree_map.values())
        if len(set(degrees)) > 1:
            detail = ", ".join(
                f"{id_to_name.get(nid, nid)}={d}" for nid, d in sorted(degree_map.items(), key=lambda x: id_to_name.get(x[0], x[0]))
            )
            result.warn(f"Asymmetric link count in role '{role}': {detail}")
        else:
            result.ok(f"Role '{role}' ({len(nids)} nodes) has symmetric link count: {degrees[0]} each")


def check_design_requirements(nodes, adjacency, net_members, networks, reqs, role_map, result):
    if not reqs:
        return

    name_to_id = {n["name"]: nid for nid, n in nodes.items()}
    id_to_name = {nid: n["name"] for nid, n in nodes.items()}

    # Required links
    for req in reqs.get("required_links", []):
        a, b = req["from"], req["to"]
        aid = name_to_id.get(a)
        bid = name_to_id.get(b)
        if not aid:
            result.fail(f"Required link: node '{a}' not found in lab")
            continue
        if not bid:
            result.fail(f"Required link: node '{b}' not found in lab")
            continue
        if bid in adjacency.get(aid, set()):
            result.ok(f"Required link present: {a} <-> {b}")
        else:
            result.fail(f"Required link MISSING: {a} <-> {b}")

    # Forbidden links
    for req in reqs.get("forbidden_links", []):
        a, b = req["from"], req["to"]
        aid = name_to_id.get(a)
        bid = name_to_id.get(b)
        if not aid or not bid:
            continue
        if bid in adjacency.get(aid, set()):
            result.fail(f"Forbidden link EXISTS: {a} <-> {b}")
        else:
            result.ok(f"Forbidden link absent: {a} <-> {b}")

    # Redundancy groups
    for grp in reqs.get("redundancy_groups", []):
        role = grp.get("role", "group")
        min_uplinks = grp.get("min_uplinks", 2)
        for node_name in grp.get("nodes", []):
            nid = name_to_id.get(node_name)
            if not nid:
                result.warn(f"Redundancy group '{role}': node '{node_name}' not found")
                continue
            count = len(adjacency.get(nid, set()))
            if count < min_uplinks:
                result.fail(f"Redundancy group '{role}': {node_name} has {count} links, requires >= {min_uplinks}")
            else:
                result.ok(f"Redundancy group '{role}': {node_name} has {count} links (>= {min_uplinks} required)")


# ---------------------------------------------------------------------------
# Connectivity matrix printer
# ---------------------------------------------------------------------------

def print_connectivity_matrix(nodes, adjacency, role_map):
    id_to_name = {nid: n["name"] for nid, n in nodes.items()}
    sorted_nodes = sorted(nodes.values(), key=lambda n: (ROLE_HIERARCHY.get(infer_role(n["name"], role_map), 99), n["name"]))

    print("\n=== CONNECTIVITY MATRIX ===")
    print(f"  {'NODE':<20} {'ROLE':<16} {'DEGREE':>6}  NEIGHBORS")
    print(f"  {'-'*20} {'-'*16} {'-'*6}  {'-'*40}")
    for node in sorted_nodes:
        nid = node["id"]
        role = infer_role(node["name"], role_map)
        neighbors = sorted(id_to_name.get(nb, nb) for nb in adjacency.get(nid, set()))
        print(f"  {node['name']:<20} {role:<16} {len(neighbors):>6}  {', '.join(neighbors)}")


def print_network_table(nodes, networks, net_members):
    id_to_name = {nid: n["name"] for nid, n in nodes.items()}
    print("\n=== NETWORK MEMBERSHIP TABLE ===")
    print(f"  {'NETWORK':<28} {'TYPE':<10} {'ENDPOINTS'}")
    print(f"  {'-'*28} {'-'*10} {'-'*40}")
    for netid in sorted(networks.keys(), key=lambda x: int(x) if x.isdigit() else x):
        net = networks[netid]
        members = net_members.get(netid, [])
        endpoint_strs = [f"{id_to_name.get(nid, nid)}/{iname}" for nid, iname in members]
        print(f"  {net['name']:<28} {net['type']:<10} {', '.join(endpoint_strs) or '(none)'}")


# ---------------------------------------------------------------------------
# Resilience score
# ---------------------------------------------------------------------------

def resilience_level(result, bridges, aps):
    failures = len(result.failures)
    warnings = len(result.warnings)
    spof_count = len(bridges) + len(aps)

    if failures > 0:
        return "CRITICAL", "One or more validation failures"
    if spof_count > 4 or warnings > 5:
        return "LOW",      "Multiple SPOFs or warnings present"
    if spof_count > 1 or warnings > 2:
        return "MEDIUM",   "Some SPOFs or asymmetries present"
    if spof_count == 1 or warnings > 0:
        return "HIGH",     "Minor resilience gaps"
    return "FULL",         "No SPOFs or validation issues detected"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Validate an EVE-NG .unl topology file")
    ap.add_argument("lab", help="Path to the .unl lab file")
    ap.add_argument("--reqs",    help="JSON file with design requirements", default=None)
    ap.add_argument("--roles",   help="JSON file mapping node name to role", default=None)
    ap.add_argument("--verbose", action="store_true", help="Show full connectivity matrix and network table")
    ap.add_argument("--json",    action="store_true", help="Output results as JSON")
    args = ap.parse_args()

    lab_path = Path(args.lab)
    if not lab_path.exists():
        print(f"ERROR: file not found: {lab_path}", file=sys.stderr)
        sys.exit(1)

    role_map = {}
    if args.roles:
        with open(args.roles) as f:
            role_map = json.load(f)

    reqs = None
    if args.reqs:
        with open(args.reqs) as f:
            reqs = json.load(f)

    lab_name, nodes, networks = parse_unl(lab_path)
    net_members, node_nets, adjacency, dangling_ifaces = build_connectivity(nodes, networks)

    node_ids = set(nodes.keys())
    aps      = find_articulation_points(node_ids, adjacency)
    bridges  = find_bridge_links(node_ids, adjacency)

    result = ValidationResult()

    check_orphan_nodes(nodes, node_nets, result)
    check_dangling_interfaces(dangling_ifaces, result)
    check_isolated_networks(net_members, networks, result)
    check_connectivity(node_ids, adjacency, result)
    check_role_adjacency(nodes, adjacency, role_map, result)
    check_spof(node_ids, adjacency, nodes, result)
    check_symmetry(nodes, adjacency, role_map, result)
    check_design_requirements(nodes, adjacency, net_members, networks, reqs, role_map, result)

    level, reason = resilience_level(result, bridges, aps)

    if args.json:
        out = {
            "lab":       lab_name,
            "nodes":     len(nodes),
            "networks":  len(networks),
            "resilience": {"level": level, "reason": reason},
            "score":     result.score,
            "passed":    result.passed,
            "warnings":  result.warnings,
            "failures":  result.failures,
        }
        print(json.dumps(out, indent=2))
        sys.exit(0 if not result.failures else 1)

    print(f"\n{'='*60}")
    print(f" EVE-NG UNL Topology Validator")
    print(f"{'='*60}")
    print(f" Lab      : {lab_name}")
    print(f" File     : {lab_path}")
    print(f" Nodes    : {len(nodes)}")
    print(f" Networks : {len(networks)}")
    print(f"{'='*60}")

    if args.verbose:
        print_connectivity_matrix(nodes, adjacency, role_map)
        print_network_table(nodes, networks, net_members)

    print(f"\n=== VALIDATION RESULTS ===")
    for msg in result.passed:
        print(f"  [PASS] {msg}")
    for msg in result.warnings:
        print(f"  [WARN] {msg}")
    for msg in result.failures:
        print(f"  [FAIL] {msg}")

    print(f"\n=== RESILIENCE ASSESSMENT ===")
    print(f"  Level : {level}")
    print(f"  Reason: {reason}")
    print(f"  Score : {result.score}/100  ({len(result.passed)} passed, {len(result.warnings)} warnings, {len(result.failures)} failures)")

    print(f"\n{'='*60}")
    if result.failures:
        print(f" RESULT: FAILED — {len(result.failures)} critical issue(s) must be resolved")
        sys.exit(1)
    elif result.warnings:
        print(f" RESULT: PASSED WITH WARNINGS — review {len(result.warnings)} item(s)")
        sys.exit(0)
    else:
        print(f" RESULT: PASSED — topology is valid and resilient")
        sys.exit(0)


if __name__ == "__main__":
    main()
