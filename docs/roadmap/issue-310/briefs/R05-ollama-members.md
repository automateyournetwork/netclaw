# R05 — Ollama members: cloud IPv6 and on-prem IPv4

- **Roadmap item:** 3 — Border and cloud member using Ollama (subnet)
- **Depends on:** R04
- **Gate:** human review before R06/R07

## Specify input

A cloud member in GCP runs Ollama on its own host and performs IPv6 subnet
calculations; an on-premises member runs Ollama locally and performs IPv4 subnet
calculations. One browser request dispatches two separately approved child
operations, one to each member, and presents the combined result. Each Ollama
instance is reachable only by its own member's guard. Model locality describes
where inference runs, not where the Border or infrastructure lives.

User stories:
- P1: The combined request runs both children, each with its own approval, and
  arithmetic is independently verified.
- P1: Nothing but the member's guard can reach either Ollama instance.
- P2: Time and resource use are recorded for local versus cloud CPU inference.

## Clarify: decisions (recommended default first)

1. Pins: Ollama 0.40.11, Qwen3 0.6B Q4_K_M, CPU inference (Thermidor-qualified);
   anything else unqualified.
2. Guard in production mode: qualify DefenseClaw in front of local Ollama. If that
   is unsupported, record the gap and specify an equivalent admission guard for
   Ollama. [HUMAN if neither works]
3. Cloud machine sizing for CPU inference; GPU is out of scope.
4. On-prem host: Linux ARM64 member in Docker on the Mac, as in Thermidor.

## Plan notes

- Thermidor recorded 28 s (local) and 150 s (cloud) for the combined request;
  use these as a baseline, not a target.
- Local Ollama removes provider API charges, not compute or transfer costs;
  results still travel to the Border and evidence collector.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Workload | Combined request with two approvals; both results independently verified |
| Isolation | Ollama port unreachable from the Border, other members and the internet; direct model call bypassing the guard refused |
| Accounting | Per-child time, CPU/memory and usage recorded; no provider API charges on Ollama paths |
| Failure | One child failing does not corrupt or replay the other |
