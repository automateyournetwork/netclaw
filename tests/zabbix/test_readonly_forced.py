"""Read-only is forced by NetClaw, not inherited. Spec 083, FR-021/021a/021b, SC-018a/018b.

The upstream library defaults READ_ONLY to True (utils.py:29) but its shipped launcher
defaults it to False (scripts/start_server.py:139). Running it the documented upstream
way ENABLES WRITES. So NetClaw must set the flag itself, and must not depend on which
upstream default wins.
"""
from __future__ import annotations
import json, re
from _harness import FAILURES, check, read, repo, run  # noqa: F401

def _cfg():
    return json.loads(read("config", "openclaw.json"))["mcpServers"]["zabbix-mcp"]

def test_read_only_is_set_explicitly():
    env = _cfg().get("env", {})
    check("READ_ONLY is present in NetClaw's own registration", "READ_ONLY" in env,
          "absent — the integration would inherit the upstream launcher's default of false")
    check("READ_ONLY is literally 'true', not a passthrough variable",
          env.get("READ_ONLY") == "true",
          f"got {env.get('READ_ONLY')!r} — a ${{VAR}} passthrough could be unset at runtime")

def test_upstream_default_is_still_inverted():
    """If upstream ever fixes this, we want to notice — but we still force the flag."""
    launcher = read("mcp-servers", "zabbix-mcp", "vendor", "zabbix-mcp-server",
                    "scripts", "start_server.py")
    lib = read("mcp-servers", "zabbix-mcp", "vendor", "zabbix-mcp-server",
               "src", "zabbix_mcp_server", "utils.py")
    inverted = 'parse_bool_env("READ_ONLY", default=False)' in launcher
    safe_lib = "default=True" in lib
    check("upstream library still defaults read-only to True", safe_lib,
          "upstream changed — re-check the NOTICE")
    check("upstream launcher still defaults read-only to False (the reason we force it)",
          inverted,
          "upstream may have fixed this; the forced flag stays regardless, but update NOTICE.md")

def test_denylist_present_and_covers_every_destructive_verb():
    deny = _cfg().get("env", {}).get("ZABBIX_API_BLACKLIST", "")
    check("a deny-list is configured", bool(deny.strip()),
          "no second layer — read-only would be the only thing standing between an agent and host.delete")
    for verb in ("delete", "create", "update", "massdelete", "massupdate", "import", "acknowledge"):
        check(f"deny-list covers '{verb}'", verb in deny, f"missing from {deny!r}")

def test_denylist_is_not_vacuous():
    """A pattern list that matches nothing is decoration."""
    deny = _cfg().get("env", {}).get("ZABBIX_API_BLACKLIST", "")
    pats = [re.compile(p.strip()) for p in deny.split(",") if p.strip()]
    for method in ("host.delete", "template.delete", "action.update", "event.acknowledge"):
        check(f"{method} matches at least one deny pattern",
              any(p.match(method) for p in pats),
              "the deny-list would not stop this")
    for method in ("host.get", "item.get", "history.get", "trend.get", "problem.get"):
        check(f"{method} is NOT denied (deny-list is not over-broad)",
              not any(p.match(method) for p in pats),
              "a read method is blocked — the integration would be useless")

def test_tls_and_no_literal_credentials():
    env = _cfg().get("env", {})
    check("VERIFY_SSL is configured", "VERIFY_SSL" in env)
    for k, v in env.items():
        if k in ("ZABBIX_TOKEN", "ZABBIX_URL"):
            check(f"{k} is a ${{VAR}} passthrough, not a literal",
                  isinstance(v, str) and v.startswith("${"),
                  f"literal value in config: {v[:20]!r}")

def test_no_write_path_is_advertised():
    for skill in ("zabbix-metrics-history", "zabbix-problem-review", "zabbix-availability"):
        text = read("workspace", "skills", skill, "SKILL.md").lower()
        check(f"{skill} states it is read-only", "read-only" in text,
              "a reader could assume writes are available")

TESTS = [test_read_only_is_set_explicitly, test_upstream_default_is_still_inverted,
         test_denylist_present_and_covers_every_destructive_verb, test_denylist_is_not_vacuous,
         test_tls_and_no_literal_credentials, test_no_write_path_is_advertised]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "read-only enforcement"))
