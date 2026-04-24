# SKILL: Demo Lab Setup — Nautobot Workshop + ContainerLab + Golden Config

## Purpose

Deploy the byrn-baker/Nautobot-Workshop environment end-to-end.

## When to Use

- User says "set up the demo" or "build the demo lab" or "deploy the workshop"

## CRITICAL RULES

1. **Follow the phases in order**
2. **Wait for user confirmation** between phases
3. **Use the workshop repo as-is** — do NOT create custom files
4. **Use Invoke** to build/start Nautobot — do NOT run docker compose directly
5. **BATCH COMMANDS** — combine multiple shell commands into ONE exec call using `&&`. Every tool call costs tokens. Aim for 1-3 exec calls per phase, not 10-20.
6. **NEVER poll builds** — no `process poll` or `process log` on long-running commands. Run it, get "still running", tell user to wait, check result once with a tiny command.
7. **Use nautobot-mcp-v2 tools** for ALL Nautobot API operations — never curl or docker exec.
8. **Suggest session breaks** between phases to reset context.
9. **Do NOT explore the repo.** Do not ls, cat, grep, find, or read README files. This skill has all the information you need. Execute the prescribed commands directly.
10. **NEVER restart Nautobot containers.** Do not run docker compose down/up, invoke stop/start, or any command that restarts the Nautobot stack. If an environment variable is missing, add it to creds.env and tell the user to restart manually.

## Prerequisites — ONE command

Run this single command to check all prerequisites:
```bash
echo "=== prereqs ===" && docker --version && clab version 2>&1 | head -1 && poetry --version && git --version && echo "=== images ===" && docker images --format '{{.Repository}}:{{.Tag}}' | grep -E "cisco_iol|ceos" && echo "=== done ==="
```

If anything is missing, fix it before proceeding.

## Phase 1: Clone and Set Up — ONE command

```bash
cd ~ && git clone https://github.com/byrn-baker/Nautobot-Workshop.git && cd ~/Nautobot-Workshop/nautobot-docker-compose && cp invoke.example.yml invoke.yml && cp environments/creds.example environments/creds.env && sed -i 's/NAUTOBOT_CREATE_SUPERUSER=false/NAUTOBOT_CREATE_SUPERUSER=true/' environments/creds.env && echo "GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}" >> environments/creds.env && echo "=== repo cloned, superuser enabled, GitHub token added ==="
```

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

**Suggest session break:** "Phase 2 done — Nautobot is running. To save tokens, start a new session and say 'continue demo from Phase 3'."

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

### Step 3c: Load config contexts

Design Builder creates devices, interfaces, IPs, and BGP but does NOT create config contexts. The config contexts are in the workshop repo and must be loaded separately.

**ONE command:**
```bash
cd ~/Nautobot-Workshop && python3 -c "import json,os,yaml,requests; token='0123456789abcdef0123456789abcdef01234567'; headers={'Authorization':f'Token {token}','Content-Type':'application/json'}; base='http://localhost:8080/api'; [requests.post(f'{base}/extras/config-contexts/',json=item,headers=headers) for d in ['config_contexts'] if os.path.isdir(d) for f in sorted(os.listdir(d)) if f.endswith(('.yml','.yaml')) for item in ([yaml.safe_load(open(os.path.join(d,f)))] if not isinstance(yaml.safe_load(open(os.path.join(d,f))),list) else yaml.safe_load(open(os.path.join(d,f))))]; print('Config contexts loaded')"
```

Verify:
```
nautobot_get_config_contexts
```

**Suggest session break:** "Phase 3 done — Nautobot populated with devices and config contexts. Start a new session and say 'continue demo from Phase 4'."

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

**Suggest session break:** "Phase 4 done — lab deployed, Nautobot connected. Start a new session for 'continue demo from Phase 5'."

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

**Suggest session break:** "Phase 5 done — configs deployed. Start a new session for golden config and demo walkthrough."

## Phase 6: Wire Golden Config

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

Create the SoT GraphQL query and link the repos to golden config settings:
```
nautobot_create_graphql_query(name="golden_config_sot", query="...")
nautobot_update_golden_config_setting(...)
```

Use the `golden-config-bootstrap` skill for the full SoT query and compliance rule setup.

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
