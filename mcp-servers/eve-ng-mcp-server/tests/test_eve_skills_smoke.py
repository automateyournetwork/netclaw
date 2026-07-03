#!/usr/bin/env python3
"""Smoke test for NetClaw EVE-NG skill docs.

Checks:
- core EVE skill files exist
- documented tool names are implemented by the MCP server
- stale local/private references are absent
- the UNL validator script responds to --help
"""

from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace" / "skills"
SERVER_DIR = REPO_ROOT / "mcp-servers" / "eve-ng-mcp-server"
SERVER = SERVER_DIR / "eve_ng_mcp_server.py"
TOOL_MODULES = [
    SERVER_DIR / "tools_lab.py",
    SERVER_DIR / "tools_node.py",
    SERVER_DIR / "tools_network.py",
    SERVER_DIR / "tools_console_exec.py",
    SERVER_DIR / "tools_config.py",
]
VALIDATOR = WORKSPACE / "eve-lab-topology-design" / "scripts" / "validate_unl_topology.py"

SKILL_FILES = [
    WORKSPACE / "eve-ng-lab-management" / "SKILL.md",
    WORKSPACE / "eve-ng-lab-management" / "references" / "operational-guardrails.md",
    WORKSPACE / "eve-ng-lab-management" / "references" / "image-and-pagination.md",
    WORKSPACE / "eve-ng-node-operations" / "SKILL.md",
    WORKSPACE / "eve-ng-node-operations" / "references" / "node-guardrails.md",
    WORKSPACE / "eve-ng-node-operations" / "references" / "node-types.md",
    WORKSPACE / "eve-ng-config-ops" / "SKILL.md",
    WORKSPACE / "eve-ng-config-ops" / "references" / "config-guardrails.md",
    WORKSPACE / "eve-ng-console-ops" / "SKILL.md",
    WORKSPACE / "eve-ng-console-ops" / "references" / "console-guardrails.md",
    WORKSPACE / "eve-lab-topology-build" / "SKILL.md",
    WORKSPACE / "eve-lab-topology-build" / "references" / "wiring-guardrails.md",
    WORKSPACE / "eve-lab-topology-build" / "references" / "network-and-interface-reference.md",
    WORKSPACE / "eve-lab-topology-design" / "SKILL.md",
    WORKSPACE / "eve-lab-topology-design" / "references" / "discovery-workflow.md",
    WORKSPACE / "eve-lab-topology-design" / "references" / "validation-workflow.md",
    WORKSPACE / "eve-lab-topology-design" / "references" / "unl-validator.md",
    WORKSPACE / "eve-lab-topology-discovery" / "SKILL.md",
    WORKSPACE / "eve-lab-topology-discovery" / "references" / "question-bank.md",
    WORKSPACE / "eve-lab-topology-discovery" / "references" / "defaults-and-options.md",
    WORKSPACE / "eve-lab-topology-discovery" / "references" / "domain-and-image-guidance.md",
    WORKSPACE / "eve-lab-topology-validation" / "SKILL.md",
    WORKSPACE / "eve-lab-topology-validation" / "references" / "decision-gate.md",
    WORKSPACE / "eve-lab-topology-validation" / "references" / "output-structure.md",
    WORKSPACE / "eve-lab-topology-validation" / "references" / "checklists.md",
    WORKSPACE / "eve-lab-topology-validation" / "references" / "build-and-config-rules.md",
    VALIDATOR,
]

BANNED_STRINGS = [
    "/root/.openclaw/workspace",
    "ENSLD/",
    "eve_api_helper.py",
    "eve_console_helper.py",
    "eve_lab_helper.py",
    "eve-ng-topology-builder",
]

BANNED_SERVER_SNIPPETS = [
    'os.getenv("EVE_USER", "admin")',
    'os.getenv("EVE_PASSWORD", "eve")',
    'session.send("admin"',
]

TOOL_RE = re.compile(r"`(eve_[a-z0-9_]+)`")


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def parse_server_tools() -> set[str]:
    tools = set()
    for path in TOOL_MODULES:
        module = ast.parse(path.read_text())
        for node in module.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Call) and getattr(decorator.func, "attr", None) == "tool":
                    tools.add(node.name)
    return tools


def documented_tools(paths: list[Path]) -> set[str]:
    tools: set[str] = set()
    for path in paths:
        if path.suffix != ".md":
            continue
        tools.update(TOOL_RE.findall(path.read_text()))
    return tools


def main() -> int:
    missing = [str(path.relative_to(REPO_ROOT)) for path in SKILL_FILES if not path.exists()]
    if missing:
        fail(f"missing required files: {', '.join(missing)}")

    md_files = [path for path in SKILL_FILES if path.suffix == ".md"]
    for path in md_files:
        text = path.read_text()
        for banned in BANNED_STRINGS:
            if banned in text:
                fail(f"stale reference '{banned}' found in {path.relative_to(REPO_ROOT)}")

    server_tools = parse_server_tools()
    docs_tools = documented_tools(md_files)
    unknown = sorted(tool for tool in docs_tools if tool not in server_tools)
    if unknown:
        fail(f"documented tools missing from server: {', '.join(unknown)}")

    all_server_files = [SERVER] + TOOL_MODULES
    for src_file in all_server_files:
        src_text = src_file.read_text()
        for snippet in BANNED_SERVER_SNIPPETS:
            if snippet in src_text:
                fail(f"hardcoded credential pattern found in {src_file.name}: {snippet}")

    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        fail("validator script did not return success for --help")

    print("PASS: EVE skill smoke test")
    print(f"Validated {len(md_files)} documentation files and {len(server_tools)} MCP tools.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
