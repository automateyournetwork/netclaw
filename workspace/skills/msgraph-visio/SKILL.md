---
name: msgraph-visio
description: "Upload and retrieve Visio (.vsdx) and other diagram files in OneDrive/SharePoint via the Microsoft 365 MCP server. Use when publishing a generated topology diagram to OneDrive, or fetching an existing .vsdx for reference"
version: 2.0.0
license: Apache-2.0
tags: [microsoft365, visio, onedrive, diagrams, upload]
---

# Microsoft 365 Visio / diagram publishing

## MCP Server

- **Package**: [`@softeria/ms-365-mcp-server`](https://www.npmjs.com/package/@softeria/ms-365-mcp-server) (MIT)
- **Invocation** — deliberately **not** `--read-only`, because publishing requires a write:
  ```
  npx -y @softeria/ms-365-mcp-server --enabled-tools 'upload-file-content|drive-item|folder-files'
  ```
- **Requires**: an Entra ID app registration with delegated `Files.ReadWrite` scope.

> **Version 2.0.0 replaced a package that did not exist.** This skill previously invoked
> `npx -y @anthropic-ai/microsoft-graph-mcp` (**404 on npm**) and documented two `graph_*`
> tool names that exist in no server. The tool names below came from the live server.

### The filter is mandatory

Unfiltered, the server exposes **188 tools at ~225,355 tokens — 45× the 5,000-token ceiling.**
Keep the filter as narrow as the task allows.

### This invocation can write — treat it accordingly

`--read-only` is omitted here on purpose, which makes this the one M365 surface that changes
remote state. Under Principle III a write to a system of record is gated: **confirm the target
path and filename with the operator before uploading**, and never overwrite an existing item
without saying so first. Use `msgraph-files` for anything that only needs reading.

## Verified tools

| Tool | What it does |
|---|---|
| `upload-file-content` | write file bytes to a drive path — **the write** |
| `get-drive-item` | metadata for one item, to check whether you are about to overwrite |
| `list-folder-files` | folder contents, to confirm the destination exists |
| `login` / `verify-login` | device-code sign-in and session state |

There are **no `graph_*` tools**, and there is **no Visio rendering or conversion tool**. This
surface moves files; it does not open or edit Visio documents.

## Workflow: publish a generated diagram

1. `verify-login`, and `login` if needed — surface the device code, never fabricate a session
2. `list-folder-files` on the destination folder — confirm it exists and note existing names
3. `get-drive-item` on the intended filename — **is this an overwrite?** If so, say so and get
   confirmation before proceeding
4. `upload-file-content` with the bytes
5. Report the resulting item id and path. Do not claim success without the server's response.

Produce the `.vsdx` itself with `document-generation` or a diagram skill; this skill only
publishes what already exists on disk.

## Reading results honestly

- **An upload confirms transfer, not correctness.** That the bytes landed says nothing about
  whether the diagram is accurate.
- **A failed upload can leave a partial item** depending on size and session; re-check with
  `get-drive-item` rather than assuming a clean failure.
- **There is no rename or delete here** — the filter excludes them deliberately. Fixing a bad
  filename is an operator action in the web UI.

## Not verified

**Tool names and manifest cost are measured; no upload has been performed.** That needs an M365
tenant with write scope, which this environment does not have. The write path is
correct-by-construction and unproven.

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `msgraph-files` | Read-only inspection — prefer it whenever you are not writing |
| `document-generation`, `drawio-diagram`, `uml-diagram` | Produce the file this publishes |
| `gait-session-tracking` | Record every upload: path, filename, item id |

## Environment Variables

- `MS365_MCP_CLIENT_ID` — Entra ID app registration (client) ID
- `MS365_MCP_TENANT_ID` — tenant ID, or `common`
