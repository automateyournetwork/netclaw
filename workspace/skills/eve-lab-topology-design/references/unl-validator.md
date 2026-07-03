# UNL validator

Validator script: `{baseDir}/scripts/validate_unl_topology.py`

## Typical commands

```bash
python3 {baseDir}/scripts/validate_unl_topology.py /opt/unetlab/labs/mylab.unl --verbose
python3 {baseDir}/scripts/validate_unl_topology.py mylab.unl --reqs design_reqs.json --roles roles.json
python3 {baseDir}/scripts/validate_unl_topology.py mylab.unl --json
```

## What it checks

- Orphan nodes
- Dangling network references
- Isolated networks
- Graph partitioning
- Role-based adjacency violations
- SPOF nodes and links
- Asymmetric peer-group uplink counts
- Required links, forbidden links, minimum uplinks from requirements files

## Requirements-file schema sketch

```json
{
  "required_links": [{"from": "CORE1", "to": "DIST1"}],
  "redundancy_groups": [{"nodes": ["CORE1", "CORE2"], "role": "core", "min_uplinks": 1}],
  "forbidden_links": [{"from": "HOST1", "to": "CORE1"}]
}
```
