# Spec 178: Set up Convergence from NetClaw, and show its VM Security findings

Created 2026-11-06; branch `178-convergence-setup`, on 1.18.6; status: implementation and
verification. Implements the scope accepted in proposal 176 (PR #330), and adds a setup
skill for the separately operated service.

## Problem

1. Proposal 176 accepted a read-only VM Security view, gated on a labelled synthetic
   source in the service. Nothing implemented it.
2. Convergence lived only inside a NetClaw fork, pinned by commit. A NetClaw user had no
   supported way to install it, and upstream's Convergence docs pointed at that fork.

Convergence now has its own repository, [byrn-baker/convergence-platform](https://github.com/byrn-baker/convergence-platform)
(MIT), with releases, setup helpers and procedures, a synthetic VM Security source and
tooling to build a K3s cluster on Proxmox VE.

## User scenarios and acceptance

1. P1 (VM Security, spec 176 US1–US2): `convergence_vm_security()` takes no arguments,
   calls only `GET /api/security/vms` for the configured site, and returns findings,
   evidence and coverage validated against the pinned contract. The HUD's Convergence
   view shows them on request. Assessments stay advisory; `not_configured`,
   `unavailable`, `unauthorized` and `compatibility` are distinct; a failed refresh
   keeps earlier data marked stale. Guest heartbeats are dropped.
2. P1 (try it, spec 176 US3): against the service's labelled synthetic source, the view
   says **Synthetic demonstration** and shows every pattern and an insufficient-evidence
   source. A response that is synthetic but labelled live is rejected.
3. P1 (setup): asked to set up Convergence, NetClaw uses the `convergence-setup` skill:
   it installs a pinned convergence-platform release, discovers what it can, asks only
   for the rest, shows the plan and waits for approval before changing infrastructure,
   and follows the release's own procedures for a Docker trial, an existing K3s cluster
   (Helm or Argo CD), or a new K3s cluster on Proxmox VE.
4. P2: upstream's Convergence docs, catalog and integration test pin the release
   (`v0.1.1`) instead of the fork commit.

## Boundaries

- The connector stays read-only: one more fixed GET path, no arguments, same settings.
- The setup skill carries no code. Helpers and procedures are versioned with the service
  in convergence-platform; the skill pins the release. NetClaw imports no service code.
- Proxmox changes happen only through the release's `deploy/cluster/proxmox.py`, limited
  to the user-approved VMID range and name prefix, and only after approval.
- Spec 161's boundary otherwise holds: no collector, storage, case mutation or automatic
  investigation in NetClaw.
