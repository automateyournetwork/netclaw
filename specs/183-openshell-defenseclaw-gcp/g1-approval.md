# G1 approval (R09A)

G1: APPROVED

- Date: 2026-11-10, by the owner in session.
- Topology: 2 Border VMs (e2-standard-2) + 1 etcd witness VM (e2-small), one region (northamerica-northeast1), VPC nc183-r09a, Ubuntu 24.04.
- Estimate accepted: about $0.20/hour, about $1.8 for a 6-hour window (specs/183-openshell-defenseclaw-gcp/cost-model.md).
- Also approved: two DNS A records and two Let's Encrypt certificates under automateyournetwork.com.
- Teardown: automatic, right after the evidence is committed (exact resource list = label netclaw-spec=183 / prefix nc183-).
- Unchanged rules: nothing published or pushed live without approval; qualified-code changes are listed for owner review.
