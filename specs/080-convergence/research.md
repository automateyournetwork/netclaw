# Research: 080-convergence

## Decisions

### D1 — Top-level HUD tabs vs overlay panel
**Decision**: Top-level COMMAND | HOME tabs.  
**Rationale**: Operator requested full product surface, not a collapsible chrome panel. Command retains Three.js risk graph.  
**Alternatives**: KnowledgePanel-style overlay (faster but not “app mode”).

### D2 — Agent plane location
**Decision**: Host NetClaw + iN2N risk by default; Docker/K3s for OBS + convergence-api.  
**Rationale**: Matches pilot; preserves any existing risk; guardian-claw is a host member unit.  
**Alternatives**: All-in-Docker agent profile for greenfield only.

### D3 — guardian-claw as product component
**Decision**: Full pipeline setup always ensures investigator member (`guardian-claw` / `network-guardian` profile).  
**Rationale**: Convergence requires investigation; greenfield must not leave operators without a claw.  
**Alternatives**: Manual member creation (rejected for full pipeline).

### D4 — Move Guardian into netclaw
**Decision**: Lift convergence-api under `netclaw/ui/convergence-api` (or `services/convergence-api`); HUD-native UI replaces EJS as primary.  
**Rationale**: Upstream self-containment; external k3s-observability-stack remains pilot until parity.  
**Alternatives**: Forever proxy to external repo (poor upstream UX).

### D5 — Spec Kit tracking
**Decision**: All PR work tracked in `specs/080-convergence/tasks.md` via specify templates.  
**Rationale**: NetClaw constitution / SDD standard (062, 049, …).

### D6 — Wireless v1
**Decision**: UniFi Integration API + unifi-exporter first; adapter interface for future vendors.  
**Rationale**: Proven pilot metrics (`unifi_radio_tx_retries_pct`, device radios).  
**Alternatives**: SNMP-only APs (unreliable on U6 until agents listen).

## Open research (later PRs)
- Exact `in2n-member-home` invocation for idempotent guardian create  
- Minimal Prometheus image memory footprint for Docker Home  
- JWT vs local-trust for Home tab auth on single-operator hosts  
