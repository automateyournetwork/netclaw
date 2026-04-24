# SKILL: Demo Lab Setup — Nautobot Workshop + ContainerLab + Golden Config

## Purpose

Deploy the byrn-baker/Nautobot-Workshop environment end-to-end:
1. Clone the workshop repo (includes nautobot-docker-compose, ContainerLab topology, Ansible roles, Design Builder jobs)
2. Stand up Nautobot 2.4.10 with all workshop plugins
3. Deploy the ContainerLab topology (20 nodes: Cisco IOL SP core + Arista cEOS EVPN/VXLAN fabric)
4. Run Design Builder to populate Nautobot with the full data model
5. Deploy device configs via Ansible
6. Wire golden config compliance

This is the showcase demo for NetClaw — an AI agent that can build and operate an entire network automation stack from conversation.

## When to Use

- User says "set up the demo" or "build the demo lab" or "deploy the workshop"
- User wants to demonstrate NetClaw + Nautobot + ContainerLab end-to-end
- User wants the byrn-baker/Nautobot-Workshop environment running

## CRITICAL RULES

1. **Follow the phases in order** — each depends on the previous
2. **Wait for user confirmation** between phases — this is a demo, the user needs to see each step
3. **Use the workshop repo as-is** — do NOT create custom docker-compose, topology, or Ansible files
4. **Use Poetry 1.5.x** — newer versions break the nautobot-docker-compose tasks.py
5. **Use Invoke** to build/start Nautobot — do NOT run docker compose directly
6. **Minimize token usage** — follow the cost control rules below

## Cost Control Rules

Long-running commands (docker builds, ansible playbooks, clab deploy) generate massive output that inflates the context window. Every poll sends the full conversation history. Follow these rules:

1. **Fire and forget long builds.** Start `invoke build` or `invoke debug` as a background process, then immediately tell the user: "The build is running. This takes 3-5 minutes. Let me know when it's done, or I'll check back in 5 minutes." Do NOT poll every 15 seconds.
2. **Poll at most twice.** For any long-running command: once after 2-3 minutes, once more if still running. If it's still going after that, tell the user to confirm when it completes.
3. **Don't log full build output.** Never use `process log` to dump Docker build output into the conversation. If you need to check for errors, use `process poll` with a timeout — it returns only new output.
4. **Suggest session breaks between phases.** After completing a phase, tell the user: "Phase N is done. To keep costs down, you can start a new session for Phase N+1 — just say 'continue the demo from Phase N+1'." This resets the context window.
5. **Use MCP tools, not shell commands.** MCP tool results are typically small JSON. Shell commands (docker exec, curl, ansible-playbook) dump verbose output that bloats context. Always prefer nautobot-mcp-v2 tools over curl/docker exec for Nautobot operations.
6. **Summarize, don't echo.** When a command completes, summarize the result in 1-2 sentences. Do NOT paste the full output back to the user unless they ask for it.

## Prerequisites

Check before starting:
```bash
docker --version          # Docker 24+
clab version              # ContainerLab 0.69+
poetry --version          # Poetry 1.5.x (pip install "poetry>=1.5.0,<1.6.0")
ansible --version         # Ansible 2.15+
git --version
```

If ContainerLab is missing:
```bash
bash -c "$(curl -sL https://get.containerlab.dev)"
```

If Poetry is wrong version:
```bash
pip install "poetry>=1.5.0,<1.6.0"
```

Required container images (must be pre-imported):
- `vrnetlab/cisco_iol:17.12.01` — Cisco IOL for P/PE/CE/RR routers
- `ceos:4.34.0F` — Arista cEOS for spine/leaf/DNS switches

Verify images:
```bash
docker images | grep -E "cisco_iol|ceos"
```

## Workshop Topology

20 nodes on management network 192.168.220.0/24:

### SP Core (Cisco IOL 17.12.01)
| Device | Role | Mgmt IP |
|--------|------|---------|
| P1 | P router | 192.168.220.2 |
| P2 | P router | 192.168.220.3 |
| P3 | P router | 192.168.220.4 |
| P4 | P router | 192.168.220.5 |
| PE1 | PE router | 192.168.220.6 |
| PE2 | PE router | 192.168.220.7 |
| PE3 | PE router | 192.168.220.8 |
| CE1 | CE router | 192.168.220.9 |
| CE2 | CE router | 192.168.220.10 |
| RR1 | Route Reflector | 192.168.220.11 |

### EVPN/VXLAN Fabric (Arista cEOS 4.34.0F)
| Device | Role | Mgmt IP |
|--------|------|---------|
| West-Spine01 | Spine | 192.168.220.12 |
| West-Spine02 | Spine | 192.168.220.13 |
| West-Leaf01 | Leaf | 192.168.220.14 |
| West-Leaf02 | Leaf | 192.168.220.15 |
| East-Spine01 | Spine | 192.168.220.16 |
| East-Spine02 | Spine | 192.168.220.17 |
| East-Leaf01 | Leaf | 192.168.220.18 |
| East-Leaf02 | Leaf | 192.168.220.19 |
| DNS-01 | DNS server | 192.168.220.20 |
| DNS-02 | DNS server | 192.168.220.21 |

## Phase 0: Provision the Lab VM (Proxmox)

If the lab VM doesn't exist yet, use the Proxmox MCP tools to create it.

### Step 0a: Check existing VMs

```
proxmox_get_nodes
proxmox_get_vms
```

### Step 0b: Create the lab VM

Requires `PROXMOX_ALLOW_ELEVATED=true` in the environment.

```
proxmox_create_vm(
  node="pve",
  name="netclaw-lab",
  cores=20,
  memory=32768,
  disk_size="100G"
)
```

Recommended specs: 20 vCPU, 32 GB RAM, 100 GB disk (Ubuntu 22.04 or 24.04).

After the VM is running, SSH in and proceed with Phase 1.

If Proxmox MCP is not configured, **ask the user to create the VM manually** and provide the IP when ready.

## Phase 1: Clone the Workshop Repo

```bash
cd ~
git clone https://github.com/byrn-baker/Nautobot-Workshop.git
cd Nautobot-Workshop
```

Verify the structure:
```bash
ls -d clabs/ nautobot-docker-compose/ ansible-lab/ jobs/
```

## Phase 2: Deploy Nautobot

### Step 2a: Set up nautobot-docker-compose

```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose
cp invoke.example.yml invoke.yml
cp environments/creds.example environments/creds.env
```

Enable auto-creation of the superuser (admin/admin):
```bash
sed -i 's/NAUTOBOT_CREATE_SUPERUSER=false/NAUTOBOT_CREATE_SUPERUSER=true/' environments/creds.env
```

This sets `NAUTOBOT_CREATE_SUPERUSER=true` so the container automatically creates the admin user with password `admin` and the default API token on first start.

### Step 2b: Poetry environment

```bash
poetry shell
poetry lock
poetry install
```

The pyproject.toml pins Nautobot 2.4.10 with these plugins:
- nautobot-plugin-nornir
- nautobot-bgp-models
- nautobot-golden-config
- nautobot-design-builder
- nautobot-device-lifecycle-mgmt
- nautobot-ssot
- nautobot-device-onboarding
- pyavd, pyats[full], genie, ntc-templates

### Step 2c: Build and start

```bash
invoke build
```

**IMPORTANT: `invoke build` takes 3-5 minutes.** Start it as a background process, tell the user it's building, and check back once after 3 minutes. Do NOT poll repeatedly. When the build completes (exit code 0), proceed to:

```bash
invoke debug
```

**IMPORTANT: `invoke debug` takes 1-2 minutes to become healthy.** Start it, tell the user to wait, and check once after 90 seconds. Verify with:

```bash
docker ps --format 'table {{.Names}}\t{{.Status}}' | grep nautobot
```

Look for `(healthy)` status. Default login: admin/admin at http://localhost:8080.

### Step 2d: Note on management network

The ContainerLab topology defines its own management network (`clab-mgmt` at 192.168.220.0/24). ContainerLab creates this network automatically during `clab deploy` — no manual bridge creation needed.

After the lab is deployed (Phase 4), connect the Nautobot containers to it:

```bash
docker network connect clab-mgmt nautobot-docker-compose-nautobot-1
docker network connect clab-mgmt nautobot-docker-compose-celery_worker-1
```

This step happens after Phase 4, not here — just noting it for awareness.

## Phase 3: Populate Nautobot with Design Builder

The workshop includes a Design Builder job that creates the full data model — locations, devices, interfaces, IPs, prefixes, BGP peering, OSPF custom fields, VLANs, everything.

### Step 3a: Enable required jobs

The Design Builder and Golden Config jobs must be enabled before they can run. The nautobot-mcp-v2 tools cannot enable jobs — this requires the Nautobot UI.

**Ask the user to do this manually:**

> I need you to enable the Design Builder and Golden Config jobs in Nautobot before I can proceed.
>
> 1. Open http://localhost:8080 and log in (admin / admin)
> 2. Navigate to **Jobs** → **Jobs**
> 3. Find and enable these jobs:
>    - **Nautobot Workshop Demo Initial Data** (Design Builder)
>    - Any Golden Config jobs (compliance, intended, backup)
> 4. Let me know when they're enabled.

**Wait for user confirmation before proceeding.**

### Step 3b: Run the initial data design

Once the user confirms jobs are enabled:

1. In the Nautobot UI: **Design** → **Design Builder** (right sidebar)
2. Select **Nautobot Workshop Demo Initial Data**
3. Click **Run**
4. Wait for completion — this creates all devices, interfaces, IPs, BGP sessions, OSPF config, VLANs

Alternatively, ask the user to run it and confirm when done.

### Step 3c: Verify the data model

After the job completes, use the nautobot-mcp-v2 tools to verify:

```
nautobot_get_devices
nautobot_get_interfaces(device="P1")
nautobot_graphql query="{ devices { name role { name } location { name } primary_ip4 { host } platform { name } } }"
nautobot_get_prefixes
nautobot_get_vlans
```

**Always use nautobot-mcp-v2 tools for Nautobot API operations** — do NOT use docker exec, curl, or direct API calls. The MCP server handles authentication, pagination, and error handling.

## Phase 4: Deploy ContainerLab Topology

**Deploy directly from the workshop's clab topology file.** Do NOT use the Ansible playbook to create the topology — that would duplicate it.

### Step 4a: Deploy the lab

```bash
cd ~/Nautobot-Workshop/clabs
sudo clab deploy --topo nautobot-workshop-topology.clab.yml
```

**IMPORTANT: `clab deploy` takes 2-5 minutes for 20 nodes.** Start it, tell the user it's deploying, and check once after 3 minutes. Do NOT poll repeatedly. When it completes, run `clab inspect` once to verify.

### Step 4b: Verify the lab

```bash
sudo clab inspect --topo nautobot-workshop-topology.clab.yml
```

Verify management connectivity from the host:
```bash
ping -c 2 192.168.220.2   # P1
ping -c 2 192.168.220.12  # West-Spine01
ping -c 2 192.168.220.18  # East-Leaf01
```

### Step 4c: Connect Nautobot to the lab network

Now that ContainerLab has created the `clab-mgmt` network, connect Nautobot:

```bash
docker network connect clab-mgmt nautobotworkshop-docker-compose-nautobot-1
docker network connect clab-mgmt nautobotworkshop-docker-compose-celery_worker-1
```

Note: The container names may vary. Check with `docker ps` for the actual names.

Verify Nautobot can reach lab devices:
```bash
docker exec nautobotworkshop-docker-compose-nautobot-1 ping -c 2 192.168.220.2
```

## Phase 5: Deploy Device Configurations via Ansible

The workshop includes Ansible roles to generate and deploy configs. The inventory uses Nautobot's GraphQL plugin, so **Design Builder must have run first** (Phase 3) before Ansible can discover devices.

### Step 5a: Set up the Ansible virtual environment

```bash
cd ~/Nautobot-Workshop/ansible-lab
python3 -m venv .venv
source .venv/bin/activate
pip install -r pip-requirements.txt
```

This installs: ansible 10.7.0, pynautobot, netaddr, netutils, paramiko, aristaproto, and other dependencies.

### Step 5b: Install Ansible Galaxy collections

```bash
ansible-galaxy collection install -r galaxy-requirements.yml -p ./ansible_collections
```

This installs `arista.avd` (>=5.4.0) and `networktocode.nautobot` (>=5.11.0).

### Step 5c: Create the vault password file

The ansible.cfg expects `~/.vault-pass.txt`. The workshop's vault.yml is plaintext (not encrypted), but Ansible still needs the file to exist:

```bash
echo "nautobot" > ~/.vault-pass.txt
chmod 600 ~/.vault-pass.txt
```

### Step 5d: Generate device configs

**Use `--tags build` only** — do NOT run the playbook without tags (that would re-run load_nautobot and build_clab_topology, duplicating work already done in Phases 3-4).

```bash
ansible-playbook pb.build-lab.yml --tags build
```

**IMPORTANT: Ansible runs take 1-3 minutes.** Start it, tell the user, check once after 2 minutes. Do NOT poll repeatedly.

This generates configs under `ansible-lab/configs/` using Jinja2 templates and Nautobot data via the GraphQL inventory plugin.

### Step 5e: Deploy configs to running lab devices

```bash
ansible-playbook pb.build-lab.yml --tags deploy
```

**IMPORTANT: Deploy takes 2-5 minutes across 20 devices.** Same rule — start it, tell the user, check once.

### Step 5f: Verify

SSH into a device and check:
```bash
ssh admin@192.168.220.12   # West-Spine01 (cEOS, admin/admin)
show ip bgp summary
show ip ospf neighbor
```

For IOL devices:
```bash
ssh admin@192.168.220.2    # P1 (IOL, admin/admin)
show ip ospf neighbor
show mpls ldp neighbor
```

## Phase 6: Wire Golden Config

With Nautobot populated and devices configured, set up golden config compliance.

### Step 6a: Create a golden config Git repository

The workshop's `nautobot-docker-compose/jobs/templates/` directory contains Jinja2 templates. These can be committed to a Git repo that Nautobot's golden config plugin tracks.

Use the `golden-config-bootstrap` skill for the full interactive workflow, or manually:

1. Create a Git repo in Nautobot (Extensibility → Git Repositories)
2. Point it at a GitHub repo containing Jinja2 templates
3. Create a GraphQL SoT aggregation query
4. Create compliance features and rules
5. Run the first compliance job

### Step 6b: Run compliance

In Nautobot UI:
1. **Golden Config** → **Compliance** → **Run**
2. Select all devices or a subset
3. Review results — intended vs actual config diffs

## Phase 7: Demo Walkthrough

Once everything is running, demonstrate NetClaw's capabilities against the live lab:

1. **"Show me all devices in Nautobot"** → nautobot_get_devices
2. **"Health check on the SP core"** → pyATS against P1-P4, PE1-PE3, RR1
3. **"Show BGP peering status"** → pyATS show ip bgp summary on PE routers
4. **"What's out of compliance?"** → golden config compliance results
5. **"Reconcile Nautobot against the live network"** → nautobot-sot reconciliation
6. **"Generate a topology diagram"** → Draw.io or UML nwdiag from Nautobot data
7. **"Trace the path from CE1 to CE2"** → pyATS traceroute + routing table analysis

## Nautobot Version Notes

The workshop targets Nautobot **2.4.10** (pinned in pyproject.toml). Key considerations for 3.x:

- **Design Builder** — check plugin compatibility before upgrading
- **Golden Config** — v2.4.x is the latest for Nautobot 2.x; 3.x may need newer plugin versions
- **GraphQL schema** — field names may change between major versions
- **nautobot-mcp-v2** — currently targets Nautobot 2.x GraphQL schema

**Recommendation:** Stay on 2.4.10 for the demo. The workshop is tested against it and all plugins are compatible.

## Model Selection Notes

The demo uses `qwen3-coder:480b` via Ollama Cloud. Observations:
- Strong at following multi-step skill procedures
- Good at interpreting CLI output from pyATS
- Handles GraphQL query construction well
- Test with your specific skill workflows — some models follow numbered steps more reliably than others

## Session Break Strategy

To minimize cost, suggest session breaks at these natural boundaries:

- **After Phase 2** (Nautobot running) — "Nautobot is up. Start a new session and say 'continue demo from Phase 3' to keep costs down."
- **After Phase 4** (ContainerLab deployed) — "Lab is deployed. Start a new session for Ansible config deployment."
- **After Phase 5** (configs deployed) — "Configs are pushed. Start a new session for golden config and the demo walkthrough."

Each new session resets the context window from potentially 200k+ tokens back to ~50k (system prompt + skills).

## Cleanup

```bash
# Stop ContainerLab
cd ~/Nautobot-Workshop/clabs
sudo clab destroy --topo nautobot-workshop-topology.clab.yml

# Stop Nautobot
cd ~/Nautobot-Workshop/nautobot-docker-compose
invoke stop

# Remove everything
rm -rf ~/Nautobot-Workshop
```

## Resource Requirements

- **CPU:** 20 vCPU recommended (50% utilization with full lab)
- **RAM:** 32 GB recommended (20 GB used with full lab)
- **Disk:** 50 GB+ (container images are large)
- **Network:** Management bridge at 192.168.220.0/24
