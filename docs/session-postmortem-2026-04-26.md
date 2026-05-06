# Session Post-Mortem: Full Demo Run — DeepSeek V4 Flash (2026-04-25/26)

## Summary
- **Model:** DeepSeek V4 Flash on Ollama Cloud (`deepseek-v4-flash:cloud`)
- **Cost:** $0.00
- **Sessions:** 2 (long-lived with compactions)
- **Duration:** ~22 hours wall clock (04:47 Apr 25 → 03:33 Apr 26), active time much less (user-paced with overnight gap)
- **Compactions:** 16 total (4 in session 1, 12 in session 2)
- **User turns:** 68 | Assistant turns: 504 | Tool calls: 553
- **Tool breakdown:** MCP: 285, Exec: 208, Process: 34, Read: 21
- **Completed:** Steps 1-20 ✅, Compliance rules ✅ (partial — got stuck on template rendering diffs)

## Session Breakdown

### Session 1 — Steps 1-11 (d8a7)
- **User turns:** 49 | **Tool calls:** 163 (MCP: 84, Exec: 77)
- **Compactions:** 4
- Clone, build, Design Builder, restart, datasource, secrets, device assignment
- Included heartbeat cycles (pyats_run_show_command_multi: 36 calls)
- Heavy use of nautobot_update_object (20) for assigning secrets to all 20 devices

### Session 2 — Steps 12-20 + Compliance (d2a6)
- **User turns:** 19 | **Tool calls:** 390 (MCP: 201, Exec: 186)
- **Compactions:** 12
- ContainerLab deploy, Ansible build/deploy, golden config repos, compliance rules
- This is where most of the work and most of the issues happened

## What Worked Well

1. **MCP discipline** — 285 MCP calls vs 208 exec. Much better ratio than Claude Sonnet (47 MCP / 281 exec). Used nautobot-mcp-v2 for Nautobot operations, pyATS for device interaction, GAIT for audit trail.
2. **Compliance rule creation** — Created 13 compliance features and 30 compliance rules using cisco_design_reference for match_config patterns. Good use of the golden-config-bootstrap skill.
3. **Parallel device operations** — Used pyats_run_show_command_multi (39 calls) for fleet-wide checks instead of device-by-device.
4. **GAIT audit trail** — 8 gait_record_turn + 6 gait_branch calls. Maintained audit discipline throughout.
5. **GitHub MCP** — Used get_file_contents (6) to inspect template repos instead of cloning locally.

## Where It Got Stuck

### 1. Arista cEOS config deploy failure (Step 17)
The Ansible `--tags deploy` playbook failed on all 10 Arista cEOS devices. The generated configs include `vrf forwarding clab-mgmt` under Management0, which conflicts with the cEOS startup config that already has the management VRF applied.

The model then spiraled into SSH heredoc/sshpass attempts instead of using pyATS as a failback. User had to intervene: "see if you can fix this issue" and "Does the Arista need to enable the http api so that it can be used instead of ssh?"

**Fix applied:** Step 17 now documents the known issue and prescribes pyATS as the failback.

### 2. Golden config git push 403 (Step 18-20)
Intended and backup jobs failed at git push with HTTP 403. Two root causes:
- Missing HTTP(S) username in GitHub Access secrets group
- Fine-grained PAT not scoped to all golden config repos

**Fix applied:** Steps 2 and 10 now include GITHUB_USERNAME=x-access-token.

### 3. cEOS backup SSH key exchange failure
The Nautobot celery worker container's SSH config blocks Arista's cEOS key exchange algorithms. Backup jobs fail for all EOS devices. User identified this: "cEOS backup failures are cosmetic — the worker container's SSH key exchange config blocks Arista's cEOS algorithms."

**Not yet fixed.** Needs either:
- SSH config override in the celery worker container
- eAPI (HTTP) transport for Arista devices instead of SSH

### 4. Compliance template rendering diffs (false positives)
The compliance engine flagged EOS BGP as non-compliant due to indentation differences (3 extra spaces in actual vs intended). Also flagged PE1 BGP due to duplicate BGP endpoints in Nautobot (one with peer-group, one without) causing extra `neighbor` lines in the rendered template.

The model correctly diagnosed both as template/data issues rather than real compliance failures, but couldn't fix them within the session.

### 5. TUI streaming stalls
Same issue as previous runs — WebSocket idle timeout causes streaming to stop mid-response, requiring a keypress to resume. Contributed to the "e" and "d" single-character user turns in Session 1.

## Tool Usage Analysis

| Tool | Calls | Notes |
|---|---|---|
| exec | 208 | Still high — Ansible, clab, SSH testing, git operations |
| pyats_run_show_command_multi | 39 | Fleet-wide parallel checks — good |
| process | 34 | Long-running command monitoring |
| nautobot_create_compliance_rule | 30 | 30 rules across IOS + EOS platforms |
| read | 21 | File reads for configs, templates |
| nautobot_update_object | 21 | 20 device secret assignments + 1 update |
| nautobot_get_job_result | 17 | Polling golden config job status |
| nautobot_create_compliance_feature | 13 | 13 features (hostname, NTP, DNS, etc.) |
| pyats_run_show_command | 12 | Single-device commands |
| nautobot_run_job | 11 | Design Builder + golden config jobs |
| cisco_design_reference | 11 | Best practice lookups for compliance rules |

## Comparison to Previous Runs

| Model | Date | Turns | Tool Calls | MCP | Exec | Cost | Completed? |
|---|---|---|---|---|---|---|---|
| qwen3-coder:480b | 04-24 | 104 | ~104 | 0 | 95 | $0 | No — ignored MCP tools |
| Claude Sonnet 4.6 | 04-24 | 317 | 338 | 47 | 281 | $15.35 | Yes — template debugging spiral |
| Kimi K2.5 | 04-25 | 254 | 287 | 94 | 130 | $0 | Yes — best MCP usage |
| DeepSeek V4 Flash (prev) | 04-25 | ~228 | ? | ? | ? | $0 | No — stuck on 403 push |
| **DeepSeek V4 Flash (full)** | **04-25/26** | **504** | **553** | **285** | **208** | **$0** | **Yes (partial)** — Arista deploy + backup issues |

## Lessons Learned

1. **Arista cEOS management VRF is a known landmine** — the workshop's Ansible templates don't account for cEOS startup config already having the VRF. This needs to be documented as a known issue with a prescribed workaround.
2. **pyATS should be the default failback for config push** — the model defaulted to raw SSH when Ansible failed, wasting turns on heredoc/sshpass debugging. The skill now explicitly says "use pyATS, not SSH."
3. **Compliance false positives from template rendering** — indentation diffs and duplicate Nautobot data objects cause false compliance failures. These need to be called out in the skill so the model doesn't chase them.
4. **16 compactions in one run** — the context window filled 16 times. Each compaction loses context. Long multi-step demos should be split into separate sessions at the mandatory stop points.
5. **Heartbeat cycles consume turns** — Session 1 had 36 pyats_run_show_command_multi calls from heartbeat checks. These are useful for monitoring but inflate the turn count.

## Fixes Applied This Session
1. **Step 2** — added `GITHUB_USERNAME=x-access-token` to creds.env
2. **Step 10** — added HTTP(S) username secret to GitHub Access secrets group
3. **Step 17** — documented Arista VRF known issue + pyATS failback

## What's Next
- Fix cEOS SSH key exchange in celery worker (or switch to eAPI transport)
- Add compliance false-positive guidance to golden-config-bootstrap skill
- Clean run with all fixes — target: Steps 1-20 + compliance in <200 tool calls
- Consider splitting into 4 sessions at mandatory stops to avoid compaction loss
