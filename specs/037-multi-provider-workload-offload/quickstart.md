# Quickstart: Multi-Provider Workload Offload

## Prerequisites

- Python 3.11+ with httpx, pydantic installed
- At least one inference provider accessible (Ollama local, Ollama Cloud, or OpenAI-compatible)

## Minimal Setup (Ollama Local Only)

```bash
# In your .env:
PROVIDER_OLLAMA_LOCAL_URL=http://192.168.30.50:11434
ROUTE_DEFAULT_PROVIDER=ollama-local
ROUTE_OSPF_MODEL=qwen3.6:35b
ROUTE_BGP_MODEL=qwen3.6:35b
ROUTE_GRAPHQL_MODEL=qwen3.6:35b
```

## Multi-Provider Setup

```bash
# Providers
PROVIDER_OLLAMA_LOCAL_URL=http://192.168.30.50:11434
PROVIDER_OLLAMA_CLOUD_URL=https://ollama.com
PROVIDER_OLLAMA_CLOUD_API_KEY=your-key-here
PROVIDER_OPENAI_GROQ_URL=https://api.groq.com/openai
PROVIDER_OPENAI_GROQ_API_KEY=gsk_your-key

# Domain routing
ROUTE_DEFAULT_PROVIDER=ollama-local
ROUTE_OSPF_PROVIDER=ollama-local
ROUTE_OSPF_MODEL=qwen3.6:35b
ROUTE_GRAPHQL_PROVIDER=openai-groq
ROUTE_GRAPHQL_MODEL=llama-3.3-70b-versatile
ROUTE_COMPRESS_PROVIDER=ollama-local
ROUTE_COMPRESS_MODEL=qwen2.5-coder:7b

# Fallback
ROUTE_OSPF_FALLBACK=ollama-cloud
ROUTE_GRAPHQL_FALLBACK=ollama-local
```

## Verify

```bash
# Test MCP handshake
printf '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}\n{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n' | \
  PROVIDER_OLLAMA_LOCAL_URL=http://192.168.30.50:11434 \
  ROUTE_DEFAULT_PROVIDER=ollama-local \
  python3 -u server.py 2>/dev/null | python3 -c "
import sys, json
for line in sys.stdin:
    data = json.loads(line.strip())
    if data.get('id') == 2:
        print(f'Tools: {len(data[\"result\"][\"tools\"])}')
"
```

## Legacy Mode (Backward Compatible)

If you have existing `OLLAMA_*` vars and no `PROVIDER_*` vars, the server operates identically to before:

```bash
OLLAMA_BASE_URL=http://192.168.30.50:11434
OLLAMA_MODEL_OSPF=qwen3.6:35b
OLLAMA_MODEL_BGP=qwen3.6:35b
```
