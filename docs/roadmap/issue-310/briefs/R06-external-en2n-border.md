# R06 — External Border over eN2N/NCFED over direct TCP

- **Roadmap item:** eN2N (independent organizations)
- **Depends on:** R03, R04a
- **Gate:** feeds R07

## Specify input

An independently administered Border federates with the GCP Border over NCFED
through a separate registered direct TCP endpoint. Federation requires bilateral
consent, verified peer identity and explicitly approved capability exports with
their own budgets. The external peer cannot reach members directly, enumerate
internal data, gain any cluster authority, or reach BGP routing control.

User stories:
- P1: Two independent Borders complete NCFED and invoke one approved exported
  capability.
- P1: Missing, one-sided or revoked consent is refused.
- P1: The external peer cannot reach anything not explicitly exported.

For this stage, include separate VS Code and Mobile impact decisions and
implementation/verification work under [G12/G13](../README.md#global-invariants-every-brief-inherits-these).
Record a reasoned no-change disposition for an unaffected client; affected
integration gaps remain part of this feature.

## Clarify: decisions (recommended default first)

1. Peer trust: pre-provision the approved peer identity through an operator
   process; disable first-contact TOFU on public endpoints.
2. Exported capability for qualification: one read-only capability (subnet
   calculator or knowledge query).
3. External Border placement: a separate GCP project or a separate machine with
   its own provider/address and trust administration, so administration is truly independent. [HUMAN]

## Plan notes

- Thermidor's federation evidence used two tailnets; this needs fresh evidence
  over direct TCP. Externally delegated Ollama or infrastructure execution was never
  qualified; keep it out of scope.
- Starting points: `bgp/federation/service.py`, `tls.py`, `channel.py`,
  `negotiate.py`, `knowledge.py` (feature 064), specs 052, 059, 063.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Positive | NCFED completes over direct TCP; exported capability returns a correct result within its budget |
| Consent | Missing, one-sided and revoked consent refused |
| Identity | Wrong peer identity, wrong pin, altered binding refused |
| Boundary | Direct member invocation, prohibited enumeration, cluster/authority access and BGP routing control all refused |
| VS Code integration | Explicit G12 impact/disposition and evidence: External peer selection, consent and answer attribution preserve the local principal |
| Mobile integration | Explicit G13 impact/disposition and evidence: Ask Border and delegated-answer attribution preserve external-peer consent and scope; reasoned no-impact outcome if unaffected |
