---
name: devnet-catalyst-search
description: Search Cisco Catalyst Center API documentation for device management and policy automation
license: Apache-2.0
user-invocable: true
metadata:
  openclaw:
    requires:
      - devnet-content-search
---

# DevNet Catalyst Center API Search

## Purpose

Enable network engineers to quickly find Catalyst Center (DNA Center) API documentation for device management, policy automation, assurance, and network provisioning without manually navigating DevNet.

## Tools Used

### CatalystCenter-API-Doc-Search

Search Catalyst Center API documentation with keyword queries.

**Parameters:**
- `query` (string, required): Search terms (e.g., "device inventory", "policy automation")
- `limit` (integer, optional): Maximum results to return

**Returns:**
- API endpoint paths and HTTP methods
- Operation descriptions and summaries
- Implementation guide references
- Tags for categorization

## Workflow

### Basic Documentation Search

1. User requests Catalyst Center API documentation on a topic
2. Invoke `CatalystCenter-API-Doc-Search` with relevant keywords
3. Present matching API endpoints with descriptions
4. User selects an operation for more details
5. Provide implementation guidance based on returned documentation

### Common Search Topics

- **Device Management**: Inventory, discovery, provisioning
- **Policy Automation**: Access control, segmentation, QoS
- **Assurance**: Health monitoring, issue detection, troubleshooting
- **Network Design**: Sites, buildings, floors, device templates
- **Software Management**: SWIM, image distribution, compliance

## Example Usage

### Search for Device Inventory APIs

```
User: "Find Catalyst Center device inventory APIs"

Tool: CatalystCenter-API-Doc-Search
Query: "device inventory"

Response:
- GET /dna/intent/api/v1/network-device
  → Returns the list of network devices
- GET /dna/intent/api/v1/network-device/{id}
  → Returns device by specified ID
- GET /dna/intent/api/v1/network-device/count
  → Returns the count of network devices
```

### Search for Policy Automation

```
User: "Show me Catalyst Center policy automation APIs"

Tool: CatalystCenter-API-Doc-Search
Query: "policy automation"

Response:
- GET /dna/intent/api/v1/business/sda/fabric-site
  → Get SDA Fabric Sites
- POST /dna/intent/api/v1/business/sda/virtual-network
  → Add Virtual Network in SDA Fabric
- GET /dna/intent/api/v1/policy/access-contract
  → Get Access Contracts
```

### Search for Assurance APIs

```
User: "Find Catalyst Center health monitoring APIs"

Tool: CatalystCenter-API-Doc-Search
Query: "health monitoring assurance"

Response:
- GET /dna/intent/api/v1/client-health
  → Returns overall client health
- GET /dna/intent/api/v1/network-health
  → Returns overall network health
- GET /dna/intent/api/v1/site-health
  → Returns site health summary
```

### Search for Device Discovery

```
User: "Show me Catalyst Center device discovery endpoints"

Tool: CatalystCenter-API-Doc-Search
Query: "device discovery"

Response:
- POST /dna/intent/api/v1/discovery
  → Initiates discovery with provided parameters
- GET /dna/intent/api/v1/discovery/{id}
  → Returns discovery by specified ID
- GET /dna/intent/api/v1/discovery/{id}/network-device
  → Returns devices discovered in discovery
```

## Error Handling

### No Results Found

If search returns no results:
- Suggest broader search terms
- Try alternative terminology (e.g., "DNA Center" vs "Catalyst Center")
- Check spelling of technical terms
- Try related concepts (e.g., "inventory" vs "device list")

### Server Unavailable

If DevNet server is unreachable:
- Verify internet connectivity
- Check https://devnet.cisco.com status
- Retry after a brief wait

### Ambiguous Results

If too many results are returned:
- Refine search with more specific terms
- Add qualifiers (e.g., "device inventory GET" vs just "device")
- Filter by API category (intent, system, data)

