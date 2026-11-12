# R09B — GCP completeness survey

- **Roadmap item:** 4 (substep 2 of 2 before Azure)
- **Depends on:** R09A
- **Status:** COMPLETE. The survey is a reference for any future GCP revisit; setup follow-on is R09C (spec 193).
- **Gate:** passed (R09C closes GCP before R10)

## Specify input

Explore the other GCP capabilities that would make the deployment more complete, and decide which to adopt before Azure so the Azure and AWS stages repeat a finished pattern. Candidate areas to assess (not a commitment): load balancing and health-checked endpoints per Border or pooled behind one hostname; edge protection (Cloud Armor, rate limiting); identity-aware admin access (IAP, OS Login) and workload identity instead of long-lived keys; Secret Manager/KMS for provider and device credentials; Cloud NAT and private egress with allow-lists; firewall policy structure and VPC-level controls; managed instance groups or other recovery automation; logging, monitoring, alerting and budgets; certificate and DNS automation (Cloud DNS, managed certificates); artifact and image supply chain.

For each candidate: what problem it solves for this deployment, cost, interaction with the HA authority and admission-timing findings, and an adopt/defer/reject decision with reasons. Adopted items become scoped follow-on work; nothing is built by the survey itself.

## Acceptance evidence

A written survey with a decision per candidate, cost estimates, and a recommended GCP reference deployment that R10 (Azure) and R12 (AWS) can mirror.
