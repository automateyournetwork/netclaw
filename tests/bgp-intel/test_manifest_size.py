"""Manifest token budget. Spec 081, FR-027a/b/c, SC-020a.

HARD CEILING: 5,000 tokens for the entire `tools/list` response.

This exists because the manifest is loaded into EVERY conversation whether or not
Fortinet is in play, so its cost is paid by every unrelated task. The clarification
that set the number rejected "don't make it too big" as untestable.

It is also why this server has ~21 parameterised tools instead of mirroring the
community servers, which ship 106 (FortiManager), 69 (FortiAnalyzer) and 204+
(FortiOS) — any one of which blows the budget several times over on its own.

Counting: the Anthropic SDK's `count_tokens` when available (the method feature
006 established), otherwise a conservative character-based estimate. The estimate
is deliberately pessimistic so a passing local run cannot be an optimistic one.

Runs with NO appliance.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "bgp-intel-mcp"))

CEILING = 5000


def count_tokens(text: str) -> tuple[int, str]:
    """Return (tokens, method). Prefers a real tokenizer; falls back pessimistically."""
    try:
        import anthropic  # type: ignore

        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", "x"))
        result = client.messages.count_tokens(
            model="claude-sonnet-5",
            messages=[{"role": "user", "content": text}],
        )
        return result.input_tokens, "anthropic.count_tokens"
    except Exception:  # noqa: BLE001 - offline/no key is normal in CI
        # ~3.4 chars/token for JSON with many short identifiers. Lower divisor =
        # higher estimate = fails sooner. Erring toward false alarm is correct
        # for a budget check.
        return int(len(text) / 3.4), "char-estimate (conservative)"


#: Verbs that would indicate a mutating tool. FR-034 — this feature queries public
#: registries and changes nothing, so there is no write path and no approval gate
#: to design. That is structurally true today only because no write code exists;
#: this keeps it true when someone later adds a tool.
_MUTATING_HINTS = (
    "create", "update", "delete", "remove", "set_", "add_", "modify",
    "install", "apply", "commit", "push", "write", "patch", "put_",
)


def check_read_only(tools) -> list[str]:
    """Return a list of problems. FR-034."""
    problems = []
    for t in tools:
        name = t.name.lower()
        for hint in _MUTATING_HINTS:
            if name.startswith(hint) or f"_{hint}" in name:
                problems.append(f"tool {t.name!r} looks mutating (matched {hint!r})")
        desc = (t.description or "").lower()
        # A read-only server should never describe itself as changing anything.
        for phrase in ("this will change", "modifies the", "writes to"):
            if phrase in desc:
                problems.append(f"tool {t.name!r} description implies mutation: {phrase!r}")
    return problems


async def build_manifest() -> tuple[str, int, list[str]]:
    import server

    tools = await server.mcp.list_tools()
    readonly_problems = check_read_only(tools)
    payload = [
        {
            "name": t.name,
            "description": t.description or "",
            "inputSchema": t.inputSchema,
        }
        for t in tools
    ]
    return json.dumps(payload, separators=(",", ":")), len(tools), readonly_problems


def main() -> int:
    manifest, tool_count, readonly_problems = asyncio.run(build_manifest())
    tokens, method = count_tokens(manifest)

    print("BGP-intel manifest budget (FR-027a)")
    print(f"  tools registered : {tool_count}")
    print(f"  serialised bytes : {len(manifest):,}")
    print(f"  measured tokens  : {tokens:,}   [{method}]")
    print(f"  ceiling          : {CEILING:,}")
    print(f"  headroom         : {CEILING - tokens:,}")
    print()
    print("  for scale, the community server this replaces:")
    print("    duksh/peerglass                42 tools (9 phases)")
    print("      (incl. DNS censorship, TLS/CT logs, satellite tracking —")
    print("       a charter far beyond R9; see research R1)")
    print()

    print("  read-only surface (FR-034):", "OK" if not readonly_problems else "FAIL")
    for p in readonly_problems:
        print(f"    - {p}")
    print()

    if readonly_problems:
        print("FAIL: this server must be read-only — it queries public registries and")
        print("changes nothing, so there is no write path and no approval gate (FR-034).")
        return 1

    if tokens > CEILING:
        print(f"FAIL: manifest exceeds the {CEILING:,}-token ceiling by {tokens - CEILING:,}.")
        print("Merge tools or fold parameters. The ceiling wins over the surface")
        print("(FR-026a) — a Fortinet integration that taxes every unrelated")
        print("conversation is a net loss.")
        return 1

    print(f"PASS: manifest is within budget ({tokens:,} <= {CEILING:,}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
