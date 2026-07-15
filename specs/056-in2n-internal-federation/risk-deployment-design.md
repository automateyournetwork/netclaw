# John's Risk — deployment design (interview-driven)

Captured from the design interview (do NOT migrate until this is complete + John
signs off). Feeds `scripts/in2n-profiles.py`, the base-floor definition, and the
per-member core configs for the migration.

## Round 1 decisions (confirmed)

- **Border footprint = pure broker + comms.** The Border carries ONLY: comms
  (Slack, Discord, Webex, Twilio/voice, Twitter, PagerDuty, ServiceNow), routing,
  audit, memory, humanrail. **No network-domain skills** — every technical ask is
  delegated to a member. (Maximum focus; smallest Border context.)
- **Member base floor (every member, non-removable) EXPANDS to:**
  technical floor (n2n-member-runtime, self-status, member_heartbeat,
  member_report_audit) **+ memory + GAIT + humanrail escalation.** So every member
  is context-aware, self-auditing, and can escalate to the operator directly.
  (These base skills are tier=base → excluded from routing specificity, FR-021b.)
- **Models = provider-agnostic, operator-assigned per claw.** Each claw is its own
  OpenClaw install with its own provider+model, so the operator picks provider
  (Anthropic / OpenAI / Google / local, etc.) and model per claw — all the same,
  per-role tiers, or per-member override. The installer PROPOSES a sensible default
  (strongest-reasoning model for the Border; lighter/cheaper for members — the
  token-economy tier) but it is fully overridable. NOT Claude-only. (Exact
  strategy TBD round 2.)
- **Comms = Border-only.** Members never talk to the outside directly; results
  flow back through the Border.

## Round 2 (partial — confirmed)

- **Model/provider = per-claw, operator-set, with smart defaults.** Any provider
  per claw — Anthropic, OpenAI, Google, **local/Ollama**, etc. — mixed freely. The
  installer proposes a default (strong for Border, lighter for members) but every
  claw is overridable. Fully offline members (local model) explicitly supported.
- **Runtime = hybrid.** A small always-on "hot set" (e.g. cml, pyats + comms) stays
  live; the Border spins up other members on first route and idles them out
  (resource/token economy across ~23 members).

### Granularity principle (John, decisive)
**One claw per vendor / platform / tool.** Real integrations each get their OWN
dedicated member with focused skills + MCP tools — do NOT bundle domains:
- **Security vendors each dedicated:** ISE claw, ASA claw, Check Point claw,
  Palo Alto claw, FortiManager claw, Zscaler claw, Claroty claw, etc. (No combined
  "security" bundle.) Local sec utilities (nmap, nvd, fwrule) can be their own
  small claws too.
- **Clouds each dedicated:** AWS claw, Azure claw, GCP claw.
- **Source-of-truth each dedicated:** NetBox claw, Nautobot claw, Infrahub claw,
  Infoblox claw.
- **Virtual-environment/lab tools each dedicated:** CML claw, EVE-NG claw, GNS3
  claw, containerlab claw (split the old bundled "cml" profile).
- **Automation each dedicated:** Itential, AAP, NSO, Terraform.
- **Assurance each dedicated:** IP Fabric, SuzieQ, Batfish, Forward, gTrace.
- **Utilities may stay GROUPED** (NOT split) — e.g. visualizations (viz) as one
  member; subnet/rfc/wikipedia live on the Border.
- **Env-gated throughout:** a vendor claw is only offered when its backend is
  configured (so unconfigured vendors — checkpoint, zscaler, aws, gcp, terraform,
  meraki — stay dormant until their env is set).

### Security posture — a risk-wide MODE (John, decisive)
- **DefenseClaw (Cisco) and OpenShell (NVIDIA sandbox)** are optional security
  claws/members that do their jobs across the risk.
- **`N2N_RISK_MODE`**: **`testing`** = DefenseClaw + OpenShell OFF (fast iteration);
  **`production`** = both ENABLED and enforcing (members run sandboxed under
  OpenShell; DefenseClaw scans/guards). Ties into the existing openclaw.json
  `security.mode` (hobby ↔ defenseclaw) and spec 027 netshell-security.

### Runtime architecture (confirmed / decided)
- **Member runtime = OpenClaw EMBEDDED mode, NOT full OpenClaw.** OpenClaw ships
  `openclaw agent --local --model <provider/model>` (embedded agent, own API keys,
  no gateway). So a member = a lightweight iN2N launcher (`scripts/in2n-member.py`,
  TODO) that dials the Border + on a delegated task runs `openclaw agent --local
  --model <member-model>` over ONLY its scoped MCP servers. No gateway, no comms,
  no 195-skill catalog, no BGP speaker. (Google ADK = possible FUTURE alt member
  runtime; not needed now — OpenClaw --local covers it.)
- **Border runtime = full OpenClaw** (gateway :18789 + comms) + the mesh daemon
  (eN2N BGP mesh + iN2N Border listener). Keeps AS 65001 / router-id 4.4.4.4.
- **Transport:** John's risk = all co-located on ONE host → loopback (no ngrok).
  Cross-host/cross-org case (another org's Border, remote members) = members DIAL
  OUT to the Border's one reachable endpoint (public/ngrok or VPN/overlay). Still
  hub-and-spoke, still NO iBGP/mesh — the Border is the hub. (Settles John's
  recurring "do we need a mesh?" question: no.)
- **Per-member .env (least privilege):** each member gets its OWN workspace/config
  dir + a .env slice with ONLY its integration's secrets (cml→CML_*, pyats→PYATS_*
  +testbed, azure→AZURE_*). Border gets comms secrets + ZERO device creds.
- **Production mode ready:** OpenShell 0.0.32 + DefenseClaw + Docker all installed
  and up. Members run sandboxed under OpenShell; DefenseClaw guards.
- Small code change needed pre-migration: member skill-exec path uses `openclaw
  agent --local --model <member-model>` (today `gateway.py run_agent_turn` uses
  gateway mode) — add a `--local`/model variant for members.

### Build status (pre-migration)
- **Cold/on-demand: DONE + tested.** Member `scripts/in2n-member.py --idle-exit N`
  self-exits when quiet; Border `ensure_member_up` cold-starts an on-demand member
  on first route (spawns its launch_cmd, waits for dial-in+auth, then delegates);
  remote members (no launch_cmd) report unreachable instead of hanging. Registered
  via `member.launch_cmd`/`on_demand` (add_member + daemon + n2n_member_add).
- **Member runtime = OpenClaw embedded (`--local --model`)** — done.
- **Migration scaffold generator `scripts/in2n-migrate.py`** (generate-only) — done:
  27 least-privilege member .env slices + run.sh + border.env.additions + RUNBOOK.md.
- **89 tests green** (44 eN2N regression + 45 iN2N). Nothing has touched the live claw.
- Remaining before "done-done": the live migration itself (= quickstart validation)
  and the HUD 3D scene geometry (build LIVE while members populate — no browser in
  the coding env). Then blog.

### Round 3 decisions (confirmed)
- **`packet` member added** (pcap): packet-analysis + kubeshark-traffic (PACKET_BUDDY).
- **Don't build unused claws:** nautobot/infrahub/eve-ng/gns3/meraki/zscaler/
  claroty (+ aws/gcp/terraform/asa/checkpoint) stay DORMANT — John doesn't use
  them; not provisioned in his risk. (They auto-activate if env is ever added.)
- **pyATS = one claw** (one framework; not split by target device).
- **John's risk MODE = production** — DefenseClaw + OpenShell ON, to prove the
  full defense apparatus works end-to-end.
- **Hot set (always-on): Border + cml + pyats + ipfabric + viz.** All other
  members are on-demand (Border spins up on first route, idles out).
- **Roster for John's migration = 27 offered members** (added packet).

## Member roster (granular — one claw per vendor/tool, env-gated)

**Offered NOW (26, backend configured):** cml, containerlab, pyats, ipfabric,
suzieq, batfish, forward, gtrace, itential, aap, nso, aci, catalyst-center, f5,
sdwan, ise, paloalto, fortimanager, nmap, nvd, fwrule, azure, netbox, infoblox,
github, viz.

**Dormant (12, skills present, no backend env — auto-activate when configured):**
eve-ng, gns3, terraform, meraki, asa, checkpoint, zscaler, claroty, aws, gcp,
nautobot, infrahub.

Plus the **Border** (comms/routing/audit/memory/humanrail) and, in PRODUCTION
mode, the **defenseclaw** + **openshell** security members. viz stays a grouped
utility. Derived + env-gated by scripts/in2n-profiles.py.
