# Quickstart — Zabbix NMS (spec 083 / R11)

Polled history: what an interface *was* doing, how long something has been down, whether this is normal.

## The lab is yours to run (not shipped)

Decided in clarification: NetClaw does not ship an NMS. Stand one up:

```bash
mkdir zlab && cd zlab && cat > compose.yaml <<'YAML'
services:
  zdb:
    image: postgres:16-alpine
    environment: {POSTGRES_USER: zabbix, POSTGRES_PASSWORD: changeme, POSTGRES_DB: zabbix}
    healthcheck: {test: ["CMD-SHELL","pg_isready -U zabbix"], interval: 5s, retries: 20}
  zserver:
    image: zabbix/zabbix-server-pgsql:alpine-7.0-latest
    environment: {DB_SERVER_HOST: zdb, POSTGRES_USER: zabbix, POSTGRES_PASSWORD: changeme, POSTGRES_DB: zabbix}
    depends_on: {zdb: {condition: service_healthy}}
    ports: ["10051:10051"]
  zweb:
    image: zabbix/zabbix-web-nginx-pgsql:alpine-7.0-latest
    environment: {ZBX_SERVER_HOST: zserver, DB_SERVER_HOST: zdb, POSTGRES_USER: zabbix,
                  POSTGRES_PASSWORD: changeme, POSTGRES_DB: zabbix, PHP_TZ: UTC}
    depends_on: [zserver]
    ports: ["8888:8080"]
YAML
docker compose up -d
```

Healthy in ~40s. **Port 8080 is often already taken** — this uses 8888. Default login `Admin` / `zabbix`;
change it. Then Users → API tokens → create one.

Add your devices as SNMP hosts and **let it poll for a few hours** before expecting trend data.

## Install

```bash
./scripts/install.sh          # select "zabbix"
```

It builds a **dedicated virtualenv**. That is not optional: this server needs fastmcp 3.x while five other
NetClaw servers pin `<3`, so a shared install would break them.

## Environment

```bash
ZABBIX_URL=http://localhost:8888
ZABBIX_TOKEN=                 # API token, not a password
READ_ONLY=true                # FORCED by NetClaw. The upstream launcher defaults it to false
VERIFY_SSL=true
ZABBIX_API_BLACKLIST=         # destructive-method deny-list, second layer
```

## The two traps — read this before trusting an empty answer

### 1. An empty result is usually the wrong question

`history.get` takes a value type and **defaults to unsigned (3)**. On a stock install **84 of 121 items are
float (0)**. Ask with the default and you get `[]` — **no error**, no warning, just nothing.

**Always call `item.get` first** and read the item's real `value_type`. Types **cannot be mixed** in one
call: a query across float and unsigned items returns only one kind, silently dropping the rest.

### 2. Empty also means "you looked in the wrong place"

Raw history is kept for ~31 days; hourly aggregates for a year or more. A 40-day question against raw
history returns nothing. `item.get` tells you both retentions — **read them and route**.

And retention can be **switched off**: `history=0` means raw values are never stored; `trends=0` means no
aggregates at all. Five items on a stock install have both. That is a *configuration fact*, not an absence.

### The five reasons you get nothing back

| | Means |
|---|---|
| wrong value type | your query was wrong — re-ask |
| aged out | beyond raw retention — use trends |
| retention disabled | this item does not keep that |
| never collected | monitored but never returned a value — **a real finding** |
| genuinely idle | zero. The only one that means nothing happened |

## Try it

> *"What did port1 on the FortiGate do overnight?"*
> *"What's broken right now, and how long has it been broken?"*
> *"Has netclaw-edge1 been flapping?"*
> *"What is Zabbix actually monitoring?"*

## Two limits, stated up front

**The guarantees are in the skill, not in the code.** This server is a generic passthrough — nothing
structurally prevents the two traps above. That is a deliberate trade (smallest surface, upstream
maintenance) and a first for NetClaw. Follow the skill.

**No per-call audit trail.** The adopted server has no audit concept and there is no platform-level MCP
audit. Acceptable only because this is strictly read-only — there is no operation to record.

## Boundaries

| Want to… | Use |
|---|---|
| Receive traps | `snmptrap-mcp` — that's push; this polls |
| Flow records | `ipfix-mcp` — flows, not counters |
| Metrics you instrumented | `prometheus`, `grafana` |
| SaaS monitoring | `auvik`, `thousandeyes`, `datadog` |
| **Current** device state | `pyats`, `multivendor-cli`, `fortinet` — this answers what it *was* |
| Change anything in Zabbix | nothing here. Read-only by design |
