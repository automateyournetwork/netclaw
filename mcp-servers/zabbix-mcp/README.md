# zabbix-mcp — SNMP-poller NMS coverage

**Spec 083 / roadmap R11.** 3 tools, stdio, **strictly read-only**. Manifest measured **589 / 5,000 tokens**.

The polled-history layer. Everything else NetClaw sees arrives *when something happens*; this is the only
source that answers **what was it doing** — is this normal, what did this interface do overnight, how long
has this been down.

## Adopted, not authored

See [NOTICE.md](./NOTICE.md). `mpeirone/zabbix-mcp-server`, pinned `0722f48`, **GPL-3.0**, vendored
unmodified, invoked over stdio as a separate program.

### Why adopt, with the numbers

Measured tool counts, by cloning and scanning — not read off READMEs:

| Candidate | Tools | Licence | State |
|---|---|---|---|
| **`mpeirone/zabbix-mcp-server`** ✅ | **3** (589 tokens) | GPL-3.0 | **adopted** |
| `mhajder/zabbix-mcp` | 53 | MIT | active |
| `mhajder/librenms-mcp` | 111 | MIT | busts the ceiling |
| `initMAX/zabbix-mcp-server` | 237 | AGPL-3.0 | active |
| 2 JavaScript servers | — | one has **no licence** | stale/abandoned |

**There is no official Zabbix LLC MCP server.** `mcpservers.org` labels initMAX "Official Zabbix MCP Server"
— **that label is wrong**; initMAX is a Zabbix Premium Partner, not Zabbix LLC. Zabbix's own AI direction is
WebMCP, a browser standard, not a server that can be adopted.

The 3-tool passthrough-plus-self-documentation design is essentially what NetClaw would have built. Adopting
it avoided rebuilding a solved problem.

## Why it runs in its own virtualenv

**Not optional.** It requires **fastmcp 3.x**; five NetClaw servers pin `fastmcp<3` —
`netbox-mcp-server`, `CiscoFMC-MCP-server-community`, `Wikipedia_MCP`, `rag-mcp`, `ISE_MCP`. A shared
install breaks all five. Same class of conflict that gave `multivendor-cli-mcp` its own venv (spec 076's
`cryptography` incident).

The venv is created with `netclaw_venv_create`/`uv` — **never bare `python3 -m venv`**, which fails on hosts
without `ensurepip` (measured on this one).

## Read-only, enforced twice

NetClaw **forces `READ_ONLY=true`** in `config/openclaw.json` rather than inheriting it, because the
upstream defaults disagree with each other:

```
src/zabbix_mcp_server/utils.py:29   READ_ONLY default True    ← the library
scripts/start_server.py:139         READ_ONLY default False   ← the shipped launcher
```

A **destructive-method deny-list** is the second layer, and it was verified to hold **with read-only
deliberately disabled**:

```
READ_ONLY=false  host.delete → REFUSED: Blacklist pattern '.*\.delete$' matched
READ_ONLY=false  host.get    → still allowed (the deny-list is not over-broad)
```

There is **no write path**. Adding one would require a NetClaw-owned layer carrying human approval, an
approved change record, *and* per-call audit — not a configuration flag.

## Two limitations, stated plainly

**1. The guarantees are in the skills, not in the code.** This is a generic passthrough with no chokepoint,
so the two silent-wrong-answer traps below are prevented by `zabbix-metrics-history`'s procedure and nothing
else. **This is the first NetClaw integration where a core distinction is enforced by guidance rather than
structure** — a deliberate trade for the smallest surface and upstream maintenance.

**2. No per-call GAIT audit.** The upstream has no audit concept, and there is no platform-level MCP audit.
Acceptable only because this is strictly read-only: there is no operation to record.

## The two traps

Both measured against live Zabbix 7.0.29. Both return an empty array **and a success status**.

1. **`history.get` defaults its value type to unsigned (3); 84 of 121 stock items are float (0).** Call
   `item.get` first, pass the real `value_type`. Types cannot be mixed in one call.
2. **Raw history ages out into hourly trends.** Read per-item `history`/`trends` and route. Retention can
   also be *disabled* (`history=0`, `trends=0`) — a configuration fact, not an absence.

## Skills

`zabbix-metrics-history` (the procedure lives here) · `zabbix-problem-review` · `zabbix-availability`

## Tests

```bash
bash tests/zabbix/run-tests.sh                        # static only
ZABBIX_URL=... ZABBIX_TOKEN=... bash tests/zabbix/run-tests.sh   # + live traps
```

Static tests prove the skill *says* the right thing. Only the live suite proves following it gives the right
*answer* — which after adopt-as-is is the only claim that matters.
