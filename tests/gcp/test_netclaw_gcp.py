"""Spec 193: provisioner tests with an injected fake gcloud runner. No real GCP calls."""
import importlib.util, os, re, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
spec = importlib.util.spec_from_file_location("netclaw_gcp", ROOT / "scripts" / "netclaw-gcp.py")
G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
import gcp_topology as T

PROJ = "my-test-project"


class Fake:
    """Tiny in-memory gcloud: tracks created names; answers describe/list/auth/services."""
    def __init__(self, auth=True, services=True, project=True, fail_on=None):
        self.created, self.calls, self.auth, self.services, self.project, self.fail_on = [], [], auth, services, project, fail_on
        self.deleted = []

    def __call__(self, argv):
        self.calls.append(argv)
        a = " ".join(argv)
        if "auth list" in a: return (0, "me@example.com\n", "") if self.auth else (0, "", "")
        if "projects describe" in a: return (0, PROJ, "") if self.project else (1, "", "nope")
        if "services list" in a:
            return (0, "compute.googleapis.com\niam.googleapis.com\niap.googleapis.com\n" if self.services else "compute.googleapis.com\n", "")
        if " describe " in a:
            name = [x for x in argv if x.startswith("nc-")]
            nm = name[0].split("@")[0] if name else ""
            return (0, "", "") if nm in self.created else (1, "", "not found")
        if " create " in a or "add-iam-policy-binding" in a:
            nm = [x for x in argv if x.startswith("nc-")]
            if self.fail_on and nm and self.fail_on in nm[0]: return (1, "", "quota")
            if nm: self.created.append(nm[0])
            return 0, "", ""
        if " delete " in a:
            nm = [x for x in argv if x.startswith("nc-")][0].split("@")[0]
            self.deleted.append(nm)
            if nm in self.created: self.created.remove(nm)
            return 0, "", ""
        if "remove-iam-policy-binding" in a: return 0, "", ""
        if " list" in a:
            return 0, self._list(argv), ""
        return 0, "", ""

    def _list(self, argv):
        a = " ".join(argv)
        lines = []
        for n in self.created:
            if "instances list" in a and "-border-" in n or "instances list" in a and "-member-" in n or "instances list" in a and "-witness-" in n:
                lines.append(f"{n} zone-b")
            elif "addresses list" in a and "-ip-" in n: lines.append(f"{n} region1")
            elif "routers list" in a and "-rtr-" in n: lines.append(f"{n} region1")
            elif "firewall-rules list" in a and "-allow-" in n: lines.append(n)
            elif "subnets list" in a and "-sub-" in n: lines.append(f"{n} region1")
            elif "networks list" in a and "subnets" not in a and n.endswith("-net"): lines.append(n)
            elif "service-accounts list" in a and n.endswith("-sa"): lines.append(f"{n}@{PROJ}.iam.gserviceaccount.com")
        return "\n".join(lines)


def cli(args, fake, tmp):
    os.environ["NETCLAW_GCP_HOME"] = tmp; os.environ["NETCLAW_GCP_FAST"] = "1"
    buf = []
    rc = G.main(args, runner=fake, out=buf.append)
    return rc, "\n".join(buf)


def plan_args(topo="gcp-border", extra=()):
    return ["plan", "--topology", topo, "--project", PROJ, "--region", "us-central1", "--https-cidr", "203.0.113.7/32", "--ack-no-auth", *extra]


class Tests(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.mkdtemp()

    def test_warning_before_plan_and_required(self):
        rc, out = cli(["plan", "--topology", "gcp-border", "--project", PROJ, "--region", "us-central1", "--https-cidr", "203.0.113.7/32"], Fake(), self.tmp)
        self.assertEqual(rc, 2); self.assertIn("NOT BEHIND ANY AUTHENTICATION", out); self.assertNotIn("plan sha256", out)

    def test_plan_creates_nothing_and_shows_cost(self):
        f = Fake(); rc, out = cli(plan_args(), f, self.tmp)
        self.assertEqual(rc, 0); self.assertEqual(f.created, []); self.assertIn("Estimated running cost", out); self.assertIn("plan sha256", out)
        self.assertFalse([c for c in f.calls if " create " in " ".join(c)])

    def test_no_default_project(self):
        rc, out = cli(["plan", "--topology", "gcp-border", "--region", "us-central1", "--https-cidr", "10.0.0.0/8", "--ack-no-auth"], Fake(), self.tmp)
        self.assertEqual(rc, 2); self.assertIn("--project is required", out)

    def test_https_open_world_refused(self):
        rc, out = cli(["plan", "--topology", "gcp-border", "--project", PROJ, "--region", "us-central1", "--https-cidr", "0.0.0.0/0", "--ack-no-auth"], Fake(), self.tmp)
        self.assertEqual(rc, 2); self.assertIn("refused", out)

    def test_prerequisites_each_reported_before_anything(self):
        for fake, needle in ((Fake(auth=False), "gcloud auth login"), (Fake(services=False), "iap.googleapis.com"), (Fake(project=False), "not found")):
            rc, out = cli(plan_args(), fake, self.tmp); self.assertEqual(rc, 3); self.assertIn(needle, out); self.assertEqual(fake.created, [])

    def _dep(self, out): return re.search(r"deployment (\w{6}),", out).group(1), re.search(r"plan sha256: (\w{64})", out).group(1)

    def test_apply_gates(self):
        f = Fake(); _, out = cli(plan_args(), f, self.tmp); dep, sha = self._dep(out)
        self.assertEqual(cli(["apply", "--deployment", dep, "--plan-sha256", sha], f, self.tmp)[0], 2)
        self.assertEqual(cli(["apply", "--deployment", dep, "--plan-sha256", "0" * 64, "--confirm-cost"], f, self.tmp)[0], 2)
        self.assertEqual(f.created, [])

    def test_apply_idempotent_and_teardown_exact(self):
        f = Fake(); _, out = cli(plan_args("ha-risk"), f, self.tmp); dep, sha = self._dep(out)
        rc, out = cli(["apply", "--deployment", dep, "--plan-sha256", sha, "--confirm-cost"], f, self.tmp); self.assertEqual(rc, 0)
        self.assertTrue(all(n.startswith(f"nc-{dep}-") for n in f.created))
        self.assertIn("keep private", out); self.assertIn("NOT BEHIND ANY AUTHENTICATION", out)
        n1 = len(f.created)
        rc, out2 = cli(["apply", "--deployment", dep, "--plan-sha256", sha, "--confirm-cost"], f, self.tmp)
        self.assertEqual(rc, 0); self.assertEqual(len(f.created), n1); self.assertIn("0 created", out2)
        f.created.append("someone-elses-vm"); f.created.append("nc-aaaaaa-border-x1")  # foreign + other deployment
        rc, lst = cli(["teardown", "--deployment", dep], f, self.tmp); self.assertEqual(rc, 0)
        h = re.search(r"list sha256: (\w{64})", lst).group(1)
        self.assertEqual(cli(["teardown", "--deployment", dep, "--confirm-list-sha256", "bad"], f, self.tmp)[0], 2)
        rc, out = cli(["teardown", "--deployment", dep, "--confirm-list-sha256", h], f, self.tmp)
        self.assertEqual(rc, 0, out); self.assertIn("0 owned resource(s) remain", out)
        self.assertIn("someone-elses-vm", f.created); self.assertIn("nc-aaaaaa-border-x1", f.created)

    def test_partial_failure_stops_and_reports(self):
        f = Fake(fail_on="-border-"); _, out = cli(plan_args(), f, self.tmp); dep, sha = self._dep(out)
        rc, out = cli(["apply", "--deployment", dep, "--plan-sha256", sha, "--confirm-cost"], f, self.tmp)
        self.assertEqual(rc, 5); self.assertIn("FAILED", out)
        self.assertEqual(G.load_state(dep)["state"], "partial")

    def test_topology_shapes(self):
        shapes = {"gcp-border": ["border"], "gcp-member": ["member"], "gcp-border-onprem-members": ["border"],
                  "onprem-border-gcp-members": ["member", "member"], "ha-risk": ["border", "border", "witness"]}
        for t, roles in shapes.items():
            p = T.build_plan(t, PROJ, ["us-central1"], "abc123", "203.0.113.7/32")
            self.assertEqual(sorted(r["role"] for r in p["resources"] if r["kind"] == "instance"), sorted(roles), t)
        p = T.build_plan("distributed-risk", PROJ, ["us-central1", "europe-west1", "asia-southeast1"], "abc123", "10.0.0.0/8")
        self.assertEqual(len([r for r in p["resources"] if r["role" if False else "kind"] == "instance"]), 3)
        with self.assertRaises(T.PlanError): T.build_plan("distributed-risk", PROJ, ["us-central1"], "abc123", "10.0.0.0/8")

    def test_witness_has_no_external_ip_and_member_not_exposed(self):
        p = T.build_plan("ha-risk", PROJ, ["us-central1"], "abc123", "203.0.113.7/32")
        w = [r for r in p["resources"] if r.get("role") == "witness"][0]; self.assertIn("--no-address", w["create"])
        p = T.build_plan("gcp-member", PROJ, ["us-central1"], "abc123", "203.0.113.7/32")
        self.assertFalse([r for r in p["resources"] if r["name"].endswith(("allow-https", "allow-in2n"))])

    def test_r09b_adopted_items_in_plan(self):
        p = T.build_plan("gcp-border", PROJ, ["us-central1"], "abc123", "203.0.113.7/32"); a = " ".join(" ".join(r["create"]) for r in p["resources"])
        for needle in ("enable-oslogin=TRUE", "--shielded-secure-boot", "--enable-private-ip-google-access", "--service-account=nc-abc123-sa@", "35.235.240.0/20", "--enable-logging"):
            self.assertIn(needle, a)
        self.assertTrue(any("Budget" in x for x in p["advisories"]))

    def test_all_names_owned_and_no_secrets(self):
        p = T.build_plan("ha-risk", PROJ, ["us-central1"], "abc123", "203.0.113.7/32")
        for r in p["resources"]: self.assertTrue(r["name"].startswith("nc-abc123-"), r["name"])
        self.assertFalse(G.SECRET_RE.search(str(p)))

    def test_bootstrap_script_prepares_host_but_never_runs_installer_or_secrets(self):
        b = (ROOT / "scripts/lib/gcp-bootstrap.sh").read_text()
        self.assertIn("sha256sum -c", b)  # Node download is checksum verified
        self.assertNotRegex(b, r"(?m)^\s*(cd netclaw && )?\./scripts/install\.sh")  # interactive step stays with the user
        self.assertFalse(G.SECRET_RE.search(b))
        self.assertTrue(G.bootstrap_command().startswith("bash -c "))

    def test_no_operator_hardcodes_in_user_path(self):
        bad = re.compile(r"netclaw-506315|nc18[23]|automateyournetwork\.com|ptcapo")
        for f in ("scripts/netclaw-gcp.py", "scripts/lib/gcp_topology.py", "scripts/lib/gcp_warning.txt", "scripts/lib/gcp-menu.sh", "scripts/lib/gcp-bootstrap.sh"):
            pth = ROOT / f
            if pth.exists(): self.assertIsNone(bad.search(pth.read_text()), f)


if __name__ == "__main__":
    unittest.main()
