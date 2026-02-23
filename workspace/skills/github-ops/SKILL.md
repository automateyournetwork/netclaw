---
name: github-ops
description: GitHub repository operations — issues, PRs, code search, and config-as-code workflows
version: 1.0.0
tags: [github, version-control, change-management]
---

# GitHub Operations Skill

You have access to GitHub's MCP server which provides 100+ tools for interacting with GitHub repositories.

## Available Capabilities

### Repository Operations
- Search repositories, list branches, get file contents
- Create/update files, create branches
- Compare branches, list commits

### Issues
- Create, list, search, update, and comment on issues
- Use issues to track network findings, audit results, and remediation tasks

### Pull Requests
- Create PRs for config changes, list PRs, get PR details
- Review and merge PRs, add comments

### Code Search
- Search across repositories for configuration patterns
- Find references to specific IPs, VLANs, ACLs in config repos

### GitHub Actions
- List workflow runs, get workflow status
- Trigger workflows for automated testing

## Workflow Patterns

### Network Finding → GitHub Issue
When you discover a network problem (via pyATS, health check, etc.):
1. Create a GitHub issue with the finding details
2. Include device name, symptom, recommended fix
3. Label appropriately (bug, security, performance)
4. Reference the GAIT session ID for audit trail

### Config Change → Pull Request
When a config change is approved:
1. Create a branch from main
2. Commit the new/updated config file
3. Open a PR with change details and ServiceNow CR number
4. Link the PR in the GAIT audit trail

### Audit Report → Repository
After health checks or audits:
1. Commit the report as a markdown file
2. Organize by date: `reports/YYYY-MM-DD/`
3. Include raw data and AI analysis

## Environment Variables
- `GITHUB_PERSONAL_ACCESS_TOKEN` — GitHub PAT with repo access

## Important Rules
- Never commit secrets, passwords, or API keys to repositories
- Always create a branch for changes — never push directly to main
- Include meaningful commit messages describing the network change
- Reference ServiceNow CR numbers in PR descriptions when applicable
