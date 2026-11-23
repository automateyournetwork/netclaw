# Genie worlds — local backend and scoped MCP

Google Genie4 provides generated media through its official API; Cisco pyATS
Genie provides frozen measured evidence. The package includes a private loopback
viewer, snapshot inspector, five scene styles, durable session/campaign ledgers,
a worker, six stdio controls and the workflow skill. Actual Mac recordings are
retained; strict fidelity and existing-Risk execution remain separate gates.

Install the optional `genie-worlds` component through terminal or source-backed
VS Code setup. See [complete setup guide](../../docs/GENIE-WORLDS.md). Node24.19.x
or26.1+ and isolated Python3.12/MCP2.3.0 are required.

`node scripts/genie-worlds/cli.mjs serve` starts only the clearly labeled offline
fixture. Set `NETCLAW_GENIE_STATE_DIR` to the selected private state root. The
manager creates `mcp-control.json`; only this control capability belongs to the
member. `live-serve /absolute/private/packet.json` requires an exact current
operator review and launch pins. Credentials remain backend-owned.

`status <original-request-id>`, `evidence <id>` and `stop <id>` inspect the same
local operation. Unknown outcomes retain reservations. Confirmed remote terminal
with missing usage retains the full bound; it is not billed-spend reconciliation.
A source change invalidates old paid packets. Never replay production evidence.

Run Node tests with `node --test --test-concurrency=1 tests/genie-worlds/*.test.mjs`,
setting `NETCLAW_BROWSER_EXECUTABLE` and `NETCLAW_MCP_PYTHON` for actual browser/MCP
checks. Python tests use the isolated SDK interpreter with `unittest discover -s
tests/genie-worlds -p '*_test.py'`. Tests do not call Google. Historical32/50pass
runner scripts are retained evidence tools, not enabled background automation.
