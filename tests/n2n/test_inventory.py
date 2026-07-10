"""T022: inventory build, visibility filtering, no-secrets invariant (FR-006/007, SC-004)."""

import json

import pytest

from bgp.federation.inventory import InventoryBuilder, _derive_badges


def _fixture_repo(tmp_path, secret=None):
    """Build a minimal repo tree: config/openclaw.json + workspace/skills + .env."""
    (tmp_path / "config").mkdir()
    (tmp_path / "config" / "openclaw.json").write_text(json.dumps({
        "mcpServers": {
            "cml-mcp": {"tools": ["list_labs", "start_lab"]},
            "meraki-mcp": {"tools": ["get_orgs"]},
        }
    }))
    skills = tmp_path / "workspace" / "skills"
    skills.mkdir(parents=True)
    for name, desc in [("cml-lab-lifecycle", "Manage CML lab lifecycle."),
                       ("secret-skill", secret or "A harmless skill.")]:
        d = skills / name
        d.mkdir()
        (d / "SKILL.md").write_text(f"# {name}\n\n{desc}\n")
    env = tmp_path / ".env"
    env.write_text("CML_PASSWORD=SuperSecret123\n" if secret is None else f"CML_PASSWORD={secret}\n")
    return tmp_path, str(env)


def test_badge_derivation():
    assert "CML" in _derive_badges(["cml-mcp"])
    assert "Meraki" in _derive_badges(["meraki-mcp"])
    assert _derive_badges(["random-mcp"]) == []


def test_build_includes_skills_and_badges(manager, tmp_path):
    repo, env = _fixture_repo(tmp_path)
    b = InventoryBuilder(manager, repo_root=str(repo),
                         openclaw_config=str(repo / "config" / "openclaw.json"), env_path=env)
    inv = b.build("as65007-7.7.7.7")
    skill_names = {s["name"] for s in inv["skills"]}
    assert "cml-lab-lifecycle" in skill_names          # skills advertised by default
    assert inv["mcp_servers"] == []                    # MCP servers hidden by default
    # Skills carry no badges (badges derive from advertised servers); make a server visible:
    manager._conn.execute("INSERT INTO visibility_setting VALUES ('mcp_server','cml-mcp','all_federated',NULL)")
    manager._conn.commit()
    inv2 = b.build("as65007-7.7.7.7")
    assert any(s["name"] == "cml-mcp" for s in inv2["mcp_servers"])
    assert "CML" in inv2["badges"]


def test_hidden_item_absent_from_payload(manager, tmp_path):
    repo, env = _fixture_repo(tmp_path)
    manager._conn.execute("INSERT INTO visibility_setting VALUES ('skill','secret-skill','hidden',NULL)")
    manager._conn.commit()
    b = InventoryBuilder(manager, repo_root=str(repo),
                         openclaw_config=str(repo / "config" / "openclaw.json"), env_path=env)
    inv = b.build("as65007-7.7.7.7")
    names = {s["name"] for s in inv["skills"]}
    assert "secret-skill" not in names                 # absent, not masked
    assert "secret-skill" not in json.dumps(inv)


def test_no_secrets_guard_blocks_advertisement(manager, tmp_path):
    # Plant the .env secret verbatim into a skill description
    repo, env = _fixture_repo(tmp_path, secret="LeakedPassw0rd!!")
    b = InventoryBuilder(manager, repo_root=str(repo),
                         openclaw_config=str(repo / "config" / "openclaw.json"), env_path=env)
    with pytest.raises(ValueError, match="secret"):
        b.build("as65007-7.7.7.7")


def test_remote_cache_and_staleness(manager):
    b = InventoryBuilder(manager)
    ident = "as65007-7.7.7.7"
    b.cache_remote(ident, {"version": 3, "skills": [], "mcp_servers": [], "badges": ["CML"]})
    got = b.load_remote(ident, refresh_s=21600)
    assert got["inventory"]["version"] == 3
    assert got["stale"] is False
    assert got["received_at"]
