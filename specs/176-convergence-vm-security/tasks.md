# Tasks: Convergence VM Security proposal

## Scope proposal

- [x] T001 Read the accepted spec 161 boundary and the spec 162 connector, HUD route and settings.
- [x] T002 Inspect the service's VM Security analysis, contract, public route and tests at a pinned revision.
- [x] T003 Compare with upstream's NSM, nmap and observability integrations.
- [x] T004 Define one tool, one panel, ownership, exclusions and acceptance; list gaps honestly.
- [ ] T005 Obtain the maintainer's scope decision.

## Implementation, only after agreement

- [ ] T006 Service: synthetic VM Security source with a label in the response; pin a public revision.
- [ ] T007 Connector: `convergence_vm_security()` with strict validation and negative fixtures.
- [ ] T008 HUD: guarded route and panel with findings, evidence, coverage and the synthetic banner.
- [ ] T009 Skill, connection guide, counts and catalog.
- [ ] T010 Qualify: synthetic demo in the HUD, one live Proxmox VE finding, access and compatibility cases.
- [ ] T011 Independent review and release metadata.

T005 gates T006–T011.
