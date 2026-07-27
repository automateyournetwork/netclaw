# Implementation Plan: NetClaw Home (067-convergence)

**Branch**: `067-convergence` | **Date**: 2026-07-24 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `/specs/067-convergence/spec.md`

## Summary

Productize the Convergence pipeline as a **CONVERGENCE** top-level tab in the Visual HUD, with convergence-api + OBS packaging (Docker or K3s), adapter wizard, and universal **risk preserve + guardian-claw ensure**. Implementation is phased PR0–PR7 (done) plus **Phase 8 optional greenfield device SNMP + agent observability** (plumbing shipped including T088 smoke), **Phase 9 investigation policy & token economics** (T0/T1/T2 policy engine + thin `alert` agent profile — T096–T110 done), and **Phase 10 telemetry setup productization** (inventory → templates → apply → curated boards; Spec Kit + PR1–PR3 done). Tracked in `tasks.md` / [`device-telemetry-greenfield.md`](./device-telemetry-greenfield.md) / [`investigation-policy.md`](./investigation-policy.md) / [`telemetry-setup.md`](./telemetry-setup.md). Work must cohere with NetClaw Spec Kit, modular installer, `.env.example`, iN2N profiles, and existing skills/MCP — not a parallel framework.

## Technical Context

**Language/Version**: JavaScript (HUD, convergence-api Node 20), Python 3.12 (alert-receiver, exporters, install helpers)  
**Primary Dependencies**: Express, Three.js/Vite (HUD), Postgres, Prometheus, Alertmanager, OpenClaw gateway, iN2N mesh  
**Storage**: Postgres (events diary); Prometheus/VM (metrics); optional RAG under `~/.openclaw/rag`  
**Testing**: Manual HUD smoke; compose smoke scripts; unit tests for adapter config generation where practical  
**Target Platform**: Linux host (NetClaw agent + HUD) + Docker Compose or K3s for OBS/convergence-api  
**Project Type**: multi-package (ui + deploy + scripts) inside monorepo `netclaw`  
**Performance Goals**: HUD tab switch <1s; Overview API p95 <2s on LAN  
**Constraints**: No wipe of existing risks; no browser secrets for UniFi/API keys; Constitution-compliant artifact coherence  
**Scale/Scope**: Single-site home / small-office first; multi-site later via existing Guardian site model

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| Safety-first / no unsafe auto-remediation | Pass | No auto radio Optimize; investigations read-only by default |
| Credential safety | Pass | Keys only in env/secrets; `.env.example` empty defaults |
| Backwards compatibility | Pass | Existing risk/members preserved; dual-run with pilot stack |
| Full-stack artifact coherence (XI) | Pass | catalog + install-steps + setup + `.env.example` + skills + docs + HUD |
| Audit / GAIT | Pass | Keep alert-receiver + investigation GAIT paths |
| Spec-driven delivery | Pass | All work in `specs/067-convergence/` via specify templates |

## Project Structure

### Documentation (this feature)

```text
specs/067-convergence/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── device-telemetry-greenfield.md   # Phase 8 plumbing
├── investigation-policy.md          # Phase 9
├── telemetry-setup.md               # Phase 10 productized setup
├── contracts/
│   ├── convergence-api.md
│   ├── adapters.md
│   ├── install-wizard.md
│   ├── investigation-policy.md
│   └── telemetry-setup.md
├── checklists/requirements.md
├── spec.md
└── tasks.md
```

### Source Code (target)

```text
ui/netclaw-visual/
  src/app-shell/          # top-level COMMAND|HOME router
  src/views/home/         # Home tab views
  src/views/command/      # optional refactor of scene boot
  src/styles/home.css
  server.js               # /api/home/* proxy
ui/convergence-api/              # moved Guardian Express API (PR2+)
deploy/convergence/
  docker-compose.yml
  k8s/
  adapters/
config/convergence.example.yaml
scripts/lib/catalog.sh    # convergence components + profile
scripts/lib/install-steps.sh
scripts/systemd/netclaw-hud.service
.env.example              # HOME_*, adapter keys
workspace/skills/         # multi-vendor wording updates
```

**Structure Decision**: HUD + deploy packages inside `netclaw/`; agent remains host NetClaw + iN2N; OBS/convergence-api via Docker or K3s.

## Delivery strategy (operator decision)

**Upstream contribution model: single PR when solid (option B).**

| Layer | Practice |
|-------|----------|
| Day-to-day | Develop and commit on **this fork’s `main`** (`origin` = `byrn-baker/netclaw-convergence`) |
| Internal slices | Still implement in **task phases** (HUD → convergence-api → Docker → K3s → installer → triage) and keep `tasks.md` checkboxes current |
| Upstream | When Home is solid end-to-end (install + test), open **one** PR: fork `main` (or a release branch cut from it) → `automateyournetwork/netclaw` `main` |
| Reviewability | Prefer a clean history (logical commits, no secrets, no pilot-only dirt) before that PR; optional squash at PR time |

**Do not** open multiple upstream PRs per phase unless strategy changes later.

### Implementation phases (maps to tasks.md; not separate upstream PRs)

| Phase | Story focus |
|-------|-------------|
| 0 | Spec kit complete (this folder) |
| 1 | US1 HUD tabs + Home shell |
| 2 | US2 convergence-api move + live Overview |
| 3 | US3 Docker minimal |
| 4 | US4 K3s minimal |
| 5 | US4–US5 installer, setup, guardian-claw ensure, framework cleanup |
| 6 | US6 Triage UI |
| 7+ | Adapter expansion |
| 8 | Optional greenfield device SNMP + agent observability (plumbing) |
| 9 | Investigation policy (T0/T1/T2) + token economics |
| 10 | Telemetry setup productization (inventory → templates → apply → boards) |

### Phase 10 delivery (post Spec Kit)

| Slice | Tasks | Outcome |
|-------|-------|---------|
| PR0 Spec | T120–T124 | Spec Kit complete (this folder) |
| PR1 Render/apply | T125–T128, T135–T136 | Lab re-applyable without hand-editing Prom |
| PR2 Wizard + SoT | T129–T131, T137 | Manual + Nautobot inventory path |
| PR3 Boards + alerts | T132–T134, T138 | First curated Grafana pass + safe named-interface alerts |
| PR4 Holistic suite | T139–T143 | Three narrative boards (Network · Security · NetClaw); T141–T143 open (syslog ingest, log selectors, pfSense depth) |

Operator path: setup → named interfaces → Grafana **:3300** folder Convergence
(**Network** · **Security** · **NetClaw**) → safe alerts → investigation policy.
No day-1 dependency on the k3s `observability` pilot.

## Complexity Tracking

> No constitution violations requiring exceptions. Scope is large but gated by PR phases.
