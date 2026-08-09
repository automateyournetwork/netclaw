"""Manifest size and the read-only surface guard. Spec 082, FR-033/038a, SC-025.

The guard's predicate matters. "No tool name implies a write" would be wrong here —
four of the six tools DO write, to files, which is the entire point of the feature. What
this server must never do is touch infrastructure: no device target, no credential, no
ticket identifier as a parameter, and no description claiming to change device or ticket
state.

`/speckit.analyze` caught the vague version of this before it was written. The guard is
also proven non-vacuous below by feeding it a deliberately bad tool.
"""

from __future__ import annotations

import asyncio
import inspect
import re

from _harness import FAILURES, check, run  # noqa: F401

import server  # noqa: E402

CEILING = 5000

# Parameters that would mean this server talks to infrastructure.
FORBIDDEN_PARAMS = re.compile(
    r"(?i)\b(device_host|hostname|device_ip|ip_address|mgmt_ip|host|target_device|"
    r"credential|password|token|api_key|secret|username|"
    r"ticket_id|change_id|incident_id|sys_id|cr_number)\b"
)

# Claims a description must not make.
FORBIDDEN_CLAIMS = re.compile(
    r"(?i)(push (?:the )?config|apply (?:the )?config|configure the device|"
    r"reboot|deploy to|write to the device|create a ticket|update the ticket|"
    r"close the change|open a change)"
)


def _tools():
    return asyncio.run(server.mcp.list_tools())


def _manifest_text() -> str:
    parts = []
    for tool in _tools():
        parts.append(tool.name)
        parts.append(tool.description or "")
        parts.append(str(tool.inputSchema))
    return "\n".join(parts)


def _estimate_tokens(text: str) -> int:
    """~4 characters per token, the same conservative estimate specs 080 and 081 used.
    Deliberately pessimistic: overestimating keeps us under the real ceiling."""
    return len(text) // 4 + text.count("\n")


def test_manifest_is_under_the_ceiling():
    text = _manifest_text()
    tokens = _estimate_tokens(text)
    print(f"  measured manifest: {tokens} / {CEILING} tokens ({len(text)} chars)")
    check(f"manifest is <= {CEILING} tokens", tokens <= CEILING, f"measured {tokens}")
    check("the tool count is what the contract says", len(_tools()) == 6, str(len(_tools())))


def test_no_tool_accepts_an_infrastructure_parameter():
    for tool in _tools():
        props = list((tool.inputSchema or {}).get("properties", {}).keys())
        bad = [p for p in props if FORBIDDEN_PARAMS.search(p)]
        check(
            f"{tool.name} accepts no device/credential/ticket parameter",
            not bad,
            f"parameters {bad} would mean this server talks to infrastructure",
        )


def test_no_description_claims_an_infrastructure_change():
    for tool in _tools():
        desc = tool.description or ""
        match = FORBIDDEN_CLAIMS.search(desc)
        check(
            f"{tool.name} claims no infrastructure change",
            match is None,
            f"description contains {match.group(0)!r}" if match else "",
        )


def test_the_guard_is_not_vacuous():
    """Feed the predicate a deliberately bad tool. If it passes, the guard is theatre."""
    fake_params = ["path", "device_host", "values"]
    caught = [p for p in fake_params if FORBIDDEN_PARAMS.search(p)]
    check("the parameter guard rejects a device_host parameter", caught == ["device_host"], str(caught))

    fake_desc = "Fill a form and then push the config to the device."
    check("the description guard rejects an infrastructure claim",
          FORBIDDEN_CLAIMS.search(fake_desc) is not None,
          "the guard would have passed a tool that claims to configure a device")

    check("the ceiling check rejects an oversized manifest", _estimate_tokens("x" * 40_000) > CEILING)


def test_every_tool_routes_through_the_chokepoint():
    """FR-005a/005b. There is exactly one way out of this server."""
    src = inspect.getsource(server)
    tool_bodies = src.split("@mcp.tool()")[1:]
    check("six tools are defined", len(tool_bodies) == 6, str(len(tool_bodies)))
    for body in tool_bodies:
        name = body.split("async def ", 1)[1].split("(", 1)[0]
        routed = ("envelope.emit" in body) or ("_write(" in body)
        check(f"{name} returns through the chokepoint", routed,
              "a tool returns without emit() — provenance and GAIT would be skipped")

    for module_name in ("writers.docx_writer", "writers.xlsx_writer",
                        "writers.pptx_writer", "writers.pdf_writer"):
        mod = __import__(module_name, fromlist=["x"])
        msrc = inspect.getsource(mod)
        check(f"{module_name} does not audit directly",
              "envelope" not in msrc,
              "a writer bypassing the chokepoint could ship an unaudited document")


TESTS = [
    test_manifest_is_under_the_ceiling,
    test_no_tool_accepts_an_infrastructure_parameter,
    test_no_description_claims_an_infrastructure_change,
    test_the_guard_is_not_vacuous,
    test_every_tool_routes_through_the_chokepoint,
]

if __name__ == "__main__":
    raise SystemExit(run(TESTS, "manifest and surface"))
