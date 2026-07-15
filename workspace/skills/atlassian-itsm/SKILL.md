---
name: atlassian-itsm
description: IT Service Management workflows using Jira for issue tracking and Confluence for documentation
license: Apache-2.0
mcp_servers:
  - atlassian-mcp
tools_used:
  - jira_search
  - jira_get_issue
  - jira_get_issue_comments
  - jira_get_projects
  - jira_get_fields
  - jira_get_issue_types
  - jira_create_issue
  - jira_update_issue
  - jira_transition_issue
  - jira_get_transitions
  - jira_add_comment
  - jira_link_issues
  - jira_get_issue_links
  - jira_get_link_types
  - jira_batch_create_issues
  - confluence_search
  - confluence_get_page
  - confluence_get_spaces
  - confluence_get_space
  - confluence_get_page_comments
  - confluence_create_page
  - confluence_update_page
  - confluence_add_comment
metadata:
  openclaw:
    requires:
      bins: [uvx]
      env: [JIRA_URL, JIRA_USERNAME, JIRA_API_TOKEN]
---

# Atlassian ITSM Skill

IT Service Management workflows using Jira for incident/change tracking and Confluence for runbooks, postmortems, and documentation.

## Purpose

This skill provides ITSM-focused workflows for network operations teams using Atlassian tools:

- **Jira**: Incident tracking, change requests, problem management, and task coordination
- **Confluence**: Runbook documentation, postmortem reports, and knowledge base maintenance

All write operations require human-in-the-loop confirmation per Constitution XIV.

## Jira Read Workflows (User Story 1)

### Discovering Projects and Issue Types

Before creating or searching issues, discover the available projects and their issue types.

**Step-by-step workflow:**

1. **List accessible projects**: Call `jira_get_projects` to see all projects the authenticated user can access
2. **Get project details**: Call `jira_get_project(project_key)` for specific project configuration
3. **List issue types**: Call `jira_get_issue_types(project_key)` to see available issue types (Bug, Task, Story, etc.)
4. **List available fields**: Call `jira_get_fields` to see standard and custom fields

**Example prompts:**
- "Show me all Jira projects I have access to"
- "What issue types are available in project NET?"
- "List the custom fields in our Jira instance"

### Searching Issues with JQL

Search issues using Jira Query Language (JQL) for powerful filtering.

**Step-by-step workflow:**

1. **Construct JQL query**: Build query using project, status, assignee, label, and date filters
2. **Execute search**: Call `jira_search(jql_query, max_results)` with the JQL string
3. **Review results**: Parse the returned issue list with key, summary, status, assignee

**Common JQL patterns:**
```
# Open issues in project NET assigned to me
project = NET AND assignee = currentUser() AND status != Done

# Critical/blocker issues created this week
project = NET AND priority IN (Critical, Blocker) AND created >= -7d

# Issues with specific label
project = NET AND labels = "outage"

# Unassigned issues in backlog
project = NET AND assignee IS EMPTY AND status = "To Do"

# Issues updated in the last 24 hours
project = NET AND updated >= -1d
```

**Example prompts:**
- "Show me open issues in project NET assigned to me"
- "Search for critical issues created this week in project OPS"
- "Find all issues with label 'network-outage'"

### Retrieving Issue Details

Get full details for a specific issue by key.

**Step-by-step workflow:**

1. **Get issue details**: Call `jira_get_issue(issue_key)` with the issue key (e.g., "NET-1234")
2. **Review issue data**: Parse fields including summary, description, status, priority, assignee, reporter, labels, components, fix versions
3. **Get comments**: Call `jira_get_issue_comments(issue_key)` to see discussion history

**Example prompts:**
- "Get details for issue NET-1234"
- "Show me the comments on issue OPS-567"
- "What is the current status and priority of NET-1234?"

## Confluence Read Workflows (User Story 2)

### Discovering Spaces

Before searching or creating pages, discover available Confluence spaces.

**Step-by-step workflow:**

1. **List all spaces**: Call `confluence_get_spaces` to see accessible spaces
2. **Get space details**: Call `confluence_get_space(space_key)` for specific space info

**Example prompts:**
- "Show me all Confluence spaces I have access to"
- "Get details for the NET-DOCS space"

### Searching Pages with CQL

Search Confluence pages using Confluence Query Language (CQL).

**Step-by-step workflow:**

1. **Construct CQL query**: Build query using space, title, text, and date filters
2. **Execute search**: Call `confluence_search(cql_query, max_results)`
3. **Review results**: Parse returned page list with title, space, ID

**Common CQL patterns:**
```
# Pages in space NET-DOCS containing "BGP"
space = "NET-DOCS" AND text ~ "BGP"

# Pages with title containing "runbook"
title ~ "runbook"

# Recently modified pages in a space
space = "NET-DOCS" AND lastModified > now("-7d")
```

**Example prompts:**
- "Search Confluence for 'BGP runbook'"
- "Find pages in NET-DOCS space containing 'OSPF'"
- "Show me recently modified pages in the network documentation space"

### Retrieving Page Content

Get full page content by ID or title+space combination.

**Step-by-step workflow:**

1. **Get page content**: Call `confluence_get_page(page_id)` or `confluence_get_page(space_key, title)`
2. **Review content**: Parse body, version number, and metadata
3. **Get comments**: Call `confluence_get_page_comments(page_id)` to see page comments

**Example prompts:**
- "Show me the 'Router Maintenance Procedures' page in NET-DOCS"
- "Get the content of Confluence page ID 123456"
- "What comments are on the BGP runbook page?"

## Jira Write Workflows (User Story 3)

### Creating Issues

Create new Jira issues with human-in-the-loop confirmation.

**Step-by-step workflow:**

1. **Query available types**: Call `jira_get_issue_types(project_key)` to verify available issue types
2. **Get available fields**: Call `jira_get_fields` to understand required/optional fields
3. **Present to operator**: Display the proposed issue details and request confirmation (Constitution XIV)
4. **Create issue**: After confirmation, call `jira_create_issue` with project, issue_type, summary, description, priority, labels, assignee
5. **Confirm creation**: Return the created issue key to the operator

**Example prompts:**
- "Create a Jira issue in project NET titled 'Router-01 BGP peer down' with priority Critical"
- "Log an incident in project OPS for the core switch fan failure"

**IMPORTANT**: Always present the full issue details to the operator and wait for explicit confirmation before calling `jira_create_issue`.

### Updating Issues

Update existing issue fields with human-in-the-loop confirmation.

**Step-by-step workflow:**

1. **Get current state**: Call `jira_get_issue(issue_key)` to see current field values (read-before-write per Constitution II)
2. **Present changes**: Display current vs proposed field values to operator
3. **Update issue**: After confirmation, call `jira_update_issue(issue_key, fields)` with the changed fields
4. **Confirm update**: Verify the update succeeded

**Updateable fields:** summary, description, priority, labels, assignee, components, fix_versions

**Example prompts:**
- "Update NET-1234 priority to Critical"
- "Add label 'outage' to issue OPS-567"
- "Assign NET-1234 to john.smith"

### Transitioning Issues

Move issues through workflow states.

**Step-by-step workflow:**

1. **Get available transitions**: Call `jira_get_transitions(issue_key)` to see valid transitions from current state
2. **Present options**: Show operator the available transitions (e.g., "Start Progress", "Resolve", "Close")
3. **Execute transition**: After confirmation, call `jira_transition_issue(issue_key, transition_id)`
4. **Confirm transition**: Verify the new status

**Example prompts:**
- "Transition NET-1234 to In Progress"
- "Mark issue OPS-567 as Resolved"
- "What workflow transitions are available for NET-1234?"

### Adding Comments

Add comments to issues for investigation updates.

**Step-by-step workflow:**

1. **Draft comment**: Prepare comment text with investigation findings
2. **Present to operator**: Show the proposed comment for confirmation
3. **Add comment**: Call `jira_add_comment(issue_key, body)` after confirmation

**Example prompts:**
- "Add a comment to NET-1234: 'Root cause identified - BGP hold timer expired due to high CPU'"
- "Update OPS-567 with: 'Fan replacement scheduled for maintenance window'"

## Confluence Write Workflows (User Story 4)

### Creating Pages

Create new Confluence pages with human-in-the-loop confirmation.

**Step-by-step workflow:**

1. **Verify target space**: Call `confluence_get_space(space_key)` to confirm space exists
2. **Present to operator**: Display proposed page title, space, and body content
3. **Create page**: After confirmation, call `confluence_create_page(space_key, title, body)`
4. **Confirm creation**: Return the created page URL to the operator

**Example prompts:**
- "Create a Confluence page in NET-DOCS titled 'Incident Postmortem: Router-01 Outage'"
- "Create a new runbook page for BGP troubleshooting in the network documentation space"

**IMPORTANT**: Always present the full page content to the operator and wait for explicit confirmation before calling `confluence_create_page`.

### Updating Pages

Update existing page content (creates a new version).

**Step-by-step workflow:**

1. **Get current page**: Call `confluence_get_page(page_id)` to retrieve current content and version (read-before-write)
2. **Present changes**: Show operator the proposed changes (diff view if possible)
3. **Update page**: After confirmation, call `confluence_update_page(page_id, title, body, version)` - note: version must be incremented
4. **Confirm update**: Verify the new version was created

**Example prompts:**
- "Update the 'Router Maintenance Procedures' page with the new reboot procedure"
- "Add a section to the BGP runbook about peer flapping troubleshooting"

### Adding Page Comments

Add comments to Confluence pages.

**Step-by-step workflow:**

1. **Draft comment**: Prepare comment text
2. **Present to operator**: Show the proposed comment for confirmation
3. **Add comment**: Call `confluence_add_comment(page_id, body)` after confirmation

**Example prompts:**
- "Add a comment to the postmortem page noting the action items are complete"

### Deleting Pages

Delete Confluence pages (requires explicit confirmation).

**Step-by-step workflow:**

1. **Get page details**: Call `confluence_get_page(page_id)` to show what will be deleted
2. **Explicit warning**: Warn operator this is a destructive action
3. **Delete page**: Only after explicit confirmation, call `confluence_delete_page(page_id)`

**IMPORTANT**: Page deletion is destructive. Require explicit confirmation including the page title.

## Cross-Product and Bulk Workflows (User Story 5)

### Linking Jira Issues

Create relationships between issues.

**Step-by-step workflow:**

1. **Get link types**: Call `jira_get_link_types` to see available link types (Blocks, Relates, Clones, etc.)
2. **Present to operator**: Show the proposed link between issues
3. **Create link**: Call `jira_link_issues(inward_issue, outward_issue, link_type)` after confirmation
4. **View links**: Call `jira_get_issue_links(issue_key)` to verify the link was created

**Example prompts:**
- "Link NET-1234 as blocking OPS-567"
- "Show me all issues linked to NET-1234"
- "What link types are available in Jira?"

### Bulk Issue Creation

Create multiple issues in a single batch operation.

**Step-by-step workflow:**

1. **Prepare issue list**: Collect all issue details (project, type, summary, description, priority)
2. **Present full batch**: Show operator ALL proposed issues for review
3. **Create batch**: After confirmation of the entire batch, call `jira_batch_create_issues(issues)`
4. **Report results**: Return all created issue keys

**Example prompts:**
- "Create 5 Jira issues in project NET for these network upgrade tasks"
- "Bulk create issues for each router in the maintenance list"

**IMPORTANT**: The entire batch must be confirmed before any issues are created.

### Incident-to-Postmortem Workflow

Cross-product workflow: Jira incident with linked Confluence postmortem.

**Step-by-step workflow:**

1. **Create Jira incident**: Following the issue creation workflow
2. **Create Confluence postmortem**: Create postmortem page in appropriate space
3. **Link documents**: Add the Confluence page URL to the Jira issue via remote link or description update
4. **Cross-reference**: Add the Jira issue key to the Confluence page

**Example prompts:**
- "Create an incident in Jira for the router-01 outage and a postmortem page in Confluence"
- "Link Confluence postmortem page 123456 to Jira issue NET-1234"

## GAIT Audit Logging

All Atlassian interactions must be logged to the GAIT audit trail via gait_mcp tools at skill invocation level.

### Logging Pattern

For each operation, log:
1. **Tool name**: Which Atlassian MCP tool was called
2. **Parameters**: Key parameters (issue key, project, search query)
3. **Result summary**: Success/failure, created item keys, record counts

### Example Log Entries

```
[GAIT] jira_search - JQL: "project = NET AND status != Done" - Found 23 issues
[GAIT] jira_get_issue - Issue: NET-1234 - Retrieved successfully
[GAIT] jira_create_issue - Project: NET, Type: Bug, Summary: "Router-01 BGP down" - Created: NET-1235
[GAIT] jira_transition_issue - Issue: NET-1234 - Transitioned: Open -> In Progress
[GAIT] confluence_create_page - Space: NET-DOCS, Title: "Postmortem: Router Outage" - Created: page_id=456789
```

### Session Requirements

- Start every Atlassian session with `gait_branch` to create an audit branch
- Record every meaningful interaction with `gait_record_turn`
- End sessions with `gait_log` to display the full audit trail

## Error Handling

### Common Errors

| Error | Cause | Resolution |
|-------|-------|------------|
| Connection failure | Atlassian instance unreachable | Check JIRA_URL/CONFLUENCE_URL and network connectivity |
| Authentication failure | Invalid token | Regenerate API token or PAT |
| Not found | Issue/page/project doesn't exist | Verify the key/ID is correct |
| Permission denied | Token lacks permissions | Check user's project/space permissions |
| Rate limited | Too many requests | Wait and retry with backoff |
| Invalid transition | Transition not available | Check `jira_get_transitions` for valid options |
| Validation error | Missing required fields | Check required fields with `jira_get_fields` |

### Graceful Degradation

- If only Jira is configured: Confluence tools are unavailable
- If only Confluence is configured: Jira tools are unavailable
- Always check tool availability before attempting operations

## Safety Checklist

Before any write operation:

- [ ] Read current state first (Constitution II: Read-Before-Write)
- [ ] Present changes to operator for confirmation (Constitution XIV: Human-in-the-Loop)
- [ ] Log the operation to GAIT audit trail (Constitution III: GAIT Logging)
- [ ] Verify the operation succeeded before reporting completion

## Example Workflows

### Incident Response Workflow

1. Search for similar past incidents: `jira_search` with relevant JQL
2. Create new incident issue: `jira_create_issue` (with confirmation)
3. Search for relevant runbook: `confluence_search`
4. Transition to In Progress: `jira_transition_issue` (with confirmation)
5. Add investigation updates: `jira_add_comment` (with confirmation)
6. Resolve and document: Update issue and create postmortem page

### Knowledge Base Maintenance

1. Search for outdated pages: `confluence_search` with date filters
2. Review page content: `confluence_get_page`
3. Update with current information: `confluence_update_page` (with confirmation)
4. Create related Jira task if major update needed: `jira_create_issue`
