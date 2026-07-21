"""Gateway openclaw resolution under a confined systemd PATH (nvm regression).

The mesh/member units (feature 057) run with a minimal Environment=PATH that
excludes the nvm bin where openclaw/node live, so bare `openclaw` was ENOENT and
every delegated agent turn (n2n chat / task) failed. gateway._openclaw_bin()
resolves it explicitly and _agent_env() puts its dir on the child PATH so the
`#!/usr/bin/env node` shebang resolves too.
"""

import os

import bgp.federation.gateway as gw


def test_env_override_wins(tmp_path, monkeypatch):
    fake = tmp_path / "openclaw"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setenv("OPENCLAW_BIN", str(fake))
    assert gw._openclaw_bin() == str(fake)


def test_falls_back_to_newest_nvm(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCLAW_BIN", raising=False)
    # no openclaw on PATH
    monkeypatch.setattr(gw.shutil, "which", lambda _: None)
    # fake ~/.nvm with two node versions, newest should win
    for v in ("v20.16.0", "v25.1.0"):
        d = tmp_path / ".nvm" / "versions" / "node" / v / "bin"
        d.mkdir(parents=True)
        (d / "openclaw").write_text("#!/usr/bin/env node\n")
    monkeypatch.setattr(os.path, "expanduser",
                        lambda p: p.replace("~", str(tmp_path)))
    got = gw._openclaw_bin()
    assert got.endswith("v25.1.0/bin/openclaw"), got


def test_agent_env_prepends_openclaw_dir(tmp_path, monkeypatch):
    fake = tmp_path / "nodebin" / "openclaw"
    fake.parent.mkdir()
    fake.write_text("#!/usr/bin/env node\n")
    monkeypatch.setenv("OPENCLAW_BIN", str(fake))
    monkeypatch.setenv("PATH", "/usr/bin:/bin")
    env = gw._agent_env()
    # the openclaw (and node) dir must be first so a confined PATH can still
    # launch it and resolve the node shebang
    assert env["PATH"].split(os.pathsep)[0] == str(fake.parent)
    assert "/usr/bin" in env["PATH"]
