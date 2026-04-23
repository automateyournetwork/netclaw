# SKILL: Demo Lab Setup — ContainerLab + Nautobot + Golden Config

## Purpose

Deploy a complete demo environment from scratch using natural language:
1. A ContainerLab network topology with routers/switches
2. A Nautobot dev instance (via nautobot-docker-compose)
3. Network connectivity between Nautobot and the lab devices
4. Device onboarding into Nautobot
5. Golden Config bootstrap (templates, compliance, intended configs)

This is the showcase demo for NetClaw — proving an AI agent can build an entire network automation stack from a single conversation.

## When to Use

- User says "set up the demo" or "build the demo lab"
- User wants to demonstrate NetClaw + Nautobot + ContainerLab end-to-end
- User wants a self-contained lab environment for golden config testing

## CRITICAL RULES

1. **Follow the phases in order** — each phase depends on the previous one
2. **Wait for user confirmation** between phases — this is a demo, the user needs to see each step
3. **Use MCP tools** for Nautobot operations — never exec/curl
4. **Use exec** for shell commands (git, docker, clab, poetry, invoke) — these have no MCP
5. **Read the sub-skills** before executing their phases — nautobot-dev-setup and golden-config-bootstrap have detailed procedures

## Prerequisites

The following must be installed on the host (the bare-metal install script handles these):
- Docker and Docker Compose
- ContainerLab (`bash -c "$(curl -sL https://get.containerlab.dev)"`)
- Poetry 1.5.x (`pip install "poetry>=1.5.0,<1.6.0"`)
- Git

Check prerequisites before starting:
```bash
docker --version
clab version
poetry --version
git --version
```

If ContainerLab is not installed:
```bash
bash -c "$(curl -sL https://get.containerlab.dev)"
```

## Phase 1: Gather Demo Requirements

Ask the user:

1. **Lab topology** — what devices? Suggest a default:
   - 2x Arista cEOS switches (leaf1, leaf2) — or SR Linux if cEOS images aren't available
   - 1x FRR router (spine1)
   - This gives a simple leaf-spine to demonstrate golden config across multiple devices

2. **Nautobot plugins** — suggest the standard set:
   - nautobot-golden-config
   - nautobot-bgp-models
   - nautobot-firewall-models
   - nautobot-igp-models
   - nautobot-plugin-nornir
   - nautobot-ssot
   - nautobot-device-onboarding
   - welcome-wizard

3. **GitHub repo** for golden config templates — ask for org/user name

4. **Confirm the plan** before proceeding

## Phase 2: Deploy ContainerLab Topology

### Step 2a: Create the topology file

Create a ContainerLab topology YAML file. The topology MUST include a management network that Nautobot can reach.

```bash
mkdir -p ~/demo-lab
```

Write the topology file at `~/demo-lab/topology.yml`:

```yaml
name: netclaw-demo

mgmt:
  network: netclaw-mgmt
  ipv4-subnet: 172.20.20.0/24

topology:
  nodes:
    leaf1:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux:latest
      type: ixrd2l
      mgmt-ipv4: 172.20.20.11
    leaf2:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux:latest
      type: ixrd2l
      mgmt-ipv4: 172.20.20.12
    spine1:
      kind: nokia_srlinux
      image: ghcr.io/nokia/srlinux:latest
      type: ixrd3l
      mgmt-ipv4: 172.20.20.13

  links:
    - endpoints: ["leaf1:e1-49", "spine1:e1-1"]
    - endpoints: ["leaf2:e1-49", "spine1:e1-2"]
    - endpoints: ["leaf1:e1-50", "leaf2:e1-50"]
```

If the user wants Arista cEOS instead (requires cEOS image to be imported):
```yaml
    leaf1:
      kind: ceos
      image: ceos:latest
      mgmt-ipv4: 172.20.20.11
```

If the user wants FRR (lightweight, no license needed):
```yaml
    spine1:
      kind: linux
      image: frrouting/frr:latest
      mgmt-ipv4: 172.20.20.13
```

### Step 2b: Deploy the topology

```bash
cd ~/demo-lab
sudo clab deploy --topo topology.yml
```

Wait for deployment to complete. Then verify:
```bash
sudo clab inspect --topo topology.yml
```

This shows the management IPs for each node. Record them — Nautobot needs these.

### Step 2c: Verify connectivity

```bash
ping -c 2 172.20.20.11
ping -c 2 172.20.20.12
ping -c 2 172.20.20.13
```

**Present the topology and management IPs to the user before proceeding.**

## Phase 3: Deploy Nautobot Dev Instance

**Read and follow the `skills/nautobot-dev-setup/SKILL.md` skill for this phase.**

Key additions for the demo:

### Step 3a: Clone and set up nautobot-docker-compose

Follow the nautobot-dev-setup skill exactly — clone the repo, use Poetry, add plugins.

### Step 3b: Connect Nautobot to the ContainerLab management network

After `invoke build` but BEFORE `invoke start`, connect the Nautobot container to the ContainerLab management network.

Edit the `environments/docker-compose.local.yml` to add the external network:

```yaml
services:
  nautobot:
    command: "nautobot-server runserver 0.0.0.0:8080"
    ports:
      - "8080:8080"
    volumes:
      - "../config/nautobot_config.py:/opt/nautobot/nautobot_config.py"
      - "../jobs:/opt/nautobot/jobs"
    networks:
      - default
      - clab-mgmt
    healthcheck:
      interval: "30s"
      timeout: "10s"
      start_period: "60s"
      retries: 3
      test: ["CMD", "true"]
  celery_worker:
    volumes:
      - "../config/nautobot_config.py:/opt/nautobot/nautobot_config.py"
      - "../jobs:/opt/nautobot/jobs"
    networks:
      - default
      - clab-mgmt

networks:
  clab-mgmt:
    external: true
    name: netclaw-mgmt
```

The `netclaw-mgmt` network was created by ContainerLab in Phase 2. This connects the Nautobot container to the same network as the lab devices.

### Step 3c: Start Nautobot and verify connectivity

```bash
cd ~/nautobot-dev
invoke start
```

Wait for healthy status, then verify Nautobot can reach the lab devices:

```bash
docker compose -f environments/docker-compose.postgres.yml -f environments/docker-compose.base.yml -f environments/docker-compose.local.yml exec nautobot ping -c 2 172.20.20.11
```

### Step 3d: Create superuser and get API token

Follow the nautobot-dev-setup skill Phase 10-11.

## Phase 4: Onboard Lab Devices into Nautobot

Once Nautobot is running and connected to the lab network:

### Step 4a: Create platform and device type

Use nautobot-mcp tools to create the necessary objects:

For SR Linux devices:
- Platform: name=`nokia_srlinux`, network_driver=`srlinux`
- Device Type: model=`ixrd2l` (or `ixrd3l` for spine), manufacturer=`Nokia`
- Device Role: name=`leaf` and `spine`
- Location: name=`Demo Lab`

For Arista cEOS:
- Platform: name=`arista_eos`, network_driver=`arista_eos`

For FRR:
- Platform: name=`linux_frr`, network_driver=`linux`

### Step 4b: Create devices in Nautobot

Use `nautobot_graphql` or the REST write tools to create:
- Location: "Demo Lab"
- Devices: leaf1 (172.20.20.11), leaf2 (172.20.20.12), spine1 (172.20.20.13)
- Assign platforms, roles, device types
- Create management interfaces and assign IPs

### Step 4c: Verify devices in Nautobot

```
nautobot_get_devices
```

Should show all three lab devices with their management IPs.

## Phase 5: Create pyATS Testbed for Lab Devices

Create a testbed.yaml that pyATS can use to connect to the lab devices:

```yaml
testbed:
  name: netclaw-demo-lab

devices:
  leaf1:
    os: linux  # or 'eos' for cEOS, adjust per platform
    type: switch
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 172.20.20.11
        port: 22
    credentials:
      default:
        username: admin
        password: NokiaSrl1!  # SR Linux default

  leaf2:
    os: linux
    type: switch
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 172.20.20.12
        port: 22
    credentials:
      default:
        username: admin
        password: NokiaSrl1!

  spine1:
    os: linux
    type: router
    connections:
      defaults:
        class: unicon.Unicon
      cli:
        protocol: ssh
        ip: 172.20.20.13
        port: 22
    credentials:
      default:
        username: admin
        password: NokiaSrl1!
```

Write this to `~/demo-lab/testbed.yaml` and update the `PYATS_TESTBED_PATH` env var.

## Phase 6: Golden Config Bootstrap

**Read and follow the `skills/golden-config-bootstrap/SKILL.md` skill for this phase.**

This is the main demo payoff:

1. Collect running configs from lab devices via pyATS
2. Analyze configs against design reference best practices
3. Generate Jinja templates
4. Create GitHub repo and commit templates
5. Wire Nautobot golden config (repos, SoT query, compliance rules)
6. Run first compliance check
7. Show the user the compliance results

## Phase 7: Demo Walkthrough

Once everything is set up, present the demo flow to the user:

1. **"Show me my network"** → `nautobot_get_devices` → shows all lab devices
2. **"Check the health of leaf1"** → pyATS health check
3. **"What does the golden config say about leaf1?"** → compliance results
4. **"What's the intended config for leaf1?"** → rendered Jinja template
5. **"What's out of compliance?"** → diff between actual and intended
6. **"Generate a topology diagram"** → Draw.io or Markmap visualization

## Cleanup

To tear down the entire demo:

```bash
# Stop Nautobot
cd ~/nautobot-dev && invoke destroy

# Destroy ContainerLab topology
cd ~/demo-lab && sudo clab destroy --topo topology.yml

# Remove files
rm -rf ~/demo-lab ~/nautobot-dev
```

## Notes

- SR Linux is the easiest ContainerLab node — free, no license, fast boot
- cEOS requires importing the Arista image first (`docker import cEOS-lab.tar ceos:latest`)
- FRR is lightweight but has limited CLI parsing support in pyATS
- The management network name (`netclaw-mgmt`) must match between the topology.yml and the docker-compose.local.yml
- ContainerLab requires `sudo` for deployment (creates network namespaces)
- The demo can run entirely on a single VM with 8GB+ RAM
