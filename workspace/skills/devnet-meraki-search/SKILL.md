---
name: devnet-meraki-search
description: Search Cisco Meraki API documentation and lookup specific operations
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      - devnet-content-search
---

# DevNet Meraki API Search

## Purpose

Enable network engineers to quickly find Meraki API documentation for firewall rules, VLAN management, wireless configuration, OAuth setup, and other automation tasks without manually navigating DevNet.

## Tools Used

### Meraki-API-Doc-Search

Search Meraki API documentation with keyword queries.

**Parameters:**
- `query` (string, required): Search terms (e.g., "L3 firewall rules", "VLAN management")
- `limit` (integer, optional): Maximum results to return

**Returns:**
- API endpoint paths and HTTP methods
- Operation descriptions and summaries
- Parameter details and code examples
- Tags for categorization

### Meraki-API-OperationId-Search

Lookup a specific Meraki API operation by its exact operation ID.

**Parameters:**
- `operationId` (string, required): Exact operation ID (e.g., "updateNetworkApplianceFirewallL3FirewallRules")

**Returns:**
- Complete OpenAPI specification for the operation
- Full parameter schemas (path, query, body)
- Request and response body schemas
- Code examples when available

## Workflow

### Basic Documentation Search

1. User requests Meraki API documentation on a topic
2. Invoke `Meraki-API-Doc-Search` with relevant keywords
3. Present matching API endpoints with descriptions
4. User selects an operation for more details
5. Optionally lookup full spec with `Meraki-API-OperationId-Search`

### Specific Operation Lookup

1. User knows the exact operation ID they need
2. Invoke `Meraki-API-OperationId-Search` with the operation ID
3. Return complete OpenAPI specification
4. User can see all parameters, schemas, and examples

## Example Usage

### Search for Firewall APIs

```
User: "Find Meraki L3 firewall API documentation"

Tool: Meraki-API-Doc-Search
Query: "L3 firewall rules"

Response:
- PUT /networks/{networkId}/appliance/firewall/l3FirewallRules
  → Update the L3 firewall rules of an MX network
- GET /networks/{networkId}/appliance/firewall/l3FirewallRules
  → Return the L3 firewall rules for an MX network
```

### Search for VLAN Management

```
User: "Show me Meraki VLAN management APIs"

Tool: Meraki-API-Doc-Search
Query: "VLAN management"

Response:
- GET /networks/{networkId}/appliance/vlans
  → List the VLANs for an MX network
- POST /networks/{networkId}/appliance/vlans
  → Add a VLAN
- PUT /networks/{networkId}/appliance/vlans/{vlanId}
  → Update a VLAN
```

### Search for Wireless Configuration

```
User: "Find Meraki wireless SSID configuration APIs"

Tool: Meraki-API-Doc-Search
Query: "wireless SSID configuration"

Response:
- GET /networks/{networkId}/wireless/ssids
  → List the MR SSIDs in a network
- PUT /networks/{networkId}/wireless/ssids/{number}
  → Update the attributes of an MR SSID
```

### Lookup Specific Operation

```
User: "Get details for createNetworkMerakiAuthUser operation"

Tool: Meraki-API-OperationId-Search
OperationId: "createNetworkMerakiAuthUser"

Response:
- Path: /networks/{networkId}/merakiAuthUsers
- Method: POST
- Summary: Create a user configured with Meraki Authentication
- Parameters: networkId (path, required)
- Request Body: email, name, password, accountType, authorizations
```

## Error Handling

### No Results Found

If search returns no results:
- Suggest broader search terms
- Check spelling of technical terms
- Try alternative terminology (e.g., "firewall" vs "ACL")

### Invalid Operation ID

If operation ID lookup fails:
- Verify the operation ID spelling (case-sensitive)
- Use `Meraki-API-Doc-Search` first to find valid operation IDs
- Check that the operation exists in current Meraki API version

### Server Unavailable

If DevNet server is unreachable:
- Verify internet connectivity
- Check https://devnet.cisco.com status
- Retry after a brief wait
