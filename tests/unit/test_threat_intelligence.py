"""Provider contract and isolation regressions. No credentials or external requests."""
import concurrent.futures
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def greynoise():
    return load("community_lookup", "mcp-servers/greynoise-community-mcp/server.py")


@pytest.mark.parametrize("ip", ["::1", "2001:db8::1", "10.0.0.1", "224.0.0.1", "bad/IP", ""])
def test_unsupported_ip_is_never_submitted(greynoise, monkeypatch, ip):
    monkeypatch.setattr(greynoise.httpx, "get", lambda *a, **kw: pytest.fail("invalid IP left this host"))
    assert "error" in greynoise.greynoise_community_lookup(ip)


@pytest.mark.parametrize("key", ["", "fixture"])
def test_optional_authentication(greynoise, monkeypatch, key):
    monkeypatch.setenv("GREYNOISE_API_KEY", key)
    monkeypatch.delenv("GREYNOISE_TIMEOUT", raising=False)

    def get(url, *, headers, timeout):
        assert url == "https://api.greynoise.io/v3/community/8.8.8.8"
        assert headers.get("key", "") == key and timeout == 10
        return greynoise.httpx.Response(200, json={"ip": "8.8.8.8", "noise": True})

    monkeypatch.setattr(greynoise.httpx, "get", get)
    assert greynoise.greynoise_community_lookup("8.8.8.8")["noise"]


@pytest.mark.parametrize("code,payload,field", [(200, [], "error"), (200, None, "error"),
                                                (404, {}, "classification"), (429, {}, "error"),
                                                (503, {"message": "secret fixture"}, "error")])
def test_misses_and_failures(greynoise, monkeypatch, code, payload, field):
    monkeypatch.delenv("GREYNOISE_TIMEOUT", raising=False)
    monkeypatch.setattr(greynoise.httpx, "get", lambda *a, **kw: greynoise.httpx.Response(code, json=payload))
    response = greynoise.greynoise_community_lookup("8.8.8.8")
    assert field in response and "secret fixture" not in str(response)
    if code == 404:
        assert response[field] == "unknown"


def test_child_gets_only_its_provider_keys(tmp_path, monkeypatch):
    launch = load("component_launcher", "scripts/component-launch.py")
    env = {"HOME": str(tmp_path), "NETCLAW_RUNTIME_ENV": str(tmp_path / ".env"),
           "PATH": os.defpath, "GREYNOISE_API_KEY": "synthetic", "OTX_API_KEY": "unrelated"}
    entry = tmp_path / "server.py"
    entry.touch()
    rule = {"servers": ["test"], "script": "server.py", "command": "true",
            "environment_keys": ["GREYNOISE_API_KEY"]}
    monkeypatch.setitem(launch.CONTRACT, "test", rule)
    args, child, _ = launch.resolve("test", env=env, repo=tmp_path)
    assert args[0] == shutil.which("true", path=os.defpath)
    assert child["GREYNOISE_API_KEY"] == "synthetic"
    assert "OTX_API_KEY" not in child and "NETCLAW_RUNTIME_ENV" not in child


def test_threatintel_retry_and_concurrent_first_install(tmp_path, monkeypatch):
    installer = load("threatintel_installer", "scripts/setup-threatintel.py")
    repo = tmp_path / "upstream"
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    (repo / ".gitignore").write_text("dist/\nnode_modules/\n")
    subprocess.run(["git", "add", ".gitignore"], cwd=repo, check=True)
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=nobody@example.org",
                    "commit", "-qm", "fixture"], cwd=repo, check=True)
    monkeypatch.setattr(installer, "SOURCE", str(repo))
    monkeypatch.setattr(installer, "REVISION", subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip())
    root = tmp_path / "mcp"
    target = root / "mcp-threatintel"

    def fail(path):
        raise RuntimeError("build failed")

    monkeypatch.setattr(installer, "build", fail)
    with pytest.raises(RuntimeError, match="build failed"):
        installer.install(root)
    assert not target.exists()

    builds = []
    def build(path):
        builds.append(path)
        for rel in ("dist/index.js", "node_modules/@modelcontextprotocol/sdk/package.json"):
            artifact = path / rel
            artifact.parent.mkdir(parents=True)
            artifact.write_text("rebuilt")

    monkeypatch.setattr(installer, "build", build)
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        list(pool.map(installer.install, [root, root]))
    entry = target / "dist/index.js"
    assert len(builds) == 2 and entry.read_text() == "rebuilt"
    entry.write_text("tampered")
    (target / "node_modules/@modelcontextprotocol/sdk/package.json").write_text("")
    installer.install(root)
    assert entry.read_text() == "rebuilt"
    assert (target / "node_modules/@modelcontextprotocol/sdk/package.json").read_text() == "rebuilt"
    monkeypatch.setattr(installer, "build", fail)
    with pytest.raises(RuntimeError, match="build failed"):
        installer.install(root)
    assert entry.read_text() == "rebuilt"
    (target / ".gitignore").write_text("operator edit")
    with pytest.raises(ValueError, match="Preserve local edits"):
        installer.install(root)
