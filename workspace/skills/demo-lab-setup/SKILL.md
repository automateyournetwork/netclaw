# SKILL: Demo Lab Setup — Nautobot Workshop + ContainerLab + Golden Config

## Purpose

Deploy the byrn-baker/Nautobot-Workshop environment end-to-end.

## When to Use

- User says "set up the demo" or "build the demo lab" or "deploy the workshop"

## CRITICAL RULES

1. **Follow the phases in order**
2. **MANDATORY STOP between every phase.** After completing each phase, you MUST stop and say: "Phase N complete. Ready for Phase N+1? (Say 'continue' to proceed, or '/new' to start a fresh session and say 'continue demo from Phase N+1')" Do NOT proceed until the user says continue.
3. **Use the workshop repo as-is** — do NOT create custom files
4. **Use Invoke** to build/start Nautobot — do NOT run docker compose directly
5. **BATCH COMMANDS** — combine multiple shell commands into ONE exec call using `&&`. Every tool call costs tokens. Aim for 1-3 exec calls per phase, not 10-20.
6. **NEVER poll builds** — no `process poll` or `process log` on long-running commands. Run it, get "still running", tell user to wait, check result once with a tiny command.
7. **Use nautobot-mcp-v2 tools** for ALL Nautobot API operations — never curl or docker exec.
8. **Do NOT explore the repo.** Do not ls, cat, grep, find, or read README files. This skill has all the information you need. Execute the prescribed commands directly.
9. **NEVER restart Nautobot containers.** Do not run docker compose down/up, invoke stop/start, or any command that restarts the Nautobot stack. If an environment variable is missing, add it to creds.env and tell the user to restart manually.

## Prerequisites — ONE command

Run this single command to check all prerequisites:
```bash
echo "=== prereqs ===" && docker --version && clab version 2>&1 | head -1 && poetry --version && git --version && echo "=== images ===" && docker images --format '{{.Repository}}:{{.Tag}}' | grep -E "cisco_iol|ceos" && echo "=== done ==="
```

If anything is missing, fix it before proceeding.

## Phase 1: Clone and Set Up — ONE command

```bash
cd ~ && git clone https://github.com/byrn-baker/Nautobot-Workshop.git && cd ~/Nautobot-Workshop/nautobot-docker-compose && cp invoke.example.yml invoke.yml && cp environments/creds.example environments/creds.env && sed -i 's/NAUTOBOT_CREATE_SUPERUSER=false/NAUTOBOT_CREATE_SUPERUSER=true/' environments/creds.env && echo "GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}" >> environments/creds.env && echo "NAUTOBOT_NAPALM_USERNAME=${NETCLAW_USERNAME}" >> environments/creds.env && echo "NAUTOBOT_NAPALM_PASSWORD=${NETCLAW_PASSWORD}" >> environments/creds.env && echo "DEVICE_USERNAME=${NETCLAW_USERNAME}" >> environments/creds.env && echo "DEVICE_PASSWORD=${NETCLAW_PASSWORD}" >> environments/creds.env && echo "=== repo cloned, superuser enabled, GitHub token + device creds added ==="
```

This appends to creds.env using variables from the shell environment (sourced from .env). The actual credentials never appear in the skill or repo. The env vars added:
- `GITHUB_PERSONAL_ACCESS_TOKEN` — for golden config repo sync
- `NAUTOBOT_NAPALM_USERNAME` / `NAUTOBOT_NAPALM_PASSWORD` — for NAPALM device connections
- `DEVICE_USERNAME` / `DEVICE_PASSWORD` — for Nornir/Secrets-based device connections

Then set up Poetry — ONE command:
```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry shell && poetry lock && poetry install
```

**Tell the user:** "Workshop repo cloned and Nautobot docker-compose configured. Poetry environment set up."

## Phase 2: Build and Start Nautobot — TWO commands max

**Command 1 — Build the image:**
```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke build
```

**STOP after "Command still running". Tell the user:**
> "Nautobot image is building (3-5 minutes). Let me know when it's done."

**Command 2 — When user confirms, verify and start:**
```bash
docker images | grep nautobot-workshop && cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke debug
```

**STOP after "Command still running". Tell the user:**
> "Nautobot is starting up (1-2 minutes). Let me know when it's ready, or I'll check shortly."

**Then check health — ONE command:**
```bash
sleep 60 && docker ps --format 'table {{.Names}}\t{{.Status}}' | grep nautobot
```

Look for `(healthy)`. Default login: admin/admin at http://localhost:8080.

**STOP. Tell the user:** "Phase 2 complete — Nautobot is running. Ready for Phase 3? (Say continue, or /new to start a fresh session and say continue demo from Phase 3)"

## Phase 3: Populate Nautobot with Design Builder

### Step 3a: Enable ALL jobs (user action required)

**Tell the user:**
> Enable ALL jobs in Nautobot before I can proceed:
> 1. Open http://localhost:8080 (admin / admin)
> 2. Navigate to **Jobs** → **Jobs**
> 3. Enable **every job** — Design Builder, Golden Config (Backup, Intended, Compliance, Deploy), and all others
> 4. Fastest way: click each job, toggle Enabled, save. There are about 15-20 jobs.
> 5. Tell me when done.

All golden config jobs must be enabled: **Backup Configurations**, **Generate Intended Configurations**, **Run Compliance**, **Deploy Golden Config**, and any others. If even one is disabled, the workflow will fail when it tries to run that job.

**Wait for confirmation.**

### Step 3b: Run Design Builder and verify — use MCP tools

Once confirmed, use nautobot-mcp-v2:
```
nautobot_run_job(job_name="Nautobot Workshop Demo Initial Data")
```

Wait for completion, then verify with ONE MCP call:
```
nautobot_get_devices
```

Should show all 20 devices.

### Step 3c: Load config contexts, schemas, and jobs via Git Data Source

Design Builder creates devices, interfaces, IPs, and BGP but does NOT create config contexts. These are in a separate Git repo that Nautobot syncs as a data source.

Register the datasource repo in Nautobot — use MCP tools:
```
nautobot_create_git_repository(
  name="nautobot-workshop-datasource",
  remote_url="https://github.com/byrn-baker/Nautobot-Workshop-Datasource.git",
  branch="main",
  provided_contents="extras.configcontext,extras.configcontextschema,extras.job"
)
```

If the repo is private, link the GitHub Secrets Group (created in Step 3d) to this repo as well.

Sync the repo:
```
nautobot_sync_git_repository(name="nautobot-workshop-datasource")
```

This loads:
- Config contexts (role-scoped: ospf_global, mpls_global, prefix_lists, route_maps, fabric configs)
- Per-device config contexts (East/West Leaf and Spine devices)
- Config context schemas (OSPF, MPLS, prefix_list, route_map validation)
- Jobs from the repo

Verify:
```
nautobot_get_config_contexts
```

### Step 3d: Set up device credentials (Secrets + Secrets Group)

Golden Config uses Nornir which gets SSH credentials from Nautobot Secrets Groups. Create the secrets referencing the environment variables added to creds.env in Phase 1:

```
nautobot_create_secrets_group(name="Device Credentials")
nautobot_create_secret(name="Device Username", provider="environment-variable", parameters='{"variable": "DEVICE_USERNAME"}')
nautobot_create_secret(name="Device Password", provider="environment-variable", parameters='{"variable": "DEVICE_PASSWORD"}')
nautobot_add_secret_to_group(secrets_group_id="<id>", secret_id="<username-secret-id>", access_type="Generic", secret_type="username")
nautobot_add_secret_to_group(secrets_group_id="<id>", secret_id="<password-secret-id>", access_type="Generic", secret_type="password")
```

Then assign the Secrets Group to all devices. Use GraphQL to get all device IDs, then update each one:
```
nautobot_graphql query="{ devices { id name } }"
```

For each device:
```
nautobot_update_object(object_type="device", identifier="<device-name>", updates='{"secrets_group": "<secrets-group-id>"}')
```

This must be done before golden config backup/intended jobs will work. Without it, Nornir cannot SSH to devices.

**STOP. Tell the user:** "Phase 3 complete — Nautobot populated with devices, config contexts, and credentials. Ready for Phase 4? (Say continue, or /new to start fresh and say continue demo from Phase 4)"

## Phase 4: Deploy ContainerLab — TWO commands max

**Command 1 — Deploy:**
```bash
cd ~/Nautobot-Workshop/clabs && sudo clab deploy --topo nautobot-workshop-topology.clab.yml
```

**STOP after "Command still running". Tell the user:**
> "ContainerLab is deploying 20 nodes (2-5 minutes). Let me know when it's done."

**Command 2 — When user confirms, verify and connect Nautobot:**
```bash
sudo clab inspect --topo ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml 2>&1 | tail -5 && NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker) && docker network connect clab-mgmt $NAUTOBOT_CONTAINER 2>/dev/null; docker network connect clab-mgmt $CELERY_CONTAINER 2>/dev/null && echo "=== Nautobot connected to clab-mgmt ===" && ping -c 1 192.168.220.2 && echo "=== P1 reachable ==="
```

**STOP. Tell the user:** "Phase 4 complete — lab deployed, Nautobot connected. Ready for Phase 5? (Say continue, or /new to start fresh and say continue demo from Phase 5)"

## Phase 4.5: Verify Connectivity Before Ansible

**Do NOT proceed to Phase 5 until all devices are reachable.** Ansible will fail on unreachable devices and waste time/tokens on retries.

**ONE command — test SSH to one device per role:**
```bash
echo "=== Testing SSH connectivity ===" && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.2 echo "P1 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.6 echo "PE1 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.12 echo "West-Spine01 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.18 echo "East-Leaf01 OK" 2>&1 | tail -1 && echo "=== All roles reachable ==="
```

If any device fails:
- IOL devices (P/PE/CE/RR) take 2-3 minutes to boot after clab deploy. Wait and retry.
- cEOS devices (spine/leaf/DNS) boot faster but may need 60 seconds for SSH.
- If still failing after 5 minutes, check `docker logs clab-nautobot_workshop-<device>` for boot issues.

**Only proceed to Phase 5 when all four test devices respond.**

## Phase 5: Deploy Configs via Ansible — THREE commands max

**Command 1 — Set up Ansible venv and install deps:**
```bash
cd ~/Nautobot-Workshop/ansible-lab && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r pip-requirements.txt && pip install -q --upgrade pynautobot && ansible-galaxy collection install -r galaxy-requirements.yml -p ./ansible_collections 2>&1 | tail -3 && echo "nautobot" > ~/.vault-pass.txt && chmod 600 ~/.vault-pass.txt && echo "=== Ansible ready ==="
```

Note: `pip install --upgrade pynautobot` is required because the workshop pins 2.6.3 but the networktocode.nautobot collection 6.x needs 2.7+ for the `exclude_m2m` parameter.

**Command 2 — Generate configs (use --tags build ONLY):**
```bash
cd ~/Nautobot-Workshop/ansible-lab && . .venv/bin/activate && export NAUTOBOT_TOKEN=0123456789abcdef0123456789abcdef01234567 && ansible-playbook pb.build-lab.yml --tags build
```

**STOP if "Command still running". Tell user to wait 1-3 minutes.**

**Command 3 — Deploy configs (use --tags deploy ONLY):**
```bash
cd ~/Nautobot-Workshop/ansible-lab && . .venv/bin/activate && export NAUTOBOT_TOKEN=0123456789abcdef0123456789abcdef01234567 && ansible-playbook pb.build-lab.yml --tags deploy
```

**STOP if "Command still running". Tell user to wait 2-5 minutes.**

**NEVER run the playbook without --tags** — that re-runs load_nautobot and build_clab_topology, duplicating Phases 3-4.

**STOP. Tell the user:** "Phase 5 complete — configs deployed. Ready for Phase 6? (Say continue, or /new to start fresh and say continue demo from Phase 6)"

## Phase 6: Wire Golden Config

### Step 6-PREREQ: Verify Nautobot can reach lab devices

**Do NOT proceed until this passes.** Golden Config backup jobs need Nautobot to SSH/connect to devices on the clab-mgmt network.

```bash
NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && docker network connect clab-mgmt $NAUTOBOT_CONTAINER 2>/dev/null; CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker-1) && docker network connect clab-mgmt $CELERY_CONTAINER 2>/dev/null; docker exec $NAUTOBOT_CONTAINER ping -c 1 192.168.220.2 && echo "=== Nautobot can reach lab devices ==="
```

If this fails, Nautobot is not connected to the clab-mgmt network. The `docker network connect` commands above fix it. If ping still fails, check that ContainerLab is running (`sudo clab inspect --all`).

The golden config Git repos already exist on GitHub. **Do NOT create new repos, do NOT set up local git servers.** Just register these existing repos in Nautobot.

### Step 6a: Register Git repos in Nautobot — use MCP tools

The repos may be private. The GitHub PAT was added to Nautobot's creds.env in Phase 1. Create a Nautobot secret and secrets group to authenticate, then link it to each repo.

**First, set up authentication:**
```
nautobot_create_secrets_group(name="GitHub Access")
nautobot_create_secret(name="GitHub PAT", provider="environment-variable", parameters='{"variable": "GITHUB_PERSONAL_ACCESS_TOKEN"}')
nautobot_add_secret_to_group(secrets_group_id="<id>", secret_id="<id>", access_type="HTTP(S)", secret_type="token")
```

**Then register each repo with the secrets group:**

```
nautobot_create_git_repository(
  name="golden-config-templates",
  remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_templates.git",
  branch="main",
  provided_contents="nautobot_golden_config.jinjatemplate"
)

nautobot_create_git_repository(
  name="golden-config-intended",
  remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_intended_configs.git",
  branch="main",
  provided_contents="nautobot_golden_config.intendedconfigs"
)

nautobot_create_git_repository(
  name="golden-config-backups",
  remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_backup_configs.git",
  branch="main",
  provided_contents="nautobot_golden_config.backupconfigs"
)

nautobot_create_git_repository(
  name="golden-config-properties",
  remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_properties.git",
  branch="main",
  provided_contents="nautobot_golden_config.configproperties"
)
```

Sync all repos:
```
nautobot_sync_git_repository(name="golden-config-templates")
nautobot_sync_git_repository(name="golden-config-intended")
nautobot_sync_git_repository(name="golden-config-backups")
nautobot_sync_git_repository(name="golden-config-properties")
```

### Step 6b: Configure Golden Config settings — use MCP tools

Create the SoT GraphQL query. This query MUST include BGP routing instances, peer groups, endpoints, config_context, interfaces with custom fields, and location VLANs. Use this EXACT query:

```
nautobot_create_graphql_query(name="nautobot_workshop_sot_agg", query="query { device(id: \"{{ id }}\") { hostname: name config_context bgp_routing_instances { extra_attributes autonomous_system { asn } address_families { afi_safi extra_attributes } peer_groups { name source_interface { name } autonomous_system { asn } extra_attributes secret { name } address_families { import_policy export_policy extra_attributes } peergroup_template { autonomous_system { asn } extra_attributes } address_families { afi_safi import_policy export_policy } } endpoints { peer_group { name } source_ip { address } source_interface { name } description peer { description source_ip { address } address_families { afi_safi import_policy export_policy } autonomous_system { asn } routing_instance { autonomous_system { asn } } } } } position serial role { name } primary_ip4 { id primary_ip4_for { id name } } tenant { name } tags { name } platform { name network_driver manufacturer { name } napalm_driver } location { name vlans { name vid vlan_group { name } } parent { name vlans { name vid vlan_group { name } } } } interfaces { name description mac_address enabled mgmt_only label lag { name } cf_ospf_network_type cf_ospf_area cf_mpls_enabled cf_vrrp_group_id cf_vrrp_ipv4_enabled cf_vrrp_ipv6_enabled cf_vrrp_disabled cf_vrrp_preempt cf_vrrp_priority_level cf_vrrp_advertisement_interval cf_vrrp_bfd_enabled cf_vrrp_mac_advertisement_interval cf_vrrp_peer_address cf_vrrp_session_name cf_vrrp_timer_interval cf_vrrp_tracked_object ip_addresses { address tags { id } } mode tagged_vlans { vid } untagged_vlan { vid } connected_interface { name device { name } } cf_mlag_interface tags { id } } } }")
```

Do NOT create a shorter or simplified query. The templates depend on every field listed above. If BGP data is missing, config generation will fail.

Then link the repos to golden config settings:
```
nautobot_update_golden_config_setting(...)
```

Use the `golden-config-bootstrap` skill for compliance rule setup.

### Step 6c: Run compliance

Ask the user to run compliance from the Nautobot UI:
> Golden Config → Compliance → Run → select devices → review results

### Golden Config GitHub Repos (reference)
- Templates: https://github.com/byrn-baker/nautobot_workshop_golden_config_templates
- Intended configs: https://github.com/byrn-baker/nautobot_workshop_golden_config_intended_configs
- Backup configs: https://github.com/byrn-baker/nautobot_workshop_golden_config_backup_configs
- Properties: https://github.com/byrn-baker/nautobot_workshop_golden_config_properties
- SoT/config: https://github.com/byrn-baker/golden_config_git

## Phase 7: Demo Walkthrough

Demonstrate NetClaw against the live lab:

1. **"Show me all devices"** → `nautobot_get_devices`
2. **"Health check on SP core"** → pyATS against P1-P4, PE1-PE3, RR1
3. **"BGP peering status"** → pyATS show ip bgp summary
4. **"What's out of compliance?"** → golden config results
5. **"Topology diagram"** → Draw.io or UML nwdiag

## Cleanup — ONE command

```bash
sudo clab destroy --all 2>/dev/null; cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke stop 2>/dev/null; docker ps -aq | xargs -r docker rm -f 2>/dev/null; docker network ls --format '{{.Name}}' | grep -v "bridge\|host\|none" | xargs -r docker network rm 2>/dev/null; rm -rf ~/Nautobot-Workshop ~/.vault-pass.txt && echo "=== clean ==="
```

## Resource Requirements

- **CPU:** 20 vCPU recommended
- **RAM:** 32 GB recommended
- **Disk:** 50 GB+
- **Network:** 192.168.220.0/24 (auto-created by ContainerLab)
