"""Shared harness for the zabbix-mcp suites. Spec 083.

Plain Python, stdlib only, following tests/bgp-intel/.

NOTE ON WHAT THESE TESTS CAN AND CANNOT PROVE. This feature adopts a third-party server
unmodified, so NetClaw authors no server code and there is no chokepoint to test. The
guarantees live in the skills. So the suites split:

  STATIC  — does NetClaw force read-only? is the deny-list real? does the skill contain a
            FOLLOWABLE PROCEDURE rather than a warning?
  LIVE    — does following that procedure produce the right answer from a real NMS?

Asserting on skill text alone would prove nothing about the answer a user receives. That
is the cost of the adopt-as-is decision, and the test strategy has to face it rather than
generate green ticks around it.
"""
from __future__ import annotations
import os, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FAILURES: list[str] = []

def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {name}")
    else:
        FAILURES.append(f"{name}: {detail}")
        print(f"  FAIL  {name} — {detail}")

def skip(name: str, why: str) -> None:
    print(f"  SKIP  {name} — {why}")

def run(tests, title: str) -> int:
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

def repo(*parts) -> str:
    return os.path.join(REPO, *parts)

def read(*parts) -> str:
    with open(repo(*parts), encoding="utf-8") as fh:
        return fh.read()

def zabbix_env() -> dict | None:
    """Live-test config, or None if no lab is configured."""
    url = os.environ.get("ZABBIX_URL")
    token = os.environ.get("ZABBIX_TOKEN")
    if not url or not token:
        return None
    return {"url": url, "token": token}
