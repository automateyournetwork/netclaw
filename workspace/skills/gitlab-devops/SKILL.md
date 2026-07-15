---
name: gitlab-devops
description: "GitLab DevOps operations — issues, merge requests, CI/CD pipelines, repository browsing, labels, milestones, releases, and wiki management. Use when querying GitLab project status, monitoring pipeline executions, browsing repository files, creating issues for network findings, opening merge requests for config changes, or managing project metadata."
version: 1.0.0
license: Apache-2.0
tags: [gitlab, devops, ci-cd, version-control, change-management]
metadata:
  { "openclaw": { "requires": { "bins": ["node", "npx"], "env": ["GITLAB_PERSONAL_ACCESS_TOKEN"] } } }
---

# GitLab DevOps Skill

## Golden Rule

**Never execute write operations (create, update, delete, merge) without explicit operator confirmation.** All mutating actions — creating issues, merging MRs, triggering pipelines, deleting labels — require human-in-the-loop approval before invocation (Constitution XIV). Always observe current state before making changes (Constitution II: Read-Before-Write).

## MCP Server

This skill uses tools provided by the **gitlab-mcp** server (`@zereight/mcp-gitlab`), a community MCP server with 98+ tools for GitLab operations. The server is spawned locally via `npx -y @zereight/mcp-gitlab` and communicates over stdio transport.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GITLAB_PERSONAL_ACCESS_TOKEN` | Yes | GitLab PAT with `api` or `read_api` scope |
| `GITLAB_API_URL` | No | GitLab API URL (default: `https://gitlab.com`) |
| `GITLAB_READ_ONLY_MODE` | No | Restrict to read-only tools (default: `false`) |

---

## Workflow 1: Query Issues and Merge Requests (P1 — MVP)

Use this workflow to search, list, and inspect GitLab issues and merge requests for network project tracking.

### Step 1: Discover Projects

Find the target project by name or keyword:

```
Tool: search_projects
Parameters: { "query": "network-automation" }
```

Or list all accessible projects:

```
Tool: list_projects
Parameters: { "per_page": 20 }
```

### Step 2: List Issues

Query issues with filters for state, labels, assignee, or milestone:

```
Tool: list_issues
Parameters: {
  "project_id": "network-team/network-automation",
  "state": "opened",
  "labels": "outage",
  "assignee_username": "jcapobianco"
}
```

### Step 3: Get Issue Details

Retrieve full details for a specific issue:

```
Tool: get_issue
Parameters: {
  "project_id": "network-team/network-automation",
  "issue_iid": 42
}
```

### Step 4: View Issue Comments

List the discussion thread on an issue:

```
Tool: list_issue_comments
Parameters: {
  "project_id": "network-team/network-automation",
  "issue_iid": 42
}
```

### Step 5: List Merge Requests

Query merge requests with filters:

```
Tool: list_merge_requests
Parameters: {
  "project_id": "network-team/infra-configs",
  "state": "opened",
  "labels": "needs-review"
}
```

### Step 6: Get Merge Request Details

Retrieve MR details including diff stats and approval status:

```
Tool: get_merge_request
Parameters: {
  "project_id": "network-team/infra-configs",
  "merge_request_iid": 15
}
```

### Example Prompts
- "Show me open issues in project network-automation"
- "List merge requests awaiting review in project infra-configs"
- "Get details for issue #42 in network-automation"
- "Show my assigned issues across all projects"
- "Find all projects matching 'network'"

---

## Workflow 2: Monitor CI/CD Pipelines (P2)

Use this workflow to monitor pipeline status, inspect job details, and troubleshoot failures.

### Step 1: List Pipelines

View pipeline executions for a project:

```
Tool: list_pipelines
Parameters: {
  "project_id": "network-team/network-configs",
  "status": "failed",
  "ref": "main"
}
```

### Step 2: Get Pipeline Details

Retrieve details for a specific pipeline:

```
Tool: get_pipeline
Parameters: {
  "project_id": "network-team/network-configs",
  "pipeline_id": 123
}
```

### Step 3: List Pipeline Jobs

Inspect jobs within a pipeline:

```
Tool: get_pipeline_jobs
Parameters: {
  "project_id": "network-team/network-configs",
  "pipeline_id": 123
}
```

### Step 4: Get Job Log

Retrieve console output for troubleshooting:

```
Tool: get_pipeline_job_log
Parameters: {
  "project_id": "network-team/network-configs",
  "job_id": 456
}
```

### Pipeline Control (Write Operations)

**Requires operator confirmation. Skipped in read-only mode.**

#### Trigger a New Pipeline

1. Verify the target branch exists and check current pipeline state
2. Present the action to the operator for confirmation
3. Trigger the pipeline:

```
Tool: create_pipeline
Parameters: {
  "project_id": "network-team/network-configs",
  "ref": "feature/bgp-tuning"
}
```

#### Retry a Failed Pipeline

1. Check the pipeline status to confirm it is in a failed state
2. Confirm with operator
3. Retry:

```
Tool: retry_pipeline
Parameters: {
  "project_id": "network-team/network-configs",
  "pipeline_id": 123
}
```

#### Cancel a Running Pipeline

1. Verify the pipeline is currently running
2. Confirm with operator
3. Cancel:

```
Tool: cancel_pipeline
Parameters: {
  "project_id": "network-team/network-configs",
  "pipeline_id": 124
}
```

### Example Prompts
- "Show pipelines for project network-configs"
- "Show failed pipelines on the main branch"
- "Get the job log for pipeline #123"
- "Retry the failed pipeline for network-configs"
- "Cancel the running pipeline #124"

---

## Workflow 3: Browse Repositories and Files (P3)

Use this workflow to inspect repository structure, read file contents, and review change history.

### Step 1: List Repository Tree

View the directory structure:

```
Tool: list_repository_tree
Parameters: {
  "project_id": "network-team/network-configs",
  "path": "ansible/",
  "ref": "main"
}
```

### Step 2: Get File Content

Read a specific file:

```
Tool: get_file_content
Parameters: {
  "project_id": "network-team/network-configs",
  "file_path": "ansible/site.yml",
  "ref": "main"
}
```

### Step 3: List Commits

View commit history with filters:

```
Tool: list_commits
Parameters: {
  "project_id": "network-team/network-configs",
  "ref_name": "main",
  "path": "ansible/",
  "since": "2026-03-01T00:00:00Z"
}
```

### Step 4: Get Commit Details

Inspect a specific commit with diff:

```
Tool: get_commit
Parameters: {
  "project_id": "network-team/network-configs",
  "sha": "abc123def"
}
```

### Step 5: Compare Branches

Review differences between branches:

```
Tool: compare_branches
Parameters: {
  "project_id": "network-team/network-configs",
  "from": "main",
  "to": "feature/bgp-tuning"
}
```

### Example Prompts
- "Show the directory structure of project network-configs"
- "Show me the contents of ansible/site.yml on the develop branch"
- "List recent commits on the main branch for the ansible/ directory"
- "Compare the main and feature/bgp-tuning branches"
- "Show the diff for commit abc123def"

---

## Workflow 4: Manage Issues and Merge Requests (P4)

**All write operations require operator confirmation. Skipped in read-only mode.**

### Issue Management

#### Create an Issue

1. Verify the target project exists via `get_project`
2. Present the issue details to the operator for confirmation
3. Create the issue:

```
Tool: create_issue
Parameters: {
  "project_id": "network-team/network-automation",
  "title": "BGP peer flapping on router-01",
  "description": "Router-01 BGP peer to router-02 (192.168.1.1) is flapping every 30 seconds. Hold timer expiry detected. Investigate and resolve.",
  "labels": "outage,bgp,priority::critical",
  "assignee_ids": [42]
}
```

#### Update an Issue

1. Read current issue state via `get_issue`
2. Present proposed changes to operator
3. Update:

```
Tool: update_issue
Parameters: {
  "project_id": "network-team/network-automation",
  "issue_iid": 42,
  "state_event": "close",
  "labels": "outage,bgp,resolved"
}
```

#### Add a Comment

```
Tool: add_issue_comment
Parameters: {
  "project_id": "network-team/network-automation",
  "issue_iid": 42,
  "body": "Root cause identified: BGP hold timer set to 10s, peer timer at 30s. Aligned timers to 90/30. Peering stable for 15 minutes."
}
```

### Merge Request Management

#### Create a Merge Request

1. Verify source and target branches exist via `compare_branches`
2. Present MR details to operator for confirmation
3. Create the MR:

```
Tool: create_merge_request
Parameters: {
  "project_id": "network-team/infra-configs",
  "title": "fix: align BGP hold timers on router-01",
  "source_branch": "fix/bgp-timer-alignment",
  "target_branch": "main",
  "description": "Aligns BGP hold timer from 10s to 90s on router-01 peer to router-02.\n\nServiceNow CR: CHG0012345\nGAIT Session: gait-abc123"
}
```

#### Update a Merge Request

1. Read current MR state via `get_merge_request`
2. Present proposed changes to operator
3. Update:

```
Tool: update_merge_request
Parameters: {
  "project_id": "network-team/infra-configs",
  "merge_request_iid": 15,
  "labels": "approved,ready-to-merge"
}
```

#### Add a Comment to a Merge Request

```
Tool: add_merge_request_comment
Parameters: {
  "project_id": "network-team/infra-configs",
  "merge_request_iid": 15,
  "body": "Verified in CML lab. BGP peering stable after timer change. Ready to merge."
}
```

#### Merge a Merge Request

1. Verify MR has no conflicts and approvals are met via `get_merge_request`
2. **Explicitly confirm with operator** — this is irreversible
3. Merge:

```
Tool: merge_merge_request
Parameters: {
  "project_id": "network-team/infra-configs",
  "merge_request_iid": 15,
  "squash": true,
  "should_remove_source_branch": true
}
```

### Example Prompts
- "Create an issue in project network-automation titled 'BGP peer flapping on router-01'"
- "Close issue #42 in network-automation"
- "Create a merge request from fix/bgp-timer-alignment to main in infra-configs"
- "Merge MR #15 in infra-configs with squash"
- "Add a comment to MR #15: 'Verified in lab, ready to merge'"

---

## Workflow 5: Manage Labels, Milestones, Releases, and Wiki (P5)

### Label Management

```
Tool: list_labels
Parameters: { "project_id": "network-team/network-automation" }

Tool: create_label  (requires confirmation, skipped in read-only mode)
Parameters: {
  "project_id": "network-team/network-automation",
  "name": "critical-infrastructure",
  "color": "#FF0000"
}
```

### Milestone Management

```
Tool: list_milestones
Parameters: { "project_id": "network-team/network-automation" }

Tool: create_milestone  (requires confirmation, skipped in read-only mode)
Parameters: {
  "project_id": "network-team/network-automation",
  "title": "Q2 2026 Network Refresh",
  "due_date": "2026-06-30"
}
```

### Release Management

```
Tool: list_releases
Parameters: { "project_id": "network-team/network-configs" }

Tool: get_release
Parameters: {
  "project_id": "network-team/network-configs",
  "tag_name": "v2.1.0"
}

Tool: create_release  (requires confirmation, skipped in read-only mode)
Parameters: {
  "project_id": "network-team/network-configs",
  "tag_name": "v2.2.0",
  "name": "Network Configs v2.2.0",
  "description": "BGP timer alignment and OSPF area optimization"
}
```

### Wiki Page Management

```
Tool: list_wiki_pages
Parameters: { "project_id": "network-team/network-automation" }

Tool: get_wiki_page
Parameters: {
  "project_id": "network-team/network-automation",
  "slug": "bgp-runbook"
}

Tool: create_wiki_page  (requires confirmation, skipped in read-only mode)
Parameters: {
  "project_id": "network-team/network-automation",
  "title": "Incident Postmortem: Router-01 BGP Flap",
  "content": "## Summary\n\nBGP peering between router-01 and router-02 was flapping..."
}
```

### Example Prompts
- "List milestones for project network-automation"
- "Create a label called 'critical-infrastructure' with red color"
- "Show releases for project network-configs"
- "Show the BGP runbook wiki page in network-automation"
- "Create a wiki page for the router-01 incident postmortem"

---

## GAIT Audit Logging

All GitLab interactions MUST be logged to the GAIT audit trail via `gait_mcp` tools at skill invocation level.

### Logging Pattern

For each operation, log:
1. **Before**: Tool name, parameters (excluding tokens), and operator intent
2. **After**: Result summary (issue key created, pipeline status, etc.)

```
Tool: gait_log
Parameters: {
  "action": "gitlab.list_issues",
  "details": "Queried open issues in network-automation with label 'outage'",
  "result": "Returned 7 open issues"
}
```

For write operations, include the confirmation step:

```
Tool: gait_log
Parameters: {
  "action": "gitlab.create_issue",
  "details": "Created issue 'BGP peer flapping on router-01' in network-automation. Operator confirmed.",
  "result": "Issue #43 created at https://gitlab.com/network-team/network-automation/-/issues/43"
}
```

---

## Read-Only Mode

When `GITLAB_READ_ONLY_MODE=true`, the skill restricts to observation-only operations:

**Allowed tools** (read-only):
- `list_issues`, `get_issue`, `list_issue_comments`
- `list_merge_requests`, `get_merge_request`
- `list_pipelines`, `get_pipeline`, `get_pipeline_jobs`, `get_pipeline_job_log`
- `list_repository_tree`, `get_file_content`, `list_commits`, `get_commit`, `compare_branches`
- `list_projects`, `get_project`, `search_projects`
- `list_labels`, `list_milestones`, `list_releases`, `get_release`
- `list_wiki_pages`, `get_wiki_page`

**Blocked tools** (write operations — skipped with message):
- `create_issue`, `update_issue`, `add_issue_comment`
- `create_merge_request`, `update_merge_request`, `merge_merge_request`, `add_merge_request_comment`
- `create_pipeline`, `retry_pipeline`, `cancel_pipeline`
- `create_label`, `update_label`, `delete_label`
- `create_milestone`, `update_milestone`
- `create_release`
- `create_wiki_page`, `update_wiki_page`, `delete_wiki_page`

When a write tool is requested in read-only mode, respond: "GitLab read-only mode is enabled (GITLAB_READ_ONLY_MODE=true). Write operations are disabled. Contact your administrator to enable write access."

---

## Integration with Other Skills

- **servicenow-change-workflow** — Reference ServiceNow CR numbers in MR descriptions and issue comments for ITSM traceability
- **gait-session-tracking** — All GitLab operations are logged to the GAIT audit trail
- **github-ops** — Similar workflows for GitHub-hosted repositories; use gitlab-devops for GitLab and github-ops for GitHub
- **canvas-network-viz** — Visualize pipeline status and project metrics in the Canvas/A2UI dashboard

## Important Rules

- Never expose personal access tokens in logs, comments, or error messages
- Always verify project existence before write operations
- Reference ServiceNow CR numbers in MR descriptions when applicable
- Log all operations to GAIT for audit compliance
- In read-only mode, gracefully skip write operations with a clear message
- For self-hosted GitLab with nested groups, use full path (e.g., "org/team/sub-team/project")
