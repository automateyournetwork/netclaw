"""Spec 174: the Border stops routing skills a member's own runtime cannot load."""
import asyncio
import json
import os
import stat
from types import SimpleNamespace

import pytest

from bgp.federation import member_inventory as mi
from bgp.federation.manager import FederationManager
from bgp.federation.risk import RiskManager, BASE_FLOOR
from bgp.federation.router import RiskRouter, NoCapableMember
from bgp.federation.service import FederationService

SCOPE = ["n2n-member-runtime", "self-status", "markmap-viz", "ue5-network-viz", "uml-diagram",
         "blender-3d-viz", "drawio-diagram", "isp-sla-claim"]


def _check(workspace):
    return {"agentId": "main", "workspaceDir": str(workspace),
            "eligible": ["markmap-viz", "drawio-diagram", "weather"],
            "missingRequirements": [{"name": "ue5-network-viz", "missing": {
                "bins": [], "anyBins": [], "env": ["UE5_MCP_URL"], "config": [], "os": []}}],
            "disabled": ["blender-3d-viz"], "blocked": [], "agentFiltered": []}


def test_report_names_each_unloadable_scoped_skill_and_why(tmp_path):
    (tmp_path / "skills" / "uml-diagram").mkdir(parents=True)
    (tmp_path / "skills" / "uml-diagram" / "SKILL.md").write_text("---\nname: uml-diagram\n---\n")
    report = mi.skill_report(SCOPE, _check(tmp_path))
    assert report == [
        {"name": "blender-3d-viz", "reason": "disabled", "missing": {}},
        # Not in this member's workspace at all.
        {"name": "isp-sla-claim", "reason": "not_installed", "missing": {}},
        {"name": "ue5-network-viz", "reason": "missing_requirements", "missing": {"env": ["UE5_MCP_URL"]}},
        # On disk but in no list: OpenClaw never loaded it (its per-source limit).
        {"name": "uml-diagram", "reason": "not_loaded", "missing": {}},
    ]
    # The base floor is served by the member daemon, not OpenClaw.
    assert "n2n-member-runtime" not in json.dumps(report) and "self-status" not in json.dumps(report)
    assert mi.skill_report(SCOPE, {"ok": False, "error": {}}) is None


def test_projection_keeps_names_only():
    out = mi.project_unavailable([
        {"name": "x", "reason": "missing_requirements", "missing": {"env": ["TOKEN", "bad value with spaces"], "values": {"TOKEN": "secret"}}},
        {"name": "y", "reason": "invented"},
        {"name": "bad name", "reason": "disabled"},
    ])
    assert out == [{"name": "x", "reason": "missing_requirements", "missing": {"env": ["TOKEN"]}}]
    card = mi.project_inventory({"mcp_servers": [], "unavailable_skills": [{"name": "x", "reason": "disabled"}]})
    assert card["unavailable_skills"] == [{"name": "x", "reason": "disabled", "missing": {}}]
    assert "unavailable_skills" not in mi.project_inventory({"mcp_servers": []})


@pytest.fixture
def border(manager):
    rm = RiskManager(manager, quarantine_threshold=5)
    rm.set_role("border", risk_name="risk", enabled_stacks="in2n", border_endpoint="10.0.0.1:1179")
    return rm


def _enroll(rm, name, skills, unavailable=None):
    scope = list(BASE_FLOOR) + [{"name": n, "type": "skill", "tier": "specialty"} for n in skills]
    cert, _ = RiskManager._generate_self_signed(name)
    rm.consume_token(rm.issue_token()["token"], name, cert, scope=scope)
    if unavailable is not None:
        rm.update_health(name, inventory=mi.project_inventory({"unavailable_skills": [
            {"name": n, "reason": "missing_requirements", "missing": {"env": ["PYATS_MCP_SCRIPT"]}} for n in unavailable]}))


def test_router_skips_a_member_that_cannot_load_the_skill(border):
    _enroll(border, "risk/narrow", ["pyats-network"], unavailable=["pyats-network"])
    _enroll(border, "risk/broad", ["pyats-network", "pyats-routing"])
    router = RiskRouter(border)
    # The narrower specialist would win on specificity; it cannot load the skill.
    assert router.select_member("pyats-network")["member_id"] == "risk/broad"


def test_no_loadable_member_says_so_without_naming_members_or_requirements(border):
    _enroll(border, "risk/pyats", ["pyats-network", "pyats-routing"], unavailable=["pyats-network"])
    router = RiskRouter(border)
    with pytest.raises(NoCapableMember) as e:
        router.select_member("pyats-network")
    message = str(e.value)
    assert "in scope, but no member's runtime can load it" in message
    assert "risk/pyats" not in message and "PYATS_MCP_SCRIPT" not in message
    assert router.specialty_capabilities() == {"pyats-routing"}
    assert router.route("pyats-routing")["member_id"] == "risk/pyats"


def test_member_without_a_report_routes_as_before(border):
    _enroll(border, "risk/pyats", ["pyats-network"])
    border.update_health("risk/pyats", inventory=mi.project_inventory({"mcp_servers": []}))
    assert RiskRouter(border).select_member("pyats-network")["member_id"] == "risk/pyats"


def test_peer_card_leaves_out_skills_no_member_can_load(tmp_path):
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="claw",
                            manager=FederationManager(base_dir=str(tmp_path / "border")))
    svc.inventory.skills_dir = tmp_path / "empty-skills"
    svc.risk.set_role("border", risk_name="risk", enabled_stacks="both")
    svc.risk.add_member("viz", profile=None, specialty=[{"name": "markmap-viz"}, {"name": "ue5-network-viz"}])
    svc.risk.add_member("viz2", profile=None, specialty=[{"name": "uml-diagram"}])
    report = [{"name": "ue5-network-viz", "reason": "missing_requirements", "missing": {"env": ["UE5_MCP_URL"]}},
              {"name": "uml-diagram", "reason": "not_loaded"}]
    asyncio.run(svc._in2n_on_member_inventory(SimpleNamespace(member_id="risk/viz"), {"unavailable_skills": report}))
    asyncio.run(svc._in2n_on_member_inventory(SimpleNamespace(member_id="risk/viz2"), {"unavailable_skills": []}))
    names = {s["name"] for s in svc.inventory.build("as65007-7.7.7.7")["skills"] if s.get("risk_aggregate")}
    assert "markmap-viz" in names and "uml-diagram" in names
    assert "ue5-network-viz" not in names
    svc.manager.close()


def _fake_openclaw(tmp_path, body):
    script = tmp_path / "openclaw"
    script.write_text("#!/usr/bin/env python3\nimport json, os, sys\n" + body)
    script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return script


def test_check_runs_locally_and_reports(tmp_path, monkeypatch):
    seen = tmp_path / "seen.json"
    script = _fake_openclaw(tmp_path, (
        f"json.dump({{'argv': sys.argv[1:], 'port': os.environ.get('OPENCLAW_GATEWAY_PORT'),"
        f" 'url': os.environ.get('OPENCLAW_GATEWAY_URL')}}, open({str(seen)!r}, 'w'))\n"
        f"print(json.dumps({json.dumps(_check(tmp_path))}))\n"))
    monkeypatch.setenv("N2N_MEMBER_AGENT", "main")
    env = {"PATH": os.environ["PATH"], "OPENCLAW_HOME": str(tmp_path), "OPENCLAW_GATEWAY_URL": "ws://border:18789"}
    monkeypatch.setenv("OPENCLAW_BIN", str(script))
    report = asyncio.run(mi.check_skills({"markmap-viz", "ue5-network-viz"}, env))
    assert report == [{"name": "ue5-network-viz", "reason": "missing_requirements", "missing": {"env": ["UE5_MCP_URL"]}}]
    call = json.loads(seen.read_text())
    assert call["argv"] == ["skills", "check", "--agent", "main", "--json"]
    # Never the Border's gateway: an unused local port, and no URL override.
    assert call["port"] and int(call["port"]) > 0 and call["url"] is None


def test_check_is_unknown_when_it_cannot_run(tmp_path, monkeypatch):
    failing = _fake_openclaw(tmp_path, "sys.exit(1)\n")
    monkeypatch.setenv("OPENCLAW_BIN", str(failing))
    env = {"PATH": os.environ["PATH"], "OPENCLAW_HOME": str(tmp_path)}
    assert asyncio.run(mi.check_skills({"markmap-viz"}, env)) is None
    assert asyncio.run(mi.check_skills(set(), env)) is None
    assert asyncio.run(mi.check_skills({"markmap-viz"}, {**env, "NETCLAW_RUNTIME": "hermes",
                                                          "HERMES_HOME": str(tmp_path)})) is None


def test_member_sends_the_report_only_on_its_current_border_channel(manager, monkeypatch):
    svc = FederationService(local_as=65001, router_id="1.1.1.1", manager=manager)
    svc.member_scope = {"markmap-viz"}
    report = [{"name": "markmap-viz", "reason": "disabled", "missing": {}}]

    async def fake_check(scope, env=None):
        return report
    monkeypatch.setattr(mi, "check_skills", fake_check)
    sent = []

    class Channel:
        async def call(self, method, params, timeout=None):
            sent.append((method, params))
    current, stale = Channel(), Channel()
    svc.border_channel = current
    asyncio.run(svc._report_skill_status(stale))
    assert sent == []
    asyncio.run(svc._report_skill_status(current))
    assert sent[0][0] == "n2n/inventory" and sent[0][1]["unavailable_skills"] == report
