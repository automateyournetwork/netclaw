# Network and interface reference

## Network types

| network_type | Description |
|---|---|
| `bridge` | Internal L2 bridge |
| `ovs` | Open vSwitch bridge |
| `pnet0`-`pnet9` | Physical uplinks |
| `cloud0`-`cloud9` | Cloud / internet mappings |

## Interface IDs

EVE-NG uses zero-based interface indices per node:
- `0` = first interface
- `1` = second interface
- `2` = third interface

Always use `eve_list_node_interfaces` to map the actual interface names before connecting.
