# Spec 164: Convergence evidence for the NetClaw Border

Created 2026-10-31; branch `164-convergence-border`; status: implementation.
Owner approved continuing the responsibility split recorded in spec163/ownership.md.
This follows spec162's optional reader; it does not replace spec163's failed model
interpretation evidence. Spec Kit artifacts are maintained manually in lifecycle order.

## User scenarios and acceptance

1. P1: A standalone operator selects a current Convergence address observation and
chooses Investigate. The existing Canvas receives bounded, parseable evidence with
exact site/window/exporter, observed counters, coverage, provenance, retrieval time,
record count/limit, sampling uncertainty and explicit omissions. Loading, failed,
stale or mismatched detail is not handed off as current evidence. No model call is
made by the Convergence panel; existing operator chat/session controls remain in use.
2. P1: An OpenClaw operator with an enabled, complete Convergence reader can select
a focused Convergence member profile. The member receives only the observation skill,
base floor and appropriate MCPs, and its connector loads its own private environment.
Disabled/incomplete configuration must not advertise a usable member. Hermes must
not newly advertise or accept Convergence through its protected subnet-only adapter.
The existing OpenClaw dispatch/receiver path must accept only the explicit Convergence
skill within an enrolled member's scope; profile selection alone is insufficient.
Unrelated delegated skills, write tools and Hermes Convergence execution stay denied.
3. P1: Convergence supplies evidence; the Border chooses available authorized
corroborating tools/members. The observation skill's no-bypass rule protects this
source but does not restrict an entire investigation to two tools. Unavailable or
denied sources remain gaps; observed text cannot grant authority or trigger writes.

## Requirements

Preserve the latest-100 response bound; no invented pagination, total matching count,
request/reply semantics, application identity, sampling meaning or threat verdict.
Create an explicit allowlisted envelope that fits the existing selected-context path
without arbitrary truncation. Preserve exact timestamp strings. Use existing owned
session, authorization, routing, provisioning and audit mechanisms. No new tools,
backend schema, external dependencies, capture, autonomous investigation loop,
production deployment or model/provider calls in this source implementation run.
A one-claw installation must remain usable; federation is optional.

## Success and qualification boundaries

Affected HUD tests/build, browser handoff interaction, profile/provisioning isolation
and negative cases, existing connector contracts and catalog/spec coherence must pass,
with independent review. Tests with simulated endpoints are explicitly fixture evidence.
Real Border/member/provider cross-source interpretation remains a separate live
qualification task; do not count synthetic routing tests as that acceptance. Hermes,
Mac/Windows, production confinement and capture remain outside this implementation.
