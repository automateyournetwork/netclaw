import json
import re
import unittest

import mock_server
from common import ROOT, cisco_iq, fixture_home, run, CANARY

TEXT = lambda p: (ROOT / p).read_text()


class PolicyTests(unittest.TestCase):
    def test_policy_schema_and_defaults(self):
        p = cisco_iq.load_policy()
        self.assertEqual(p["allow"], [])
        self.assertTrue(p["read_only"]); self.assertEqual(p["mode"], "deny-by-default")
        schema = json.loads(TEXT("specs/191-cisco-iq-mcp/contracts/policy.schema.json"))
        for k in schema["required"]:
            self.assertIn(k, p)

    def test_classification(self):
        p = cisco_iq.load_policy()
        p["allow"] = [{"name": "list_things", "verified": False}, {"name": "delete_thing", "verified": False}]
        c = cisco_iq.classify(["list_things", "delete_thing", "update_x", "mystery_read", "run_job"], p)
        self.assertEqual(c["allowed"], ["list_things"])
        self.assertEqual(set(c["denied"]), {"delete_thing", "update_x", "run_job"})   # deny wins over allow
        self.assertEqual(c["unlisted"], ["mystery_read"])

    def test_policy_check_cli_and_live(self):
        home = fixture_home(); tf = home / "tools.json"
        tf.write_text(json.dumps({"tools": [{"name": "get_a"}, {"name": "create_b"}]}))
        r = run(["policy-check", "--tools-file", str(tf)], None, home)
        self.assertEqual(r.rc, 0); self.assertIn("defenseclaw tool block create_b", r.out); self.assertIn("get_a", r.out)
        run(["enable", "--region", "us", "--key-stdin"], CANARY, home)
        srv, url, _ = mock_server.make(tools=[{"name": "x_lookup"}])
        r = run(["policy-check", "--live", "--json", "--endpoint-override", url], None, home); srv.shutdown()
        self.assertEqual(json.loads(r.out)["unlisted"], ["x_lookup"]); self.assertNotIn(CANARY, r.text)

    def test_bad_policy_rejected(self):
        home = fixture_home(); bad = home / "p.json"
        bad.write_text(json.dumps({"mode": "allow-all", "read_only": False, "allow": [], "deny_patterns": []}))
        self.assertEqual(run(["policy-check", "--policy", str(bad), "--tools-file", str(bad)], None, home).rc, 1)


class DocTests(unittest.TestCase):
    def test_endpoint_table_agrees_everywhere(self):
        for path in ("docs/CISCO-IQ.md", "workspace/skills/cisco-iq/SKILL.md", "config/components/catalog.json"):
            t = TEXT(path)
            for url in cisco_iq.REGIONS.values():
                if path.endswith("catalog.json") and url not in t:
                    continue  # catalog may carry region names only; docs/skill must carry URLs
                self.assertIn(url, t, path)
        for path in ("docs/CISCO-IQ.md", "workspace/skills/cisco-iq/SKILL.md"):
            found = set(re.findall(r"https://[a-z0-9-]+\.iq\.cisco\.com/mcp", TEXT(path)))
            self.assertEqual(found, set(cisco_iq.REGIONS.values()), path)

    def test_skill_disclaimers_and_no_invented_tools(self):
        s = TEXT("workspace/skills/cisco-iq/SKILL.md").lower()
        for needle in ("tools/list", "user principal", "not validated", "key owner", "read-only", "do not invent"):
            self.assertIn(needle, s)
        self.assertNotRegex(s, r"\b(get|list|search|find)_[a-z_]+\(")

    def test_docs_state_credential_facts(self):
        d = TEXT("docs/CISCO-IQ.md").lower()
        for needle in ("user principal", "service-account", "expire", "inherit", "403", "could not be verified",
                       "never inferred", "rotate", "disable", "diagnose", "defenseclaw"):
            self.assertIn(needle, d)

    def test_no_key_like_values_committed(self):
        for path in ("config/cisco-iq-policy.json", "scripts/cisco_iq.py", "docs/CISCO-IQ.md", ".env.example"):
            self.assertNotRegex(TEXT(path), r"Bearer\s+(?!\$\{)[A-Za-z0-9]{16,}")
        self.assertNotIn("openclaw.json#cisco-iq", "")
        cfg = json.loads(TEXT("config/openclaw.json"))
        self.assertNotIn("cisco-iq-mcp", cfg["mcpServers"])   # region is mandatory: never pre-seeded


if __name__ == "__main__":
    unittest.main()
