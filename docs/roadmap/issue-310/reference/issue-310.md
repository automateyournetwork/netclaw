# Feature Request: Enterprise Multi-User Support for NetClaw Visual UI – Entra ID SSO, Isolated User Contexts, Shared Agent & Team Knowledge

Source: https://github.com/automateyournetwork/netclaw/issues/310

Retrieved: 2026-11-01T17:31:47.744106+00:00; state: OPEN

I would like to propose native multi-user support for the NetClaw Visual UI, specifically designed for enterprise network operations teams.

The goal is to allow multiple network engineers to access a single, centrally hosted NetClaw instance, authenticate using their existing Microsoft Entra ID accounts, and interact with a shared NetClaw/OpenClaw agent while maintaining isolated personal conversations, sessions, and memories.

At the same time, the team should benefit from a shared, persistent network knowledge base that allows NetClaw to reuse previously discovered information, troubleshooting experience, and validated solutions.

Ideally, this functionality would be integrated directly into NetClaw Visual rather than requiring a separate installation or agent for every engineer.

1. Problem / Current Limitations

NetClaw already provides a powerful interface for network automation, troubleshooting, and AI-assisted operations.

However, using it as a centralized platform for an entire enterprise network team introduces additional requirements:

* Individual user authentication and identity management.
* Separation of personal conversations and contextual information.
* Persistent, user-specific AI memory.
* Shared technical knowledge across the network team.
* Role-based permissions for potentially sensitive network operations.
* Traceability of actions performed by individual users.

Without these capabilities, operating a single NetClaw instance as a shared enterprise service becomes difficult, particularly when multiple engineers work on different incidents simultaneously.

2. Proposed Architecture

The preferred architecture is:

Microsoft Entra ID → NetClaw Visual UI → User-Specific Context → Shared OpenClaw Agent → Network Integrations

All authenticated users would interact with the same underlying agent, but the backend would maintain separate session and memory contexts for each user.

A dedicated OpenClaw agent or gateway per user should not be required.

The architecture should distinguish between:

1. User context: Private conversations, personal memory, preferences, and active troubleshooting sessions.
2. Shared team context: Network topology, documentation, validated troubleshooting findings, known issues, and reusable solutions.
3. Operational context: Current information retrieved from Cisco devices, monitoring systems, APIs, and other network integrations.

3. Microsoft Entra ID Authentication

Native support for Microsoft Entra ID authentication through OpenID Connect (OIDC) would be highly desirable.

Suggested capabilities:

* Single Sign-On using existing enterprise identities.
* No separate local user accounts required.
* Automatic identification of the authenticated user.
* Optional restriction to specific Entra ID groups.
* Support for group-based authorization.
* Secure session expiration, logout, and token handling.
* Compatibility with reverse proxies and standard enterprise deployment architectures.

An organization should be able to manage user access centrally through Microsoft Entra ID.

Ideally, the authentication architecture could remain extensible to other OIDC-compatible identity providers in the future.

4. Isolated User Conversations and Sessions

Each user should have an independent chat environment.

Requirements:

* Personal chat history.
* Multiple conversations per user.
* Persistent conversation history across browser sessions and devices.
* Ability to resume previous troubleshooting sessions.
* Server-side ownership and access validation.
* Isolation between simultaneous users.
* Support for the standard Chat and Canvas interfaces.

For example, Engineer A investigating a Cisco ISE authentication problem should not interfere with Engineer B investigating a Cisco ASA firewall issue.

Both engineers should be able to work concurrently using the same underlying agent.

The application must not rely solely on browser-local storage or client-supplied session identifiers for user isolation.

5. Personal AI Memory

Each user should have an individual persistent memory context.

This could include:

* Previously investigated incidents.
* Personal troubleshooting notes.
* Preferred diagnostic workflows.
* Relevant conversation history.
* Saved technical findings.
* Ongoing investigations.

The agent should automatically retrieve relevant personal context when useful, without requiring users to repeat information in every conversation.

However, personal memory must remain private and must not automatically become accessible to other users.

Users should also be able to inspect, correct, and delete their own stored memories.

6. Shared Network Knowledge Base

One of the most valuable capabilities would be a persistent knowledge base shared across the entire network team.

Potential content:

* Network topology and infrastructure relationships.
* Cisco device inventories and platform information.
* Known configuration dependencies.
* Common troubleshooting procedures.
* Previously identified root causes.
* Validated solutions and workarounds.
* Network standards and operational guidelines.
* Historical incidents and lessons learned.

Example

Engineer A investigates an intermittent Cisco ISE authentication failure.

After analyzing switch configurations, RADIUS responses, and authorization policies, the root cause is identified and resolved.

The confirmed findings can be published to the shared knowledge base.

Several weeks later, Engineer B encounters a similar issue.

NetClaw should be able to retrieve the previous finding, explain its relevance, and suggest appropriate verification steps.

The agent should not simply assume that the previous solution is correct. It should validate the current environment before recommending or executing changes.

Knowledge Management Requirements

Ideally, the shared knowledge base would support:

* Automatic identification of potentially reusable findings.
* Explicit user confirmation before publishing personal findings as team knowledge.
* Source references and timestamps.
* Information about the affected devices and technologies.
* Confidence or validation status.
* Updating or superseding outdated information.
* Search and semantic retrieval.
* Deduplication of similar findings.
* Review and approval workflows for shared knowledge.

The goal is to make NetClaw progressively more useful through accumulated operational experience, without allowing unverified AI-generated assumptions to become authoritative knowledge.

7. Role-Based Access Control (RBAC)

Network operations often involve sensitive systems and potentially disruptive actions.

Permissions should ideally be derived from Microsoft Entra ID groups.

Example roles:

Role	Permissions
Network Viewer	Read-only diagnostics and knowledge retrieval
Network Engineer	Diagnostics, configuration analysis, and change preparation
Network Administrator	Authorized configuration changes and administrative operations

Permissions should apply to actual backend operations, including MCP tools, SSH sessions, API integrations, and automation workflows.

Authorization must be enforced server-side rather than relying on AI instructions or UI restrictions.

The system should also support approval requirements for high-impact operations.

8. Shared Agent with User-Aware Execution

A key design objective is to reuse one centrally managed OpenClaw agent.

The agent should receive the authenticated user’s identity and authorized context for each request.

It should then:

* Load only that user’s personal conversation and memory context.
* Retrieve relevant shared knowledge.
* Enforce the user’s permissions when invoking tools.
* Keep concurrent conversations isolated.
* Prevent information leakage between users.
* Preserve the identity of the initiating user throughout tool execution.

Special consideration should be given to agent memory, session identifiers, temporary files, terminal sessions, credentials, and background tasks.

A shared agent must not accidentally expose information from another user’s previous interaction.

9. Audit Logging and Accountability

For enterprise network environments, it should be possible to determine:

* Which user initiated a request.
* Which network devices were accessed.
* Which tools or integrations were invoked.
* Which commands or configuration changes were executed.
* Whether a change was approved.
* Whether the operation succeeded or failed.

Sensitive information, including passwords, tokens, and secrets, should be excluded or appropriately protected.

Audit records should be accessible to authorized administrators.

10. User Experience in NetClaw Visual

The existing NetClaw Visual experience should ideally be preserved.

Suggested UI enhancements:

* Sign in with Microsoft Entra ID.
* Display the currently authenticated user.
* Personal conversation history.
* Resume previous sessions.
* Personal memory management.
* Searchable shared network knowledge.
* Option to submit validated findings to team knowledge.
* Clear distinction between personal and shared information.
* Role-aware visibility of available network operations.
* Consistent identity and session handling across Chat, Canvas, and terminal workflows.

The goal is not to replace NetClaw’s existing network-focused interface, but to make it suitable for collaborative enterprise use.

11. Security Considerations

This feature should explicitly address:

* Server-side user and session isolation.
* Authorization for every protected API endpoint.
* Protection against cross-user memory retrieval.
* Separation of user-specific temporary files and terminal sessions.
* Secure credential and token management.
* WebSocket authentication and authorization.
* Prevention of unauthorized MCP tool execution.
* Protection against indirect access through agent tools.
* Appropriate data retention and deletion policies.
* Concurrent-user isolation testing.

Authentication alone should not be considered sufficient for multi-user security.

12. Suggested Implementation Phases

To keep the scope manageable, this could be introduced incrementally.

Phase 1 – Multi-User Foundation

* Microsoft Entra ID / OIDC authentication.
* Server-side user identity.
* Isolated and persistent chat sessions.
* Shared agent integration.
* Basic authorization and security tests.

Phase 2 – Persistent Knowledge and Memory

* Personal user memory.
* Shared network knowledge base.
* Knowledge publishing and retrieval.
* Memory management and retention controls.

Phase 3 – Enterprise Authorization

* Entra ID group-based RBAC.
* Permission-aware MCP and network tool execution.
* Audit logging.
* Approval workflows for sensitive operations.

13. Expected Benefits

This would allow NetClaw to evolve from an individually operated AI network assistant into a collaborative platform for enterprise network teams.

Expected benefits include:

* Centralized deployment and maintenance.
* Reuse of existing enterprise identities.
* Independent troubleshooting by multiple engineers.
* Reduced duplication of investigations.
* Preservation of operational knowledge.
* Faster diagnosis of recurring network problems.
* Consistent troubleshooting practices.
* Better access control and accountability.
* Improved long-term usefulness of the AI agent.

14. Related Existing Work

Some existing pull requests may provide useful foundations:

* #273 – Default Chat, Canvas, and native OpenClaw UI choices.
* #275 – Network terminal and Canvas workflows.

It would be interesting to determine whether existing OpenClaw session management and identity-related capabilities could be reused rather than implementing an entirely separate multi-user framework.

Questions for the Maintainers

1. Is native enterprise multi-user support already planned for NetClaw Visual?
2. Could a single OpenClaw agent safely support multiple isolated user contexts?
3. Would Microsoft Entra ID / generic OIDC integration fit the project’s architecture?
4. Could existing OpenClaw session and memory functionality be extended for this purpose?
5. Would the maintainers be open to a phased implementation of these capabilities?

I believe this would be a valuable addition for organizations looking to use NetClaw as a centralized AI-powered network operations platform rather than as an individual engineering tool.

## Comment — byrn-baker

2026-10-31T18:13:54Z — https://github.com/automateyournetwork/netclaw/issues/310#issuecomment-6547276827

I recommend one central Border service with isolated user execution and permission-controlled delegation to remote NetClaws.

<img width="1558" height="990" alt="Image" src="https://github.com/user-attachments/assets/79ce5420-98ca-4346-a127-e633229fc516" />

The key architectural decisions are:
- Share the service and agent configuration. Keep each user’s runtime state, conversations, files and memory isolated. OpenClaw explicitly says shared-agent session ownership does not provide security isolation. [Upstream trust model](https://docs.openclaw.ai/gateway/security/trust-model)
- Classify remote claws by ownership. Your organization’s distributed specialists use iN2N; independently administered NetClaws use eN2N.
- Carry user authority through every delegation. Each destination must enforce the user’s permitted operations and devices alongside existing peer grants. Border access must never imply administrator access.
- Keep integration credentials at the executing member. Give the Border scoped delegation authority.
- Publish shared knowledge explicitly, with review, provenance and freshness checks.
- Include authorization and audit in phase one, alongside SSO and isolation.

This fits NetClaw’s existing Border/member foundation, but requires an enterprise authorization layer and stronger runtime boundaries.
A SSO proxy alone won’t satisfy this issue.

## Comment — automateyournetwork

2026-10-31T20:20:10Z — https://github.com/automateyournetwork/netclaw/issues/310#issuecomment-6548647168

Thank you for all of this great stuff and using your meat and AI tokens - it's really a great road map - what I will do is leave this issue open; take your issue; break it down into smaller specs; and keep you posted. Might include google and other forms of auth if we are adding entra would love a BYO approach here. But this is all sound. And a good roadmap.

I am just finishing another spec right now but will make this my next set of spects. Thanks. Please do join us in the VIbeOps Forum we are all there to discuss the other maintianers myself and a bunch of users. #netclaw_users channel
