# Reviewed subnet MCP source fixture

Exact upstream `servers/subnetcalculator_mcp.py` from
[GeminiCLI_SubnetCalculator_Extension](https://github.com/automateyournetwork/GeminiCLI_SubnetCalculator_Extension/tree/5178da6f83ebd894fa7331a62e1087ec9550751b),
commit `5178da6f83ebd894fa7331a62e1087ec9550751b`, Apache-2.0 (LICENSE included).
The source is unmodified, including its original whitespace; SHA256
`bfb8bb548aa7096c0b2324a3798c581ce917a26388aa6193ae66eb0708e7dd45`.

The R06 offline federation tests copy these bytes into a temporary source tree
and apply the existing hash-checked `subnet-calc` migration from
`config/fastmcp-external-patches.json`. They then execute that real FastMCP tool
through the selected component launcher. Model chat/skill behavior remains a
clearly labeled deterministic fixture. This snapshot does not install a component
or change any operator home. It removes dependence on an ignored vendor checkout
and requires no network access during the tests. Refresh only against an explicit
reviewed upstream/installer-manifest update; unexpected bytes must fail the patch
check. This exact-byte fixture is the sole source whitespace-check exclusion.
