# SKILL: Demo Lab Setup — Nautobot Workshop + ContainerLab + Golden Config

## Purpose

Deploy the byrn-baker/Nautobot-Workshop environment end-to-end. Fully autonomous — validate each step before proceeding, no user input required except at session checkpoints.

## When to Use

- User says "set up the demo" or "build the demo lab" or "deploy the workshop"

## CRITICAL RULES

1. **Execute steps 1 through 20 in exact order. Do NOT skip any step.**
2. **Every step has a GATE.** Do not proceed to the next step until the gate passes. If a gate fails, retry up to 2 times with a 30-second wait between retries. After 2 retries, STOP and report the failure to the user. Do NOT improvise alternative solutions.
3. **SESSION CHECKPOINTS after steps 4, 11, 14, 17, and 20.** Tell the user: "Checkpoint: Step N complete. You can say 'continue' to proceed, or '/new' and say 'continue demo from Step N+1' to start a fresh session." These are the ONLY places you wait for user input.
4. **Use the workshop repo as-is** — do NOT create custom files.
5. **Use Invoke** to build/start Nautobot — do NOT run docker compose directly.
6. **BATCH COMMANDS** — combine multiple shell commands into ONE exec call using `&&`. Every tool call costs tokens.
7. **NEVER poll builds** — no `process poll` or `process log` on long-running commands. Start the command, wait the prescribed time, then check once.
8. **Use nautobot-mcp-v2 tools** for ALL Nautobot API operations — never curl or docker exec.
9. **Do NOT explore the repo.** Do not ls, cat, grep, find, or read README files. Execute the prescribed commands directly.
10. **NEVER restart Nautobot containers** unless this skill explicitly says to.
11. **If a step fails and the skill does not prescribe a fix, STOP and tell the user.** Do NOT attempt creative workarounds, SSH heredocs, local git servers, or manual API calls.

---

## Step 1: Check Prerequisites

```bash
echo "=== prereqs ===" && docker --version && clab version 2>&1 | head -1 && poetry --version && git --version && echo "=== images ===" && docker images --format '{{.Repository}}:{{.Tag}}' | grep -E "cisco_iol|ceos" && echo "=== done ==="
```

**GATE:** Output must show docker, clab, poetry, git versions AND at least one cisco_iol or ceos image. If any tool is missing or no images found, STOP and tell the user what's missing.

## Step 2: Clone Repo and Configure Credentials

```bash
cd ~ && git clone https://github.com/byrn-baker/Nautobot-Workshop.git && cd ~/Nautobot-Workshop/nautobot-docker-compose && cp invoke.example.yml invoke.yml && cp environments/creds.example environments/creds.env && sed -i 's/NAUTOBOT_CREATE_SUPERUSER=false/NAUTOBOT_CREATE_SUPERUSER=true/' environments/creds.env && echo "GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PERSONAL_ACCESS_TOKEN}" >> environments/creds.env && echo "GITHUB_USERNAME=x-access-token" >> environments/creds.env && echo "NAUTOBOT_NAPALM_USERNAME=${NETCLAW_USERNAME}" >> environments/creds.env && echo "NAUTOBOT_NAPALM_PASSWORD=${NETCLAW_PASSWORD}" >> environments/creds.env && echo "DEVICE_USERNAME=${NETCLAW_USERNAME}" >> environments/creds.env && echo "DEVICE_PASSWORD=${NETCLAW_PASSWORD}" >> environments/creds.env && echo "=== repo cloned, superuser enabled, GitHub token + username + device creds added ==="
```

**GATE:** Command exits 0 and output contains "repo cloned". If the repo already exists, `rm -rf ~/Nautobot-Workshop` first and retry.

## Step 3: Set Up Poetry

```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry shell && poetry lock && poetry install
```

**GATE:** Command exits 0. Poetry environment is active.

## Step 4: Build and Start Nautobot

Build the image:
```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke build
```

Wait for build to complete (3-5 minutes). Do NOT poll. After "Command still running" returns, wait 240 seconds then check:
```bash
docker images | grep nautobot-workshop
```

**GATE:** `nautobot-workshop` image exists. If not, wait another 120 seconds and check once more.

Start Nautobot:
```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke debug
```

Wait 90 seconds for startup, then validate:
```bash
sleep 90 && docker ps --format 'table {{.Names}}\t{{.Status}}' | grep nautobot
```

**GATE:** At least nautobot-1, celery_worker, and celery_beat containers are running. If any show "Restarting" or are missing, wait 60 more seconds and check once more.

**SESSION CHECKPOINT.** Tell the user: "Checkpoint: Step 4 complete — Nautobot is running. Say 'continue' to proceed, or '/new' and say 'continue demo from Step 5'."

## Step 5: Enable ALL Jobs

Enable all disabled jobs in one call:
```
nautobot_enable_job(enable_all=True)
```

**GATE:** Response shows `enabled_count` > 0 (or "All jobs already enabled"). Then verify:
```
nautobot_list_jobs(limit=100)
```
Every job must show `enabled: true`. If any remain disabled, call `nautobot_enable_job(enable_all=True)` once more. If still disabled after retry, STOP and report.

## Step 6: Run Design Builder

First, find the Design Builder job ID:
```
nautobot_list_jobs(q="Workshop")
```

Run it:
```
nautobot_run_job(job_id="<design-builder-job-id>")
```

Wait 30 seconds, then check the job result:
```
nautobot_get_job_result(job_result_id="<job-result-id>")
```

**GATE:** Job status must be "completed" (not "failed" or "pending"). If "pending", wait 30 more seconds and check once more. If "failed", STOP and report the error.

Verify devices were created:
```
nautobot_get_devices(limit=25)
```

**GATE:** Device count must be >= 20. If fewer, STOP and report.

## Step 7: Restart Nautobot (MANDATORY after Design Builder)

Design Builder creates custom fields (cf_ospf_area, cf_mpls_enabled, cf_vrrp_*, cf_mlag_interface). The GraphQL schema will NOT recognize them until containers restart.

```bash
cd ~/Nautobot-Workshop/nautobot-docker-compose && poetry run invoke restart
```

Wait 90 seconds, then validate:
```bash
sleep 90 && docker ps --format 'table {{.Names}}\t{{.Status}}' | grep nautobot
```

**GATE:** All Nautobot containers running and healthy. Then verify API is responsive:
```
nautobot_test_connection
```

**GATE:** Both `graphql: true` and `rest: true`. If either is false, wait 30 seconds and retry once.

## Step 8: Load Config Contexts via Git Data Source

Register the datasource repo:
```
nautobot_create_git_repository(name="nautobot-workshop-datasource", remote_url="https://github.com/byrn-baker/Nautobot-Workshop-Datasource.git", branch="main", provided_contents="extras.configcontext,extras.configcontextschema,extras.graphqlquery")
```

**GATE:** Response contains `"created": true`. If error contains "already exists", that's OK — proceed.

Sync the repo:
```
nautobot_sync_git_repository(repository_id="<repo-id>")
```

Verify config contexts loaded:
```
nautobot_get_config_contexts
```

**GATE:** At least 1 config context exists. If count is 0, wait 15 seconds and retry the sync + check once.

Also verify GraphQL queries loaded:
```
nautobot_get_graphql_queries
```

**GATE:** At least 1 saved GraphQL query exists (the SoT aggregation query).

## Step 9: Create Device Credentials (Secrets + Secrets Group)

```
nautobot_create_secrets_group(name="Device Credentials")
```

Save the secrets_group ID from the response.

```
nautobot_create_secret(name="Device Username", provider="environment-variable", parameters='{"variable": "DEVICE_USERNAME"}')
nautobot_create_secret(name="Device Password", provider="environment-variable", parameters='{"variable": "DEVICE_PASSWORD"}')
```

Save both secret IDs, then associate them:
```
nautobot_add_secret_to_group(secrets_group_id="<group-id>", secret_id="<username-secret-id>", access_type="Generic", secret_type="username")
nautobot_add_secret_to_group(secrets_group_id="<group-id>", secret_id="<password-secret-id>", access_type="Generic", secret_type="password")
```

**GATE:** All 4 calls return `"created": true`. If any "already exists" error, that's OK.

## Step 10: Create GitHub Secrets Group (for private repos)

Nautobot's git credential helper needs BOTH a username and token for HTTPS auth. GitHub expects `x-access-token` as the username when using a PAT.

```
nautobot_create_secrets_group(name="GitHub Access")
nautobot_create_secret(name="GitHub Username", provider="environment-variable", parameters='{"variable": "GITHUB_USERNAME"}')
nautobot_create_secret(name="GitHub PAT", provider="environment-variable", parameters='{"variable": "GITHUB_PERSONAL_ACCESS_TOKEN"}')
nautobot_add_secret_to_group(secrets_group_id="<group-id>", secret_id="<username-secret-id>", access_type="HTTP(S)", secret_type="username")
nautobot_add_secret_to_group(secrets_group_id="<group-id>", secret_id="<pat-secret-id>", access_type="HTTP(S)", secret_type="token")
```

**GATE:** All calls succeed or return "already exists".

## Step 11: Assign Secrets Groups to All Devices

Get all device IDs and the Device Credentials secrets group ID:
```
nautobot_graphql(query="{ devices { id name } }")
```

For each device, assign the Device Credentials secrets group:
```
nautobot_update_object(object_type="device", identifier="<device-name>", updates='{"secrets_group": "<device-credentials-group-id>"}')
```

Do this for all 20 devices.

**GATE:** After all updates, spot-check 3 devices by querying them. Verify `secrets_group` is set (non-null). If any are null, retry those specific devices.

**SESSION CHECKPOINT.** Tell the user: "Checkpoint: Step 11 complete — Nautobot fully configured with 20 devices, config contexts, and credentials. Say 'continue' to proceed, or '/new' and say 'continue demo from Step 12'."

## Step 12: Deploy ContainerLab

```bash
cd ~/Nautobot-Workshop/clabs && sudo clab deploy --topo nautobot-workshop-topology.clab.yml
```

Wait for deployment (2-5 minutes). After "Command still running" returns, wait 180 seconds then verify:
```bash
sudo clab inspect --topo ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml 2>&1 | grep -c "running"
```

**GATE:** At least 20 nodes in "running" state. If fewer, wait 60 more seconds and check once more.

## Step 13: Connect Nautobot to Lab Network

```bash
NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker) && BEAT_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_beat) && docker network connect clab-mgmt $NAUTOBOT_CONTAINER 2>/dev/null; docker network connect clab-mgmt $CELERY_CONTAINER 2>/dev/null; docker network connect clab-mgmt $BEAT_CONTAINER 2>/dev/null && echo "=== Nautobot + celery connected to clab-mgmt ==="
```

**GATE:** Verify Nautobot can reach a lab device:
```bash
NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && docker exec $NAUTOBOT_CONTAINER python3 -c "import socket; s=socket.socket(); s.settimeout(5); s.connect(('192.168.220.2', 22)); print('P1 SSH reachable from Nautobot'); s.close()"
```

Output must contain "P1 SSH reachable". If not, retry the network connect commands and check again.

### Fix cEOS SSH Key Exchange in Celery Worker

```bash
CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker) && docker exec $CELERY_CONTAINER bash -c 'mkdir -p /root/.ssh && cat >> /root/.ssh/config << EOF
Host 192.168.220.*
  KexAlgorithms +diffie-hellman-group14-sha1,diffie-hellman-group1-sha1
  HostKeyAlgorithms +ssh-rsa
  PubkeyAcceptedAlgorithms +ssh-rsa
EOF
chmod 600 /root/.ssh/config' && echo "=== celery worker SSH config updated for cEOS ==="
```

**GATE:** Output contains "celery worker SSH config updated".

## Step 14: Verify SSH Connectivity Before Ansible

```bash
echo "=== Testing SSH connectivity ===" && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.2 echo "P1 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.6 echo "PE1 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.12 echo "West-Spine01 OK" 2>&1 | tail -1 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes admin@192.168.220.18 echo "East-Leaf01 OK" 2>&1 | tail -1 && echo "=== All roles reachable ==="
```

**GATE:** Output contains "All roles reachable". If any device fails, wait 120 seconds (IOL devices boot slowly) and retry the full test once. If still failing after retry, STOP and report which devices are unreachable.

**SESSION CHECKPOINT.** Tell the user: "Checkpoint: Step 14 complete — lab deployed and connectivity verified. Say 'continue' to proceed, or '/new' and say 'continue demo from Step 15'."

## Step 15: Set Up Ansible

```bash
cd ~/Nautobot-Workshop/ansible-lab && python3 -m venv .venv && . .venv/bin/activate && pip install -q -r pip-requirements.txt && pip install -q --upgrade pynautobot && ansible-galaxy collection install -r galaxy-requirements.yml -p ./ansible_collections 2>&1 | tail -3 && echo "nautobot" > ~/.vault-pass.txt && chmod 600 ~/.vault-pass.txt && echo "=== Ansible ready ==="
```

**GATE:** Output contains "Ansible ready". If pip or galaxy install fails, STOP and report.

## Step 16: Generate Device Configs

**Use --tags build ONLY. NEVER run without tags.**
```bash
cd ~/Nautobot-Workshop/ansible-lab && . .venv/bin/activate && export NAUTOBOT_TOKEN=0123456789abcdef0123456789abcdef01234567 && ansible-playbook pb.build-lab.yml --tags build
```

**GATE:** Ansible exits 0 with no fatal errors. Some warnings are OK. If fatal errors occur, STOP and report.

## Step 17: Deploy Device Configs

**Use --tags deploy ONLY.**
```bash
cd ~/Nautobot-Workshop/ansible-lab && . .venv/bin/activate && export NAUTOBOT_TOKEN=0123456789abcdef0123456789abcdef01234567 && ansible-playbook pb.build-lab.yml --tags deploy
```

**GATE:** Check Ansible output. IOS devices should succeed. Arista devices may fail — this is a known issue (see below).

### Known Issue: Arista cEOS Management VRF
The Ansible-generated configs include `vrf forwarding clab-mgmt` under Management0. This fails on cEOS because the startup config already has the management VRF applied. **IOS devices will succeed; Arista devices may fail.**

### Failback: Push Arista configs via pyATS
If Ansible deploy fails for Arista devices, read the generated config files from `~/Nautobot-Workshop/ansible-lab/configs/` for each failed device. Strip the `vrf forwarding clab-mgmt` lines from Management0 before pushing.

For each failed Arista device:
```
pyats_configure_device(device="<device-name>", configuration="<config-lines-without-mgmt-vrf>")
```

Do NOT attempt to fix this with sshpass, SSH heredocs, or manual SSH commands. pyATS handles EOS enable mode and config sessions correctly.

**GATE:** After deploy (including pyATS failback), verify at least one device per role responds to a show command:
```bash
ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no admin@192.168.220.2 "show ip route summary" 2>&1 | head -3 && ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no admin@192.168.220.12 "show ip route summary" 2>&1 | head -3 && echo "=== configs deployed ==="
```

**SESSION CHECKPOINT.** Tell the user: "Checkpoint: Step 17 complete — configs deployed to all devices. Say 'continue' to proceed, or '/new' and say 'continue demo from Step 18'."

## Step 18: Register Golden Config Git Repos

First verify Nautobot can still reach lab devices (network connections may drop after restarts):
```bash
NAUTOBOT_CONTAINER=$(docker ps --format '{{.Names}}' | grep nautobot-1) && docker network connect clab-mgmt $NAUTOBOT_CONTAINER 2>/dev/null; CELERY_CONTAINER=$(docker ps --format '{{.Names}}' | grep celery_worker) && docker network connect clab-mgmt $CELERY_CONTAINER 2>/dev/null; docker exec $NAUTOBOT_CONTAINER python3 -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('192.168.220.2', 22)); print('P1 SSH reachable'); s.close()" && echo "=== Nautobot can reach lab devices ==="
```

**GATE:** Output contains "P1 SSH reachable".

Get the GitHub Access secrets group ID:
```
nautobot_get_git_repositories
```

Register each repo:
```
nautobot_create_git_repository(name="nautobot_workshop_templates", remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_templates.git", branch="main", provided_contents="nautobot_golden_config.jinjatemplate")
nautobot_create_git_repository(name="nautobot_workshop_intended", remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_intended_configs.git", branch="main", provided_contents="nautobot_golden_config.intendedconfigs")
nautobot_create_git_repository(name="nautobot_workshop_backup", remote_url="https://github.com/byrn-baker/nautobot_workshop_golden_config_backup_configs.git", branch="main", provided_contents="nautobot_golden_config.backupconfigs")
```

**GATE:** All 3 repos created (or "already exists"). Get their IDs from the responses.

**CRITICAL: Link GitHub Access secrets group to EVERY repo.** Without this, git push fails with 403.
```
nautobot_update_git_repository(repository_id="<templates-repo-id>", updates='{"secrets_group": "<github-access-group-id>"}')
nautobot_update_git_repository(repository_id="<intended-repo-id>", updates='{"secrets_group": "<github-access-group-id>"}')
nautobot_update_git_repository(repository_id="<backup-repo-id>", updates='{"secrets_group": "<github-access-group-id>"}')
```

**GATE:** All 3 updates return `"updated": true`.

Sync all repos:
```
nautobot_sync_git_repository(repository_id="<templates-repo-id>")
nautobot_sync_git_repository(repository_id="<intended-repo-id>")
nautobot_sync_git_repository(repository_id="<backup-repo-id>")
```

**GATE:** All 3 syncs succeed.

## Step 19: Configure Golden Config Settings

Get the golden config setting ID, all repo IDs, and the SoT query ID:
```
nautobot_get_golden_config_settings
nautobot_get_git_repositories
nautobot_get_graphql_queries
```

**GATE:** Golden config settings must return at least 1 setting. Git repos must include the 3 golden config repos + the datasource repo. GraphQL queries must include at least 1 SoT aggregation query.

Update the setting with ALL repos, the SoT query, and path templates:
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

**GATE:** Verify the update:
```
nautobot_get_golden_config_settings
```

Confirm ALL of these fields are non-null: `jinja_repository`, `intended_repository`, `backup_repository`, `sot_agg_query`. If ANY is null, the golden config jobs will crash. Retry the update for the null fields.

## Step 20: Run Golden Config Jobs

Run intended config generation:
```
nautobot_run_job(job_id="<intended-job-id>")
```

Wait 30 seconds, then check result:
```
nautobot_get_job_result(job_result_id="<job-result-id>")
```

**GATE:** Job status is "completed". If "pending", wait 30 more seconds and check once. If "failed", report the error but continue to the next job.

Run backup:
```
nautobot_run_job(job_id="<backup-job-id>")
```

Wait 30 seconds, then check result.

### Known Issue: cEOS Backup Failures
If Step 13's SSH config fix was not applied, backup jobs will fail for all EOS devices with SSH key exchange errors. IOS device backups should succeed. This is cosmetic — the intended configs and compliance engine still work. Do NOT spend turns debugging SSH from inside the celery container.

**GATE:** Job completed (even with partial failures for EOS devices — that's expected).

Run compliance:
```
nautobot_run_job(job_id="<compliance-job-id>")
```

Wait 30 seconds, then check result.

### Known Issue: Compliance False Positives
The compliance engine may flag some devices as non-compliant due to:
- **Indentation diffs** — EOS actual config may have different whitespace than the intended template output.
- **Duplicate Nautobot data objects** — e.g., a BGP endpoint appearing twice causes extra lines in the rendered template.
- **Line ordering** — IOS may reorder `neighbor` statements differently than the template renders them.

Do NOT chase these false positives. Report them as known template/data issues and move on.

**GATE:** Compliance job completed.

**SESSION CHECKPOINT.** Tell the user: "Checkpoint: Step 20 complete — Golden Config fully bootstrapped. Intended configs generated, backups collected, compliance run. Say 'continue' to proceed, or '/new' and say 'continue demo from Step 21'."

## Step 21: Deploy Observability Stack

Config contexts for SNMP/syslog/IP SLA live in [Nautobot-Workshop-Datasource](https://github.com/byrn-baker/Nautobot-Workshop-Datasource.git) (`config_contexts/observability.yml` and `config_contexts/devices/PE*.yml`). Sync that Git repo in Nautobot before deploying device configs (Step 17 should already have rendered observability + IP SLA if contexts are synced).

Invoke the deploy-observability skill procedure:

```bash
cd /home/ubuntu/netclaw/observability
docker compose -f docker-compose.observability.yml up -d
sleep 90
curl -sf "http://192.168.220.201:8428/api/v1/query?query=interface_status" | \
  python3 -c "import sys,json; r=json.load(sys.stdin); print(f'{len(r[\"data\"][\"result\"])} interface_status series')"
```

**GATE:** Docker compose reports 4 containers Up. VictoriaMetrics query returns **> 0** `interface_status` series (expect ~60+ after SNMP is enabled on devices).

If series count is 0, devices lack SNMP — re-run Step 17 deploy, or run:

```bash
cd /home/ubuntu/netclaw && PYATS_TESTBED_PATH=/home/ubuntu/netclaw/testbed/testbed.yaml .venv/bin/python3 scripts/observability/push-lab-observability.py
```

**GATE:** Push script reports success for PE/CE/P routers (Arista may fail SSH — known issue; IOS devices are required for this gate).

Register observability VMs in Nautobot (optional but recommended — see deploy-observability skill Step 9).

**SESSION CHECKPOINT.** Tell the user: "Checkpoint: Step 21 complete — observability stack running, metrics flowing. Ready for demo walkthrough?"

---

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

## Session Management

This demo takes 200-500+ tool calls depending on issues encountered. Context windows WILL fill up. When the user says `/new` or starts a fresh session:
- State where you stopped (e.g., "Step 14 complete, starting Step 15")
- The new session prompt should say "continue demo from Step N" with a summary of what's already done
- Do NOT re-explore or re-verify completed steps. Trust the user's summary and proceed.

## Resource Requirements
- **CPU:** 20 vCPU recommended
- **RAM:** 32 GB recommended
- **Disk:** 50 GB+
- **Network:** 192.168.220.0/24 (auto-created by ContainerLab)
