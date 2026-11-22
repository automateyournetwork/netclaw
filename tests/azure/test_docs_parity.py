"""Spec 198: Azure docs / installer step / env example parity, warning presence, and no secrets in tracked docs."""
import re, subprocess, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
WARN = [l.strip() for l in (ROOT / "scripts/lib/azure_warning.txt").read_text().strip().splitlines()]
rd = lambda p: (ROOT / p).read_text()


class AzureParity(unittest.TestCase):
    def test_warning_verbatim_in_readme_guide_and_mesh(self):
        for f in ("README.md", "docs/NETCLAW-IN-AZURE.md"):
            t = rd(f)
            for line in WARN:
                self.assertIn(line, t, f"{f}: {line}")

    def test_guide_near_top_has_warning(self):
        self.assertLess(rd("docs/NETCLAW-IN-AZURE.md").index("NOT BEHIND ANY AUTHENTICATION"), 900)
        self.assertLess(rd("docs/NETCLAW-MULTICLOUD-MESH.md").index("NOT BEHIND ANY AUTHENTICATION"), 900)

    def test_docs_link_guides_and_state_no_auth(self):
        for f in ("README.md", "docs/GETTING-STARTED-VSCODE.md", "docs/ASSISTANT-INSTALL.md", "docs/CLAW-PLAN.md"):
            t = rd(f)
            self.assertIn("NETCLAW-IN-AZURE.md", t, f)
            self.assertRegex(t, r"(?i)NOT behind any authentication", f)
        self.assertIn("NETCLAW-MULTICLOUD-MESH.md", rd("README.md"))

    def test_install_sh_offers_azure_readonly(self):
        sh, menu = rd("scripts/install.sh"), rd("scripts/lib/azure-menu.sh")
        self.assertIn("azure_deploy_menu", sh)
        self.assertIn("azure_warning.txt", menu)
        self.assertIn("ha-r10-preflight.sh", menu)
        # the menu must never create a billable resource itself
        for forbidden in ("ha-r10-phase.sh up", "az vm create", "az group create"):
            code = "\n".join(l for l in menu.splitlines() if not l.lstrip().startswith("echo") and not l.lstrip().startswith("#"))
            self.assertNotIn(forbidden, code)
        self.assertIn("0.0.0.0/0 is refused", menu)

    def test_guide_facts_match_scripts(self):
        g = rd("docs/NETCLAW-IN-AZURE.md")
        for needle in ("Standard_D2as_v7", "canadacentral", "eastus2", "swedencentral", "Ubuntu 24.04", "R10_ADMISSION_MS", "ha-r10-build-group.sh",
                       "$25", "$15", "R10_AZ_REGION_EW1", "R10_SIZE", "fence", "Ollama"):
            self.assertIn(needle, g, needle)
        self.assertRegex(g, r"(?i)ollama not required")

    def test_env_example_names_only(self):
        t = rd(".env.example")
        for name in ("R10_SSH_ALLOW_CIDR", "R10_AZ_REGION_EW1", "R10_AZ_REGION_ASE1", "R10_SIZE", "R10_GO", "R10_GO_DNS", "R10_RUN_ID",
                     "R10_ACME_EMAIL", "R10_ADMISSION_MS", "R10_GUARD_DIR", "GCP_VM_PREFIX"):
            self.assertRegex(t, rf"(?m)^{name}=$", f"{name} must be present with no value")
        self.assertNotRegex(t, r"(?m)^(GODADDY_PAT|ANTHROPIC_API_KEY|NETBOX_TOKEN)=\S")

    def test_no_secret_shapes_in_new_docs(self):
        for f in ("docs/NETCLAW-IN-AZURE.md", "docs/NETCLAW-MULTICLOUD-MESH.md", "scripts/lib/azure-menu.sh", "scripts/lib/azure_warning.txt"):
            t = rd(f)
            self.assertNotRegex(t, r"nbt_[A-Za-z0-9]{6,}|sk-ant-[A-Za-z0-9]|AKIA[0-9A-Z]{12}|ghp_[A-Za-z0-9]{20}", f)
            self.assertNotRegex(t, r"[\w.+-]+@(gmail|itential)\.com", f)

    def test_menu_syntax(self):
        for f in ("scripts/lib/azure-menu.sh", "scripts/install.sh"):
            r = subprocess.run(["bash", "-n", str(ROOT / f)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
