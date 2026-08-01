# Requirements checklist: 080-convergence

**Feature**: [spec.md](../spec.md)

- [x] User stories prioritized with independent tests
- [x] Acceptance scenarios Given/When/Then
- [x] Functional requirements numbered
- [x] Success criteria measurable
- [x] Assumptions and out-of-scope listed
- [x] Risk preserve + guardian-claw ensure specified for any operator
- [x] Spec Kit / tasks.md PR mapping defined
- [x] Framework coherence (catalog, .env.example, skills) called out
- [x] Spec review sign-off before large code PRs (operator)

## Review log

| Date | Reviewer | Scope | Outcome |
|------|----------|-------|---------|
| 2026-07-27 | operator + Kiro | Drift audit after Phase 10 PR1–PR3 | Spec realigned to shipped state: US10 + FR-030–FR-035 + SC-014–SC-016 added for the holistic Network·Security·NetClaw suite; FR-027 / SC-012 retargeted off retired board names; T132/T133 marked superseded by T139; T141–T143 opened for syslog ingest, log selectors, pfSense depth. |

## Drift guard (pre-PR)

Before opening the single upstream PR, confirm no spec/implementation drift:

```bash
# retired board names must not appear as acceptance surfaces
# (tasks.md keeps them only inside the superseded T132/T133 history entries)
grep -rn "Campus Interfaces\|Home NOC\|network-interfaces\|device-snmp-switches" \
  specs/080-convergence/spec.md specs/080-convergence/plan.md \
  specs/080-convergence/quickstart.md specs/080-convergence/telemetry-setup.md \
  specs/080-convergence/contracts/

# provisioned suite matches FR-027
ls deploy/convergence/grafana/provisioning/dashboards/json/
```

Every provisioned dashboard panel must map to a collector installable from this
repo (FR-031). If a panel needs the pilot `k3s-observability-stack`, it is a
drift finding, not a feature.
