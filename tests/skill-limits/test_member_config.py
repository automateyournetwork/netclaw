import importlib.util
import json
import sys
from pathlib import Path

import skill_limits as sl
from conftest import ROOT

sys.path.insert(0, str(ROOT / "mcp-servers/protocol-mcp"))
spec = importlib.util.spec_from_file_location("imh188", ROOT / "scripts/in2n-member-home.py")
imh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imh)


def test_spec_member_skills_section_has_limits_without_merging_border():
    section = imh.spec_skills_section({"limits": {"maxSkillsLoadedPerSource": 5}, "entries": {}}, ["a"])
    assert section["limits"] == sl.policy_limits()
    assert section["workshop"] == {"autonomous": {"mode": "off"}}


def test_spec_member_skills_section_with_no_border_skills():
    assert imh.spec_skills_section(None, [])["limits"] == sl.policy_limits()


def test_profile_member_path_raises_limits_on_inherited_border_config():
    # Profile members deep-copy the Border config; the provisioning code raises limits on
    # that copy so a Border that predates spec 188 still yields a covered member.
    source = (ROOT / "scripts/in2n-member-home.py").read_text()
    assert "skill_limits.raise_limits(m," in source
    border = {"skills": {"limits": {"maxSkillsLoadedPerSource": 150}}}
    sl.raise_limits(border)
    assert border["skills"]["limits"]["maxSkillsLoadedPerSource"] == sl.policy_limits()["maxSkillsLoadedPerSource"]
