# Ollama MCP — Local LLM Domain Expert Delegation

An MCP server that lets your orchestrating AI model (Claude, GPT, Qwen, DeepSeek, etc.) delegate domain-specific tasks to local Ollama models running on your own GPU. Instead of one model doing everything, purpose-built specialists handle structured tasks while the orchestrator focuses on planning and user interaction.

## Why

Running AI agents with dozens of tools and complex multi-step workflows burns through cloud LLM tokens fast. Many of those tokens go to structured tasks that don't need frontier-level reasoning:

- Generating config from structured data (template-filling with rules)
- Parsing show command output (pattern matching)
- Building API queries (schema mapping)
- Validating configs against a source of truth (checklist evaluation)

These tasks are ideal for **small local models (7B) with baked-in system prompts**. The expertise lives in the prompt, not the model weights.

## Architecture

```
┌─────────────────────────────────────────┐
│ Orchestrating Model (Claude, etc.)      │
│ Plans, decides, interacts with user     │
└──────────┬──────────────────────────────┘
           │ MCP tool calls
           ▼
┌─────────────────────────────────────────┐
│ ollama-mcp (this server)                │
│ Routes by domain → local expert model   │
└──────────┬──────────────────────────────┘
           │ HTTP API
           ▼
┌─────────────────────────────────────────┐
│ Ollama Instance (local GPU)             │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐   │
│ │ ospf:7b │ │ bgp:7b  │ │ frr:7b  │   │
│ └─────────┘ └─────────┘ └─────────┘   │
│ Same base weights, different prompts    │
└─────────────────────────────────────────┘
```

All expert "models" share the same base weights (e.g., `qwen2.5-coder:7b`). Only their system prompts differ. Ollama deduplicates shared layers on disk.

## Tools Provided

| Tool | Purpose |
|------|---------|
| `ollama_generate_config` | Delegate config generation to a domain expert |
| `ollama_validate_design` | Validate a network design against RFCs |
| `ollama_domain_query` | Ask a domain expert a technical question |
| `ollama_validate_config_against_sot` | Validate config matches source-of-truth intent |
| `ollama_build_graphql_query` | Build GraphQL queries from natural language |
| `ollama_summarize_state` | Compress show command output to JSON digest |
| `ollama_compress_context` | Reduce large API responses to task-relevant JSON |
| `ollama_list_experts` | List configured experts and availability |
| `ollama_health_check` | Check Ollama connectivity |
| `ollama_delegation_stats` | Show token savings metrics |

## Quick Start

### 1. Install Ollama and pull a base model

```bash
# On your GPU machine
ollama pull qwen2.5-coder:7b
```

### 2. Create domain expert models

```bash
cd mcp-servers/ollama-mcp/modelfiles/

# Use the examples as starting points
cp Modelfile.example-ospf Modelfile.my-ospf
# Edit the system prompt for your topology/rules
ollama create my-ospf-expert:7b -f Modelfile.my-ospf
```

### 3. Configure environment

```bash
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_TIMEOUT=60
export OLLAMA_MODEL_OSPF=my-ospf-expert:7b
export OLLAMA_MODEL_BGP=my-bgp-expert:7b
export OLLAMA_MODEL_GENERAL=qwen2.5-coder:7b
export OLLAMA_MODEL_FALLBACK=qwen2.5-coder:7b
```

### 4. Run the MCP server

```bash
cd mcp-servers/ollama-mcp/
pip install -r requirements.txt
python server.py
```

### 5. Add to your OpenClaw/agent config

```json
{
  "ollama-mcp": {
    "command": "python3",
    "args": ["-u", "mcp-servers/ollama-mcp/server.py"],
    "env": {
      "OLLAMA_BASE_URL": "http://localhost:11434",
      "OLLAMA_TIMEOUT": "60",
      "OLLAMA_MODEL_OSPF": "my-ospf-expert:7b",
      "OLLAMA_MODEL_GENERAL": "qwen2.5-coder:7b",
      "OLLAMA_MODEL_FALLBACK": "qwen2.5-coder:7b"
    }
  }
}
```

## Creating Custom Domain Experts

The "expert" is just a base model + system prompt. No training required.

### Modelfile Structure

```
FROM qwen2.5-coder:7b           ← base model (any Ollama model)
PARAMETER temperature 0.1        ← low = deterministic output
PARAMETER num_predict 4096       ← max output tokens
SYSTEM """
Your domain-specific rules, examples, and output format here.
"""
```

### What Makes a Good Expert

1. **Narrow scope** — handle one specific task type well
2. **Explicit rules** — "NEVER do X", "ALWAYS do Y" with ❌ markers
3. **Worked examples** — complete input→output pairs
4. **Output format** — rigidly defined (JSON schema, config syntax)
5. **Low temperature** — 0.1 for structured output, 0.3 for explanations

### Adding a New Domain

1. Create `modelfiles/Modelfile.my-domain`
2. Run `ollama create my-domain-expert:7b -f Modelfile.my-domain`
3. Set `OLLAMA_MODEL_MY_DOMAIN=my-domain-expert:7b`
4. The router picks it up automatically — no code changes needed

### Model Size Guidance

| Size | Speed | When to Use |
|------|-------|-------------|
| 3B | ~80 tok/s | Too small for most tasks |
| 7B | ~42 tok/s | Structured config generation, parsing (recommended) |
| 14B | ~21 tok/s | Domain questions, complex reasoning |
| 32B | ~10 tok/s | Only if 7B quality is insufficient |

For structured output with good system prompts, 7B matches 32B quality.

## Token Savings Strategy

The biggest wins come from these patterns:

1. **Query building** — Local expert builds API queries instead of the orchestrator guessing
2. **Context compression** — Reduce 2KB API responses to 400B before the orchestrator reasons about them
3. **State summarization** — Pass/fail signals instead of raw output parsing
4. **Config generation** — The most token-intensive task, fully offloaded

Typical savings: 15-25K tokens per complex workflow run.

## File Layout

```
mcp-servers/ollama-mcp/
├── server.py              # MCP server (10 tools, stdio transport)
├── router.py              # Domain → model routing (env-var driven)
├── ollama_client.py       # Async Ollama HTTP client
├── models.py              # Pydantic request/response schemas
├── metrics.py             # Token savings tracker
├── requirements.txt       # Dependencies: mcp, httpx, pydantic
└── modelfiles/            # Example Ollama Modelfiles
    ├── Modelfile.example-ospf
    ├── Modelfile.example-state-summarizer
    └── Modelfile.example-graphql-builder
```

## Requirements

- Python 3.10+
- Ollama running somewhere accessible (local or remote)
- A base model pulled (e.g., `qwen2.5-coder:7b`)
- Dependencies: `mcp`, `httpx`, `pydantic`

## License

BSL-1.1 (same as parent project)
