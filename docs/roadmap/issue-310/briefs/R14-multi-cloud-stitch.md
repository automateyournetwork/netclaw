# R14 — Multi-cloud: nine Borders, three providers

- **Roadmap item:** 7 — stitch everything together
- **Depends on:** R11, R13
- **Gate:** human review before multi-user work

## Specify input

One organization cluster of nine Borders, three per provider in GCP, Azure and
AWS. All Borders are meshed (36 cluster links). Every member, the few local
members plus the cloud members in each provider, holds one identity and attaches
to all nine Borders. Member-to-member is refused. Voter placement survives the
loss of any single provider. Non-voting Borders serve the HUD and forward
protected actions to the authority. Provider-local clusters from R09, R11 and R13
are retired as their Borders join the global cluster; clusters are not merged in
place.

User stories:
- P1: Any workload runs through any of the nine Borders.
- P1: Losing an entire provider keeps service, with no replay.
- P1: Shared dependencies are visible and their failure behavior is known.

## Clarify: decisions (recommended default first)

1. Voters: five placed 2/2/1 across providers (survives any one provider loss);
   three placed 1/1/1 is the cheaper alternative. [HUMAN]
2. Provider reachability: a provider network/address outage partitions
   every cloud at once. Either accept and document it, or qualify a secondary
   transport for cluster links (cloudflared from spec 108 or provider VPN). [HUMAN]
3. Migration order: join one provider's Borders at a time; retire each
   provider-local cluster only after its Borders are healthy in the global one.
4. Member identity consolidation: one identity per member; retire the per-provider
   enrollments from R10–R13.
5. Optional global operations view: extend spec 121 (federated topology viz).

## Plan notes

- Record service ports separately from provider public-IP counts and quotas; optional
  ngrok deployments record their account limits separately.
- Clock skew across providers must stay within the lease assumptions from R08.
- Other shared dependencies to list: DNS, model providers, the Mac's sleep and
  residential link, any device VPN.

## Acceptance evidence

| Group | Evidence |
|---|---|
| Mesh | 36 healthy cluster links; M × 9 authenticated attachments with M recorded |
| Topology | Member-to-member negative tests from every member |
| Workloads | Every workload via at least one Border per provider |
| Provider loss | Each provider removed in turn: service continues, no replay |
| Partitions | Cross-provider partitions: at most one authority |
| Transport dependency | Documented provider/address outage drill; optional ngrok outage scoped to its deployments |
| Cost and inventory | Monthly cost; service endpoint/public-IP counts versus provider quotas |
