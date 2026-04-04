# Quickstart: Terraform MCP Server Integration

**Feature**: 018-terraform-mcp-server | **Date**: 2026-04-04

## Prerequisites

1. Terraform CLI installed (v1.x+)
2. HCP Terraform account (for workspace features)
3. NetClaw OpenClaw gateway running

## Setup (5 minutes)

### Step 1: Install Terraform MCP Server

```bash
# Using Go
go install github.com/hashicorp/terraform-mcp-server@latest

# Or download binary from releases
curl -LO https://releases.hashicorp.com/terraform-mcp-server/latest/terraform-mcp-server_linux_amd64.zip
unzip terraform-mcp-server_linux_amd64.zip
sudo mv terraform-mcp-server /usr/local/bin/
```

### Step 2: Generate HCP Terraform Token (Optional)

1. Log in to HCP Terraform (app.terraform.io)
2. Navigate to **User Settings** → **Tokens**
3. Create a new API token
4. Copy the token

### Step 3: Configure Environment

Add to your `.env` file:

```bash
# Terraform MCP Server
TFE_TOKEN=your_hcp_terraform_token_here

# Optional: Self-hosted Terraform Enterprise
# TFE_ADDRESS=https://tfe.example.com
```

### Step 4: Register MCP Server

Add to `config/openclaw.json`:

```json
{
  "mcpServers": {
    "terraform-mcp": {
      "command": "terraform-mcp-server",
      "args": ["--enable-all-toolsets"],
      "env": {
        "TFE_TOKEN": "${TFE_TOKEN}",
        "TFE_ADDRESS": "${TFE_ADDRESS}"
      }
    }
  }
}
```

### Step 5: Restart OpenClaw Gateway

```bash
# Restart to load new MCP server
openclaw restart
```

## Verification

### Test 1: Search Providers

```
Search Terraform providers for Cisco
```

**Expected**: List of Cisco-related providers (ACI, IOS, NX-OS, etc.).

### Test 2: Search Modules

```
Search Terraform modules for AWS VPC
```

**Expected**: List of VPC modules with inputs and outputs.

### Test 3: List Workspaces

```
List my HCP Terraform workspaces in the network-ops organization
```

**Expected**: Array of workspaces with status and last run info.

### Test 4: Validate Configuration

```
Validate the Terraform configuration in ~/infrastructure/network
```

**Expected**: Validation success or error messages.

## Skills Available

| Skill | Invocation | Description |
|-------|------------|-------------|
| `/terraform-registry` | Provider/module search | Find providers and modules |
| `/terraform-workspaces` | HCP Terraform | Manage workspaces and runs |
| `/terraform-operations` | Local Terraform | Plan, apply, and manage state |

## Common Queries

### Registry Operations

```
# Find network providers
Search Terraform providers for network automation

# Get provider details
Show documentation for the cisco/aci provider

# Find modules
Search Terraform modules for network firewall

# Get module details
Show inputs and outputs for the hashicorp/consul/aws module
```

### Workspace Operations

```
# List workspaces
List all workspaces in my-organization

# Get workspace details
Show details for the network-core workspace

# Trigger a run
Trigger a Terraform run on the network-staging workspace

# Check run status
Show status of run-abc123
```

### Local Operations

```
# Initialize
Initialize Terraform in ~/infrastructure/network

# Validate
Validate the Terraform configuration in ~/infrastructure/network

# Plan
Create a Terraform plan for ~/infrastructure/network

# Apply (requires CR approval)
Apply the Terraform plan for ~/infrastructure/network
```

## Security Notes

- Apply and destroy operations require ServiceNow CR approval
- TFE_TOKEN is never logged or displayed
- Use dedicated service account for NetClaw integration
- Destroy operations require double confirmation
- Consider using Sentinel policies for additional guardrails

## Troubleshooting

### "Unauthorized" Error

- Verify `TFE_TOKEN` is set correctly
- Ensure token has required permissions
- Check token hasn't expired

### "Provider Not Found" Error

- Verify provider namespace and name
- Check provider is published to registry
- Try searching with partial name

### "Workspace Not Found" Error

- Verify organization name is correct
- Ensure workspace exists
- Check token has access to organization

### "Plan Failed" Error

- Check Terraform configuration syntax
- Verify all required variables are set
- Ensure providers are properly configured
