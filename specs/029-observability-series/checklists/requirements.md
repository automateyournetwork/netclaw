# Artifact Coherence Checklist: Observability Series

## Week 1 (Part 13) ✅

- [X] observability/docker-compose.observability.yml
- [X] observability/otel-collector/otel-config.yaml
- [X] observability/loki/loki-config.yaml
- [X] observability/grafana/provisioning/datasources/datasources.yaml
- [X] observability/grafana/provisioning/dashboards/dashboards.yaml
- [X] observability/grafana/dashboards/network-device-health.json
- [X] observability/grafana/dashboards/interface-status.json
- [X] observability/README.md
- [X] workspace/skills/deploy-observability/SKILL.md
- [X] Nautobot MCP v2 virtualization tools (server.py + nautobot_client.py)
- [X] config_contexts/observability.yml (Nautobot-Workshop + Datasource repos)
- [X] config_context_schemas/observability_schema.yaml (both repos)
- [X] ios/observability.j2 (Ansible + golden config template repos)
- [X] eos/observability.j2 (Ansible + golden config template repos)
- [X] Platform template includes (7 templates × 2 repos)
- [X] Blog Part 13 (local, not committed to repo)

## Week 2 (Part 14)

- [ ] workspace/skills/lab-noc-watch/SKILL.md
- [ ] workspace/skills/lab-alert-triage/SKILL.md
- [ ] Grafana alert rule provisioning (observability/grafana/provisioning/alerting/)
- [ ] Blog Part 14

## Week 3 (Part 15)

- [ ] mcp-servers/pfsense-mcp/server.py (read tools)
- [ ] mcp-servers/pfsense-mcp/pfsense_client.py
- [ ] mcp-servers/pfsense-mcp/requirements.txt
- [ ] mcp-servers/pfsense-mcp/README.md
- [ ] workspace/skills/lab-troubleshoot/SKILL.md
- [ ] workspace/skills/pfsense-firewall-ops/SKILL.md
- [ ] specs/029-observability-series/contracts/pfsense-mcp-tools.md
- [ ] config/openclaw.json (register pfSense MCP)
- [ ] .env.example (pfSense credentials)
- [ ] Blog Part 15

## Week 4 (Part 16)

- [ ] mcp-servers/pfsense-mcp/server.py (write tools added)
- [ ] mcp-servers/nautobot-mcp-v2/server.py (firewall plugin write tools)
- [ ] workspace/skills/firewall-reconcile/SKILL.md
- [ ] Blog Part 16

## Week 5 (Part 17)

- [ ] workspace/skills/lab-threat-intel/SKILL.md
- [ ] Threat enrichment integration (AbuseIPDB, GreyNoise)
- [ ] OTEL Collector config update (pfSense filterlog parsing)
- [ ] Blog Part 17

## Week 6 (Part 18)

- [ ] workspace/skills/compliance-watch/SKILL.md
- [ ] One-prompt deployment skill update
- [ ] Final validation (clone → deploy → monitor < 15 min)
- [ ] Blog Part 18
