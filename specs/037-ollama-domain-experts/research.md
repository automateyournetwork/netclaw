# Research: Ollama Domain Expert Delegation

## Fine-Tuning Approaches for Network Engineering LLMs

### Approach 1: Ollama Modelfile with System Prompts (Zero Training)

**How it works**: Ollama's `Modelfile` format lets you layer a custom system prompt and parameters on top of any base model. The result is a named model you can invoke like any other.

**Example** (OSPF expert):
```
FROM deepseek-coder-v2:16b

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 4096

SYSTEM """
You are a CCIE-certified OSPF expert. You generate FRRouting (FRR) configurations.

Rules:
- Output ONLY valid FRR vtysh configuration blocks
- Always include router-id
- Use interface-level OSPF configuration (ip ospf area X)
- Include passive-interface for loopbacks
- Include authentication when specified
- Reference RFC 2328 (OSPFv2) and RFC 5340 (OSPFv3) for correctness
- Never generate configurations that violate OSPF area design rules (split areas, virtual links without documentation)

FRR syntax reference:
- router ospf
- ospf router-id A.B.C.D
- network A.B.C.D/M area X
- interface <name>
-   ip ospf area <area-id>
-   ip ospf cost <1-65535>
-   ip ospf hello-interval <1-65535>
-   ip ospf dead-interval <1-65535>
"""
```

**Pros**: Zero training time, immediate results, easy to iterate on prompts.
**Cons**: Limited by base model's existing knowledge, system prompt consumes context window.
**Best for**: Getting started, rapid prototyping, models >14B that already know networking.

### Approach 2: QLoRA Fine-Tuning (4-8 hours on single GPU)

**How it works**: Quantized Low-Rank Adaptation trains a small adapter (1-5% of model parameters) while keeping the base model frozen in 4-bit precision. This makes fine-tuning possible on a single consumer GPU.

**Pipeline**:
1. **Prepare dataset** — JSONL format with instruction/input/output triplets
2. **Choose base model** — deepseek-coder-v2:16b, qwen2.5-coder:14b, or codellama:13b
3. **Train with Unsloth** — ~4 hours on RTX 3090/4090 for 1000 examples
4. **Merge adapters** — Combine LoRA weights with base model
5. **Convert to GGUF** — Using `llama.cpp`'s convert script
6. **Import to Ollama** — `ollama create model-name -f Modelfile`

**Training data sources for network engineering**:
- RFC text (IETF archives, public domain)
- FRRouting documentation and example configs
- Validated lab configs from ContainerLab/CML topologies
- Cisco IOS-XE/NX-OS config examples (documentation, not proprietary)
- NANOG/RIPE presentation slides (publicly available)
- Network engineering textbooks (fair use for training)

**Pros**: Significantly better domain accuracy, smaller/faster models can match larger general ones.
**Cons**: Requires GPU time, dataset curation is labor-intensive, risk of catastrophic forgetting.
**Best for**: Production use where accuracy matters, models <14B that need domain knowledge injected.

### Approach 3: RAG-Augmented Generation (No Training, Dynamic Context)

**How it works**: Instead of fine-tuning, dynamically inject relevant RFC sections, config examples, and validation rules into the prompt based on the specific task. The MCP server maintains a knowledge base and selects relevant chunks.

**Architecture**:
```
User request → Frontier model → MCP tool call with domain + task
    → MCP server selects relevant context (RFC chunks, examples)
    → Constructs prompt: system prompt + relevant context + user task
    → Sends to Ollama base model
    → Returns structured response
```

**Pros**: No training needed, always up-to-date (just update the knowledge base), transparent (you can see what context was used).
**Cons**: Uses more context window per request, slower for large knowledge bases, requires good chunking strategy.
**Best for**: RFC validation (where you need exact text), evolving standards, multi-RFC cross-references.

## Ollama API Reference

### Generate Endpoint
```
POST http://<host>:11434/api/generate
{
  "model": "netclaw-ospf",
  "prompt": "Generate OSPF config for...",
  "stream": false,
  "options": {
    "temperature": 0.1,
    "num_predict": 4096
  }
}
```

### Chat Endpoint (preferred for multi-turn)
```
POST http://<host>:11434/api/chat
{
  "model": "netclaw-bgp",
  "messages": [
    {"role": "system", "content": "You are a BGP expert..."},
    {"role": "user", "content": "Generate BGP config for..."}
  ],
  "stream": false,
  "options": {
    "temperature": 0.1
  }
}
```

### Model Management
```
GET  http://<host>:11434/api/tags          # List models
POST http://<host>:11434/api/show          # Model details
POST http://<host>:11434/api/pull          # Pull model
POST http://<host>:11434/api/create        # Create from Modelfile
```

## Recommended Base Models for Network Engineering

| Model | Size | Strengths | Best For |
|-------|------|-----------|----------|
| deepseek-coder-v2:16b | 16B | Strong code generation, good instruction following | Config generation, scripting |
| qwen2.5-coder:14b | 14B | Excellent structured output, fast inference | Structured config output |
| codellama:13b | 13B | Good code understanding, Llama base | Config analysis |
| mistral:7b | 7B | Fast, good general reasoning | Quick validation tasks |
| phi-3:14b | 14B | Efficient, good at following constraints | Constrained config generation |

## Existing Ollama MCP Implementations

Several community Ollama MCP servers exist that we can reference for patterns:

- **mcp-ollama** (PyPI) — Basic MCP server exposing Ollama chat/generate
- **ollama-cloud-mcp** (bryankthompson) — Multi-model research capabilities
- **mcts-mcp-server** (angrysky56) — Bayesian MCTS with Ollama for analysis

Our implementation differs by adding **domain routing** and **network engineering context injection** — features none of the existing implementations provide.

## Hardware Requirements

| Configuration | Models Supported | Concurrent Requests |
|--------------|-----------------|-------------------|
| RTX 3090 (24GB) | 1x 35B or 2x 14B | 1-2 |
| RTX 4090 (24GB) | 1x 35B or 2x 14B | 1-2 |
| 2x RTX 3090 | 1x 70B or 3x 14B | 2-3 |
| Mac M2 Ultra (192GB) | Multiple 70B | 3-4 |
| Cloud A100 (80GB) | 1x 70B + 2x 14B | 4-5 |

For the user's setup (192.168.30.50:11434), the available GPU memory determines which models can run simultaneously. Ollama handles model loading/unloading automatically but swapping is slow (~10-30s).
