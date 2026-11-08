#!/usr/bin/env python3
"""Spec 182 multi-region GCP plan/apply/status/teardown (gcloud driven, no OpenTofu).

plan      read-only: prints what would be created (and which resources already exist).
apply     creates resources; refuses without --confirm-cost AND a recorded G1 approval file.
status    read-only: lists owned resources.
teardown  --list is read-only. Deleting needs --delete plus --confirm-list-sha256 of the printed list.

Ownership: label netclaw-spec=182 where gcloud supports labels (instances, disks; NOT addresses);
networks, subnets and firewall rules have no labels, so they carry the exact name prefix nc182-.
Never touches resources outside that set (old VM, equinix-*, pyats-mcp, gateway5, drawio-mcp).
Never use a pipe to read an exit code.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys

PROJECT = "netclaw-506315"
SPEC = "182"
PREFIX = "nc182-"
LABEL_KEY, LABEL_VALUE = "netclaw-spec", "182"
NETWORK = PREFIX + "r09"
REGIONS = {
    "nne1": {"region": "northamerica-northeast1", "zone": "northamerica-northeast1-b", "cidr": "10.182.1.0/24"},
    "ew1": {"region": "europe-west1", "zone": "europe-west1-b", "cidr": "10.182.2.0/24"},
    "ase1": {"region": "asia-southeast1", "zone": "asia-southeast1-a", "cidr": "10.182.3.0/24"},
}
MACHINE_TYPE = "e2-medium"
DISK_GB, DISK_TYPE = 40, "pd-balanced"
ETCD_PORTS = "2379-2380"
CLUSTER_PORT = 7443   # set at manifest time; cluster/NCFED
IN2N_PORT = 7444      # set at manifest time; member attach
IAP_RANGE = "35.235.240.0/20"
G1_FILE = os.path.join(os.path.dirname(__file__), "..", "specs", "182-multi-region-ha-borders", "g1-approval.md")


def labels(role):
    return f"{LABEL_KEY}={LABEL_VALUE},netclaw-role={role}"


def build_plan(cfg=None):
    """Pure function: ordered list of resource dicts, each with kind, name, region/zone and the create argv."""
    res = []
    g = ["gcloud", "--project", PROJECT]
    res.append({"kind": "network", "name": NETWORK, "labelable": False,
                "create": g + ["compute", "networks", "create", NETWORK, "--subnet-mode=custom"],
                "describe": g + ["compute", "networks", "describe", NETWORK, "--format=value(name)"]})
    for code, r in REGIONS.items():
        n = f"{PREFIX}sub-{code}"
        res.append({"kind": "subnet", "name": n, "region": r["region"], "labelable": False,
                    "create": g + ["compute", "networks", "subnets", "create", n, "--network", NETWORK,
                                   "--region", r["region"], "--range", r["cidr"]],
                    "describe": g + ["compute", "networks", "subnets", "describe", n, "--region", r["region"], "--format=value(name)"]})
    for code, r in REGIONS.items():
        n = f"{PREFIX}ip-{code}"
        res.append({"kind": "address", "name": n, "region": r["region"], "labelable": False,
                    "create": g + ["compute", "addresses", "create", n, "--region", r["region"]],
                    "describe": g + ["compute", "addresses", "describe", n, "--region", r["region"], "--format=value(address)"]})
    res.append({"kind": "firewall", "name": PREFIX + "allow-iap-ssh", "labelable": False,
                "source_ranges": [IAP_RANGE], "allow": ["tcp:22"],
                "create": g + ["compute", "firewall-rules", "create", PREFIX + "allow-iap-ssh", "--network", NETWORK,
                               "--direction=INGRESS", "--allow=tcp:22", "--source-ranges=" + IAP_RANGE, "--target-tags=nc182-border"],
                "describe": g + ["compute", "firewall-rules", "describe", PREFIX + "allow-iap-ssh", "--format=value(name)"]})
    res.append({"kind": "firewall", "name": PREFIX + "allow-public", "labelable": False,
                "source_ranges": ["0.0.0.0/0"], "allow": ["tcp:443", f"tcp:{IN2N_PORT}"],
                "create": g + ["compute", "firewall-rules", "create", PREFIX + "allow-public", "--network", NETWORK,
                               "--direction=INGRESS", f"--allow=tcp:443,tcp:{IN2N_PORT}", "--source-ranges=0.0.0.0/0", "--target-tags=nc182-border"],
                "describe": g + ["compute", "firewall-rules", "describe", PREFIX + "allow-public", "--format=value(name)"]})
    internal = ",".join(r["cidr"] for r in REGIONS.values())
    res.append({"kind": "firewall", "name": PREFIX + "allow-mesh", "labelable": False, "needs_border_ips": True,
                "source_ranges": ["<border static IPs /32 after reserve>", internal],
                "allow": [f"tcp:{ETCD_PORTS}", f"tcp:{CLUSTER_PORT}"],
                "create": g + ["compute", "firewall-rules", "create", PREFIX + "allow-mesh", "--network", NETWORK,
                               "--direction=INGRESS", f"--allow=tcp:{ETCD_PORTS},tcp:{CLUSTER_PORT}",
                               "--source-ranges={SOURCES}", "--target-tags=nc182-border"],
                "describe": g + ["compute", "firewall-rules", "describe", PREFIX + "allow-mesh", "--format=value(name)"]})
    for code, r in REGIONS.items():
        n = f"{PREFIX}border-{code}"
        res.append({"kind": "instance", "name": n, "region": r["region"], "zone": r["zone"], "labelable": True,
                    "labels": labels("border"), "machine_type": MACHINE_TYPE, "disk_gb": DISK_GB, "disk_type": DISK_TYPE,
                    "create": g + ["compute", "instances", "create", n, "--zone", r["zone"], "--machine-type", MACHINE_TYPE,
                                   "--subnet", f"{PREFIX}sub-{code}", "--address", f"{PREFIX}ip-{code}",
                                   "--image-family=debian-12", "--image-project=debian-cloud",
                                   f"--boot-disk-size={DISK_GB}GB", f"--boot-disk-type={DISK_TYPE}",
                                   "--labels=" + labels("border"), "--tags=nc182-border", "--metadata=enable-oslogin=TRUE"],
                    "describe": g + ["compute", "instances", "describe", n, "--zone", r["zone"], "--format=value(name)"]})
    return res


def run(argv):
    """Real runner. Injected out in tests. Returns (returncode, stdout)."""
    p = subprocess.run(argv, capture_output=True, text=True)
    return p.returncode, p.stdout


def exists(item, runner):
    rc, _ = runner(item["describe"])
    return rc == 0


def cmd_plan(runner, out=print):
    plan = build_plan()
    out(f"Spec 182 plan (read-only). Project {PROJECT}. Only describe calls are made.")
    for it in plan:
        state = "exists" if exists(it, runner) else "create"
        where = it.get("zone") or it.get("region") or "global"
        lab = " labelled " + it["labels"] if it.get("labelable") else " name-prefix nc182-"
        out(f"  [{state:6s}] {it['kind']:8s} {it['name']} ({where}){lab}")
    return 0


def border_ips(runner):
    ips = []
    for it in build_plan():
        if it["kind"] == "address":
            rc, so = runner(it["describe"])
            if rc != 0 or not so.strip():
                raise SystemExit(f"address {it['name']} not reserved yet")
            ips.append(so.strip())
    return ips


def g1_recorded(path=G1_FILE):
    try:
        with open(path) as f:
            t = f.read()
    except OSError:
        return False
    return "Approved by:" in t and "Gate: G1" in t


def cmd_apply(runner, confirm_cost, g1_path=G1_FILE, out=print):
    if not confirm_cost:
        out("REFUSED: apply needs --confirm-cost (billed resources).")
        return 2
    if not g1_recorded(g1_path):
        out(f"REFUSED: no recorded G1 approval at {os.path.normpath(g1_path)}.")
        return 2
    created = 0
    for it in build_plan():
        if exists(it, runner):
            out(f"  exists  {it['kind']} {it['name']}")
            continue
        argv = list(it["create"])
        if it.get("needs_border_ips"):
            sources = ",".join([f"{ip}/32" for ip in border_ips(runner)] + [r["cidr"] for r in REGIONS.values()])
            argv = [a.replace("{SOURCES}", sources) for a in argv]
        rc, _ = runner(argv)
        if rc != 0:
            out(f"  FAILED  {it['kind']} {it['name']} (rc={rc}); stopping, nothing is retried or deleted")
            return 1
        created += 1
        out(f"  created {it['kind']} {it['name']}")
    out(f"apply done: {created} created")
    return 0


def owned(runner):
    """Exact owned set: label-listing for labelable kinds, name prefix for the rest. Read-only."""
    g = ["gcloud", "--project", PROJECT, "compute"]
    found = []
    filt = f"labels.{LABEL_KEY}={LABEL_VALUE}"
    for kind, sub, fmt in (("instance", ["instances", "list"], "value(name,zone.basename())"),
                           ("address", ["addresses", "list"], "value(name,region.basename())")):
        rc, so = runner(g + sub + ["--filter", filt, "--format", fmt])
        for line in so.splitlines():
            if line.strip():
                found.append((kind, line.split()[0] if line.split() else line, " ".join(line.split()[1:])))
    for kind, sub, fmt in (("firewall", ["firewall-rules", "list"], "value(name)"),
                           ("subnet", ["networks", "subnets", "list"], "value(name,region.basename())"),
                           ("network", ["networks", "list"], "value(name)")):
        rc, so = runner(g + sub + ["--filter", f"name~^{PREFIX}", "--format", fmt])
        for line in so.splitlines():
            if line.strip():
                parts = line.split()
                found.append((kind, parts[0], " ".join(parts[1:])))
    return found


def list_digest(found):
    return hashlib.sha256(json.dumps(sorted(found)).encode()).hexdigest()


def cmd_status(runner, out=print):
    for k, n, w in owned(runner):
        out(f"  {k:8s} {n} {w}")
    return 0


def cmd_teardown(runner, list_only, delete, confirm, out=print):
    found = owned(runner)
    for k, n, w in found:
        out(f"  {k:8s} {n} {w}")
    digest = list_digest(found)
    out(f"list sha256: {digest}")
    if list_only or not delete:
        return 0
    if confirm != digest:
        out("REFUSED: --confirm-list-sha256 does not match the printed list.")
        return 2
    order = {"instance": 0, "address": 1, "firewall": 2, "subnet": 3, "network": 4}
    g = ["gcloud", "--project", PROJECT, "compute", "--quiet"]
    for k, n, w in sorted(found, key=lambda x: order[x[0]]):
        if not n.startswith(PREFIX):
            out(f"  SKIP (not owned) {n}")
            continue
        if k == "instance":
            argv = g + ["instances", "delete", n, "--zone", w]
        elif k == "address":
            argv = g + ["addresses", "delete", n, "--region", w]
        elif k == "firewall":
            argv = g + ["firewall-rules", "delete", n]
        elif k == "subnet":
            argv = g + ["networks", "subnets", "delete", n, "--region", w]
        else:
            argv = g + ["networks", "delete", n]
        rc, _ = runner(argv)
        out(f"  {'deleted' if rc == 0 else 'FAILED '} {k} {n}")
    return 0


def main(argv=None, runner=run):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    a = sub.add_parser("apply"); a.add_argument("--confirm-cost", action="store_true")
    sub.add_parser("status")
    t = sub.add_parser("teardown"); t.add_argument("--list", action="store_true", dest="list_only")
    t.add_argument("--delete", action="store_true"); t.add_argument("--confirm-list-sha256", default="")
    args = ap.parse_args(argv)
    if args.cmd == "plan":
        return cmd_plan(runner)
    if args.cmd == "apply":
        return cmd_apply(runner, args.confirm_cost)
    if args.cmd == "status":
        return cmd_status(runner)
    return cmd_teardown(runner, args.list_only, args.delete, args.confirm_list_sha256)


if __name__ == "__main__":
    sys.exit(main())
