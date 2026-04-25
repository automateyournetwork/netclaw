# SKILL: Demo Lab Setup — Nautobot Workshop + ContainerLab + Golden Config

## Purpose

Deploy the byrn-baker/Nautobot-Workshop environment end-to-end.

## When to Use

- User says "set up the demo" or "build the demo lab" or "deploy the workshop"

## CRITICAL RULES

1. **Execute steps 1 through 20 in exact order. Do NOT skip any step.**
2. **MANDATORY STOP after steps 4, 11, 14, 17, and 20.** You MUST stop and say: "Step N complete. Ready for the next step? (Say 'continue' to proceed, or '/new' to start a fresh session and say 'continue demo from Step N+1')" Do NOT proceed until the user says continue.
3. **Use the workshop repo as-is** — do NOT create custom files
4. **Use Invoke** to build/start Nautobot — do NOT run docker compose directly
5. **BATCH COMMANDS** — combine multiple shell commands into ONE exec call using `&&`. Every tool call costs tokens.
6. **NEVER poll builds** — no `process poll` or `process log` on long-running commands.
7. **Use nautobot-mcp-v2 tools** for ALL Nautobot API operations — never curl or docker exec.
8. **Do NOT explore the repo.** Do not ls, cat, grep, find, or read README files. Execute the prescribed commands directly.
9. **NEVER restart Nautobot containers** unless this skill explicitly says to. If an environment variable is missing, tell the user to restart manually.

---

## Step 1: Check Prerequisites

```bash
echo "=== prereqs ===" && docker --version && clab version 2>&1 | head -1 && poetry --version && git --version && echo "=== images ===" && docker images --format '{{.Repository}}:{{.Tag}}' | grep -E "cisco_iol|ceos" && echo "=== done ==="
```

If anything is missing, fix it before proceeding.

## Step 2: Clone Repo and Configure Credentials

```bash
cd ~ && git clone https://github.com/byrn-baker/Nautobot-Workshop.git && cd ~/Nautobot-Workshop/nautobot-docker-compose && cp invoke.example.yml invoke.yml && cp environments/creds.example environments/creds.env && sed -i 's/NAUTOBOT_CREATE_SUPERUSER=false/NAUTOBOT_CREATE_SUPERUSER=true/' environments/creds.env && echo "GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}" >> environments/creds.env && echo "NAUTOBOT_NAPALM_USERNAME=${NETCLAW_USERNAME}" >> environments/creds.env && echo "NAUTOBOT_NAPALM_PASSWORD=${NETCLAW_PASSWORD}" >> environments/creds.env && echo "DEVICE_USERNAME=${NETCLAW_USERNAME}" >> environments/creds.env && echo "DEVICE_PASSWORD=${NETCLAW_PASSWORD}" >> environments/creds.env && echo "=== repo cloned, superuser enabled, GitHub token + device creds added ==="
```

## Step 3: Set Up Poetry

```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry shell && poetry lock && poetry install
```

## Step 4: Build and Start Nautobot

Build the image:
```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke build
```

**STOP after "Command still running". Tell user: "Nautobot image is building (3-5 minutes). Let me know when it's done."**

When user confirms, verify and start:
```bash
docker images | grep nautobot-workshop && cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke debug
```

**STOP after "Command still running". Wait 90 seconds, then check health:**
```bash
sleep 90 && docker ps --format 'table {{.Names}}\t{{.Status}}' | grep nautobot
```

**MANDATORY STOP.** Tell the user: "Step 4 complete — Nautobot is running. Ready for Step 5? (Say continue, or /new and say 'continue demo from Step 5')"

## Step 5: Enable ALL Jobs (user action required)

**Tell the user:**
> Enable ALL jobs in Nautobot before I can proceed:
> 1. Open http://localhost:8080 (admin / admin)
> 2. Navigate to **Jobs** → **Jobs**
> 3. Enable **every job** — Design Builder, Golden Config (Backup, Intended, Compliance, Deploy), and all others
> 4. Tell me when done.

**Wait for confirmation.**

## Step 6: Run Design Builder

```
nautobot_run_job(job_name="Nautobot Workshop Demo Initial Data")
```

Wait for completion, then verify:
```
nautobot_get_devices
```

Should show all 20 devices.

## Step 7: Restart Nautobot (MANDATORY after Design Builder)

Design Builder creates custom fields (cf_ospf_area, cf_mpls_enabled, cf_vrrp_*, cf_mlag_interface). The GraphQL schema will NOT recognize them until containers restart.

```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke restart
```

**STOP after "Command still running". Wait 90 seconds, then check health:**
```bash
sleep 90 && docker ps --format 'table {{.Names}}\t{{.Status}}' | grep nautobot
```

Look for `(healthy)` before proceeding.

## Step 8: Load Config Contexts via Git Data Source

Register the datasource repo:
```
nautobot_create_git_repository(
  name="nautobot-workshop-datasource",
  remote_url="https://github.com/byrn-baker/Nautobot-Workshop-Datasource.git",
  branch="main",
  provided_contents="extras.configcontext,extras.configcontextschema,extras.graphqlquery"
)
```

If the repo is private, link the GitHub Secrets Group (created in Step 10) to this repo.

Sync the repo:
```
nautobot_sync_git_repository(name="nautobot-workshop-datasource")
```

Verify:
```
nautobot_get_config_contexts
```

## Step 9: Create Device Credentials (Secrets + Secrets Group)

Golden Config uses Nornir which gets SSH credentials from Nautobot Secrets Groups.

```
nautobot_create_secrets_group(name="Device Credentials")
nautobot_create_secret(name="Device Username", provider="environment-variable", parameters='{"variable": "DEVICE_USERNAME"}')
nautobot_create_secret(name="Device Password", provider="environment-variable", parameters='{"variable": "DEVICE_PASSWORD"}')
nautobot_add_secret_to_group(secrets_group_id="<id>", secret_id="<username-secret-id>", access_type="Generic", secret_type="username")
nautobot_add_secret_to_group(secrets_group_id="<id>", secret_id="<password-secret-id>", access_type="Generic", secret_type="password")
```

## Step 10: Create GitHub Secrets Group (for private repos)

```
nautobot_create_secrets_group(name="GitHub Access")
nautobot_create_secret(name="GitHub PAT", provider="environment-variable", parameters='{"variable": "GITHUB_PERSONAL_ACCESS_TOKEN"}')
nautobot_add_secret_to_group(secrets_group_id="<id>", secret_id="<id>", access_type="HTTP(S)", secret_type="token")
```

## Step 11: Assign Secrets Groups to All Devices

Get all device IDs:
```
nautobot_graphql query="{ devices { id name } }"
```

For each device, assign the Device Credentials secrets group:
```
nautobot_update_object(object_type="device", identifier="<device-name>", updates='{"secrets_group": "<device-credentials-group-id>"}')
```

Do this for all 20 devices. Without it, Nornir cannot SSH to devices and golden config backup jobs will fail.

**MANDATORY STOP.** Tell the user: "Step 11 complete — Nautobot fully configured with devices, config contexts, and credentials. Ready for Step 12? (Say continue, or /new and say 'continue demo from Step 12')"

## Step 12: Deploy ContainerLab

```bash
cd ~/Nautobot-Workshop/clabs && sudo clab deploy --topo nautobot-workshop-topology.clab.yml
```

**STOP after "Command still running". Tell user: "ContainerLab is deploying 20 nodes (2-5 minutes). Let me know when it's done."**

## Step 13: Connect Nautobot to Lab Network

When user confirms clab is up, verify and connect:
```bash
sudo clab inspect --topo ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml 2>&1 | tail -5 && NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker) && BEAT_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_beat) && docker network connect clab-mgmt $NAUTOBOT_CONTAINER 2>/dev/null; docker network connect clab-mgmt $CELERY_CONTAINER 2>/dev/null; docker network connect clab-mgmt $BEAT_CONTAINER 2>/dev/null && echo "=== Nautobot + celery connected to clab-mgmt ===" && docker exec $NAUTOBOT_CONTAINER python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('192.168.220.2', 22)); print('P1 SSH reachable from Nautobot'); s.close()"
```

**CRITICAL.** Without this, golden config backup jobs WILL fail.

## Step 14: Verify SSH Connectivity Before Ansible

```bash
echo "=== Testing SSH connectivity ===" && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.2 echo "P1 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.6 echo "PE1 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.12 echo "West-Spine01 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.18 echo "East-Leaf01 OK" 2>&1 | tail -1 && echo "=== All roles reachable ==="
```

If any fail, wait 2-3 minutes (IOL devices boot slowly) and retry. Do NOT proceed until all pass.

**MANDATORY STOP.** Tell the user: "Step 14 complete — lab deployed and connectivity verified. Ready for Step 15? (Say continue, or /new and say 'continue demo from Step 15')"

## Step 15: Set Up Ansible

```bash
cd ~/Nautobot-Workshop/ansible-lab && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r pip-requirements.txt && pip install -q --upgrade pynautobot && ansible-galaxy collection install -r galaxy-requirements.yml -p ./ansible_collections 2>&1 | tail -3 && echo "nautobot" > ~/.vault-pass.txt && chmod 600 ~/.vault-pass.txt && echo "=== Ansible ready ==="
```

## Step 16: Generate Device Configs

**Use --tags build ONLY. NEVER run without tags.**
```bash
cd ~/Nautobot-Workshop/ansible-lab && . .venv/bin/activate && export NAUTOBOT_TOKEN=0123456789abcdef0123456789abcdef01234567 && ansible-playbook pb.build-lab.yml --tags build
```

## Step 17: Deploy Device Configs

**Use --tags deploy ONLY.**
```bash
cd ~/Nautobot-Workshop/ansible-lab && . .venv/bin/activate && export NAUTOBOT_TOKEN=0123456789abcdef0123456789abcdef01234567 && ansible-playbook pb.build-lab.yml --tags deploy
```

**MANDATORY STOP.** Tell the user: "Step 17 complete — configs deployed to all devices. Ready for Step 18? (Say continue, or /new and say 'continue demo from Step 18')"

## Step 18: Register Golden Config Git Repos

First verify Nautobot can reach lab devices:
```bash
NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && docker network connect clab-mgmt $NAUTOBOT_CONTAINER 2>/dev/null; CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker-1) && docker network connect clab-mgmt $CELERY_CONTAINER 2>/dev/null; docker exec $NAUTOBOT_CONTAINER python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('192.168.220.2', 22)); print('P1 SSH reachable'); s.close()" && echo "=== Nautobot can reach lab devices ==="
```

Then register each repo (link GitHub Secrets Group from Step 10 to each):
```
nautobot_create_git_repository(name="nautobot_workshop_templates", remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_templates.git", branch="main", provided_contents="nautobot_golden_config.jinjatemplate")
nautobot_create_git_repository(name="nautobot_workshop_intended", remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_intended_configs.git", branch="main", provided_contents="nautobot_golden_config.intendedconfigs")
nautobot_create_git_repository(name="nautobot_workshop_backup", remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_backup_configs.git", branch="main", provided_contents="nautobot_golden_config.backupconfigs")
```

Sync all repos:
```
nautobot_sync_git_repository(name="nautobot_workshop_templates")
nautobot_sync_git_repository(name="nautobot_workshop_intended")
nautobot_sync_git_repository(name="nautobot_workshop_backup")
```

## Step 19: Configure Golden Config Settings

Get the golden config setting ID and all repo IDs:
```
nautobot_get_golden_config_settings
nautobot_get_git_repositories
```

Update the setting with ALL repos, the SoT query, and path templates. **Every field is required — if any repo is null, jobs crash.**
```
nautobot_update_golden_config_setting(
  setting_id="<golden-config-setting-id>",
  updates='{
    "sot_agg_query": "<sot-query-id>",
    "jinja_repository": "<templates-repo-id>",
    "intended_repository": "<intended-configs-repo-id>",
    "backup_repository": "<backup-configs-repo-id>",
    "jinja_path_template": "{{ obj.platform.network_driver }}.j2",
    "intended_path_template": "{{ obj.location.name }}/{{ obj.name }}.cfg",
    "backup_path_template": "{{ obj.location.name }}/{{ obj.name }}.cfg"
  }'
)
```

Verify:
```
nautobot_get_golden_config_settings
```

Confirm `jinja_repository`, `intended_repository`, `backup_repository`, and `sot_agg_query` are ALL non-null.

## Step 20: Run Golden Config Jobs

Run intended config generation:
```
nautobot_run_job(job_name="Generate Intended Configurations")
```

Run backup:
```
nautobot_run_job(job_name="Backup Configurations")
```

Run compliance:
```
nautobot_run_job(job_name="Run Compliance")
```

**MANDATORY STOP.** Tell the user: "Step 20 complete — Golden Config fully bootstrapped. Intended configs generated, backups collected, compliance run. Ready for demo walkthrough?"

## Demo Walkthrough

1. **"Show me all devices"** → `nautobot_get_devices`
2. **"Health check on SP core"** → pyATS against P1-P4, PE1-PE3, RR1
3. **"BGP peering status"** → pyATS show ip bgp summary
4. **"What's out of compliance?"** → golden config results
5. **"Topology diagram"** → Draw.io or UML nwdiag

## Cleanup — ONE command

```bash
sudo clab destroy --all 2>/dev/null; cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke stop 2>/dev/null; docker ps -aq | xargs -r docker rm -f 2>/dev/null; docker volume ls -q | xargs -r docker volume rm -f 2>/dev/null; docker network ls --format '{{.Name}}' | grep -v "bridge\|host\|none" | xargs -r docker network rm 2>/dev/null; rm -rf ~/Nautobot-Workshop ~/.vault-pass.txt && echo "=== clean ==="
```

## Golden Config GitHub Repos (reference)
- Datasource (contexts, schemas, queries): https://github.com/byrn-baker/Nautobot-Workshop-Datasource
- Templates: https://github.com/byrn-baker/nautobot_workshop_golden_config_templates
- Intended configs: https://github.com/byrn-baker/nautobot_workshop_golden_config_intended_configs
- Backup configs: https://github.com/byrn-baker/nautobot_workshop_golden_config_backup_configs
- Properties: https://github.com/byrn-baker/nautobot_workshop_golden_config_properties

## Resource Requirements
- **CPU:** 20 vCPU recommended
- **RAM:** 32 GB recommended
- **Disk:** 50 GB+
- **Network:** 192.168.220.0/24 (auto-created by ContainerLab)
