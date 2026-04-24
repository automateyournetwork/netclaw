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

## Prerequisites — ONE command

Run this single command to check all prerequisites:
```bash
echo "=== prereqs ===" && docker --version && clab version 2>&1 | head -1 && poetry --version && git --version && echo "=== images ===" && docker images --format '{{.Repository}}:{{.Tag}}' | grep -E "cisco_iol|ceos" && echo "=== done ==="
```

If anything is missing, fix it before proceeding.

## Phase 1: Clone and Set Up — ONE command

```bash
cd ~ && git clone https://github.com/byrn-baker/Nautobot-Workshop.git && cd ~/Nautobot-Workshop/nautobot-docker-compose && cp invoke.example.yml invoke.yml && cp environments/creds.example environments/creds.env && sed -i 's/NAUTOBOT_CREATE_SUPERUSER=false/NAUTOBOT_CREATE_SUPERUSER=true/' environments/creds.env && echo "=== repo cloned, nautobot-docker-compose configured, superuser enabled ==="
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

### Step 3a: Enable jobs (user action required)

**Tell the user:**
> Enable the Design Builder and Golden Config jobs in Nautobot:
> 1. Open http://localhost:8080 (admin / admin)
> 2. Jobs → Jobs → enable **Nautobot Workshop Demo Initial Data**
> 3. Enable any Golden Config jobs
> 4. Tell me when done.

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

Should show all 20 devices. If it does, Phase 3 is done.

**Suggest session break:** "Phase 3 done — Nautobot populated. Start a new session and say 'continue demo from Phase 4'."

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
cd ~/Nautobot-Workshop/ansible-lab && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r pip-requirements.txt && ansible-galaxy collection install -r galaxy-requirements.yml -p ./ansible_collections 2>&1 | tail -3 && echo "nautobot" > ~/.vault-pass.txt && chmod 600 ~/.vault-pass.txt && echo "=== Ansible ready ==="
```

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

Nautobot's Golden Config plugin needs a Git repository containing Jinja2 templates. **Use a GitHub repo — do NOT set up a local git server (nginx, gitea, etc.).** The Nautobot container can clone directly from GitHub.

### Step 6a: Create GitHub repo and push templates — use GitHub MCP

The workshop has templates at `~/Nautobot-Workshop/nautobot-docker-compose/jobs/templates/`. Use the GitHub MCP to create a repo and push them:

```
github_create_repository(name="nautobot-golden-config-templates", description="Golden config Jinja2 templates for Nautobot Workshop", private=false, auto_init=true)
```

Then push the template files using the GitHub MCP:
```
github_push_files(owner="<USER>", repo="nautobot-golden-config-templates", branch="main", files=[...], message="Add golden config templates")
```

Read the template files from disk first, then push them via the MCP. Do NOT use `git init` / `git push` shell commands — the GitHub MCP handles authentication and repo creation.

If GitHub MCP is not configured (no `GITHUB_PERSONAL_ACCESS_TOKEN`), **ask the user to create a public repo and provide the URL**. Do NOT set up a local git server (nginx, gitea, etc.).

### Step 6b: Configure Golden Config in Nautobot — use MCP tools

```
nautobot_create_git_repository(
  name="golden-config-templates",
  remote_url="https://github.com/<USER>/nautobot-golden-config-templates.git",
  branch="main",
  provided_contents="nautobot_golden_config.jinjatemplate"
)
```

Then sync the repo:
```
nautobot_sync_git_repository(name="golden-config-templates")
```

Create the SoT query and compliance settings using the `golden-config-bootstrap` skill.

### Step 6c: Run compliance

Ask the user to run compliance from the Nautobot UI:
> Golden Config → Compliance → Run → select devices → review results

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
