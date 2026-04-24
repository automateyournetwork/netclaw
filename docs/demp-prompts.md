# Phase 1-2 (initial prompt):
Deploy the byrn-baker/Nautobot-Workshop demo environment end-to-end — Nautobot, Design Builder, Ansible configs, ContainerLab topology, and golden config. Once the Golden Config plugin has been setup we need to work on compliance rules so that the golden config plugin is fully bootstrapped. Ensure you read all skills pertinent to this task carefully and do not make up your own solutions without prompting me first.

# Phase 3 (after Nautobot is running):
Continue demo from Phase 3. Nautobot is running at localhost:8080 (admin/admin). I have enabled all jobs in the Nautobot UI. Run the Design Builder initial data job, load config contexts, and verify all 20 devices are populated. Use nautobot-mcp-v2 tools only — do not use curl or docker exec for Nautobot operations.

# Phase 4 (after Design Builder):
Continue demo from Phase 4. Nautobot is populated with all 20 devices. Deploy the ContainerLab topology from ~/Nautobot-Workshop/clabs/nautobot-workshop-topology.clab.yml, then connect the Nautobot containers to the clab-mgmt network and verify connectivity. Do not proceed to Ansible until SSH connectivity to at least one device per role is confirmed.

# Phase 5 (after ContainerLab):
Continue demo from Phase 5. ContainerLab is running with all 20 devices and Nautobot is connected to the clab-mgmt network. Set up the Ansible venv, install deps (including pynautobot upgrade), and run the playbook with --tags build then --tags deploy. NEVER run the playbook without tags.

# Phase 6 (after Ansible):
Continue demo from Phase 6. All 20 devices are configured. Wire golden config using the existing GitHub repos at byrn-baker/nautobot_workshop_golden_config_*. First verify Nautobot can reach lab devices (docker network connect if needed), then register the repos with GitHub PAT authentication, create the SoT GraphQL query, configure golden config settings, and run intended config generation. Do NOT create new repos or set up local git servers. Use nautobot-mcp-v2 tools for all Nautobot operations.

# Phase 6b (compliance rules):
Continue with golden config compliance rules. Use the golden-config-bootstrap skill and the cisco_design_reference tool to create compliance features and rules for the workshop devices. Cover at minimum: hostname, NTP, DNS, logging, AAA, interfaces, OSPF, BGP, and MPLS for IOS devices, plus interfaces, BGP, and MLAG for EOS devices. Use nautobot-mcp-v2 tools to create each feature and rule.
