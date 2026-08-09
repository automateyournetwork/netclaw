"""Manifest token budget. Spec 080, FR-025/FR-026/FR-026a, SC-013.

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

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "mcp-servers", "fortinet-mcp"))

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


async def build_manifest() -> tuple[str, int]:
    import server

    tools = await server.mcp.list_tools()
    payload = [
        {
            "name": t.name,
            "description": t.description or "",
            "inputSchema": t.inputSchema,
        }
        for t in tools
    ]
    return json.dumps(payload, separators=(",", ":")), len(tools)


def main() -> int:
    manifest, tool_count = asyncio.run(build_manifest())
    tokens, method = count_tokens(manifest)

    print("Fortinet MCP manifest budget (FR-026)")
    print(f"  tools registered : {tool_count}")
    print(f"  serialised bytes : {len(manifest):,}")
    print(f"  measured tokens  : {tokens:,}   [{method}]")
    print(f"  ceiling          : {CEILING:,}")
    print(f"  headroom         : {CEILING - tokens:,}")
    print()
    print("  for scale, the community servers this replaces:")
    print("    rstierli/fortimanager-mcp    106 tools")
    print("    rstierli/fortianalyzer-mcp    69 tools")
    print("    paoloamato2/fortinet-mcp     204+ tools")
    print()

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
