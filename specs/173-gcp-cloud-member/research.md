# R04 research decisions

2026-11-03, source52b3fbdb; three independent read-only worktree assessments.

| Decision | Evidence / rationale | Alternative |
|---|---|---|
| Existing NetClaw skill/MCP | Explicit owner instruction | No direct REST replacement |
| Existing demo source | Owner supplied endpoint/token | No seeded server or private CML upload |
| v2 Bearer compatibility | Installed14ec2fe7 NetBox client hardcodes Token | Managed tested compatibility patch |
| Singular object types | Installed MCP accepts dcim.device/ipam.prefix; skill uses plurals | Discover actual schemas and correct guidance |
| Sonnet4.6 | Current provider/guard/runtime pin | Brief Haiku is Thermidor-only evidence; deferred |
| Exact object reads | Existing netbox_get_object_by_id | No arbitrary searches in execution profile |
| Actual skill context | Current protected OpenClaw skips bootstrap, pyATS-only prompt | Hash/load reviewed skill with scoped constraints |
| Bounded subnet | Existing calculator materializes addresses | Preserve IPv4 /24–/30 and adjacent-network bounds |
| Explicit member role | Current role launcher refuses cloud members | Add role; preserve Border fail-closed behavior |
| Linux Unix socket | host.docker.internal/127.0.0.1 path only Mac-qualified | No exposed host broker port |
| Docker-aware quota | R03 meters OUTPUT only | Include FORWARD and metadata denial |
| Full HUD selection identity | device_name absent for all new tools | Compare member/tool/canonical arguments |

Primary source: [NetBox authentication](https://netbox.readthedocs.io/en/stable/integrations/rest-api/#authenticating-to-the-api), retrieved2026-11-03. v2 tokens use Bearer; legacy v1 tokens use Token. Endpoint access is not yet qualified.

All assessments are source observations. No actual R04 cloud/NetBox/model/browser
workload is implied. Future token isolation requires actual process/artifact checks.
