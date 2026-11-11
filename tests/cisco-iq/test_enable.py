import json
import os
import subprocess
import unittest

from common import CANARY, ROOT, cisco_iq, fixture_home, mode, run


class EnableTests(unittest.TestCase):
    def test_each_region_gets_exact_endpoint(self):
        expected = {"emea": "https://eu-central-1.iq.cisco.com/mcp",
                    "us": "https://us-west-2.iq.cisco.com/mcp",
                    "apjc": "https://ap-southeast-2.iq.cisco.com/mcp"}
        self.assertEqual(cisco_iq.REGIONS, expected)
        for region, url in expected.items():
            home = fixture_home()
            r = run(["enable", "--region", region, "--key-stdin"], CANARY, home)
            self.assertEqual(r.rc, 0, r.text)
            cfg = json.loads((home / "openclaw.json").read_text())
            reg = cfg["mcpServers"]["cisco-iq-mcp"]
            self.assertEqual(reg["url"], url)
            self.assertEqual(reg["headers"], {"Authorization": "Bearer ${CISCO_IQ_API_KEY}"})
            self.assertIn("other", cfg["mcpServers"])

    def test_region_required_and_validated_no_state_change(self):
        for argv in (["enable"], ["enable", "--region", "mars"], ["enable", "--region", ""]):
            home = fixture_home()
            before = (home / "openclaw.json").read_text()
            r = run(argv, CANARY, home)
            self.assertEqual(r.rc, 2, r.text)
            self.assertEqual((home / "openclaw.json").read_text(), before)
            self.assertFalse((home / ".env").exists())
            self.assertIn("emea", r.text)

    def test_region_never_inferred(self):
        src = (ROOT / "scripts" / "cisco_iq.py").read_text()
        for banned in ("import locale", "import socket", "timezone", "tzname", "geoip", "gethostbyname"):
            self.assertNotIn(banned, src)

    def test_key_only_in_env_file_mode_0600(self):
        home = fixture_home()
        r = run(["enable", "--region", "us", "--key-stdin"], CANARY, home)
        self.assertEqual(r.rc, 0)
        self.assertNotIn(CANARY, r.text)
        self.assertEqual(mode(home / ".env"), 0o600)
        self.assertIn(CANARY, (home / ".env").read_text())
        for f in home.iterdir():
            if f.name == ".env" or f.name.endswith(".bak") or f.name.endswith(".json") and ".state" in f.name:
                continue
            self.assertNotIn(CANARY, f.read_text(), f.name)

    def test_idempotent(self):
        home = fixture_home()
        run(["enable", "--region", "us", "--key-stdin"], CANARY, home)
        first = (home / "openclaw.json").read_text()
        env1 = (home / ".env").read_text()
        r = run(["enable", "--region", "us"], None, home)
        self.assertEqual(r.rc, 0, r.text)
        self.assertEqual((home / "openclaw.json").read_text(), first)
        self.assertEqual((home / ".env").read_text(), env1)

    def test_dry_run_writes_nothing_and_is_redacted(self):
        home = fixture_home()
        before = (home / "openclaw.json").read_text()
        r = run(["enable", "--region", "emea", "--key-stdin", "--dry-run"], CANARY, home)
        self.assertEqual(r.rc, 0)
        self.assertNotIn(CANARY, r.text)
        self.assertEqual((home / "openclaw.json").read_text(), before)
        self.assertFalse((home / ".env").exists())

    def test_secret_on_argv_rejected_without_echo(self):
        for flag in (["--key", CANARY], ["--api-key=" + CANARY], ["--token", CANARY]):
            r = run(["enable", "--region", "us"] + flag, None, fixture_home())
            self.assertEqual(r.rc, 2)
            self.assertNotIn(CANARY, r.text)

    def test_newline_key_rejected(self):
        home = fixture_home()
        r = run(["enable", "--region", "us", "--key-stdin"], "abcd\nefgh", home)
        self.assertEqual(r.rc, 2)

    def test_symlinked_env_refused(self):
        home = fixture_home()
        target = home / "elsewhere"; target.write_text("")
        os.symlink(target, home / ".env")
        r = run(["enable", "--region", "us", "--key-stdin"], CANARY, home)
        self.assertEqual(r.rc, 1)
        self.assertEqual(target.read_text(), "")

    def test_config_location_detection(self):
        home = fixture_home(with_config=False)
        (home / "config").mkdir()
        (home / "config" / "openclaw.json").write_text(json.dumps({"mcpServers": {}}))
        r = run(["enable", "--region", "apjc", "--key-stdin"], CANARY, home)
        self.assertEqual(r.rc, 0, r.text)
        cfg = json.loads((home / "config" / "openclaw.json").read_text())
        self.assertIn("cisco-iq-mcp", cfg["mcpServers"])
        self.assertFalse((home / "openclaw.json").exists())

    def test_refuses_unknown_config_layout(self):
        home = fixture_home(with_config=False)
        (home / "openclaw.json").write_text(json.dumps({"servers": {}}))
        r = run(["enable", "--region", "us", "--key-stdin"], CANARY, home)
        self.assertEqual(r.rc, 1)

    def test_non_https_endpoint_refused(self):
        with self.assertRaises(cisco_iq.AdminError):
            cisco_iq.check_endpoint("http://example.com/mcp", allow_loopback_http=True)
        with self.assertRaises(cisco_iq.AdminError):
            cisco_iq.check_endpoint("http://127.0.0.1:1/mcp")
        self.assertTrue(cisco_iq.check_endpoint("http://127.0.0.1:1/mcp", allow_loopback_http=True))

    def test_wrapper_script_runs(self):
        r = subprocess.run([str(ROOT / "scripts/cisco-iq-enable.sh"), "enable", "--home", str(fixture_home()),
                            "--dry-run"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("Region is required", r.stderr)

    def test_redact_function(self):
        cisco_iq.register_secret(CANARY)
        for s in ("Authorization: Bearer " + CANARY, "x " + CANARY + " y", "Bearer abcdef123456",
                  "{'Authorization': 'Bearer zzzzzzzz'}"):
            out = cisco_iq.redact(s)
            self.assertNotIn(CANARY, out); self.assertNotIn("abcdef123456", out); self.assertNotIn("zzzzzzzz", out)
        self.assertIn("${CISCO_IQ_API_KEY}", cisco_iq.redact("Authorization: Bearer ${CISCO_IQ_API_KEY}"))


if __name__ == "__main__":
    unittest.main()
