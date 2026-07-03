# Quickstart: Check Point Integration

**Time to complete**: ~5 minutes
**Prerequisites**: NetClaw installed, Check Point credentials ready

## Step 1: Enable Check Point Integration

### Option A: New Installation

During `install.sh`, answer "y" when prompted:

```
Enable Check Point Security Integration? [y/N] y
```

### Option B: Existing Installation

Run the enablement script:

```bash
./scripts/checkpoint-enable.sh
```

## Step 2: Configure Credentials

Add your Check Point credentials to `~/.openclaw/.env`:

### Minimum Setup (Management Server Only)

```bash
# Check Point Management Server
CHKP_MGMT_HOST=192.168.1.100
CHKP_MGMT_API_KEY=your-api-key-here

# Disable telemetry (recommended)
CHKP_TELEMETRY_DISABLED=true
```

### Full Setup (All Products)

```bash
# ═══════════════════════════════════════════
# Check Point MCP Integration
# ═══════════════════════════════════════════

# Management Server (required for policy queries)
CHKP_MGMT_HOST=192.168.1.100
CHKP_MGMT_PORT=443
CHKP_MGMT_API_KEY=your-management-api-key

# Smart-1 Cloud (alternative to on-prem management)
# CHKP_S1C_API_KEY=your-smart1-cloud-key
# CHKP_S1C_URL=https://your-tenant.maas.checkpoint.com

# Harmony SASE
CHKP_SASE_API_KEY=your-sase-api-key
CHKP_SASE_MGMT_HOST=https://api.us1.sase.checkpoint.com/api
CHKP_SASE_ORIGIN=https://your-tenant.sase.checkpoint.com

# Reputation Service (contact TCAPI_SUPPORT@checkpoint.com)
CHKP_REPUTATION_API_KEY=your-reputation-api-key

# Threat Emulation
CHKP_TE_API_KEY=your-threat-emulation-key

# Spark Management (MSP)
CHKP_SPARK_API_KEY=your-spark-api-key

# Argos ERM
CHKP_ARGOS_API_KEY=your-argos-api-key

# Global Settings
CHKP_TELEMETRY_DISABLED=true
CHKP_LOG_LEVEL=standard
```

## Step 3: Verify Installation

### Check MCP Availability

```bash
# List configured Check Point MCPs
openclaw mcp list | grep chkp
```

Expected output:
```
chkp-management         @chkp/quantum-management-mcp     configured
chkp-management-logs    @chkp/management-logs-mcp        configured
chkp-threat-prevention  @chkp/threat-prevention-mcp      configured
...
```

### Test Basic Query

```bash
# Start OpenClaw and test
openclaw

# In the chat:
> /checkpoint show my firewall policies
```

### Test Reputation Lookup

```bash
> /checkpoint check reputation of IP 8.8.8.8
```

## Step 4: Explore Capabilities

### Policy Audit
```
/checkpoint audit my policies for overly permissive rules
/checkpoint show all rules allowing any-any
/checkpoint suggest policy optimizations
```

### Threat Intelligence
```
/checkpoint check reputation of IP 185.220.101.1
/checkpoint is this URL malicious: http://suspicious.example.com
/checkpoint check file reputation for SHA256 abc123...
```

### Gateway Diagnostics
```
/checkpoint show gateway health status
/checkpoint what's causing high CPU on the gateway
/checkpoint debug connection from 10.1.1.1 to 8.8.8.8
```

### Documentation
```
/checkpoint how do I configure HTTPS inspection
/checkpoint what is ClusterXL
```

## Troubleshooting

### "MCP not configured" Error

Ensure the required environment variables are set:
```bash
cat ~/.openclaw/.env | grep CHKP
```

### "Authentication failed" Error

1. Verify your API key is correct
2. Check network connectivity to management server:
   ```bash
   curl -k https://$CHKP_MGMT_HOST:$CHKP_MGMT_PORT/web_api/login
   ```

### "No Check Point MCPs available"

Run the enablement script:
```bash
./scripts/checkpoint-enable.sh
```

## Next Steps

- See [docs/CHECKPOINT.md](../../docs/CHECKPOINT.md) for detailed documentation
- Explore cross-platform queries with CML, SuzieQ, or Batfish
- Configure additional Check Point products as needed
