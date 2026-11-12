"""Spec 193: docs / installer / extension parity and warning presence."""
import re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
import gcp_topology as T

WARN = [l.strip() for l in (ROOT / "scripts/lib/gcp_warning.txt").read_text().strip().splitlines()]
rd = lambda p: (ROOT / p).read_text()


class Parity(unittest.TestCase):
    def test_warning_verbatim_in_readme_and_guide(self):
        for f in ("README.md", "docs/NETCLAW-IN-GCP.md"):
            t = rd(f)
            for line in WARN:
                self.assertIn(line.replace("!! NOT BEHIND ANY AUTHENTICATION !!", "!! NOT BEHIND ANY AUTHENTICATION !!"), t, f"{f}: {line}")

    def test_guide_near_top_has_warning(self):
        self.assertLess(rd("docs/NETCLAW-IN-GCP.md").index("NOT BEHIND ANY AUTHENTICATION"), 400)

    def test_every_topology_in_guide_tui_and_extension(self):
        guide, menu, ext = rd("docs/NETCLAW-IN-GCP.md"), rd("scripts/lib/gcp-menu.sh"), rd("extensions/netclaw-vscode/src/setup/gcp.ts")
        for t in T.TOPOLOGIES:
            self.assertIn(f"`{t}`", guide, t); self.assertIn(t, menu, t); self.assertIn(f'"{t}"', ext, t)

    def test_docs_link_guide_and_state_no_auth(self):
        for f in ("README.md", "docs/GETTING-STARTED-VSCODE.md", "docs/ASSISTANT-INSTALL.md", "docs/CLAW-PLAN.md"):
            t = rd(f); self.assertIn("NETCLAW-IN-GCP.md", t, f); self.assertRegex(t, r"(?i)NOT behind any authentication", f)

    def test_no_doc_claims_auth_exists(self):
        t = rd("docs/NETCLAW-IN-GCP.md")
        self.assertNotRegex(t, r"(?i)\b(sign-in is|authenticated with SSO|RBAC is enabled)")

    def test_install_sh_offers_gcp_and_summary_prints_warning(self):
        self.assertIn("gcp_deploy_menu", rd("scripts/install.sh"))
        self.assertIn("gcp_warning.txt", rd("scripts/lib/gcp-menu.sh"))

    def test_roadmap(self):
        r = rd("docs/roadmap/issue-310/README.md")
        self.assertRegex(r, r"R09B[^\n]*\*\*Complete\*\*"); self.assertRegex(r, r"\| R10 \| Azure single region \| 5 \| R09C \|")
        self.assertIn("R09C", r); self.assertRegex(r, r"\| R15 \| Multi-user foundation \| 8 \| R14 \|")

    def test_cost_table_matches_estimates(self):
        # guide cost table must be within 15% of the builder's own estimate
        g = rd("docs/NETCLAW-IN-GCP.md")
        for topo, regs in (("gcp-member", ["us-central1"]), ("gcp-border", ["us-central1"]), ("ha-risk", ["us-central1"]),
                           ("distributed-risk", ["us-central1", "europe-west1", "asia-southeast1"])):
            est = T.build_plan(topo, "my-test-project", regs, "abc123", "10.0.0.0/8")["est_monthly_usd"]
            m = re.search(rf"`{topo}` \| ~\$(\d+)", g); self.assertIsNotNone(m, topo)
            self.assertLess(abs(int(m.group(1)) - est) / est, 0.15, f"{topo}: doc {m.group(1)} vs {est}")


if __name__ == "__main__":
    unittest.main()
