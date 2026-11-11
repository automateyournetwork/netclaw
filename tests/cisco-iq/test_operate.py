import json
import unittest

import mock_server
from common import CANARY, cisco_iq, fixture_home, mode, run


def enabled(region="us"):
    home = fixture_home()
    assert run(["enable", "--region", region, "--key-stdin"], CANARY, home).rc == 0
    return home


def diag(home, url, *extra):
    return run(["diagnose", "--live", "--json", "--endpoint-override", url, *extra], None, home)


class OperateTests(unittest.TestCase):
    def test_not_enabled_and_key_unset(self):
        r = run(["diagnose", "--json"], None, fixture_home())
        self.assertEqual(json.loads(r.out)["status"], "NOT_ENABLED"); self.assertEqual(r.rc, 1)
        home = enabled(); run(["rotate", "--key-stdin"], "newkey-1234567", home)
        cisco_iq._known_secrets.clear()
        env = home / ".env"; env.write_text("CISCO_IQ_REGION=us\n")
        self.assertEqual(json.loads(run(["diagnose", "--json"], None, home).out)["status"], "KEY_UNSET")

    def test_env_permissions_finding(self):
        home = enabled(); (home / ".env").chmod(0o644)
        self.assertEqual(json.loads(run(["diagnose", "--json"], None, home).out)["status"], "ENV_PERMISSIONS")

    def test_offline_ok_makes_no_network_claim(self):
        r = run(["diagnose"], None, enabled())
        self.assertEqual(r.rc, 0); self.assertIn("No network check", r.out)

    def test_live_ok_json_and_sse(self):
        for sse in (False, True):
            srv, url, seen = mock_server.make(tools=[{"name": "t1"}], sse=sse)
            r = diag(enabled(), url)
            srv.shutdown()
            self.assertEqual(json.loads(r.out)["status"], "OK", r.text)
            self.assertEqual(seen["auth"][0], "Bearer " + CANARY)
            self.assertNotIn(CANARY, r.text)
            self.assertEqual(seen["methods"][:1], ["initialize"])

    def test_zero_tools_distinct(self):
        srv, url, _ = mock_server.make(tools=[]); r = diag(enabled(), url); srv.shutdown()
        rep = json.loads(r.out)
        self.assertEqual(rep["status"], "ZERO_TOOLS"); self.assertIn("service-account", " ".join(rep["hints"]))

    def test_auth_failure_redacts_and_hedges(self):
        srv, url, _ = mock_server.make(require_key="someone-elses-key"); r = diag(enabled(), url); srv.shutdown()
        rep = json.loads(r.out)
        self.assertEqual(rep["status"], "AUTH_FAILURE"); self.assertNotIn(CANARY, r.text)
        self.assertIn("not confirmed", " ".join(rep["hints"]))

    def test_transport_failure_distinct(self):
        srv, url, _ = mock_server.make(); srv.shutdown(); srv.server_close()
        self.assertEqual(json.loads(diag(enabled(), url).out)["status"], "TRANSPORT_FAILURE")
        srv, url, _ = mock_server.make(status_override=500)
        self.assertEqual(json.loads(diag(enabled(), url).out)["status"], "TRANSPORT_FAILURE"); srv.shutdown()

    def test_override_must_be_loopback_http(self):
        r = run(["diagnose", "--live", "--endpoint-override", "http://example.com/mcp"], None, enabled())
        self.assertEqual(r.rc, 2)

    def test_rotate_only_changes_key_keeps_backup(self):
        home = enabled(); cfg = (home / "openclaw.json").read_text()
        (home / ".env").write_text((home / ".env").read_text() + "UNRELATED=keepme\n")
        new = "rotated-secret-98765"
        r = run(["rotate", "--key-stdin"], new, home)
        self.assertEqual(r.rc, 0, r.text); self.assertNotIn(new, r.text); self.assertNotIn(CANARY, r.text)
        env = (home / ".env").read_text()
        self.assertIn(new, env); self.assertNotIn(CANARY, env); self.assertIn("UNRELATED=keepme", env)
        self.assertEqual((home / "openclaw.json").read_text(), cfg)
        baks = [p for p in home.glob(".env.cisco-iq-*.bak")]
        self.assertEqual(len(baks), 1); self.assertEqual(mode(baks[0]), 0o600)
        journal = baks[0].with_name(baks[0].name + ".state.json")
        self.assertNotIn(CANARY, journal.read_text())
        self.assertEqual(mode(home / ".env"), 0o600)

    def test_rotate_requires_key_input(self):
        self.assertEqual(run(["rotate", "--key-stdin"], "", enabled()).rc, 2)

    def test_update_region_keeps_key(self):
        home = enabled("us"); r = run(["update", "--region", "emea"], None, home)
        self.assertEqual(r.rc, 0); self.assertIn("us -> emea", r.out)
        reg = json.loads((home / "openclaw.json").read_text())["mcpServers"]["cisco-iq-mcp"]
        self.assertEqual(reg["url"], cisco_iq.REGIONS["emea"]); self.assertIn(CANARY, (home / ".env").read_text())
        self.assertEqual(run(["update", "--region", "bad"], None, home).rc, 2)

    def test_disable_keeps_key_then_purge_and_noop(self):
        home = enabled()
        self.assertEqual(run(["disable"], None, home).rc, 0)
        self.assertNotIn("cisco-iq-mcp", json.loads((home / "openclaw.json").read_text())["mcpServers"])
        self.assertIn("other", json.loads((home / "openclaw.json").read_text())["mcpServers"])
        self.assertIn(CANARY, (home / ".env").read_text())
        r = run(["disable"], None, home); self.assertEqual(r.rc, 0); self.assertIn("already absent", r.out)
        self.assertEqual(run(["disable", "--purge-credential"], None, home).rc, 0)
        self.assertNotIn("CISCO_IQ", (home / ".env").read_text())

    def test_status_never_shows_value(self):
        r = run(["status", "--json"], None, enabled())
        self.assertNotIn(CANARY, r.text); d = json.loads(r.out)
        self.assertTrue(d["key_set"]); self.assertEqual(d["region"], "us"); self.assertEqual(d["env_mode"], "0o600")


if __name__ == "__main__":
    unittest.main()
