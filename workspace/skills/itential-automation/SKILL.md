---
name: itential-automation
description: "Itential Automation Platform (IAP) — network automation orchestration, device configuration management, compliance enforcement, workflow execution, golden config, lifecycle management, and gateway services via 65+ MCP tools. Use when automating network changes through Itential, running compliance plans, deploying golden configs, or orchestrating IAP workflows"
license: Apache-2.0
user-invocable: true
metadata:
  { "openclaw": { "requires": { "bins": ["python3"], "env": ["ITENTIAL_MCP_PLATFORM_HOST"] } } }
---

# Itential Automation Platform

## MCP Server

| Field | Value |
|-------|-------|
| **Repository** | [itential/itential-mcp](https://github.com/itential/itential-mcp) |
| **Transport** | stdio (default), SSE, HTTP |
| **Python** | 3.10+ (supports 3.10, 3.11, 3.12, 3.13) |
| **Dependencies** | `fastmcp`, `ipsdk>=0.7.0`, `python-toon`, `wsproto` |
| **Install** | `pip install itential-mcp` |
| **Entry Point** | `itential-mcp run` |
| **Auth** | Basic (user/pass), OAuth 2.0, JWT |
| **Container** | `ghcr.io/itential/itential-mcp:latest` |

## Environment Variables

### Required
| Variable | Purpose |
|----------|---------|
| `ITENTIAL_MCP_PLATFORM_HOST` | IAP hostname or IP address |
| `ITENTIAL_MCP_PLATFORM_USER` | Username for platform authentication |
| `ITENTIAL_MCP_PLATFORM_PASSWORD` | Password for platform authentication |

### Optional
| Variable | Default | Purpose |
|----------|---------|---------|
| `ITENTIAL_MCP_PLATFORM_PORT` | `443` | Platform connection port |
| `ITENTIAL_MCP_PLATFORM_TIMEOUT` | `30` | Request timeout (seconds) |
| `ITENTIAL_MCP_PLATFORM_DISABLE_TLS` | `false` | Disable TLS to platform |
| `ITENTIAL_MCP_PLATFORM_DISABLE_VERIFY` | `false` | Skip certificate verification |
| `ITENTIAL_MCP_SERVER_TRANSPORT` | `stdio` | Transport type (stdio/sse/http) |
| `ITENTIAL_MCP_SERVER_LOG_LEVEL` | `INFO` | Log verbosity |
| `ITENTIAL_MCP_SERVER_TOOLS_PATH` | — | Custom tools directory |

---

## Tools by Category

### Platform Health (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_health` | — | Comprehensive platform health: status, system, server, applications, adapters (5 parallel API calls) |

### Configuration Manager — Devices (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_devices` | — | List all devices known to the platform with connection details |
| `get_device_configuration` | `name` | Fetch the current running configuration from a device |
| `backup_device_configuration` | `name`, `description?`, `notes?` | Create a config backup with optional metadata; returns backup ID |
| `apply_device_configuration` | `device`, `config` | Deploy configuration commands to a target device |

### Configuration Manager — Compliance (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_compliance_plans` | — | List all compliance plans (config validation rules for org standards) |
| `run_compliance_plan` | `name` | Execute a compliance plan against devices; returns pass/fail results |
| `describe_compliance_report` | `report_id` | Detailed compliance report: rule violations, device status, config analysis |

### Configuration Manager — Device Groups (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_device_groups` | — | List all device groups with member devices |
| `create_device_group` | `name`, `description?`, `devices?` | Create a new device group for bulk operations |
| `add_devices_to_group` | `name`, `devices` | Add devices to an existing group |
| `remove_devices_from_group` | `name`, `devices` | Remove devices from a group |

### Configuration Manager — Golden Config (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_golden_config_trees` | — | List all Golden Configuration trees with versions |
| `create_golden_config_tree` | `name`, `device_type`, `template?`, `variables?` | Create a new Golden Config tree with Jinja2 template |
| `add_golden_config_node` | `tree_name`, `name`, `version?`, `path?`, `template?` | Add a hierarchical config node to a tree |

### Configuration Manager — Inventory (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_inventories` | — | List all inventories with node counts |
| `describe_inventory` | `name` | Inventory details: groups, actions, tags, nodes with attributes |
| `create_inventory` | `name`, `groups`, `description?`, `devices?` | Create a new inventory with groups and optional devices |
| `add_nodes_to_inventory` | `inventory_name`, `nodes` | Bulk add nodes with connection attributes and tags |
| `delete_inventory` | `name` | Permanently remove an inventory |

### Configuration Manager — Templates (1 tool)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `render_template` | `template`, `variables?` | Render a Jinja2 template string with variables |

### Operations Manager — Workflows (5 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_workflows` | — | List all enabled workflow API endpoints with input schemas |
| `start_workflow` | `route_name`, `data?` | Execute a workflow by route; returns job ID, tasks, status, metrics |
| `get_jobs` | `name?`, `project?` | List workflow execution instances with status and timing |
| `describe_job` | `object_id` | Full job details: tasks, status, metrics, timestamps |
| `expose_workflow` | `name`, `route_name?`, `project?`, `endpoint_name?`, `endpoint_description?`, `endpoint_schema?` | Create an API endpoint trigger to expose a workflow |

### Automation Studio — Command Templates (6 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_command_templates` | — | List all command templates from global space and projects |
| `describe_command_template` | `name`, `project?` | Detailed template info including commands and validation rules |
| `run_command_template` | `name`, `devices`, `project?` | Execute a command template against devices with rule evaluation |
| `run_command` | `cmd`, `devices` | Execute a single CLI command across multiple devices |
| `create_command_template` | `name`, `commands`, `project?`, `description?`, `os?`, `pass_rule?`, `ignore_warnings?` | Create a template with commands and validation rules (`<!variable!>` syntax) |
| `update_command_template` | `name`, `commands`, `project?`, `description?`, `os?`, `pass_rule?`, `ignore_warnings?` | Update an existing command template |

### Automation Studio — Templates (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_templates` | `template_type?` | List all templates, optionally filtered by type (textfsm/jinja2) |
| `describe_template` | `name`, `project?` | Template details: content, sample data, type, group, command |
| `create_template` | `name`, `template_type`, `group`, `project?`, `command?`, `template?`, `sample_data?` | Create a new TextFSM or Jinja2 template |
| `update_template` | `name`, `project?`, `command?`, `template?`, `sample_data?` | Update existing template (partial update supported) |

### Automation Studio — Projects (2 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_projects` | — | List all Automation Studio projects |
| `describe_project` | `name` | Project details including component types, folders, references |

### Lifecycle Manager (7 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_resources` | — | List all resource models with descriptions |
| `create_resource` | `name`, `schema`, `description?` | Create a resource model with JSON Schema definition |
| `describe_resource` | `name` | Resource details including lifecycle actions and input schemas |
| `get_instances` | `resource_name` | List all instances of a resource model |
| `describe_instance` | `resource_name`, `instance_name` | Instance details: data, last action, state |
| `run_action` | `resource_name`, `action_name`, `instance_name?`, `instance_description?`, `input_params?` | Execute a lifecycle action; returns job ID and status |
| `get_action_executions` | `resource_name`, `instance_name` | Execution history: timestamps, status, before/after states |

### Adapters (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_adapters` | — | List all adapters with name, version, state |
| `start_adapter` | `name`, `timeout?` | Start a stopped adapter; waits for RUNNING state |
| `stop_adapter` | `name`, `timeout?` | Stop a running adapter; waits for STOPPED state |
| `restart_adapter` | `name`, `timeout?` | Restart a running adapter (use `start_adapter` for stopped ones) |

### Applications (4 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_applications` | — | List all applications with name, version, state |
| `start_application` | `name`, `timeout?` | Start a stopped application |
| `stop_application` | `name`, `timeout?` | Stop a running application |
| `restart_application` | `name`, `timeout?` | Restart a running application |

### Gateway Manager (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_services` | — | List all services with name, cluster, type, description |
| `get_gateways` | — | List connected gateways with status |
| `run_service` | `name`, `cluster`, `input_params?` | Execute a gateway service; returns stdout, stderr, return code, timing |

### Integrations (3 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_integrations` | `model?` | List integration instances, optionally filtered by model |
| `get_integration_models` | — | List all integration models with version info |
| `create_integration_model` | `model` | Create an integration model from OpenAPI spec |

### Workflow Engine — Metrics (6 tools)

| Tool | Parameters | Description |
|------|-----------|-------------|
| `get_job_metrics` | — | Aggregate job metrics across all workflows |
| `get_job_metrics_for_workflow` | `name` | Job metrics filtered by workflow name |
| `get_task_metrics` | — | Comprehensive task metrics across all workflows |
| `get_task_metrics_for_workflow` | `name` | Task metrics filtered by workflow name |
| `get_task_metrics_for_app` | `name` | Task metrics filtered by application name |
| `get_task_metrics_for_task` | `name` | Metrics for a specific task across all workflows |

### Dynamic Tool Bindings

The server also supports dynamically registered tools:

- **Endpoint bindings** — Expose IAP workflow triggers as MCP tools via `ITENTIAL_MCP_TOOL_<NAME>_TYPE=endpoint`
- **Service bindings** — Expose Gateway Manager services as MCP tools via `ITENTIAL_MCP_TOOL_<NAME>_TYPE=service`

---

## Workflows

### 1. Platform Health Check
```
get_health → assess status/system/server/applications/adapters health
→ get_adapters → check for DEAD/STOPPED adapters
→ get_applications → check for stopped applications
→ Report overall platform status → GAIT
```

### 2. Device Configuration Audit
```
get_devices → inventory all managed devices
→ get_device_groups → understand grouping strategy
→ get_compliance_plans → list org compliance rules
→ run_compliance_plan(plan_name) → execute against devices
→ describe_compliance_report(report_id) → review violations
→ Severity-sort findings → GAIT
```

### 3. Golden Config Deployment
```
get_golden_config_trees → review available configs
→ get_devices → select target devices
→ render_template(jinja2_template, variables) → preview config
→ backup_device_configuration(device) → baseline before change
→ apply_device_configuration(device, rendered_config) → deploy
→ get_device_configuration(device) → verify post-change
→ GAIT
```

### 4. Workflow Orchestration
```
get_workflows → discover available automations
→ get_projects → review Automation Studio projects
→ start_workflow(route_name, data) → trigger execution
→ describe_job(object_id) → monitor progress and tasks
→ get_job_metrics_for_workflow(name) → performance analysis
→ GAIT
```

### 5. Command Template Execution
```
get_command_templates → list available templates
→ describe_command_template(name) → review commands and rules
→ get_device_groups → select target group
→ run_command_template(name, devices) → execute with rule evaluation
→ Review per-device results → GAIT
```

### 6. Lifecycle Resource Management
```
get_resources → discover resource models
→ describe_resource(name) → review lifecycle actions and schemas
→ get_instances(resource_name) → list existing instances
→ run_action(resource, action, instance, params) → execute lifecycle action
→ get_action_executions(resource, instance) → verify execution history
→ GAIT
```

### 7. Integration Model Onboarding
```
get_integration_models → review existing integrations
→ create_integration_model(openapi_spec) → register new model
→ get_integrations(model) → verify instance created
→ GAIT
```

---

## Integration with Other Skills

| Skill | Integration |
|-------|-------------|
| **pyats-network** | Use Itential command templates to run structured commands; compare pyATS parsed output with Itential compliance results |
| **pyats-config-mgmt** | Itential golden config as the desired state; pyATS for pre/post verification; ServiceNow for CR gating |
| **netbox-reconcile** | Itential inventories reflect NetBox source of truth; compliance plans validate against NetBox-defined intent |
| **nautobot-sot** | Same as NetBox — cross-reference Itential device inventory with Nautobot IPAM data |
| **infrahub-sot** | Cross-reference Infrahub schema-driven nodes with Itential device groups and inventories |
| **servicenow-change-workflow** | Gate all Itential config deployments behind ServiceNow Change Requests |
| **gait-session-tracking** | Every Itential workflow execution, config push, and compliance run logged in GAIT |
| **fmc-firewall-ops** | Itential workflows can orchestrate firewall policy changes validated by FMC search |
| **nso-device-ops** | Itential as the orchestration layer on top of NSO for multi-vendor service deployment |
| **te-network-monitoring** | Validate network health via ThousandEyes after Itential config deployments |
| **aws-network-ops** | Itential workflows for hybrid network automation spanning on-prem and AWS |
| **gcp-compute-ops** | Itential lifecycle management for resources spanning on-prem and GCP |

---

## Tag-Based Tool Filtering

Itential MCP supports tag-based filtering to restrict which tools are exposed:

| Tag | Tools | Use Case |
|-----|-------|----------|
| `health` | 1 | Platform monitoring |
| `configuration_manager` | 15 | Device config, compliance, golden config, templates, inventories |
| `operations_manager` | 5 | Workflow execution and job management |
| `automation_studio` | 12 | Command templates, projects, device commands, TextFSM/Jinja2 templates |
| `lifecycle_manager` | 7 | Resource models, instances, lifecycle actions |
| `workflow_engine` | 6 | Job and task performance metrics |
| `adapters` | 4 | Adapter lifecycle management |
| `applications` | 4 | Application lifecycle management |
| `gateway_manager` | 3 | Gateway and service operations |
| `integrations` | 3 | Integration model management |

Use `--include-tags` to restrict to specific categories or `--exclude-tags` to hide experimental tools.

---

## Itential vs Other Orchestration Platforms

| Capability | Itential IAP | Cisco NSO | Ansible |
|-----------|-------------|-----------|---------|
| **Focus** | Full lifecycle automation orchestration | Network service orchestration | Config management + ad-hoc tasks |
| **Device Management** | Inventory, groups, config backup/push | CDB, device sync, NED-based | Inventory, groups, playbooks |
| **Compliance** | Built-in compliance plans + reports | Custom via templates | Custom via assert/compliance roles |
| **Golden Config** | Hierarchical tree-based with versioning | Config templates via services | Jinja2 templates in roles |
| **Workflow Engine** | Visual workflow builder + API triggers | Service deployment plans | Playbooks + AWX/Tower |
| **Lifecycle Mgmt** | Resource models with action schemas | Service lifecycle via FASTMAP | Roles with tags |
| **MCP Tools** | 65+ tools across 10 categories | 5 tools (devices + services) | N/A |
| **Integration** | OpenAPI-based integration models | NED packages | Modules + collections |
| **Gateway** | Gateway Manager for distributed execution | LSA for distributed NSO | Execution environments |

---

## Guardrails

- **Gate config deployments** — All `apply_device_configuration` calls must be preceded by a ServiceNow Change Request in `Implement` state
- **Always backup first** — Call `backup_device_configuration` before any `apply_device_configuration`
- **Verify after deployment** — Call `get_device_configuration` after applying changes to confirm they took effect
- **Compliance before and after** — Run `run_compliance_plan` pre- and post-change to verify compliance posture
- **Record in GAIT** — Every workflow execution, config push, compliance run, and template operation must be logged
- **Adapter health awareness** — Check `get_adapters` for DEAD or STOPPED adapters before attempting device operations
- **Case-sensitive names** — Workflow names, device names, template names, and plan names are all case-sensitive in the IAP API
