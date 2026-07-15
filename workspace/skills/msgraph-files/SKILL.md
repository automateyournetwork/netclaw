---
name: msgraph-files
description: "Manage files on OneDrive and SharePoint via Microsoft Graph API - upload, download, list, search, and organize network documentation and artifacts. Use when uploading reports to SharePoint, retrieving network docs from OneDrive, organizing config backups, or searching for topology diagrams"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["npx"], "env": ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"] } } }
---

# Microsoft Graph — File Operations

## How to Call the Tools

The Microsoft Graph MCP server is invoked via npx with Azure AD credentials:

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" <tool-name> '<arguments-json>'
```

## Available Operations

### 1. List Files in a Drive or Folder

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_list_files '{"driveId":"<drive-id>","folderId":"root"}'
```

### 2. Search for Files

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_search_files '{"query":"network topology diagram","driveId":"<drive-id>"}'
```

### 3. Download / Read File Content

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_get_file_content '{"driveId":"<drive-id>","itemId":"<item-id>"}'
```

### 4. Upload a File

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_upload_file '{"driveId":"<drive-id>","parentId":"<folder-id>","fileName":"health-report-2026-02-22.md","content":"<file-content>"}'
```

### 5. Create a Folder

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_create_folder '{"driveId":"<drive-id>","parentId":"root","folderName":"NetClaw Reports"}'
```

### 6. List SharePoint Sites

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_list_sites '{}'
```

### 7. Get Site Drive

```bash
AZURE_TENANT_ID=$AZURE_TENANT_ID AZURE_CLIENT_ID=$AZURE_CLIENT_ID AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET \
  python3 $MCP_CALL "npx -y @anthropic-ai/microsoft-graph-mcp" graph_get_site_drive '{"siteId":"<site-id>"}'
```

## When to Use

- **Store audit reports** — Upload health check, security audit, and reconciliation reports to SharePoint
- **Archive configuration backups** — Push running-config snapshots to a versioned SharePoint library
- **Retrieve reference documents** — Pull network design docs, standards, or runbooks from SharePoint
- **Organize artifacts** — Create folder structures per site, per device, or per change request
- **Search documentation** — Find existing topology diagrams, IP address plans, or change records

## Integration with Other Skills

- Use **pyats-health-check** or **pyats-security** to generate reports, then upload to SharePoint via this skill
- Use **netbox-reconcile** to produce drift reports, then store them in a dated folder on SharePoint
- Use **msgraph-visio** to generate Visio diagrams, then organize them in SharePoint document libraries
- Use **gait-session-tracking** to produce audit logs, then archive them to SharePoint for compliance

## Folder Organization Pattern

```
SharePoint: Network Engineering/
  ├── Health Reports/
  │   ├── 2026-02-22-fleet-health.md
  │   └── 2026-02-21-r1-health.md
  ├── Security Audits/
  │   └── 2026-02-22-cis-audit.md
  ├── Topology/
  │   ├── campus-topology.vsdx
  │   └── dc-fabric.vsdx
  ├── Configuration Backups/
  │   ├── R1/
  │   └── SW1/
  └── Change Records/
      └── CHG0012345-loopback99.md
```

## GAIT Audit Trail

Record file operations in GAIT:

```bash
python3 $MCP_CALL "python3 -u $GAIT_MCP_SCRIPT" gait_record_turn '{"input":{"role":"assistant","content":"Uploaded fleet health report (2026-02-22-fleet-health.md) to SharePoint Network Engineering/Health Reports/. 4 devices assessed, 1 WARNING (SW1 CPU 82%), 3 HEALTHY.","artifacts":[]}}'
```
