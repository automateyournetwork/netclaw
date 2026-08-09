#!/usr/bin/env python3
"""anta-mcp — structured network-state validation for Arista EOS (spec 098 / roadmap R25).

The assertion layer. Everything else in NetClaw reads state; this one asserts on it and returns a
structured verdict.

FOUR TOOLS FOR 208 TESTS. ANTA ships 208 tests across 33 modules. One tool per test would cost
roughly 58,000 tokens -- 11.6x the 5,000-token ceiling, the same failure that forced spec 087 to
build a dispatcher over Catalyst Center's 515 tools. Discovery describes tests on demand instead.

READ-ONLY. ANTA tests; it does not configure. No configuration path exists in this server, and
tests/anta/run-tests.sh asserts the source contains none.

Runs from its own virtualenv: ANTA pulls cryptography 50.0.0, while the system interpreter holds
46.0.5 with four unbounded dependents including NetClaw's federation TLS stack (spec 060). Spec
076's cryptography incident is why that was measured before installing rather than after.
"""

from __future__ import annotations

import importlib
import inspect
import os
import pkgutil
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verdict as V  # noqa: E402

mcp = FastMCP("anta-mcp")

_CATALOGUE: dict[str, dict] = {}


def _load_catalogue() -> dict[str, dict]:
    """Enumerate ANTA's test classes once, at import. Never exposed as individual tools."""
    global _CATALOGUE
    if _CATALOGUE:
        return _CATALOGUE
    import anta.tests
    from anta.models import AntaTest

    found: dict[str, dict] = {}
    for mod_info in pkgutil.walk_packages(anta.tests.__path__, anta.tests.__name__ + "."):
        try:
            mod = importlib.import_module(mod_info.name)
        except Exception:  # noqa: BLE001 - a broken optional module must not kill discovery
            continue
        category = mod_info.name.replace("anta.tests.", "")
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, AntaTest) and obj is not AntaTest and obj.__module__ == mod_info.name:
                doc = (inspect.getdoc(obj) or "").strip().split("\n")[0]
                found[name] = {"name": name, "category": category, "description": doc, "cls": obj}
    _CATALOGUE = found
    return _CATALOGUE


def _input_schema(cls) -> dict | None:
    inp = getattr(cls, "Input", None)
    if inp is None or not hasattr(inp, "model_fields"):
        return None
    out = {}
    for fname, f in inp.model_fields.items():
        if fname in ("result_overwrite", "filters"):
            continue
        out[fname] = {
            "type": str(getattr(f, "annotation", "")),
            "required": f.is_required(),
            "description": (f.description or "")[:160],
        }
    return out or None


def _creds() -> tuple[str | None, str | None, str | None]:
    return (
        os.environ.get("ANTA_USERNAME"),
        os.environ.get("ANTA_PASSWORD"),
        os.environ.get("ANTA_ENABLE_PASSWORD"),
    )


@mcp.tool()
def anta_list_tests(category: str = "", keyword: str = "", limit: int = 40) -> dict:
    """Search ANTA's test catalogue. Contacts no device.

    Use this before running anything, to find which tests apply. `category` matches a module path
    such as 'routing.bgp', 'interfaces' or 'security'. `keyword` matches the test name or its
    description.
    """
    cat = _load_catalogue()
    items = []
    for e in cat.values():
        if category and not e["category"].startswith(category.lower()):
            continue
        if keyword and keyword.lower() not in (e["name"] + " " + e["description"]).lower():
            continue
        items.append({"name": e["name"], "category": e["category"], "description": e["description"]})
    items.sort(key=lambda x: (x["category"], x["name"]))
    truncated = len(items) > limit
    return {
        "total_in_catalogue": len(cat),
        "matched": len(items),
        "returned": min(len(items), limit),
        "truncated": truncated,
        "tests": items[:limit],
        "note": "no device was contacted" + (
            " - result truncated, narrow with category or keyword" if truncated else ""),
    }


@mcp.tool()
def anta_describe_test(test: str) -> dict:
    """Describe one test: what it checks and what inputs it needs. Contacts no device.

    Call this before anta_run_tests when a test needs inputs -- it reports what is required rather
    than letting a default be guessed.
    """
    cat = _load_catalogue()
    e = cat.get(test)
    if not e:
        near = [n for n in cat if test.lower() in n.lower()][:8]
        return {"error": f"unknown test {test!r}", "did_you_mean": near,
                "hint": "use anta_list_tests to search the catalogue"}
    return {
        "name": e["name"],
        "category": e["category"],
        "description": e["description"],
        "inputs": _input_schema(e["cls"]),
        "note": "no device was contacted",
    }


@mcp.tool()
async def anta_run_tests(
    host: str,
    tests: list[str] | None = None,
    category: str = "",
    inputs: dict | None = None,
    verify_tls: bool | None = None,
    port: int | None = None,
) -> dict:
    """Run selected ANTA tests against one EOS device and return structured verdicts.

    `host` is the device address (per call - there is no inventory). Credentials come from
    ANTA_USERNAME / ANTA_PASSWORD in the environment and are never accepted as arguments.

    Select tests either by name (`tests`) or by `category`. `inputs` maps a test name to its input
    dict - call anta_describe_test first to learn what a test requires.

    Verdicts are pass / fail / not_applicable / skipped / error, counted separately. A test whose
    feature is not configured is reported as not_applicable, NOT as a failure.
    """
    username, password, enable_pw = _creds()
    if not username or not password:
        return {"error": "ANTA_USERNAME and ANTA_PASSWORD must be set in the environment",
                "hint": "credentials are never passed as tool arguments"}

    if verify_tls is None:
        verify_tls = os.environ.get("ANTA_VERIFY_TLS", "false").lower() == "true"

    cat = _load_catalogue()
    selected = []
    if tests:
        for t in tests:
            if t in cat:
                selected.append(cat[t])
            else:
                return {"error": f"unknown test {t!r}",
                        "hint": "use anta_list_tests to find valid names"}
    elif category:
        selected = [e for e in cat.values() if e["category"].startswith(category.lower())]
    if not selected:
        return V.no_tests_selected(selector=(", ".join(tests) if tests else category) or "(none)")

    # `await`, never asyncio.run(): FastMCP already runs tools inside an event loop, and
    # asyncio.run() there raises "cannot be called from a running event loop". Caught by the
    # end-to-end MCP test, which is why that test speaks the protocol rather than calling
    # the function directly.
    return await _run(host, selected, inputs or {}, username, password, enable_pw,
                      verify_tls, port)


async def _run(host, selected, inputs, username, password, enable_pw, verify_tls, port) -> dict:
    from anta.device import AsyncEOSDevice

    dev = AsyncEOSDevice(
        host=host, username=username, password=password, name=host,
        enable_password=enable_pw, enable=bool(enable_pw),
        port=port, insecure=not verify_tls, disable_cache=True,
        timeout=float(os.environ.get("ANTA_TIMEOUT", "30")),
    )
    try:
        await dev.refresh()
    except Exception as e:  # noqa: BLE001
        return V.unreachable(host, f"{type(e).__name__}: {e}", tls_verified=verify_tls)
    if not dev.established:
        return V.unreachable(host, "device did not establish an eAPI session",
                             tls_verified=verify_tls)

    results = []
    for e in selected:
        entry = {"test": e["name"], "category": e["category"], "device": host}
        try:
            t = e["cls"](device=dev, inputs=inputs.get(e["name"]) or None)
            await t.test()
            r = t.result
            outcome, note = V.classify(str(r.result), list(r.messages or []))
            entry["verdict"] = outcome
            if r.messages:
                entry["messages"] = list(r.messages)
            if note:
                entry["note"] = note
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "input" in msg.lower() and ("required" in msg.lower() or "missing" in msg.lower()):
                entry["verdict"] = V.SKIPPED
                entry["note"] = "required inputs not supplied"
                entry["required_inputs"] = _input_schema(e["cls"])
            else:
                entry["verdict"] = V.ERROR
                entry["messages"] = [f"{type(exc).__name__}: {msg}"]
        results.append(entry)

    return V.envelope(host, results, tls_verified=verify_tls)


@mcp.tool()
def anta_status() -> dict:
    """Server health: ANTA version, catalogue size, and whether credentials are configured."""
    import importlib.metadata as md

    cat = _load_catalogue()
    username, password, _ = _creds()
    cats: dict[str, int] = {}
    for e in cat.values():
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    return {
        "anta_version": md.version("anta"),
        "catalogue_tests": len(cat),
        "catalogue_categories": len(cats),
        "largest_categories": dict(sorted(cats.items(), key=lambda x: -x[1])[:8]),
        "credentials_configured": bool(username and password),
        "verify_tls_default": os.environ.get("ANTA_VERIFY_TLS", "false"),
        "read_only": True,
        "note": "discovery tools contact no device; only anta_run_tests does",
    }


if __name__ == "__main__":
    mcp.run()
