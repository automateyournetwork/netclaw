#!/usr/bin/env python3
"""NetClaw in GCP (spec 193 / R09C): plan, apply, status, ssh, bootstrap, teardown. gcloud driven, stdlib only.

NOT BEHIND ANY AUTHENTICATION: see scripts/lib/gcp_warning.txt (shown by `plan`, required before anything is planned).
No default project. Nothing is created without `apply --confirm-cost --plan-sha256 <sha>`. Teardown removes only resources
carrying this deployment's prefix/label and needs the list hash. Secrets are never accepted on argv or printed.
`GCLOUD` overrides the gcloud binary; NETCLAW_GCP_HOME overrides the state directory (tests).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
import gcp_topology as T  # noqa: E402

WARNING_FILE = HERE / "lib" / "gcp_warning.txt"
SECRET_RE = re.compile(r"(AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY)")
REQUIRED_SERVICES = ["compute.googleapis.com", "iam.googleapis.com", "iap.googleapis.com"]
KIND_ORDER = ["network", "subnet", "serviceaccount", "iam-binding", "firewall", "address", "router", "nat", "instance"]


def warning_text():
    return WARNING_FILE.read_text()


def state_dir():
    d = Path(os.environ.get("NETCLAW_GCP_HOME") or Path.home() / ".openclaw" / "gcp")
    d.mkdir(parents=True, exist_ok=True, mode=0o700)
    return d


def save_state(dep, data):
    p = state_dir() / f"{dep}.json"
    tmp = p.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)


def load_state(dep):
    p = state_dir() / f"{dep}.json"
    if not p.exists():
        raise SystemExit(f"no such deployment '{dep}' (no state file)")
    return json.loads(p.read_text())


def gcloud_bin():
    return os.environ.get("GCLOUD", "gcloud")


def run(argv):
    """Real runner (injected out in tests). Returns (returncode, stdout, stderr)."""
    try:
        p = subprocess.run(argv, capture_output=True, text=True)
    except FileNotFoundError:
        return 127, "", "gcloud not found"
    return p.returncode, p.stdout, p.stderr


def prerequisites(project, runner):
    """Return list of unmet-prerequisite messages (empty = ok). Read-only."""
    g = gcloud_bin()
    missing = []
    rc, out, _ = runner([g, "auth", "list", "--filter=status:ACTIVE", "--format=value(account)"])
    if rc == 127:
        return ["gcloud CLI not installed (https://cloud.google.com/sdk/docs/install)"]
    if rc != 0 or not out.strip():
        missing.append("no active gcloud login: run `gcloud auth login`")
    rc, _, _ = runner([g, "projects", "describe", project, "--format=value(projectId)"])
    if rc != 0:
        missing.append(f"project '{project}' not found or no access (check the id and your permissions)")
        return missing
    rc, out, _ = runner([g, "services", "list", "--enabled", "--project", project, "--format=value(config.name)"])
    enabled = set(out.split()) if rc == 0 else set()
    for s in REQUIRED_SERVICES:
        if s not in enabled:
            missing.append(f"service {s} is not enabled: `gcloud services enable {s} --project {project}`")
    return missing


def print_plan(plan, out=print):
    out(f"NetClaw in GCP plan: deployment {plan['deployment']}, topology {plan['topology']}, project {plan['project']}")
    out(f"Regions: {', '.join(plan['regions'])}   Ownership: prefix {plan['prefix']} + label {plan['label']}")
    out(f"{'KIND':14s} {'NAME':34s} {'WHERE':26s} DETAIL")
    for r in plan["resources"]:
        out(f"{r['kind']:14s} {r['name']:34s} {r['where']:26s} {r['detail']}")
    out(f"Estimated running cost (public list prices, NOT a billing quote): ~${plan['est_monthly_usd']}/month (~${plan['est_hourly_usd']}/hour) while up.")
    for a in plan["advisories"]:
        out("NOTE: " + a)
    out(f"plan sha256: {plan['plan_sha256']}")


def cmd_plan(a, runner, out=print, inp=input, isatty=None):
    out(warning_text().rstrip())
    tty = sys.stdin.isatty() if isatty is None else isatty
    if not a.ack_no_auth:
        if not tty:
            out("REFUSED: acknowledge the warning above with --ack-no-auth (no resource is planned without it).")
            return 2
        if inp("Type 'yes' to acknowledge there is NO authentication: ").strip().lower() != "yes":
            out("Declined. Nothing planned, nothing created.")
            return 2
    if not a.project:
        out("REFUSED: --project is required (no default project is ever assumed).")
        return 2
    dep = a.deployment or T.new_id(f"{a.project}{time.time_ns()}")
    regions = a.region or []
    try:
        plan = T.build_plan(a.topology, a.project, regions, dep, a.https_cidr, gcloud_bin())
    except T.PlanError as e:
        out(f"REFUSED: {e}")
        return 2
    missing = prerequisites(a.project, runner)
    if missing:
        for m in missing:
            out("PREREQUISITE MISSING: " + m)
        out("Nothing was created.")
        return 3
    print_plan(plan, out)
    st = {"deployment": dep, "project": a.project, "topology": a.topology, "prefix": plan["prefix"], "label": plan["label"],
          "regions": plan["regions"], "https_cidr": a.https_cidr, "plan_sha256": plan["plan_sha256"], "state": "planned",
          "ack": {"warning_sha256": hashlib.sha256(warning_text().encode()).hexdigest(), "at": int(time.time())},
          "created": []}
    save_state(dep, st)
    out(f"Next: apply --deployment {dep} --plan-sha256 {plan['plan_sha256']} --confirm-cost")
    return 0


def rebuild(st):
    return T.build_plan(st["topology"], st["project"], st["regions"] if st["topology"] != "gcp-member" else st["regions"],
                        st["deployment"], st["https_cidr"], gcloud_bin())


def describe_argv(project, r):
    g = [gcloud_bin(), "--project", project, "--quiet"]
    k, n, w = r["kind"], r["name"], r["where"]
    if k == "network":
        return g + ["compute", "networks", "describe", n]
    if k == "subnet":
        return g + ["compute", "networks", "subnets", "describe", n, "--region", w]
    if k == "serviceaccount":
        return g + ["iam", "service-accounts", "describe", f"{n}@{project}.iam.gserviceaccount.com"]
    if k == "firewall":
        return g + ["compute", "firewall-rules", "describe", n]
    if k == "address":
        return g + ["compute", "addresses", "describe", n, "--region", w]
    if k == "router":
        return g + ["compute", "routers", "describe", n, "--region", w]
    if k == "nat":
        return g + ["compute", "routers", "nats", "describe", n, "--router", n.replace("-nat-", "-rtr-"), "--region", w]
    if k == "instance":
        return g + ["compute", "instances", "describe", n, "--zone", w]
    return None  # iam-binding: add is idempotent


def cmd_apply(a, runner, out=print):
    if not a.confirm_cost:
        out("REFUSED: apply needs --confirm-cost (these resources are billed while they exist).")
        return 2
    st = load_state(a.deployment)
    if a.plan_sha256 != st["plan_sha256"]:
        out("REFUSED: --plan-sha256 does not match the reviewed plan for this deployment.")
        return 2
    missing = prerequisites(st["project"], runner)
    if missing:
        for m in missing:
            out("PREREQUISITE MISSING: " + m)
        return 3
    plan = rebuild(st)
    if plan["plan_sha256"] != st["plan_sha256"]:
        out("REFUSED: plan changed since review; run plan again.")
        return 2
    created = 0
    for r in sorted(plan["resources"], key=lambda x: KIND_ORDER.index(x["kind"])):
        d = describe_argv(st["project"], r)
        if d and runner(d)[0] == 0:
            out(f"  exists  {r['kind']} {r['name']}")
            continue
        rc, _, err = runner(r["create"])
        if rc != 0:
            st["state"] = "partial"
            save_state(a.deployment, st)
            out(f"  FAILED  {r['kind']} {r['name']} (rc={rc}): {SECRET_RE.sub('[redacted]', err.strip()[:300])}")
            out("Stopped. Re-run apply to converge, or teardown to remove what exists.")
            return 5
        if r["kind"] == "iam-binding":
            out(f"  ensured {r['kind']} {r['name']}")
            continue
        created += 1
        if r["name"] not in st["created"]:
            st["created"].append(r["name"])
        out(f"  created {r['kind']} {r['name']}")
    st["state"] = "applied"
    save_state(a.deployment, st)
    out(f"apply done: {created} created.")
    summary(st, runner, out)
    return 0


def summary(st, runner, out=print):
    out("")
    out(warning_text().rstrip())
    out("Endpoints (KEEP PRIVATE):")
    rc, so, _ = runner([gcloud_bin(), "--project", st["project"], "--quiet", "compute", "addresses", "list",
                        "--filter", f"name~^{st['prefix']}", "--format", "value(name,address)"])
    for line in (so.splitlines() if rc == 0 else []):
        if line.strip():
            out(f"  {line.split()[0]}  https://{line.split()[-1]}   [keep private]")
    out(f"Next: bootstrap --deployment {st['deployment']}   |   teardown --deployment {st['deployment']}")


def owned(st, runner):
    """Exact owned set for this deployment: label where supported, else prefix. Read-only. [(kind,name,where)]"""
    g = [gcloud_bin(), "--project", st["project"], "--quiet", "compute"]
    p = st["prefix"]
    found = []
    specs = [("instance", ["instances", "list", "--filter", f"labels.netclaw-deployment={st['deployment']}", "--format", "value(name,zone.basename())"]),
             ("address", ["addresses", "list", "--filter", f"name~^{p}", "--format", "value(name,region.basename())"]),
             ("nat", None),
             ("router", ["routers", "list", "--filter", f"name~^{p}", "--format", "value(name,region.basename())"]),
             ("firewall", ["firewall-rules", "list", "--filter", f"name~^{p}", "--format", "value(name)"]),
             ("subnet", ["networks", "subnets", "list", "--filter", f"name~^{p}", "--format", "value(name,region.basename())"]),
             ("network", ["networks", "list", "--filter", f"name~^{p}", "--format", "value(name)"])]
    for kind, sub in specs:
        if sub is None:
            continue
        rc, so, _ = runner(g + sub)
        for line in (so.splitlines() if rc == 0 else []):
            parts = line.split()
            if parts and parts[0].startswith(p):
                found.append((kind, parts[0], parts[1] if len(parts) > 1 else ""))
    rc, so, _ = runner([gcloud_bin(), "--project", st["project"], "--quiet", "iam", "service-accounts", "list",
                        "--filter", f"email~^{p}sa@", "--format", "value(email)"])
    for line in (so.splitlines() if rc == 0 else []):
        if line.strip().startswith(p + "sa@"):
            found.append(("serviceaccount", line.strip().split("@")[0], ""))
    return sorted(found)


def digest(found):
    return hashlib.sha256(json.dumps(found).encode()).hexdigest()


def cmd_status(a, runner, out=print):
    st = load_state(a.deployment)
    out(f"deployment {st['deployment']} ({st['topology']}, project {st['project']}) state={st['state']}")
    for k, n, w in owned(st, runner):
        out(f"  {k:14s} {n} {w}")
    return 0


def cmd_teardown(a, runner, out=print):
    st = load_state(a.deployment)
    found = owned(st, runner)
    for k, n, w in found:
        out(f"  {k:14s} {n} {w}")
    dg = digest(found)
    out(f"list sha256: {dg}")
    if not a.confirm_list_sha256:
        out("Listed only. Re-run with --confirm-list-sha256 <hash> to delete exactly this list.")
        return 0
    if a.confirm_list_sha256 != dg:
        out("REFUSED: --confirm-list-sha256 does not match the current list.")
        return 2
    g = [gcloud_bin(), "--project", st["project"], "--quiet"]
    order = ["instance", "address", "nat", "router", "firewall", "subnet", "network", "serviceaccount"]
    plan = rebuild(st)
    # remove IAM bindings first (the service account must exist to name the member)
    for r in plan["resources"]:
        if r["kind"] == "iam-binding":
            role = r["name"].split(":", 1)[1]
            runner(g + ["projects", "remove-iam-policy-binding", st["project"],
                        f"--member=serviceAccount:{st['prefix']}sa@{st['project']}.iam.gserviceaccount.com", f"--role={role}", "--condition=None"])
    failed = 0
    for kind in order:
        for k, n, w in found:
            if k != kind or not n.startswith(st["prefix"]):
                continue
            if k == "nat":
                continue
            argv = {"instance": g + ["compute", "instances", "delete", n, "--zone", w, "--delete-disks=all"],
                    "address": g + ["compute", "addresses", "delete", n, "--region", w],
                    "router": g + ["compute", "routers", "delete", n, "--region", w],
                    "firewall": g + ["compute", "firewall-rules", "delete", n],
                    "subnet": g + ["compute", "networks", "subnets", "delete", n, "--region", w],
                    "network": g + ["compute", "networks", "delete", n],
                    "serviceaccount": g + ["iam", "service-accounts", "delete", f"{n}@{st['project']}.iam.gserviceaccount.com"]}[k]
            rc, _, _ = runner(argv)
            out(f"  {'deleted' if rc == 0 else 'FAILED '} {k} {n}")
            failed += rc != 0
    left = owned(st, runner)
    out(f"verification: {len(left)} owned resource(s) remain")
    if not left and not failed:
        st["state"] = "torn-down"
        save_state(a.deployment, st)
        return 0
    return 5


def cmd_ssh(a, runner, out=print):
    st = load_state(a.deployment)
    if not a.node.startswith(st["prefix"]):
        out(f"REFUSED: '{a.node}' is not a node of deployment {st['deployment']}")
        return 2
    zone = None
    for k, n, w in owned(st, runner):
        if k == "instance" and n == a.node:
            zone = w
    if not zone:
        out("REFUSED: node not found in this deployment")
        return 2
    for _ in range(4):
        rc, so, err = runner([gcloud_bin(), "compute", "ssh", a.node, "--zone", zone, "--project", st["project"],
                              "--tunnel-through-iap", "--quiet", "--command", a.command, "--", "-o", "StrictHostKeyChecking=no"])
        if rc == 0:
            out(so.rstrip())
            return 0
        time.sleep(1 if os.environ.get("NETCLAW_GCP_FAST") else 8)
    noise = re.compile(r"(?i)numpy|iap/docs|^WARNING:?\s*$|^\s*$")
    tail = [l for l in (so + "\n" + err).splitlines() if not noise.search(l)][-12:]
    out(SECRET_RE.sub("[redacted]", "\n".join(tail)))
    return 5


BOOTSTRAP_FILE = HERE / "lib" / "gcp-bootstrap.sh"


def bootstrap_command():
    import shlex
    return "bash -c " + shlex.quote(BOOTSTRAP_FILE.read_text())


def cmd_bootstrap(a, runner, out=print):
    st = load_state(a.deployment)
    nodes = [n for k, n, w in owned(st, runner) if k == "instance"]
    if not nodes:
        out("no instances found for this deployment (run apply first)")
        return 2
    rc_all = 0
    for n in nodes:
        if "witness" in n:
            out(f"  skip {n} (etcd witness; configured by the HA bootstrap)")
            continue
        ns = argparse.Namespace(deployment=a.deployment, node=n, command=bootstrap_command())
        rc = cmd_ssh(ns, runner, out)
        out(f"  bootstrap {n}: {'ok' if rc == 0 else 'FAILED'}")
        rc_all = rc_all or rc
    if not rc_all:
        zones = {n: w for k, n, w in owned(st, runner) if k == "instance"}
        for n in nodes:
            if n in zones:
                out(f"  Finish on {n} (interactive, your provider choices): gcloud compute ssh {n} --zone {zones[n]} "
                    f"--project {st['project']} --tunnel-through-iap -- -t 'cd netclaw && ./scripts/install.sh'")
        out("Then enroll each node into your Risk with the Claw Plan Member/Border flow (docs/NETCLAW-IN-GCP.md).")
    out(warning_text().rstrip())
    return rc_all


def main(argv=None, runner=run, out=print):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("topologies")
    p = sub.add_parser("plan")
    p.add_argument("--topology", required=True, choices=list(T.TOPOLOGIES))
    p.add_argument("--project")
    p.add_argument("--region", action="append")
    p.add_argument("--deployment")
    p.add_argument("--https-cidr", required=True, help="source CIDR allowed to reach HTTPS 443 (0.0.0.0/0 refused)")
    p.add_argument("--ack-no-auth", action="store_true")
    ap_ = sub.add_parser("apply")
    ap_.add_argument("--deployment", required=True)
    ap_.add_argument("--plan-sha256", required=True)
    ap_.add_argument("--confirm-cost", action="store_true")
    for name in ("status", "bootstrap"):
        s = sub.add_parser(name)
        s.add_argument("--deployment", required=True)
    s = sub.add_parser("ssh")
    s.add_argument("--deployment", required=True)
    s.add_argument("node")
    s.add_argument("command")
    t = sub.add_parser("teardown")
    t.add_argument("--deployment", required=True)
    t.add_argument("--confirm-list-sha256", default="")
    a = ap.parse_args(argv)
    if a.cmd == "topologies":
        for k, v in T.TOPOLOGIES.items():
            out(f"{k:28s} {v}")
        return 0
    return {"plan": cmd_plan, "apply": cmd_apply, "status": cmd_status, "ssh": cmd_ssh, "bootstrap": cmd_bootstrap,
            "teardown": cmd_teardown}[a.cmd](a, runner, out)


if __name__ == "__main__":
    sys.exit(main())
