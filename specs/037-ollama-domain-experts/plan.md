# Implementation Plan: Ollama Domain Expert Delegation MCP

**Branch**: `037-ollama-domain-experts` | **Date**: 2026-06-22 | **Spec**: specs/037-ollama-domain-experts/spec.md

## Summary

Build an MCP server that lets NetClaw's Frontier model (Claude) delegate domain-specific network engineering tasks to local Ollama models. The server routes requests to specialized models based on domain tags (OSPF, BGP, RFC-design) and includes a progressive learning path from system-prompt Modelfiles to full QLoRA fine-tuning.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: `mcp` (MCP SDK), `httpx` (async HTTP client for Ollama API), `pydantic` (request/response validation)

**Storage**: None (stateless MCP server, metrics held in-memory per session)

**Testing**: pytest + httpx mock for Ollama API

**Target Platform**: Linux (same as all NetClaw MCP servers)

**Project Type**: MCP server (stdio transport)

**Performance Goals**: <30s response for 7B model config generation, <120s for 35B models

**Constraints**: Must work with Ollama HTTP API (no custom protocols), must fit existing NetClaw MCP patterns

**Scale/Scope**: 3-5 domain expert models, single Ollama instance (multi-instance is future work)

## Project Structure

### Documentation (this feature)

```text
specs/037-ollama-domain-experts/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Fine-tuning research and approaches
├── data-model.md        # Request/response schemas
├── quickstart.md        # Getting started guide
├── tasks.md             # Implementation tasks
└── contracts/           # MCP tool schemas
```

### Source Code

```text
mcp-servers/ollama-experts/
├── server.py                    # MCP server entry point
├── router.py                    # Domain-based model routing logic
├── ollama_client.py             # Async Ollama HTTP API client
├── models.py                    # Pydantic models for requests/responses
├── metrics.py                   # Delegation tracking (tokens saved, latency)
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Optional containerized deployment
├── modelfiles/                  # Example Ollama Modelfiles
│   ├── Modelfile.ospf           # OSPF domain expert
│   ├── Modelfile.bgp            # BGP domain expert
│   ├── Modelfile.rfc-design     # RFC validation expert
│   └── Modelfile.frr-codegen    # General FRR config generation
├── training/                    # Fine-tuning resources
│   ├── README.md                # Fine-tuning guide (QLoRA → GGUF → Ollama)
│   ├── datasets/                # Example training data format
│   │   ├── ospf-examples.jsonl  # OSPF Q&A pairs
│   │   ├── bgp-examples.jsonl   # BGP Q&A pairs
│   │   └── rfc-examples.jsonl   # RFC validation pairs
│   └── scripts/                 # Training helper scripts
│       ├── prepare-dataset.py   # Convert raw data to training format
│       └── export-gguf.py       # Merge LoRA + export to GGUF
└── tests/
    ├── test_router.py
    ├── test_ollama_client.py
    └── test_server.py
```

### Kiro Integration

```text
.kiro/settings/mcp.json         # Add ollama-experts server config
```

## Training Pipeline Overview (Learning Path)

### Level 1: System Prompt Engineering (No Training Required)

Create Ollama Modelfiles with specialized system prompts. This is the fastest path to working domain experts and requires zero ML knowledge.

```
Base Model (e.g., deepseek-coder-v2:16b)
    + Domain System Prompt (RFC excerpts, FRR syntax rules, validation criteria)
    + Tuned Parameters (temperature=0.1 for config gen, 0.3 for design)
    = Named Ollama Model (e.g., netclaw-ospf:latest)
```

### Level 2: RAG-Augmented Prompts (No Training Required)

Stuff relevant RFC sections and reference configs into the prompt context dynamically. The MCP server selects context based on the domain and specific task.

### Level 3: QLoRA Fine-Tuning (Requires GPU + Training Time)

Full fine-tuning pipeline:
1. **Curate dataset** — Q&A pairs from RFCs, validated configs, troubleshooting scenarios
2. **Train with Unsloth/QLoRA** — 4-bit quantized training on single GPU (4-8 hours)
3. **Merge LoRA adapters** — Combine with base model
4. **Export to GGUF** — `llama.cpp` conversion for Ollama compatibility
5. **Import to Ollama** — `ollama create netclaw-ospf-ft -f Modelfile.ospf-finetuned`
6. **Benchmark** — Compare against Level 1 system-prompt-only model

## Constitution Check

No violations. Single MCP server, follows existing patterns exactly.
