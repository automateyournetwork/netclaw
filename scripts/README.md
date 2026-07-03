# Scripts Directory

This folder contains a mix of general project utilities and **Part 15 (BGP Route Observability)** specific tooling.

## Quick Start for Part 15 / Route Stability

See the spec quickstart and blog for full context:

```bash
# Read-only proof of the three telemetry planes (no Grafana needed)
bash scripts/observability/demo-part15-observability.sh

# Full automated validation of phases
bash scripts/observability/validate-bgp-metrics.sh --phase 1   # ... through --phase 6

# Run all failure scenarios (A–F + BMP) that prove alerts + skills
bash scripts/observability/run-all-scenarios.sh --all

# Individual scenarios (thin wrappers around the above)
bash scripts/observability/run-scenario-b.sh   # link flap on PE1
```

Key validation entrypoints (user-facing):
- `demo-part15-observability.sh` — CLI demo of SNMP/gNMI/BMP/syslog/IP SLA → netclaw_* metrics + Loki.
- `validate-bgp-metrics.sh` — Phase 1–6 checkpoints (exporters, VM series, BMP, gNMI, alerts, golden config).
- `run-all-scenarios.sh` + `run-scenario-*.sh` — pyATS-driven fault injection + alert correlation (uses `.venv` pyATS).
- `validate-alert-scenarios.sh`, `validate-part15-chain.sh` — alert wiring and end-to-end checks.
- `setup-part15-lab.sh` — one-time lab prep for the observability config.

## Directory Layout & Categories

### Part 15 Observability & Validation (primary for this feature)
- `demo-part15-observability.sh`
- `validate-bgp-metrics.sh`
- `validate-alert-scenarios.sh`
- `validate-alert-automation.sh`
- `validate-part15-chain.sh`
- `setup-part15-lab.sh`
- `nautobot-push-observability.py`
- `push-lab-observability.py`
- `post-discord-webhook.sh`

### Failure Scenario Runners (A–F + BMP for testing alerts/skills)
- `run-all-scenarios.sh` (main dispatcher, sets env + calls Python)
- `run-scenario-a.sh` ... `run-scenario-f.sh` (convenience wrappers)
- `scenarios/run-scenarios.py` (core logic, requires pyATS + scenario_lib)
- `scenarios/scenario_lib.py` (shared pyATS / VM / Loki / alert wait helpers)
- `scenarios/run_scenario_b.py`, `scenarios/scenario-d-flap.py` (standalone / alternative runners for specific cases)

These drive real config changes (shutdown, netem, etc.) on the ContainerLab devices and assert on `netclaw_*` metrics + Grafana alerts.

### One-off Fixes & Migrations (historical, from bringing up Part 15 lab)
These were used during development to patch device configs, VRF logging, BMP on CSR, IP SLA, IOL→CSR migration, etc. Run only if you are recreating the exact lab state.

They live in `dev-fixes/` to keep the scripts root less confusing:
- `dev-fixes/apply-csr-observability-gaps.py`
- `dev-fixes/deploy-csr-configs.sh`
- `dev-fixes/fix-csr-syslog-vrf.sh`
- `dev-fixes/fix-pe-ip-sla.sh`
- `dev-fixes/fix-rr1-bmp-csr.sh`
- `dev-fixes/migrate-iol-to-csr-nautobot.py`

### General / Project Utilities
- `install.sh`, `install-bare-metal.sh`, `setup.sh`, `clean-slate.sh`
- `mcp-call.py`, `mcp-multi-call.py`
- `netclaw-watch.py`
- `gait-stdio.py`

## Notes
- Most Part 15 scripts assume the observability Docker stack + ContainerLab lab is running on `clab-mgmt`.
- pyATS scenarios require the project venv: `$ROOT/.venv/bin/python` (or the wrappers set it up).
- Many docs (blog, failure-scenarios.md, spec quickstart, observability/README) reference these by name under `scripts/`.
- Do not run the "fix-*" scripts unless you are debugging a fresh lab bring-up.

For the full story and validation steps, see:
- `specs/031-bgp-route-observability/quickstart.md`
- `docs/blogs/blog-part15-route-stability-observability.md`
- `docs/failure-scenarios.md`
- `docs/baselines/bgp-route-stability.md`
