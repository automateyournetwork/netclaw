# Terraform Registry Skill

Discover providers and modules from the Terraform Registry.

## Tools

| Tool | Description |
|------|-------------|
| `search_providers` | Search for providers in the Registry |
| `get_provider_details` | Get provider documentation and versions |
| `search_modules` | Search for modules in the Registry |
| `get_module_details` | Get module documentation and inputs/outputs |
| `list_provider_versions` | List available versions for a provider |
| `list_module_versions` | List available versions for a module |

## Example Queries

```
Search for AWS networking providers

What modules are available for Cisco ACI?

Show details for the hashicorp/aws provider

Find VPC modules in the registry
```

## Prerequisites

- No authentication required for public Registry
- `TFE_TOKEN` required for private modules

## Server

This skill uses the `terraform-mcp` server with Registry toolset enabled.
