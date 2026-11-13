#!/usr/bin/env python3
"""Install the pinned community threat intelligence server inside an MCP directory."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile

SOURCE = "https://github.com/aplaceforallmystuff/mcp-threatintel.git"
REVISION = "1f36c2d29877124bd60ac1fe4562b203e3fd3a14"


def install(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    target = root / "mcp-threatintel"
    with (root / ".mcp-threatintel.install.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if target.exists() or target.is_symlink():
            if target.is_symlink() or not (target / ".git").is_dir():
                raise ValueError(f"Unexpected source at {target}")
            head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=target, text=True).strip()
            dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=target)
            if head != REVISION or dirty:
                raise ValueError(f"Expected clean checkout at {REVISION}. Preserve local edits in {target} before retrying.")
            # Build from committed files. Ignored generated output, local npm
            # configuration, or an old dependency tree must not affect the build.
            with tempfile.TemporaryDirectory(prefix=".mcp-threatintel-", dir=root) as staging:
                fresh = Path(staging) / "source"
                subprocess.run(["git", "clone", "-q", "--no-local", "--no-checkout",
                                str(target), str(fresh)], check=True)
                subprocess.run(["git", "checkout", "-q", "--detach", REVISION], cwd=fresh, check=True)
                build(fresh)
                replace_build(fresh, target)
            return
        with tempfile.TemporaryDirectory(prefix=".mcp-threatintel-", dir=root) as staging:
            checkout = Path(staging) / "source"
            subprocess.run(["git", "init", "-q", str(checkout)], check=True)
            subprocess.run(["git", "remote", "add", "origin", SOURCE], cwd=checkout, check=True)
            subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", REVISION], cwd=checkout, check=True)
            subprocess.run(["git", "checkout", "-q", "--detach", REVISION], cwd=checkout, check=True)
            build(checkout)
            os.rename(checkout, target)


def replace_build(fresh: Path, target: Path) -> None:
    # The source checkout can contain operator-owned ignored files. Replace
    # only the two installer outputs, after the new build completes.
    moved = []
    installed = []
    try:
        for name in ("node_modules", "dist"):
            original = target / name
            backup = fresh.parent / ("previous-" + name)
            if original.exists() or original.is_symlink():
                os.rename(original, backup)
                moved.append((backup, original))
            os.rename(fresh / name, original)
            installed.append((original, fresh / name))
    except OSError:
        for current, new in reversed(installed):
            os.rename(current, new)
        for backup, original in reversed(moved):
            os.rename(backup, original)
        raise


def build(checkout: Path) -> None:
    subprocess.run(["npm", "ci", "--include=dev", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=checkout, check=True)
    subprocess.run(["npm", "run", "build"], cwd=checkout, check=True)
    if not (checkout / "dist/index.js").is_file():
        raise ValueError("Threat intelligence build did not produce dist/index.js")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mcp_directory", type=Path)
    try:
        install(parser.parse_args().mcp_directory)
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Threat intelligence installation failed: {exc}\n")
