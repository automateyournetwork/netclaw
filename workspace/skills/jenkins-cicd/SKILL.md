---
name: jenkins-cicd
description: Jenkins CI/CD pipeline management — monitor builds, trigger pipelines, analyze logs, and track SCM changes for network automation workflows.
version: "1.0"
license: Apache-2.0
tags:
  - cicd
  - jenkins
  - pipelines
  - builds
  - devops
metadata:
  mcp_servers:
    - jenkins-mcp
  tools_used:
    - getJob
    - getJobs
    - triggerBuild
    - getQueueItem
    - getBuild
    - updateBuild
    - getBuildLog
    - searchBuildLog
    - getJobScm
    - getBuildScm
    - getBuildChangeSets
    - findJobsWithScmUrl
    - whoAmI
    - getStatus
    - getPipelineRuns
    - getPipelineRunLog
  transport: remote-http
  auth: basic
---

# Jenkins CI/CD Skill

## Purpose

Manage Jenkins CI/CD pipelines for network automation workflows. This skill provides operational workflows for monitoring job and build status, triggering builds with parameters, analyzing build logs for troubleshooting, and tracking SCM changes across Jenkins projects.

The Jenkins MCP server is an official Jenkins plugin running natively inside Jenkins via Streamable HTTP transport — netclaw connects to it as a remote HTTP client.

## Golden Rule

**Never trigger a build or modify build metadata without explicit operator confirmation.** All write operations (`triggerBuild`, `updateBuild`) require human-in-the-loop approval per Constitution XIV. Always read current state before proposing any write action (Constitution II — Read-Before-Write).

---

## Workflow 1: Pipeline and Build Monitoring (US1 — MVP)

Monitor Jenkins job status, build results, queue state, and pipeline run history.

### Steps

1. **List all jobs** — Use `getJobs` with optional pagination (`offset`, `limit`) and regex name filter to discover available jobs.
   ```
   Tool: getJobs
   Parameters: { "nameFilter": "deploy-.*", "offset": 0, "limit": 25 }
   ```

2. **Get job details** — Use `getJob` with the full job name (supports folder paths like `folder1/folder2/job-name`) to retrieve job configuration, last build number, and health status.
   ```
   Tool: getJob
   Parameters: { "fullName": "network-automation/deploy-network-config" }
   ```

3. **Get build details** — Use `getBuild` with job name and build number to retrieve result, duration, timestamp, parameters, and causes.
   ```
   Tool: getBuild
   Parameters: { "jobFullName": "deploy-network-config", "buildNumber": 42 }
   ```

4. **Check queue status** — Use `getQueueItem` to inspect queued build requests — waiting reason, position, estimated start time.
   ```
   Tool: getQueueItem
   Parameters: { "queueId": 1234 }
   ```

5. **View pipeline run history** — Use `getPipelineRuns` to list pipeline execution history with status, duration, and branch info.
   ```
   Tool: getPipelineRuns
   Parameters: { "jobFullName": "deploy-network-config" }
   ```

### Example Prompts

- "Show me all Jenkins jobs"
- "What is the status of the last build for deploy-network-config?"
- "List all failed builds for job network-validation"
- "Are there any builds waiting in the queue?"
- "Show pipeline run history for deploy-network-config"

---

## Workflow 2: Build Triggering and Tracking (US2)

Trigger new builds with parameters, track queue-to-build progression, and update build metadata. All write operations require operator confirmation.

### Steps

1. **Verify job exists and check parameters** — Use `getJob` to confirm the job exists and inspect its parameter definitions before triggering (read-before-write, Constitution II).
   ```
   Tool: getJob
   Parameters: { "fullName": "deploy-network-config" }
   → Returns parameter definitions: BRANCH (String), DRY_RUN (Boolean), ENVIRONMENT (Choice)
   ```

2. **Present parameters and confirm with operator** — Display the job's parameter definitions and proposed values. Wait for explicit operator approval before proceeding (Constitution XIV — Human-in-the-Loop).
   ```
   Confirmation prompt:
   "Ready to trigger build for 'deploy-network-config' with parameters:
    - BRANCH: main (String)
    - DRY_RUN: true (Boolean)
    - ENVIRONMENT: staging (Choice: [dev, staging, prod])
   Proceed? [yes/no]"
   ```

3. **Trigger the build** — Use `triggerBuild` with the confirmed parameters. Supported parameter types: String, Boolean, Choice, Text, Password, Run.
   ```
   Tool: triggerBuild
   Parameters: {
     "jobFullName": "deploy-network-config",
     "parameters": [
       { "name": "BRANCH", "value": "main" },
       { "name": "DRY_RUN", "value": "true" },
       { "name": "ENVIRONMENT", "value": "staging" }
     ]
   }
   → Returns queue item ID
   ```

4. **Track queue progression** — Use `getQueueItem` to monitor until the build starts, then switch to `getBuild`.
   ```
   Tool: getQueueItem
   Parameters: { "queueId": <returned-queue-id> }
   → When build starts, returns build number
   ```

5. **Monitor build until completion** — Use `getBuild` to poll build status until result is available.
   ```
   Tool: getBuild
   Parameters: { "jobFullName": "deploy-network-config", "buildNumber": <build-number> }
   → Result: SUCCESS | FAILURE | UNSTABLE | ABORTED | NOT_BUILT
   ```

6. **Update build metadata (optional)** — Use `updateBuild` to set a descriptive display name or mark the build as keep-forever. Requires confirmation.
   ```
   Tool: updateBuild
   Parameters: {
     "jobFullName": "deploy-network-config",
     "buildNumber": <build-number>,
     "displayName": "Production Deploy - v2.4.1",
     "keepLog": true
   }
   ```

### Example Prompts

- "Trigger a build for deploy-network-config with BRANCH=main"
- "Start job network-validation with DRY_RUN=true and ENVIRONMENT=staging"
- "Mark build #42 of deploy-network-config as keep-forever"
- "Track queue item 1234 until the build completes"

---

## Workflow 3: Build Log Analysis (US3)

Retrieve and search build logs for troubleshooting failed builds, identifying errors, and diagnosing pipeline issues.

### Steps

1. **Retrieve build log** — Use `getBuildLog` with job name and build number. For large logs, use the `start` offset parameter for pagination.
   ```
   Tool: getBuildLog
   Parameters: { "jobFullName": "deploy-network-config", "buildNumber": 42 }
   → Returns console output text
   ```

2. **Paginate large logs** — If the log is truncated, use the `start` offset to retrieve subsequent sections.
   ```
   Tool: getBuildLog
   Parameters: { "jobFullName": "deploy-network-config", "buildNumber": 42, "start": 50000 }
   → Returns output starting from byte offset 50000
   ```

3. **Search logs by pattern** — Use `searchBuildLog` with a regex pattern to find specific lines (errors, warnings, timeouts).
   ```
   Tool: searchBuildLog
   Parameters: {
     "jobFullName": "deploy-network-config",
     "buildNumber": 42,
     "pattern": "ERROR|FATAL|Exception"
   }
   → Returns matching log lines
   ```

4. **Retrieve pipeline-specific logs** — Use `getPipelineRunLog` for pipeline jobs that produce structured run logs.
   ```
   Tool: getPipelineRunLog
   Parameters: { "jobFullName": "deploy-network-config", "runId": "42" }
   ```

### Example Prompts

- "Show me the build log for deploy-network-config build #42"
- "Show the last 100 lines of the build log for network-validation #15"
- "Search the build log for 'ERROR' in deploy-network-config build #42"
- "Find timeout messages in the latest build of network-validation"
- "Show the pipeline log for deploy-network-config run #42"

### Handling Large Logs

Build logs can be very large (hundreds of MB for verbose builds). Guidelines:
- Start with `searchBuildLog` to find relevant sections before retrieving the full log
- Use `start` offset pagination to retrieve specific sections
- For troubleshooting, search for `ERROR`, `FATAL`, `Exception`, `FAILURE`, or `timeout` first

---

## Workflow 4: SCM Change Tracking (US4)

Track source code changes associated with Jenkins jobs and builds — correlate builds with commits, find jobs by repository, and review change history.

### Steps

1. **Get job SCM configuration** — Use `getJobScm` to view the repository URL, branch spec, and polling configuration for a job.
   ```
   Tool: getJobScm
   Parameters: { "jobFullName": "deploy-network-config" }
   → Returns: repository URL, branches, credential ID, polling config
   ```

2. **Get build SCM details** — Use `getBuildScm` to see the exact revision (commit hash) and branch checked out for a specific build.
   ```
   Tool: getBuildScm
   Parameters: { "jobFullName": "deploy-network-config", "buildNumber": 42 }
   → Returns: revision hash, branch name at build time
   ```

3. **List change sets (commits)** — Use `getBuildChangeSets` to see all commits included in a build — author, message, timestamp, and affected files.
   ```
   Tool: getBuildChangeSets
   Parameters: { "jobFullName": "deploy-network-config", "buildNumber": 42 }
   → Returns: list of change sets with commit details
   ```

4. **Find jobs by repository** — Use `findJobsWithScmUrl` to discover all Jenkins jobs configured to build from a specific repository.
   ```
   Tool: findJobsWithScmUrl
   Parameters: { "scmUrl": "https://github.com/org/network-configs" }
   → Returns: list of jobs using this repository
   ```

### Example Prompts

- "What repository does deploy-network-config use?"
- "Show me the commits in build #42 of deploy-network-config"
- "Which commit triggered build #42?"
- "Find all Jenkins jobs that use the network-configs repository"
- "What files changed in the latest build of deploy-network-config?"

---

## Workflow 5: Health Check and Setup Verification (US5)

Verify Jenkins connectivity, authentication, and instance health. Recommended as a pre-flight check before first use and as a diagnostic tool when other operations fail.

### Steps

1. **Verify authentication** — Use `whoAmI` to confirm the connection works and inspect the authenticated user's identity and permissions.
   ```
   Tool: whoAmI
   Parameters: {}
   → Returns: user name, authorities/permissions list
   ```

2. **Check instance health** — Use `getStatus` to verify Jenkins is healthy and operational.
   ```
   Tool: getStatus
   Parameters: {}
   → Returns: mode (NORMAL/SHUTDOWN), version, quietingDown status
   ```

### When to Use

- **First-time setup**: Run both `whoAmI` and `getStatus` to validate the connection
- **Authentication failures**: Run `whoAmI` to diagnose credential issues
- **Unexpected errors**: Run `getStatus` to check if Jenkins is shutting down or in maintenance mode
- **Permission problems**: Run `whoAmI` to verify the user has required authorities

### Example Prompts

- "Check my Jenkins connection"
- "Who am I on Jenkins?"
- "Is Jenkins healthy?"
- "Verify Jenkins is running and I have access"

---

## GAIT Audit Logging

All Jenkins interactions are logged to the GAIT audit trail via `gait_mcp` tools at the skill invocation level (per Constitution IV — GAIT Audit Trail).

### Logging Pattern

For each Jenkins operation:

1. **Before invocation**: Log the tool name and parameters being sent
   ```
   gait_mcp.log_action({
     action: "jenkins_tool_call",
     tool: "getJobs",
     parameters: { "nameFilter": "deploy-.*" },
     status: "initiated"
   })
   ```

2. **After invocation**: Log the result summary
   ```
   gait_mcp.log_action({
     action: "jenkins_tool_call",
     tool: "getJobs",
     result_summary: "Returned 12 jobs matching filter",
     status: "completed"
   })
   ```

3. **For write operations**: Log the confirmation step
   ```
   gait_mcp.log_action({
     action: "jenkins_write_confirmation",
     tool: "triggerBuild",
     parameters: { "jobFullName": "deploy-network-config", "parameters": [...] },
     operator_confirmed: true,
     status: "approved"
   })
   ```

### What Gets Logged

- Tool name and parameters for every invocation
- Result summary (success/failure, record count, key identifiers)
- Operator confirmation for write operations
- Error details when operations fail

---

## Integration with Other Skills

- **suzieq-observability**: After a network deployment build completes, use SuzieQ to validate network state post-change
- **aci-change-deploy**: Coordinate ACI changes with Jenkins pipeline execution — trigger build after change approval
- **gitlab-devops**: Correlate GitLab merge requests with Jenkins builds via SCM change tracking
- **canvas-a2ui**: Visualize build status trends and pipeline health in network dashboards
- **gait_mcp**: All Jenkins operations are audit-logged for compliance and traceability

---

## Important Rules

1. **Read-before-write**: Always use `getJob` to verify a job exists and inspect its parameters before `triggerBuild` or `updateBuild`
2. **Human-in-the-loop**: All write operations require explicit operator confirmation — never auto-trigger builds
3. **Folder-aware job names**: Jenkins jobs in folders use path notation (e.g., `folder1/folder2/job-name`) — always use the full name
4. **Parameterized builds**: Check parameter definitions via `getJob` before triggering — pass correct types (String, Boolean, Choice, Text, Password, Run)
5. **Large log handling**: Use `searchBuildLog` before full log retrieval to avoid overwhelming context with large console output
6. **GAIT logging**: Every Jenkins tool invocation must be logged to the audit trail
7. **Credential safety**: Never log or display raw API tokens — credentials are managed via environment variables (Constitution XIII)
8. **Remote server**: This MCP server is a remote HTTP service — connectivity depends on network access to the Jenkins instance
