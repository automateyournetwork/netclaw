---
name: domain-expert-delegation
description: "Offload structured workloads (config generation, design validation, GraphQL building, state summarization, context compression) to local or cloud LLM providers via the ollama-mcp server. Saves tokens on the orchestrating model by delegating domain-specific tasks."
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["PROVIDER_OLLAMA_LOCAL_URL"] } } }
---

# Domain Expert Delegation

Offload structured, token-intensive workloads to dedicated LLM providers instead of consuming the orchestrating model's context window.

## When to Use

- Generating device configurations (OSPF, BGP, ACL, MPLS)
- Building GraphQL queries for Nautobot
- Validating network designs against RFCs
- Summarizing large `show` command outputs into structured JSON
- Compressing verbose API responses before analysis
- Any task where structured input → structured output and doesn't need full agent reasoning

## MCP Server

`ollama-mcp` (10 tools)

## Tools

| Tool | Purpose | When |
|------|---------|------|
| `ollama_generate_config` | Generate device config from structured context | Need IOS/EOS/FRR config for a protocol |
| `ollama_validate_design` | Validate a design against RFC standards | Before pushing config changes |
| `ollama_domain_query` | Ask a domain expert a technical question | Need protocol-specific knowledge |
| `ollama_validate_config_against_sot` | Compare generated config against Nautobot SoT | Verify config matches intended state |
| `ollama_build_graphql_query` | Build a Nautobot/NetBox GraphQL query from intent | Need to query SoT but don't know the schema |
| `ollama_summarize_state` | Compress show command output to structured JSON | Processing large device output |
| `ollama_compress_context` | Reduce API response to task-relevant minimum | Large Nautobot/Grafana responses |
| `ollama_list_experts` | Show configured domain experts and providers | Check what's available |
| `ollama_health_check` | Verify provider connectivity and models | Troubleshooting delegation failures |
| `ollama_delegation_stats` | View metrics (tokens saved, latency, cost) | Evaluate offload efficiency |

## Workflow: Config Generation

1. Gather device context from Nautobot (`nautobot_get_devices`, `nautobot_get_interfaces`)
2. Call `ollama_generate_config` with domain, task description, device context, and constraints
3. Review generated config
4. Optionally validate with `ollama_validate_design`
5. Apply via pyATS or golden config pipeline

## Workflow: GraphQL Query Building

1. Describe what data you need in natural language
2. Call `ollama_build_graphql_query` with intent and target platform (nautobot/netbox)
3. Use the generated query with `nautobot_graphql`

## Workflow: State Summarization

1. Collect verbose output from pyATS (`show ip bgp summary`, routing tables, etc.)
2. Call `ollama_summarize_state` with the raw output
3. Get structured JSON suitable for analysis or reporting

## Provider Routing

The server routes workloads to different providers based on domain:
- Heavy inference (config gen, validation) → local GPU for zero cost
- Light inference (compression, summarization) → local or cloud
- Fallback: if local GPU is busy/down, cloud picks up automatically

Check current routing with `ollama_list_experts`.
Check provider health with `ollama_health_check`.

## Graceful Degradation

If no provider is available, the tool returns `success: false` with `NO_PROVIDER_AVAILABLE`. When you see this:
- Handle the task directly (generate the config yourself, write the query manually)
- Don't retry indefinitely — the health checker will bring the provider back when it recovers

## Required Environment Variables

- `PROVIDER_OLLAMA_LOCAL_URL` — Local Ollama endpoint (e.g., http://192.168.30.50:11434)
- `ROUTE_DEFAULT_PROVIDER` — Default provider ID for unrouted domains
- `ROUTE_<DOMAIN>_MODEL` — Model to use for each domain
- See `ollama_list_experts` output for full current configuration
