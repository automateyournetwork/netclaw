# Quickstart: Ollama Domain Expert Delegation

Get domain-specific local models working with NetClaw in under 5 minutes.

## Prerequisites

- Ollama running on your AI host (`http://192.168.30.50:11434`) ✅ Already confirmed
- Python 3.11+ with the netclaw venv

## Available Models on Your Host

Your Ollama instance already has excellent base models for domain experts:

| Model | Size | Best For |
|-------|------|----------|
| `qwen2.5-coder:32b-instruct-q8_0` | 32.8B Q8 | Config generation (highest accuracy) |
| `qwen2.5-coder:32b-instruct-q6_K` | 32.8B Q6 | Config generation (faster, still great) |
| `codestral:latest` | 22.2B Q4 | Fast code/config generation |
| `qwen3:32b` | 32.8B Q4 | General domain queries with thinking |
| `qwen3.5:35b` | 36.0B Q4 | Vision + thinking + tools |
| `qwen3-coder-next:latest` | 79.7B Q4 | Maximum quality (slower) |

**Recommended base for Modelfiles**: `qwen2.5-coder:32b-instruct-q8_0` — it's strong on structured output, follows instructions precisely, and you have the Q8 quantization for maximum accuracy.

## Step 1: Create Domain Expert Models

On your Ollama host (192.168.30.50):

```bash
# Copy modelfiles to the Ollama host or create them there
cd /path/to/netclaw-demo/mcp-servers/ollama-experts/modelfiles/

# Create domain experts from qwen2.5-coder base
ollama create netclaw-ospf -f Modelfile.ospf
ollama create netclaw-bgp -f Modelfile.bgp
ollama create netclaw-rfc-design -f Modelfile.rfc-design
ollama create netclaw-frr-codegen -f Modelfile.frr-codegen
```

**Note**: The default Modelfiles use `deepseek-coder-v2:16b` as the base. Since you have `qwen2.5-coder:32b-instruct-q8_0`, edit the `FROM` line in each Modelfile to use it instead for better results:

```
FROM qwen2.5-coder:32b-instruct-q8_0
```

## Step 2: Install MCP Server Dependencies

```bash
cd /home/ubuntu/netclaw-demo/mcp-servers/ollama-experts/
pip install -r requirements.txt
```

## Step 3: Configure Environment

Add to your `.env` or export:

```bash
export OLLAMA_BASE_URL=http://192.168.30.50:11434
export OLLAMA_TIMEOUT=120
export OLLAMA_MODEL_OSPF=netclaw-ospf:latest
export OLLAMA_MODEL_BGP=netclaw-bgp:latest
export OLLAMA_MODEL_RFC=netclaw-rfc-design:latest
export OLLAMA_MODEL_GENERAL=netclaw-frr-codegen:latest
export OLLAMA_MODEL_FALLBACK=qwen2.5-coder:32b-instruct-q8_0
```

## Step 4: Test the MCP Server Directly

```bash
# Health check
OLLAMA_BASE_URL=http://192.168.30.50:11434 \
  python3 -c "
import asyncio
from ollama_client import OllamaClient
async def test():
    c = OllamaClient('http://192.168.30.50:11434')
    print('Reachable:', await c.is_reachable())
    print('Models:', await c.list_models())
asyncio.run(test())
"
```

## Step 5: Add to NetClaw Config

Add to `config/openclaw.json` (or `openclaw-demo.json`) under `mcpServers`:

```json
"ollama-experts": {
  "command": "python3",
  "args": ["-u", "mcp-servers/ollama-experts/server.py"],
  "env": {
    "OLLAMA_BASE_URL": "${OLLAMA_BASE_URL:-http://192.168.30.50:11434}",
    "OLLAMA_TIMEOUT": "${OLLAMA_TIMEOUT:-120}",
    "OLLAMA_MODEL_OSPF": "${OLLAMA_MODEL_OSPF:-netclaw-ospf:latest}",
    "OLLAMA_MODEL_BGP": "${OLLAMA_MODEL_BGP:-netclaw-bgp:latest}",
    "OLLAMA_MODEL_RFC": "${OLLAMA_MODEL_RFC:-netclaw-rfc-design:latest}",
    "OLLAMA_MODEL_GENERAL": "${OLLAMA_MODEL_GENERAL:-qwen2.5-coder:32b-instruct-q8_0}",
    "OLLAMA_MODEL_FALLBACK": "${OLLAMA_MODEL_FALLBACK:-qwen2.5-coder:32b-instruct-q8_0}"
  }
}
```

## Step 6: Use It

Ask NetClaw:
- "Generate OSPF config for router P1" → Routes to OSPF expert
- "Validate this BGP design against RFC 4271" → Routes to RFC expert
- "What's the BGP path selection order?" → Routes to BGP expert
- "Show delegation stats" → See tokens saved

---

## For Kiro IDE

The Ollama MCP is already configured in your Kiro (`~/.kiro/settings/mcp.json`) pointing to `192.168.30.50:11434`. To add the **domain expert** MCP alongside it, add this entry:

```json
"ollama-experts": {
  "command": "python3",
  "args": ["-u", "/home/ubuntu/netclaw-demo/mcp-servers/ollama-experts/server.py"],
  "env": {
    "OLLAMA_BASE_URL": "http://192.168.30.50:11434",
    "OLLAMA_MODEL_OSPF": "netclaw-ospf:latest",
    "OLLAMA_MODEL_BGP": "netclaw-bgp:latest",
    "OLLAMA_MODEL_RFC": "netclaw-rfc-design:latest",
    "OLLAMA_MODEL_GENERAL": "qwen2.5-coder:32b-instruct-q8_0",
    "OLLAMA_MODEL_FALLBACK": "qwen2.5-coder:32b-instruct-q8_0"
  }
}
```

This gives you two complementary Ollama integrations in Kiro:
1. **`ollama`** — Raw access to chat/generate with any model (general purpose)
2. **`ollama-experts`** — Domain-routed network engineering delegation with structured responses

---

## Quick Test with Existing Ollama MCP in Kiro

Even before building the domain expert models, you can test the concept right now using the existing Ollama MCP. Try asking me to delegate a question to your local models:

```
Use ollama_chat to ask qwen2.5-coder:32b-instruct-q8_0 to generate an FRR OSPF config for router P1
```

This proves the Frontier-to-local delegation pattern works. The `ollama-experts` MCP just adds routing, structured prompts, and metrics on top.
