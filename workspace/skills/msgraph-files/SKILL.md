---
name: msgraph-files
description: "Read OneDrive and SharePoint files via the Microsoft 365 MCP server — list folder contents, fetch item metadata, inspect versions and sharing permissions. Use when locating a document in OneDrive/SharePoint, checking who a file is shared with, or reviewing file version history"
version: 2.0.0
license: Apache-2.0
tags: [microsoft365, onedrive, sharepoint, files, read-only]
---

# Microsoft 365 Files (read-only)

## MCP Server

- **Package**: [`@softeria/ms-365-mcp-server`](https://www.npmjs.com/package/@softeria/ms-365-mcp-server) (MIT)
- **Invocation**:
  ```
  npx -y @softeria/ms-365-mcp-server --read-only --enabled-tools 'drive-item|folder-files'
  ```
- **Requires**: an Entra ID (Azure AD) app registration and delegated Graph scopes. The server
  handles the device-code sign-in itself via its `login` tool.

> **Version 2.0.0 replaced a package that did not exist.** Until spec 093 this skill invoked
> `npx -y @anthropic-ai/microsoft-graph-mcp`, which **404s on npm**, and documented seven
> `graph_*` tool names that exist in no server. Every call it described failed. The tool names
> below were read from the live server's `tools/list`, not recalled.

### Why the `--enabled-tools` filter is mandatory

The unfiltered server exposes **188 tools measured at ~225,355 tokens — 45× NetClaw's 5,000
token manifest ceiling.** It is unusable without a filter. The filter above lands **12 tools at
~4,599 tokens**, which fits with little room to spare, so keep it narrow.

## Verified tools

Read from the running server, `--read-only` with the filter above:

| Tool | What it does |
|---|---|
| `list-folder-files` | contents of a drive folder |
| `get-drive-item` | metadata for one item by id or path |
| `list-drive-item-versions` | version history of an item |
| `list-drive-item-permissions` | who an item is shared with |
| `list-drive-item-thumbnails` | available thumbnail renditions |
| `login` / `verify-login` / `logout` | device-code sign-in and session state |
| `list-accounts` / `select-account` / `remove-account` | multi-account handling |

There are **no `graph_*` tools**. If you find yourself reaching for one, it came from this
skill's old text and does not exist.

## Workflow: locate and inspect a document

1. `verify-login` — is there a live session? If not, `login` and surface the device code to
   the operator; never fabricate a sign-in.
2. `list-folder-files` from the drive root, then descend
3. `get-drive-item` for the candidate — size, timestamps, path
4. `list-drive-item-permissions` if the question is about sharing or exposure
5. `list-drive-item-versions` if the question is "what changed and when"

## Reading results honestly

- **Read-only.** No upload, move, rename or delete. `--read-only` strips them, and this skill
  must not offer them. Writing a file is `msgraph-visio`'s narrower, write-enabled invocation.
- **A permission list is a point-in-time answer**, and sharing links can be created outside
  this surface. "No permissions listed" is not "not shared."
- **An empty folder listing means this folder, as this account sees it.** Delegated scopes and
  account selection both narrow what is visible; state which account you were signed in as.
- **`list-accounts` returning one account is not proof there is only one tenant.**

## Not verified

**The tool names and manifest cost are measured; the calls themselves are not.** Verifying a
real fetch needs an M365 tenant and an app registration, which this environment does not have.
Treat the workflows as correct-by-construction until run against a live tenant.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `msgraph-visio` | Writing a `.vsdx` back to OneDrive (write-enabled invocation) |
| `document-generation` | Produces the documents this skill locates |
| `gait-session-tracking` | Record which account and item were accessed |

## Environment Variables

- `MS365_MCP_CLIENT_ID` — Entra ID app registration (client) ID
- `MS365_MCP_TENANT_ID` — tenant ID, or `common` for multi-tenant
