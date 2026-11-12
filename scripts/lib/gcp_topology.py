"""Pure topology -> resource plan builder for NetClaw in GCP (spec 193). No I/O, no gcloud calls.

Nothing here has a default project: the caller supplies project, regions and deployment id.
"""
import hashlib
import json
import re

TOPOLOGIES = {
    "gcp-border": "One Border in GCP (focused Risk head).",
    "gcp-member": "One Member in GCP, to attach to any Border (GCP or on-prem).",
    "gcp-border-onprem-members": "GCP Border; attach on-prem Members (pyATS, CML, ...) to it.",
    "onprem-border-gcp-members": "GCP Members attached to an on-prem Border (two Members, one zone).",
    "ha-risk": "Highly available Risk: two Borders and an etcd witness in one region.",
    "distributed-risk": "Distributed Risk: one Border in each of three regions, meshed.",
}
ID_RE = re.compile(r"^[0-9a-f]{6}$")
PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
REGION_RE = re.compile(r"^[a-z]+-[a-z]+[0-9]+$")
IAP_RANGE = "35.235.240.0/20"
IMAGE = ["--image-family=ubuntu-2404-lts-amd64", "--image-project=ubuntu-os-cloud"]
# Order-of-magnitude public list-price ESTIMATES (USD per month, 730 h). Not a billing quote.
PRICE = {"e2-standard-2": 49.0, "e2-medium": 25.0, "e2-small": 12.0, "disk40": 4.0, "disk20": 2.0, "ip": 3.0, "nat": 1.5}
MACHINE = {"border": ("e2-standard-2", 40), "member": ("e2-medium", 30), "witness": ("e2-small", 20)}
ZONE_SUFFIX = ["b", "c", "a"]
BORDER_PORTS = ["tcp:7444"]
MESH_PORTS = "tcp:2379-2380,tcp:12379,tcp:7443"


class PlanError(ValueError):
    pass


def new_id(seed):
    return hashlib.sha256(str(seed).encode()).hexdigest()[:6]


def validate(topology, project, regions, dep_id, https_cidr):
    if topology not in TOPOLOGIES:
        raise PlanError(f"unknown topology '{topology}' (valid: {', '.join(TOPOLOGIES)})")
    if not PROJECT_RE.match(project or ""):
        raise PlanError("a valid GCP project id is required (no default is ever assumed)")
    if not ID_RE.match(dep_id or ""):
        raise PlanError("deployment id must be 6 lowercase hex characters")
    for r in regions:
        if not REGION_RE.match(r):
            raise PlanError(f"invalid region '{r}'")
    if topology == "distributed-risk":
        if len(regions) != 3 or len(set(regions)) != 3:
            raise PlanError("distributed-risk needs exactly 3 distinct regions")
    elif len(regions) < 1:
        raise PlanError(f"{topology} needs a region")
    if not re.match(r"^\d{1,3}(\.\d{1,3}){3}/\d{1,2}$", https_cidr or ""):
        raise PlanError("--https-cidr must be an IPv4 CIDR (the source range allowed to reach port 443)")
    if https_cidr == "0.0.0.0/0":
        raise PlanError("--https-cidr 0.0.0.0/0 is refused: this deployment has no authentication; restrict the source range")


def nodes_for(topology, regions):
    """Return [(role, region, zone_suffix)]"""
    r0 = regions[0]
    if topology in ("gcp-border", "gcp-border-onprem-members"):
        return [("border", r0, "b")]
    if topology == "gcp-member":
        return [("member", r0, "b")]
    if topology == "onprem-border-gcp-members":
        return [("member", r0, "b"), ("member", r0, "c")]
    if topology == "ha-risk":
        return [("border", r0, "b"), ("border", r0, "c"), ("witness", r0, "b")]
    return [("border", r, ZONE_SUFFIX[i]) for i, r in enumerate(regions)]


def build_plan(topology, project, regions, dep_id, https_cidr, gcloud="gcloud"):
    """Pure: returns dict {prefix,label,resources:[...],est_monthly_usd,advisories:[...]}. Every name starts with the prefix."""
    validate(topology, project, regions, dep_id, https_cidr)
    prefix = f"nc-{dep_id}-"
    label = f"netclaw-deployment={dep_id}"
    g = [gcloud, "--project", project, "--quiet"]
    net = prefix + "net"
    sa = prefix + "sa"
    sa_email = f"{sa}@{project}.iam.gserviceaccount.com"
    nodes = nodes_for(topology, regions)
    used_regions = []
    for _, r, _z in nodes:
        if r not in used_regions:
            used_regions.append(r)
    res = []
    block = int(dep_id, 16) % 100 + 100  # 10.<100-199>.<n>.0/24
    cidrs = {r: f"10.{block}.{i}.0/24" for i, r in enumerate(used_regions)}
    res.append(dict(kind="network", name=net, where="global", detail="custom-mode VPC",
                    create=g[:-1] + ["compute", "networks", "create", net, "--subnet-mode=custom", "--quiet"]))
    for r in used_regions:
        n = f"{prefix}sub-{r}"
        res.append(dict(kind="subnet", name=n, where=r, detail=f"{cidrs[r]}, Private Google Access",
                        create=g[:-1] + ["compute", "networks", "subnets", "create", n, "--network", net, "--region", r,
                                         "--range", cidrs[r], "--enable-private-ip-google-access", "--quiet"]))
    res.append(dict(kind="serviceaccount", name=sa, where="global",
                    detail="dedicated least-privilege identity for the nodes (no keys created)",
                    create=g[:-1] + ["iam", "service-accounts", "create", sa, "--display-name", f"NetClaw {dep_id}", "--quiet"]))
    for role in ("roles/logging.logWriter", "roles/monitoring.metricWriter"):
        res.append(dict(kind="iam-binding", name=f"{prefix}sa:{role}", where="project", detail=f"{role} for {sa}",
                        create=g[:-1] + ["projects", "add-iam-policy-binding", project, f"--member=serviceAccount:{sa_email}",
                                         f"--role={role}", "--condition=None", "--quiet"]))
    has_border = any(x[0] == "border" for x in nodes)
    res.append(dict(kind="firewall", name=prefix + "allow-iap-ssh", where="global", detail=f"tcp:22 from {IAP_RANGE} (IAP only)",
                    create=g[:-1] + ["compute", "firewall-rules", "create", prefix + "allow-iap-ssh", "--network", net,
                                     "--direction=INGRESS", "--allow=tcp:22", f"--source-ranges={IAP_RANGE}",
                                     f"--target-tags={prefix}node", "--enable-logging", "--quiet"]))
    if has_border:
        res.append(dict(kind="firewall", name=prefix + "allow-https", where="global",
                        detail=f"tcp:443 from {https_cidr} only (HUD; NO authentication)",
                        create=g[:-1] + ["compute", "firewall-rules", "create", prefix + "allow-https", "--network", net,
                                         "--direction=INGRESS", "--allow=tcp:443", f"--source-ranges={https_cidr}",
                                         f"--target-tags={prefix}border", "--enable-logging", "--quiet"]))
        res.append(dict(kind="firewall", name=prefix + "allow-in2n", where="global",
                        detail="tcp:7444 from 0.0.0.0/0 (mutual-TLS, pinned keys; peers are anywhere)",
                        create=g[:-1] + ["compute", "firewall-rules", "create", prefix + "allow-in2n", "--network", net,
                                         "--direction=INGRESS", "--allow=" + ",".join(BORDER_PORTS), "--source-ranges=0.0.0.0/0",
                                         f"--target-tags={prefix}border", "--enable-logging", "--quiet"]))
    if topology in ("ha-risk", "distributed-risk"):
        res.append(dict(kind="firewall", name=prefix + "allow-mesh", where="global",
                        detail=f"{MESH_PORTS} from {','.join(cidrs.values())} (cluster plane stays internal)",
                        create=g[:-1] + ["compute", "firewall-rules", "create", prefix + "allow-mesh", "--network", net,
                                         "--direction=INGRESS", "--allow=" + MESH_PORTS,
                                         "--source-ranges=" + ",".join(cidrs.values()), f"--target-tags={prefix}node", "--quiet"]))
    counters = {}
    monthly = 0.0
    for role, r, zs in nodes:
        counters[role] = counters.get(role, 0) + 1
        idx = f"{r.split('-')[0][:2]}{r.split('-')[1][:1]}{counters[role]}"
        name = f"{prefix}{role}-{idx}"
        mt, disk = MACHINE[role]
        zone = f"{r}-{zs}"
        monthly += PRICE[mt] + (PRICE["disk40"] if disk >= 30 else PRICE["disk20"])
        argv = g[:-1] + ["compute", "instances", "create", name, "--zone", zone, "--machine-type", mt,
                         "--subnet", f"{prefix}sub-{r}"] + IMAGE + [
                         f"--boot-disk-size={disk}GB", "--boot-disk-type=pd-balanced",
                         f"--labels={label},netclaw-role={role}",
                         f"--tags={prefix}node" + (f",{prefix}border" if role == "border" else ""),
                         "--metadata=enable-oslogin=TRUE", f"--service-account={sa_email}", "--scopes=cloud-platform",
                         "--shielded-secure-boot", "--shielded-vtpm", "--shielded-integrity-monitoring", "--quiet"]
        if role == "witness":
            argv.insert(argv.index("--quiet"), "--no-address")
        elif role == "border":
            addr = f"{prefix}ip-{role}-{idx}"
            res.append(dict(kind="address", name=addr, where=r, detail="static external IPv4",
                            create=g[:-1] + ["compute", "addresses", "create", addr, "--region", r, "--quiet"]))
            monthly += PRICE["ip"]
            argv.insert(argv.index("--quiet"), f"--address={addr}")
        res.append(dict(kind="instance", name=name, where=zone, role=role,
                        detail=f"{mt} ubuntu-2404 {disk}GB shielded VM, OS Login ({role})", create=argv))
        if role == "witness":
            rt, nat = f"{prefix}rtr-{r}", f"{prefix}nat-{r}"
            res.append(dict(kind="router", name=rt, where=r, detail="for witness egress (no external IP)",
                            create=g[:-1] + ["compute", "routers", "create", rt, "--network", net, "--region", r, "--quiet"]))
            res.append(dict(kind="nat", name=nat, where=r, detail="Cloud NAT for witness egress only",
                            create=g[:-1] + ["compute", "routers", "nats", "create", nat, "--router", rt, "--region", r,
                                             "--auto-allocate-nat-external-ips", "--nat-all-subnet-ip-ranges", "--quiet"]))
            monthly += PRICE["nat"]
    advisories = [
        "Budget alert is NOT created automatically; set one in the GCP console (Billing > Budgets) before leaving this running.",
        "Teardown stops all charges: scripts/netclaw-gcp.py teardown --deployment " + dep_id,
        "Endpoints have NO authentication. Keep URLs private until the users/SSO/RBAC phase (R15-R17).",
    ]
    if topology == "distributed-risk":
        advisories.append("Multi-region exposure still needs the owner-approved published client builds (R09 gate).")
    if topology in ("gcp-border-onprem-members", "onprem-border-gcp-members"):
        advisories.append("Attach the on-prem side with the Claw Plan Member flow (docs/N2N-FEDERATION-GUIDE.md).")
    plan = dict(deployment=dep_id, topology=topology, project=project, regions=used_regions, prefix=prefix, label=label,
                resources=res, est_monthly_usd=round(monthly, 2), est_hourly_usd=round(monthly / 730, 3), advisories=advisories)
    plan["plan_sha256"] = plan_digest(plan)
    return plan


def plan_digest(plan):
    core = [(r["kind"], r["name"], r["where"], " ".join(r["create"])) for r in plan["resources"]]
    return hashlib.sha256(json.dumps(core).encode()).hexdigest()
