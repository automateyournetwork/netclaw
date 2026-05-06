## Prompt 1 (Steps 1–4)

```
Deploy the byrn-baker/Nautobot-Workshop demo environment end-to-end. Follow the demo-lab-setup skill steps 1 through 20 in exact order. Do not skip any step. Do not improvise — if a gate fails after retries, stop and tell me. Use nautobot-mcp-v2 tools for all Nautobot operations. Start with Step 1.
```

| Step | What It Does |
|------|-------------|
| 1 | Checks that docker, containerlab, poetry, and git are installed, and that at least one Cisco IOL or Arista cEOS image exists locally |
| 2 | Clones the Nautobot Workshop repo, copies the example config files, enables superuser creation, and injects GitHub PAT, GitHub username, and device SSH credentials into the environment |
| 3 | Initializes the Poetry virtual environment and installs Python dependencies for the Nautobot Docker tooling |
| 4 | Builds the Nautobot Docker image via Invoke, starts the Nautobot stack (Nautobot, PostgreSQL, Redis, Celery worker, Celery beat), and waits for all containers to be healthy |

*Checkpoint — agent pauses here*

---

## Prompt 2 (Steps 5–11)

```
Continue demo from Step 5. Nautobot is running at localhost:8080. Execute Steps 5 through 11 in order. Use nautobot-mcp-v2 tools only.
```

| Step | What It Does |
|------|-------------|
| 5 | Lists all Nautobot jobs via the API and enables every disabled one (Design Builder, Golden Config Backup/Intended/Compliance/Deploy, and all others) so they can be triggered programmatically |
| 6 | Runs the "Nautobot Workshop Demo Initial Data" Design Builder job, which populates Nautobot with 20 devices, hundreds of interfaces, IP addresses, BGP sessions, OSPF configs, VLANs, and all the relationships between them |
| 7 | Restarts the Nautobot containers so the GraphQL schema picks up the custom fields (cf_ospf_area, cf_mpls_enabled, cf_vrrp_*, cf_mlag_interface) that Design Builder just created, then verifies the API is responsive |
| 8 | Registers the Nautobot-Workshop-Datasource git repo in Nautobot and syncs it, which loads config contexts (NTP, SNMP, logging parameters), config context schemas, and the SoT aggregation GraphQL query that Golden Config needs to render templates |
| 9 | Creates a "Device Credentials" secrets group with two environment-variable-backed secrets (DEVICE_USERNAME and DEVICE_PASSWORD) so Nornir can SSH to devices during Golden Config backup jobs |
| 10 | Creates a "GitHub Access" secrets group with both an HTTP(S) username (x-access-token) and an HTTP(S) token (the GitHub PAT) so Nautobot can push to private GitHub repos — both are required or git push returns 403 |
| 11 | Assigns the Device Credentials secrets group to all 20 devices so Golden Config's Nornir inventory can resolve SSH credentials for each device |

*Checkpoint — agent pauses here*

---

## Prompt 3 (Steps 12–14)

```
Continue demo from Step 12. Nautobot has all 20 devices with config contexts and credentials assigned. Execute Steps 12 through 14.
```

| Step | What It Does |
|------|-------------|
| 12 | Deploys the ContainerLab topology — 20 network nodes (Cisco IOL routers for the SP core and Arista cEOS switches for the DC fabrics) connected per the workshop's topology file |
| 13 | Connects the Nautobot, celery_worker, and celery_beat Docker containers to the clab-mgmt network so they can reach the lab devices at 192.168.220.x, verifies reachability with a socket test, and injects an SSH config into the celery worker to allow Arista's older key exchange algorithms |
| 14 | Tests SSH connectivity to one device from each role (P router, PE router, spine switch, leaf switch) to confirm all device types are booted and reachable before Ansible runs |

*Checkpoint — agent pauses here*

---

## Prompt 4 (Steps 15–17)

```
Continue demo from Step 15. ContainerLab is running with all 20 devices and Nautobot is connected to clab-mgmt. Execute Steps 15 through 17. If Arista deploy fails, use the pyATS failback from the skill.
```

| Step | What It Does |
|------|-------------|
| 15 | Creates a Python venv for Ansible, installs the pip requirements, upgrades pynautobot to 2.7+ (needed for the Nautobot collection), installs the Ansible Galaxy collections, and creates the vault password file |
| 16 | Runs the Ansible playbook with `--tags build` only, which queries Nautobot's SoT data and generates device configuration files into the configs/ directory — one per device |
| 17 | Runs the Ansible playbook with `--tags deploy` to push configs to all 20 devices. IOS devices succeed; Arista cEOS devices fail due to a management VRF conflict. The agent then reads the generated Arista configs, strips the conflicting `vrf forwarding clab-mgmt` lines, and pushes them via pyATS instead |

*Checkpoint — agent pauses here*

---

## Prompt 5 (Steps 18–20)

```
Continue demo from Step 18. All 20 devices are configured. Execute Steps 18 through 20. Do NOT create new repos or local git servers — use the byrn-baker GitHub repos. Use nautobot-mcp-v2 tools for everything.
```

| Step | What It Does |
|------|-------------|
| 18 | Re-verifies Nautobot-to-lab connectivity, registers the three Golden Config GitHub repos (templates, intended configs, backup configs) in Nautobot, links the GitHub Access secrets group to each repo for push authentication, and syncs all three |
| 19 | Retrieves the Golden Config setting, all repo IDs, and the SoT aggregation query ID, then wires them together — linking the template repo, intended repo, backup repo, SoT query, and path templates (jinja, intended, backup) into the Golden Config setting. Validates that no field is null |
| 20 | Runs three Golden Config jobs in sequence: Generate Intended Configurations (renders Jinja templates against SoT data), Backup Configurations (SSHes to devices and captures running configs), and Run Compliance (diffs intended vs actual per compliance feature). Reports results including known false positives |

*Checkpoint — demo complete*
