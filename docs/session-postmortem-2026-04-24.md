# Session Post-Mortem: Demo Lab Setup (2026-04-24)

## Summary
- **Cost:** $15.35
- **Turns:** 317
- **Tool calls:** 338 (281 exec, 10 process, 47 MCP)
- **Duration:** ~47 minutes (15:14 - 16:01)
- **Cache read:** 42.7M tokens ($12.83 at $0.30/M — would have been $128 without caching)

## Root Causes of Cost

### 1. Exploration instead of execution (37 exec calls wasted)
The model spent the first 2 minutes exploring the environment (ls, cat, grep, find) instead of following the skill's prescribed commands. It read the README, inspected docker-compose files, checked creds.env contents, explored directory structures — all information already in the skill.

**Fix:** Add to skill: "Do NOT explore the repo structure. The skill has all the information you need. Execute the prescribed commands directly."

### 2. Local git server fiasco (29 exec calls wasted)
The model set up nginx + fcgiwrap + bare git repos to serve golden config templates to Nautobot. This was completely unnecessary — Nautobot can clone from GitHub directly, and the GitHub MCP is available.

**Fix:** Already addressed in skill rewrite. Phase 6 now explicitly says use GitHub MCP.

### 3. curl instead of MCP (46 exec calls wasted)
The model used curl to check Nautobot API status, authenticate, check job results, etc. — all things the nautobot-mcp-v2 tools handle.

**Fix:** Already addressed in AGENTS.md rule 11. Need stronger enforcement in the skill itself.

### 4. Template debugging loop (70+ exec calls)
The golden config Jinja2 templates from the workshop's Ansible roles don't work directly in Nautobot because:
- Ansible uses `cf_*` prefix for custom fields; Nautobot GraphQL uses `_custom_field_data`
- Ansible uses `ipaddr` Jinja filter; Nautobot uses `ipaddress_interface` from netutils
- Templates use `{% do %}` tag which isn't available in Nautobot's Jinja2
- Include paths use absolute `/eos/...` paths that don't resolve in Nautobot's git repo context
- Config contexts weren't loaded by Design Builder (had to be loaded separately)
- CE routers don't have MPLS config context (templates assumed all devices have it)

**Fix:** This is the biggest issue. The workshop's Ansible templates are NOT compatible with Nautobot golden config out of the box. The skill needs to either:
  a. Pre-build a compatible template repo (checked into netclaw or a known GitHub repo)
  b. Document every incompatibility and prescribe exact sed commands to fix them
  c. Skip golden config in the automated demo and do it as a separate manual phase

### 5. Config context gap
Design Builder created devices, interfaces, IPs, BGP, but NOT config contexts. The model had to write a Python script to load 18 config contexts from YAML files. This was 10+ exec calls.

**Fix:** Document this in the skill. Prescribe the exact command to load config contexts.

### 6. Ansible compatibility issues
- `pynautobot` version mismatch (`exclude_m2m` parameter)
- `clab` role has hardcoded paths for the blog author's environment
- `build` role queries `cf_*` GraphQL fields that don't exist (Nautobot 2.x uses `_custom_field_data`)

**Fix:** Document the exact pip upgrade and Ansible role patches needed.

## Specific Failures That Caused Decision Loops

### F1: Nautobot not responding after docker compose up
- Nautobot was running migrations (first boot)
- Model wrote a bash polling loop (18 iterations × curl) instead of waiting
- **Fix:** Skill should say "First boot takes 2-3 minutes for migrations. Wait, then check once."

### F2: pynautobot exclude_m2m error
- networktocode.nautobot collection 6.1.1 passes `exclude_m2m` to pynautobot
- Workshop's pip-requirements.txt pins pynautobot 2.6.3 which doesn't support it
- Model had to upgrade pynautobot to 2.7+
- **Fix:** Add `pip install --upgrade pynautobot` to Ansible setup step.

### F3: Custom field GraphQL schema mismatch
- Ansible roles query `cf_ospf_area`, `cf_mpls_enabled` etc.
- Nautobot 2.x GraphQL exposes these as `_custom_field_data { ospf_area }`
- Model wrote a `set_fact` task to normalize — clever but 5+ exec calls
- **Fix:** Prescribe the exact set_fact patch in the skill.

### F4: Config contexts not loaded
- Design Builder job creates devices but not config contexts
- Config contexts are in `config_contexts/` and `config_context_schemas/` dirs
- Model wrote a Python loader script — 10+ exec calls
- **Fix:** Prescribe the exact loader command in the skill.

### F5: cEOS image tag mismatch
- Topology references `ceos:4.34.0F` but image was tagged `ceos:latest`
- Model had to retag or fix the topology
- **Fix:** Add image verification to prerequisites check.

### F6: Golden config template incompatibilities (biggest time sink)
- `ipaddr` filter → `ipaddress_interface`
- `{% do %}` tag → namespace workaround
- Absolute include paths → relative paths
- `cf_*` prefix → `_custom_field_data` access
- Missing `mpls` guard for CE routers
- **Fix:** Pre-build a Nautobot-compatible template repo.

## Recommendations

### For the next run (immediate)
1. Pre-build a golden config template repo that works with Nautobot (not Ansible)
2. Add config context loader command to Phase 3
3. Add pynautobot upgrade to Phase 5 Ansible setup
4. Add custom field normalization patch to Phase 5
5. Verify cEOS image tag in prerequisites

### For Ollama compatibility
The batched command rewrite should help significantly. But the template debugging loop (F6) is the real problem — an Ollama model will struggle even more with iterative Jinja2 debugging across 70+ exec calls. The only viable fix is to eliminate the debugging entirely by providing pre-built compatible templates.

### Cost projection with fixes
- Current: 317 turns, $15.35
- With batched commands only: ~80 turns, ~$4
- With batched commands + pre-built templates: ~30 turns, ~$1.50
- With session breaks between phases: ~$0.50-1.00 per session × 3-4 sessions
