# Session Post-Mortem: Demo Lab Setup — Steps 18-20 (2026-04-25)

## Summary
- **Model:** DeepSeek V4 Flash on Ollama Cloud (`deepseek-v4-flash:cloud`)
- **Cost:** $0.00
- **Sessions:** 3 (context window splits)
- **Duration:** ~24 minutes (04:09 - 04:33 UTC)
- **Completed:** No — got stuck on golden config git push 403 errors

## What Worked
- Model correctly followed the skill steps 18-20 in order
- Used nautobot-mcp-v2 tools (not curl or docker exec) — good MCP discipline
- Synced all 4 git repos successfully
- Triggered golden config jobs correctly
- Diagnosed the 403 as a git push authentication issue
- Batched parallel MCP calls (e.g., syncing 4 repos in one turn)

## Where It Got Stuck

### 1. Git push 403 on golden config repos
The "Generate Intended Configurations" and "Backup Configurations" jobs both failed at the git push stage with HTTP 403. The model correctly identified this as an auth issue but then entered a debugging spiral:
- Checked token permissions via GitHub API (showed push=true)
- Tested raw git push from inside the container
- Tried single-device targets to rule out timeouts
- Explored fork approaches, local git alternatives
- Never found the actual root cause

**Root cause (found post-session):** TWO issues:
1. **Missing HTTP(S) username** — Nautobot's git credential helper builds `https://<username>:<token>@github.com/...`. The GitHub Access secrets group only had the token, not the username. Without it, Nautobot logs: `HTTP Username not found for secrets group GitHub Access`. Fix: add `GITHUB_USERNAME=x-access-token` env var and an HTTP(S) username secret to the group.
2. **Fine-grained PAT repo scope** — The GitHub fine-grained token was scoped to specific repos and the golden config repos (templates, intended, backup) were not in the allowed list. Even though the token owner owned the repos, push was denied.

### 2. TUI streaming stalls
The TUI stopped streaming output mid-response, requiring a keypress to resume. This caused the model to lose context on what it had already output, contributing to repeated/confused responses across session boundaries.

**Root cause:** WebSocket idle timeout between TUI and gateway during long MCP tool calls. Fix: set `keepAlive: 30` in openclaw.json gateway config.

### 3. Context window splits
3 sessions in 24 minutes means the context filled up fast. Each new session lost the debugging context from the previous one, causing the model to re-discover the same 403 error and re-attempt the same diagnostics.

### 4. Arista cEOS Management VRF deploy failure
The Ansible `--tags deploy` playbook fails on all 10 Arista cEOS devices because the generated configs include `vrf forwarding clab-mgmt` under Management0. The cEOS startup config already has the management VRF applied, and Ansible's `replace: line` mode conflicts with it. The model then spiraled into sshpass/SSH heredoc attempts instead of using pyATS (which was available and handles EOS correctly).

**Fix:** Added known issue + pyATS failback instructions to Step 17 in the skill. Explicitly tells the model to strip the mgmt VRF lines and use `pyats_configure_device()` instead of SSH hacks.

## Comparison to Previous Runs

| Model | Date | Turns | Exec | MCP | Cost | Completed? |
|---|---|---|---|---|---|---|
| qwen3-coder:480b | 04-24 | 104 | 95 | 0 | $0 | No — ignored MCP tools |
| Claude Sonnet 4.6 | 04-24 | 317 | 281 | 47 | $15.35 | Yes — template debugging spiral |
| Kimi K2.5 | 04-25 | 254 | 130 | 94 | $0 | Yes — best MCP usage |
| DeepSeek V4 Flash | 04-25 | ~228 | ? | ? | $0 | No — stuck on 403 push |

## Fixes Applied

### Skill updates (demo-lab-setup SKILL.md)
1. **Step 2** — now adds `GITHUB_USERNAME=x-access-token` to creds.env
2. **Step 10** — now creates both username and token secrets in the GitHub Access secrets group:
   - HTTP(S) / username → `GITHUB_USERNAME` env var
   - HTTP(S) / token → `GITHUB_PERSONAL_ACCESS_TOKEN` env var

### Progress notes updated
- Added issue #11 (GitHub Secrets Group needs BOTH username + token)
- Added issue #12 (fine-grained PAT repo scope must include all golden config repos)

## Lessons Learned

1. **Nautobot git auth requires username + token** — this is not obvious from the Nautobot docs. The debug log (`HTTP Username not found`) is the clue but it's DEBUG level, easy to miss.
2. **Fine-grained PATs are repo-scoped** — even if the token owner owns the repo, the token must explicitly list it. Classic PATs (`ghp_`) don't have this restriction.
3. **Model can't fix infra issues** — the 403 was an infrastructure/credential problem, not a logic error. The model correctly diagnosed "auth issue" but couldn't fix it because the fix required changing the PAT scope in GitHub's UI and adding a missing env var to the Docker environment.
4. **Session splits kill debugging** — when the model is mid-investigation and the context window fills, the new session starts cold. Need either larger context or checkpointing.

## What's Next
- Clean run with both fixes applied (username secret + correctly scoped PAT)
- Should complete Steps 18-20 in a single session now that the 403 is resolved
- Verify intended + backup + compliance jobs all succeed end-to-end
