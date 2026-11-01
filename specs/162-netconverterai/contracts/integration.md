# NetConverter integration contract

## Configuration

One component `netconverter`, one stdio server `netconverter-mcp`. Modes: `hosted-readonly` and `local-terminal`; reject unknown values. Fixed production destinations: `https://api.netconverter.ai/` and `https://api.netconverter.ai/mcp/v1/`. Tests inject controlled transports internally, never expose a general insecure endpoint override.

Settings: public mode; private selected workspace, executable and account reference; secret selected API key; generated private data directory and installation binding. No secret literal in plans/editor state. The managed Terminal profile explicitly selects key authentication, never automatic Clerk/keychain fallback. Operator licensing is a prerequisite, not an installer action.

## MCP tools

| Tool | Inputs | Effect and output |
|---|---|---|
| `netconverter_status` | bounded discovery request | Local readiness and optional upstream metadata/capability evidence; no file transfer |
| `netconverter_prepare_submission` | local path, source vendor, optional target, job type, bounded options | Freeze local bytes, validate direction/options, return request ID and exact review metadata; no hosted transfer |
| `netconverter_submit_approved` | request ID only | Verify stored request/grant and binding; one atomic submission attempt; job identity or durable unknown state |
| `netconverter_request_status` | request ID | Local safe metadata, approval/attempt status and known job reference |
| `netconverter_read` | discovered allowed read name and bounded schema-validated arguments | Read-only allowlist intersected with actual discovery and strict exposure rules; no generic mutation proxy |
| `netconverter_job_status` | bound job reference | Provider status, actual evidence completeness and safe progress |
| `netconverter_wait_for_job` | bound job reference, bounded timeout | One finite polling sequence; no submit retry |
| `netconverter_download` | bound job reference | Download into run-owned private output, independently verify paths/hashes/lengths, return artifact references |

Existing jobs must be explicitly associated with the selected connection; never reuse a job selected through another account by implication. Discovery reports the actual read schema set; no fixed upstream total is promised.

Forbidden initial exposures: `submit_file` as a raw pass-through, `apply_mapping_answers`, guided mutations, raw target config retrieval, unparsed source sections, arbitrary fetch URLs/files, arbitrary shell commands and grant creation. Unsupported advanced workflows explain their status and preserve the selected route.

## Operator CLI

`netconverter-settings.py` provides status, review and approve-submission for an existing request. Native review displays exact full digest, source path/size, destination/account reference, operation/direction/options and expiry. A stale digest cannot approve a changed request. Approval is single-use and requires an actual operator action; the skill instructs the agent to present the review rather than execute approval itself.

## Transport and privacy

Use official SDK clients with finite read/connection bounds, explicit completion semantics and mutation retry disabled, including automatic input-required retry rounds. Ignore tool-result instructions. Capture upstream diagnostics privately and return safe error categories without configuration or credential data.

Snapshots live inside the configured workspace and inherit its restrictive privacy cap. The child environment/argv fixes authentication and destinations and disables model/provider/update side effects. Do not override an existing `none` policy. Hosted read mode sends strict-view headers and does not follow redirects or environment proxies.

## Error outcomes

Distinguish invalid mode/path/schema, missing executable/license/account, capability unavailable, approval required/expired/invalidated/consumed, declined, upstream refusal, unknown submission outcome, incomplete evidence, integrity failure and unsupported workflow. Unknown is never reported as a confirmed failure with permission to resubmit.

## Required contract tests

Tamper every bound request field; race two submissions; crash/restart after acceptance; reject unexpected/mutation schemas; prove key/endpoint isolation and workspace privacy preservation; reject malicious output paths/corrupt downloads; verify no source/key canary reaches result/stdout/public logs; prove setup never submits or accepts a license.
