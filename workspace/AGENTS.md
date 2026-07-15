# NetClaw Operating Instructions

## Memory System

NetClaw uses **Memory MCP** exclusively — a SQLite + ChromaDB hybrid that stores facts, decisions, and session summaries without consuming prompt context.

### How It Works
- Facts are stored in SQLite with temporal validity (auto-superseded when updated)
- Session summaries are embedded in ChromaDB for semantic recall
- Memory is queried on-demand via tool calls — it is NOT loaded into the system prompt

### Usage Pattern
- **Learn a fact** → `memory_record_fact entity="R1" key="os_version" value="17.9.4"`
- **Recall facts** → `memory_get_facts entity="R1"`
- **Record a decision** → `memory_record_decision context="..." decision="..." rationale="..."`
- **End of session** → `memory_store_session summary="..." entities="..." topics="..."`
- **Search past sessions** → `memory_recall query="that BGP flap last week"`
- **Check history** → `memory_timeline entity="R1"`
- **Invalidate stale** → `memory_invalidate fact_id="..." reason="..."`

### Rules
- Do NOT write memory files to disk. All memory goes through memory-mcp tools.
- Memory is queried only when needed — don't preload facts into your working context.
- For reference docs (skill details, protocol knowledge), read from `reference/` on demand.

## Safety Rules

1. **Never guess device state.** Run a show command first. Always.
2. **Never apply config without a baseline.** Capture pre-change state in GAIT.
3. **Never run destructive commands** — `write erase`, `erase`, `reload`, `delete`, `format` are refused.
4. **Always verify after changes.** Confirm the device reflects what was intended.
5. **Don't exfiltrate data.** Private network configs, credentials, and topology stay local.
6. **Ask before making changes** unless explicitly told to proceed.

## GAIT Audit Trail

```
Session start  → gait_branch "descriptive-name"
During work    → gait_record_turn (what was asked, found, changed)
Session end    → gait_log (display full trail for the human)
```

## Alert Handling

Alerts arrive via Grafana webhooks. When triggered:
1. Investigate autonomously using available MCP tools
2. Report findings concisely
3. Don't auto-remediate — wait for human confirmation
