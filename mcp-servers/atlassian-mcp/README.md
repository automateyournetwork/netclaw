# Atlassian MCP Server

Community MCP server integration for Jira and Confluence via the `mcp-atlassian` package.

## Overview

| Attribute | Value |
|-----------|-------|
| Package | mcp-atlassian (by sooperset) |
| License | Apache 2.0 |
| Tools | 72 |
| Transport | stdio (via `uvx mcp-atlassian`) |
| Auth | API Token (Cloud) or Personal Access Token (Server/DC) |
| Platforms | Atlassian Cloud, Jira Server/DC, Confluence Server/DC |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JIRA_URL` | Conditional | Jira instance URL (required if using Jira tools) |
| `JIRA_USERNAME` | Conditional | Email (Cloud) or username (Server/DC) |
| `JIRA_API_TOKEN` | Conditional | API token (Cloud) or Personal Access Token (Server/DC) |
| `CONFLUENCE_URL` | Conditional | Confluence instance URL (required if using Confluence tools) |
| `CONFLUENCE_USERNAME` | Conditional | Email (Cloud) or username (Server/DC) |
| `CONFLUENCE_API_TOKEN` | Conditional | API token (Cloud) or Personal Access Token (Server/DC) |

**Note**: At least one product (Jira or Confluence) must be configured. If only one is configured, tools for the other product return "not configured" messages.

## Authentication

### Atlassian Cloud

1. Generate an API Token: https://id.atlassian.com/manage-profile/security/api-tokens
2. Use your email address as the username
3. Use the same token for both Jira and Confluence (same Atlassian account)

```bash
export JIRA_URL="https://your-domain.atlassian.net"
export JIRA_USERNAME="your-email@example.com"
export JIRA_API_TOKEN="your-api-token"

export CONFLUENCE_URL="https://your-domain.atlassian.net/wiki"
export CONFLUENCE_USERNAME="your-email@example.com"
export CONFLUENCE_API_TOKEN="your-api-token"
```

### Server/Data Center

1. Generate a Personal Access Token: Profile -> Personal Access Tokens -> Create token
2. Use your server username
3. Jira and Confluence may be separate instances with different URLs

```bash
export JIRA_URL="https://jira.example.com"
export JIRA_USERNAME="your-username"
export JIRA_API_TOKEN="your-personal-access-token"

export CONFLUENCE_URL="https://confluence.example.com"
export CONFLUENCE_USERNAME="your-username"
export CONFLUENCE_API_TOKEN="your-personal-access-token"
```

## Tool Categories (72 tools)

### Jira Issues (~20 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| jira_search | Search issues using JQL | No |
| jira_get_issue | Get issue details by key | No |
| jira_create_issue | Create a new issue | Yes |
| jira_update_issue | Update issue fields | Yes |
| jira_delete_issue | Delete an issue | Yes |
| jira_get_issue_comments | List comments on an issue | No |
| jira_add_comment | Add a comment to an issue | Yes |
| jira_batch_create_issues | Create multiple issues in one operation | Yes |

### Jira Transitions (~5 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| jira_get_transitions | List available transitions for an issue | No |
| jira_transition_issue | Perform a workflow transition | Yes |

### Jira Project & Fields (~10 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| jira_get_projects | List all accessible projects | No |
| jira_get_project | Get project details by key | No |
| jira_get_fields | List all fields (standard + custom) | No |
| jira_get_issue_types | List available issue types for a project | No |

### Jira Links (~5 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| jira_link_issues | Create a link between two issues | Yes |
| jira_get_issue_links | List links for an issue | No |
| jira_get_link_types | List available link types | No |

### Confluence Pages (~15 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| confluence_search | Search pages using CQL | No |
| confluence_get_page | Get page content by ID or title+space | No |
| confluence_create_page | Create a new page | Yes |
| confluence_update_page | Update page content (new version) | Yes |
| confluence_delete_page | Delete a page | Yes |

### Confluence Comments (~5 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| confluence_get_page_comments | List comments on a page | No |
| confluence_add_comment | Add a comment to a page | Yes |

### Confluence Spaces (~5 tools)

| Tool | Description | Write? |
|------|-------------|--------|
| confluence_get_spaces | List all accessible spaces | No |
| confluence_get_space | Get space details by key | No |

## Running Standalone

```bash
# Test the server standalone
uvx mcp-atlassian
```

The server communicates via stdio. It will wait for JSON-RPC messages on stdin.

## Verification

```bash
# Verify Jira API access (Cloud)
curl -u "email:token" "https://your-domain.atlassian.net/rest/api/3/myself"

# Verify Confluence API access (Cloud)
curl -u "email:token" "https://your-domain.atlassian.net/wiki/rest/api/space?limit=1"
```

## Graceful Degradation

- If only Jira environment variables are set: Confluence tools are unavailable
- If only Confluence environment variables are set: Jira tools are unavailable
- If neither product is configured: Server fails to start

## Error Responses

All tools return structured error messages for:
- **Connection failure**: Atlassian instance unreachable
- **Authentication failure**: Invalid API token or PAT
- **Not found**: Project, issue, page, or space does not exist
- **Permission denied**: Token lacks required permissions
- **Rate limited**: Too many requests - retry after backoff
- **Invalid transition**: Workflow transition not available from current status
- **Validation error**: Required fields missing or invalid values

## Links

- Package: https://pypi.org/project/mcp-atlassian/
- Source: https://github.com/sooperset/mcp-atlassian
- Atlassian API Tokens: https://id.atlassian.com/manage-profile/security/api-tokens
