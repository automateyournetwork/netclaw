---
name: prisma-sdwan-apps
description: "View Prisma SD-WAN application definitions for policy visibility"
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: ["PAN_CLIENT_ID", "PAN_CLIENT_SECRET", "PAN_TSG_ID"]
---

# Prisma SD-WAN Application Visibility

View application definitions in your Palo Alto Networks Prisma SD-WAN fabric. Understand which applications are defined for policy enforcement, their categories, and risk levels.

## When to Use

- Listing all application definitions in the fabric
- Finding applications by name or category
- Understanding application risk classifications
- Reviewing SaaS vs on-premise application types
- Auditing application categories for policy decisions

## MCP Server

- **Server**: `prisma-sdwan-mcp` (community MCP from iamdheerajdubey)
- **Command**: `python3 -u mcp-servers/prisma-sdwan-mcp/src/prisma_sdwan_mcp/server.py` (stdio transport)
- **Auth**: OAuth2 via `PAN_CLIENT_ID`, `PAN_CLIENT_SECRET`, `PAN_TSG_ID`
- **Region**: `PAN_REGION` (americas or europe, default: americas)

## Available Tools

| Tool | Parameters | What It Does |
|------|------------|--------------|
| `get_app_defs` | None | List all application definitions with categories and risk |

## Workflow Examples

### Application Discovery

```bash
# List all applications
"Show me all SD-WAN application definitions"

# Find specific application
"Is Office 365 defined as an application?"

# List by category
"What business applications are defined?"
```

### Risk Analysis

```bash
# Find high-risk applications
"Which applications are classified as high risk?"

# Review SaaS applications
"List all SaaS application definitions"
```

### Policy Planning

```bash
# Understand categories
"What application categories are available for policies?"

# Review productivity apps
"Show me all productivity category applications"
```

## Integration with Other Skills

- **prisma-sdwan-config**: View policies that reference these applications
- **prisma-sdwan-topology**: Understand where policies are applied
- **prisma-sdwan-status**: Check if app-based policies are working

## Response Examples

### Application Definitions Response

```json
{
  "applications": [
    {
      "id": "app001",
      "name": "office365",
      "display_name": "Microsoft Office 365",
      "category": "business",
      "subcategory": "productivity",
      "risk": "low",
      "app_type": "saas"
    },
    {
      "id": "app002",
      "name": "zoom",
      "display_name": "Zoom Video Communications",
      "category": "business",
      "subcategory": "conferencing",
      "risk": "low",
      "app_type": "saas"
    }
  ],
  "total_count": 250
}
```

## Error Handling

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| AUTH_FAILED | OAuth2 authentication failed | Verify PAN_CLIENT_ID, PAN_CLIENT_SECRET, PAN_TSG_ID |
| RATE_LIMITED | API rate limit exceeded | Wait and retry |

## Notes

- Read-only operations - no ServiceNow CR gating required
- Application definitions are fabric-wide (not per-site)
- Risk levels: low, medium, high
- App types: saas, on-premise, custom
- All operations logged to GAIT audit trail
