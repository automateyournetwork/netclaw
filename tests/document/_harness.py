"""Shared harness for the document-mcp suites. Spec 082.

Plain Python, stdlib only, no pytest — following tests/bgp-intel/ and, before it,
tests/reconcile/ (spec 075). No new test framework in the shared environment.

Every suite here runs with NO network and NO credentials, because everything under test
is structural. But note what that does NOT buy: spec 080 had 24 passing appliance-free
tests while shipping a tool that returned three nulls, because its suites asserted on
the ENVELOPE and never on the CONTENT. This feature's entire output is content, so the
suites below reopen the generated files and assert on what is inside them.
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR = os.path.join(_HERE, "..", "..", "mcp-servers", "document-mcp")
sys.path.insert(0, os.path.abspath(SERVER_DIR))

FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")


def sandbox() -> str:
    """An isolated output dir + audit log for one suite."""
    d = tempfile.mkdtemp(prefix="document-mcp-test-")
    os.environ["DOCUMENT_OUTPUT_DIR"] = os.path.join(d, "out")
    os.environ["DOCUMENT_AUDIT_LOG"] = os.path.join(d, "gait.jsonl")
    os.makedirs(os.environ["DOCUMENT_OUTPUT_DIR"], exist_ok=True)
    return d


def cleanup(d: str) -> None:
    shutil.rmtree(d, ignore_errors=True)


def run(tests: list, title: str) -> int:
    for fn in tests:
        print(f"\n{fn.__name__}")
        fn()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILED")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print(f"all {title} tests passed")
    return 0


def abspath(artifact_path: str) -> str:
    """Artifacts report a repo-relative path when they land under the repo, and an
    absolute one otherwise (as they do in a sandbox)."""
    if os.path.isabs(artifact_path):
        return artifact_path
    return os.path.abspath(os.path.join(_HERE, "..", "..", artifact_path))
