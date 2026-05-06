# SKILL: Golden Config Bootstrap

## Purpose

Interactively set up the Nautobot Golden Config plugin from scratch. This is a conversational workflow — the agent guides the user through analyzing their running configs, designing compliance features, building Jinja templates, creating the GitHub repository, and wiring everything into Nautobot. The user makes the design decisions; the agent provides recommendations, executes the work, and explains the rationale.

## When to Use

- User says "set up golden config" or "bootstrap golden config"
- User wants to create intended config templates for their devices
- User wants to establish config compliance checking in Nautobot
- User asks about config standardization or hardening

## MCP Tools Used

### Device Config Collection
- **pyATS MCP**: `pyats_run_command` — collect `show running-config` from devices

### Design Guidance
- **nautobot-mcp-v2**: `cisco_design_reference` — Cisco best practices, config examples, rationale, RFCs per feature
- **RFC MCP**: `rfc_lookup` — deep-dive into specific standards (NTP, syslog, SNMP, SSH)

### Nautobot Configuration
- **nautobot-mcp-v2**: `nautobot_get_devices` — discover devices in scope
- **nautobot-mcp-v2**: `nautobot_get_interfaces` — get interface inventory for template generation
- **nautobot-mcp-v2**: `nautobot_get_vlans` — get VLAN inventory
- **nautobot-mcp-v2**: `nautobot_graphql` — query config_context, locations, platforms
- **nautobot-mcp-v2**: `nautobot_create_compliance_feature` — create compliance features
- **nautobot-mcp-v2**: `nautobot_create_compliance_rule` — create compliance rules with match_config patterns
- **nautobot-mcp-v2**: `nautobot_create_graphql_query` — create SoT aggregation query
- **nautobot-mcp-v2**: `nautobot_create_git_repository` — register git repo in Nautobot
- **nautobot-mcp-v2**: `nautobot_update_golden_config_setting` — wire repos, paths, SoT query
- **nautobot-mcp-v2**: `nautobot_get_golden_config_settings` — check current GC state
- **nautobot-mcp-v2**: `nautobot_get_compliance_rules` — verify what's already configured

### GitHub Repository
- **GitHub MCP**: `create_repository` — create private repo for templates
- **GitHub MCP**: `create_or_update_file` — commit template files
- **GitHub MCP**: `push_files` — batch commit multiple files

## Workflow

This is a CONVERSATIONAL workflow. Do not execute all steps automatically. Present findings, make recommendations, and wait for user input at each decision point.

### Phase 1: Discovery

1. Query Nautobot for devices in scope: `nautobot_get_devices()`
2. Check which devices have platforms with network_driver set (only those can use golden config)
3. Check current Golden Config Setting state: `nautobot_get_golden_config_settings()`
4. Check existing compliance features and rules: `nautobot_get_compliance_rules()`
5. Check existing git repositories: `nautobot_get_git_repositories()`
6. Check existing config contexts: `nautobot_graphql` query for devices with config_context

**Present to user:** Summary of what's in scope, what's already configured, and what needs to be set up.

### Phase 2: Config Analysis

1. Collect running config from each in-scope device via pyATS
2. Parse the running config into logical sections
3. For each section, query the design reference: `cisco_design_reference(feature="ntp")`, etc.
4. Compare the running config against best practices
5. Identify gaps (e.g., no NTP configured, SNMP using default communities, no AAA)

**Present to user:** For each config section:
- What the running config currently has
- What Cisco best practices recommend
- What the relevant RFC says (if applicable)
- A recommendation: keep as-is, harden, or add missing config
- Ask the user what they want to do

**Wait for user decisions before proceeding.**

### Phase 3: Template Design

Based on the user's decisions from Phase 2, build the Jinja template structure:

**Directory structure:**
```
{network_driver}/
├── {network_driver}.j2              # Entry point — dispatches by device role
├── platform_templates/
│   └── {role}.j2                    # Full config skeleton with {% include %} calls
├── services/
│   └── vrf.j2                       # VRF definitions
├── management/
│   ├── aaa.j2                       # AAA configuration
│   ├── ntp.j2                       # NTP servers and authentication
│   ├── logging.j2                   # Syslog configuration
│   ├── snmp.j2                      # SNMP communities, traps, host
│   ├── ssh.j2                       # SSH version, source interface
│   ├── http.j2                      # HTTP/HTTPS server settings
│   ├── users.j2                     # Local user accounts
│   ├── routing.j2                   # Static routes, FTP source
│   └── line_vty.j2                  # VTY and console line config
├── switching/
│   ├── vlans.j2                     # VLAN database from SoT
│   ├── spanning_tree.j2             # STP mode, priority, extensions
│   └── vtp.j2                       # VTP mode
└── interfaces/
    ├── interfaces.j2                # Dispatcher — loops interfaces, includes sub-templates
    ├── _l2_access.j2               # Switchport access mode ports
    ├── _l2_trunk.j2               # Switchport trunk mode ports
    ├── _lag_member.j2             # Port-channel member interfaces
    ├── _port_channel.j2           # Port-channel logical interfaces
    ├── _svi.j2                    # VLAN interfaces (L3 SVIs)
    └── _unused.j2                 # Shutdown/unused ports
```

**Template principles:**
- The main platform template (`home_switch.j2`) is the full config skeleton — it `{% include %}` each section template
- Each section template reads from `config_context` for operational parameters (NTP servers, SNMP communities, logging hosts)
- Interface templates read from the `interfaces` list provided by the SoT aggregation query
- VLAN templates read from `location.vlans` in the SoT data
- Device-specific values (hostname, management IP) come from the device object itself
- Secrets (passwords, SNMP communities) use `{{ secrets.key }}` references where possible

**Present each template to the user for review.** Walk through what it generates and why. Modify based on feedback.

### Phase 4: Config Context

If the user's Nautobot doesn't have config contexts set up yet:

1. Design a config context schema based on what the templates need
2. Create the schema in Nautobot
3. Create a config context with the actual values (extracted from running config + user decisions)
4. Scope it to the appropriate role/location so devices inherit it

**Present the config context data to the user.** Explain what each section controls and how it feeds into the templates.

### Phase 5: GitHub Repository

1. Ask the user for their preferred repo name and GitHub org/user
2. Create a **private** repository via GitHub MCP
3. Create the directory structure:
   - `templates/` — Jinja templates (organized by network_driver)
   - `backups/` — will be populated by golden config backup jobs
   - `intended/` — will be populated by golden config intended jobs
4. Commit all templates to the repo

**Note:** The repo MUST be private — it will contain network-specific configuration patterns.

### Phase 5b: Nautobot Git Repository Secrets

Nautobot needs credentials to clone the GitHub repo. This requires setting up Secrets and Secrets Groups in Nautobot.

**Instruct the user to configure the Nautobot server:**

1. Tell the user they need a GitHub Personal Access Token with `repo` scope for Nautobot to use
2. The user should add this token as an environment variable on the Nautobot server:
   ```
   # In /opt/nautobot/nautobot_config.py or the Nautobot environment:
   # Add to the environment where Nautobot runs (systemd unit, Docker env, etc.)
   NAUTOBOT_GIT_TOKEN=ghp_xxxxxxxxxxxx
   ```
3. Ask the user to provide the environment variable name they used (e.g., `NAUTOBOT_GIT_TOKEN`)
4. Once the user confirms the env var is set on the Nautobot server, create the Nautobot objects via REST API:

   a. **Create a Secret** — type "environment-variable", variable name matching what the user set:
   ```
   POST /api/extras/secrets/
   {
     "name": "GitHub Token",
     "provider": "environment-variable",
     "parameters": {"variable": "NAUTOBOT_GIT_TOKEN"}
   }
   ```

   b. **Create a Secrets Group** — associate BOTH username and token secrets. Nautobot's git credential helper builds `https://<username>:<token>@github.com/...` — without the username, git push gets 403:
   ```
   POST /api/extras/secrets-groups/
   {"name": "GitHub Credentials"}

   # Username secret (GitHub expects "x-access-token" when using PAT)
   POST /api/extras/secrets/
   {
     "name": "GitHub Username",
     "provider": "environment-variable",
     "parameters": {"variable": "GITHUB_USERNAME"}
   }
   # Set GITHUB_USERNAME=x-access-token in the Nautobot environment

   POST /api/extras/secrets-groups-associations/
   {
     "secrets_group": "<secrets_group_id>",
     "secret": "<username_secret_id>",
     "access_type": "HTTP(S)",
     "secret_type": "username"
   }

   POST /api/extras/secrets-groups-associations/
   {
     "secrets_group": "<secrets_group_id>",
     "secret": "<token_secret_id>",
     "access_type": "HTTP(S)",
     "secret_type": "token"
   }
   ```

   c. **Update the Git Repository** — associate the secrets group:
   ```
   PATCH /api/extras/git-repositories/<repo_id>/
   {"secrets_group": "<secrets_group_id>"}
   ```

5. After wiring the secrets group, trigger a git repo sync to verify Nautobot can clone the repo

**Wait for user confirmation at each step.** The env var must be set and Nautobot restarted before the Secret can resolve.

### Phase 6: Register Repo in Nautobot and Wire Golden Config Setting

1. Register the git repo in Nautobot via `nautobot_create_git_repository` with `provided_contents`:
   - `nautobot_golden_config.jinjatemplate`
   - `nautobot_golden_config.backupconfigs`
   - `nautobot_golden_config.intendedconfigs`
2. Associate the secrets group created in Phase 5b with the git repository
3. Trigger a repo sync to verify Nautobot can clone and read the templates
4. Get the Golden Config Setting ID
5. Update it with:
   - `jinja_repository` → the registered git repo
   - `backup_repository` → same repo (or separate if user prefers)
   - `intended_repository` → same repo (or separate if user prefers)
   - `sot_agg_query` → the SoT aggregation GraphQL query
   - `jinja_path_template` → e.g., `{{obj.platform.network_driver}}/cisco_xe.j2`
   - `backup_path_template` → e.g., `{{obj.location.name}}/{{obj.name}}.cfg`
   - `intended_path_template` → e.g., `{{obj.location.name}}/{{obj.name}}.cfg`

### Phase 7: Compliance Features and Rules

1. Create compliance features for each config section the user wants to track
2. Create compliance rules linking each feature to the platform with `match_config` regex patterns
3. The `match_config` patterns come from the design reference: `cisco_design_reference(feature="ntp")` returns `match_config: "^ntp "`

### Known Compliance False Positives
The compliance engine compares intended vs actual config line-by-line. Some diffs are NOT real compliance failures:
- **Indentation differences** — EOS may indent `address-family` sub-commands differently than the Jinja template renders. This is a template whitespace issue.
- **Line ordering** — IOS may reorder `neighbor` statements (e.g., `remote-as` before `peer-group`). The compliance engine treats ordering as a diff.
- **Duplicate SoT data** — If Nautobot has duplicate objects (e.g., a BGP endpoint with and without a peer-group), the template renders extra lines that don't exist on the device.

When presenting compliance results, flag these as template/data issues and recommend fixing the template or Nautobot data rather than changing the device config.

### Phase 8: Validation

1. Sync the git repository in Nautobot (trigger repo sync)
2. Verify templates are visible in Nautobot's golden config UI
3. If possible, trigger a test intended config generation for one device
4. Review the rendered output with the user
5. Iterate on templates if the output doesn't match expectations

## Key Design Decisions to Discuss with User

During the conversation, the agent should raise these questions:

- **AAA model:** Local only, or TACACS+/RADIUS? (Home lab typically stays local)
- **NTP:** Which servers? Authentication or not? (Design reference recommends auth)
- **SNMP:** v2c or v3? Which communities? (Design reference recommends v3 or at minimum non-default communities with ACLs)
- **Logging level:** Debugging (verbose) or informational (standard)?
- **STP priority:** Should one switch be root? What priority?
- **Unused ports:** Shut down and move to black-hole VLAN, or leave as-is?
- **BPDU Guard:** Enable on all access ports? (Design reference says yes)
- **Exec timeout:** 0 0 (never timeout) for lab, or 15 0 for security?
- **HTTP server:** Keep enabled or disable? (Design reference says disable if not needed)
- **Single repo or multiple:** One repo for templates+backups+intended, or separate repos?

## Required Environment Variables

- `NAUTOBOT_URL`, `NAUTOBOT_TOKEN` — Nautobot API access
- `GITHUB_PERSONAL_ACCESS_TOKEN` — GitHub repo creation and commits
- `PYATS_TESTBED_PATH` — device connectivity for config collection

## Notes

- This skill produces templates as a STARTING POINT. The user refines them through conversation.
- The design reference (`cisco_design_reference`) provides Cisco best practices but the user's environment may have valid reasons to deviate. Always explain the recommendation and accept the user's decision.
- pfSense and other non-IOS devices should be excluded from golden config scope (no network_driver for Nornir/NAPALM).
- Config context secrets should use `{{ secrets.key }}` references where Nautobot secrets groups are configured, or literal values for lab environments.
- The compliance rules use `match_config` regex patterns that identify which lines of the running config belong to each feature. Golden config uses these to extract the relevant section for comparison.
