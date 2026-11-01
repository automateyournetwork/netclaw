# Operations and exact-file submission

Official references: [MCP setup](https://netconverter.ai/mcp.html),
[Terminal repository](https://github.com/valeronlabs/netconverter_terminals),
[vendor matrix](https://netconverter.ai/docs/supported-vendors.html).
Initial research: Terminal 0.5.0, source ef28f5613a5f014dca7e8b2e38b8219cb461559f.
Actual account/client qualification on 2026-10-31 used official Terminal 0.6.0;
see [live evidence](../../../../specs/162-netconverterai/live-iterations.md).
The operator installs and accepts the Terminal license. NetClaw installs its own
guard dependencies only; it does not redistribute or patch the Terminal.

## Choose the route

- `hosted-readonly`: fixed official HTTPS MCP, explicit selected API key, strict
  requested view; discovery and allowed reads only.
- `local-terminal`: operator-selected executable/workspace, explicit key auth,
  fixed official API/MCP destinations, strict cap preserving a workspace's lower
  `none` policy. No automatic Clerk/keychain borrowing or provider/model calls.

The guard exposes eight tools. The upstream catalog is discovered and narrowed;
do not promise a fixed upstream tool count. Raw `submit_file`, arbitrary URLs,
mapping-triggered submissions and guided draft mutations are not exposed.
Guided preparation itself may upload data; it is not an approval-free alternative.

## Prepare and submit

1. Obtain an existing private file from an authorized collector or operator.
   Confirm device class and format. A CMDB row or lab topology is insufficient.
2. Discover account capabilities. Match an offered source/target/operation.
   Require explicit matching device class and source/target roles. The guard
   currently accepts UTF-8 text inputs only. XML advertised as text is eligible;
   binary/archive and non-text handoffs and metadata-incomplete legacy paths
   remain unavailable. Preserve unknown preview status as unknown.
   ASA and ArubaOS are source-only; SCM is not a hosted target; FMC output is an
   import file, not a controller deployment. FRR has no established native path.
   IOS-XE router↔Junos router is distinct from switch paths; IOS-XE switch↔Junos
   switch is not a direct supported path.
3. Call `netconverter_prepare_submission` with the local path and bounded options.
   It freezes bytes inside the selected workspace and returns the full review
   digest. It does not upload the source.
4. Present the native operator command using the selected private environment:

   ```text
   python3 scripts/netconverter-settings.py --env-file /absolute/selected/.env review REQUEST_ID
   python3 scripts/netconverter-settings.py --env-file /absolute/selected/.env approve-submission REQUEST_ID --digest FULL_REVIEW_DIGEST
   ```

   The operator types the digest in a native terminal. The agent does not execute
   that approval. The grant expires after five minutes by default, is bound to
   the exact request and is consumed before one outbound attempt.
5. Call `netconverter_submit_approved(request_id)`. Preserve the returned job
   reference. No blind retry after cancellation, timeout, lost receipt or unknown
   outcome. Read/reconcile actual service history before considering another
   independently approved request; a new ID must not conceal a retry.
6. Poll a known job with `netconverter_job_status` or `netconverter_wait_for_job`,
   at most 45 seconds per call and five minutes unattended. Resume later by job
   reference; never submit again to obtain progress.
7. Review evidence then call `netconverter_download`. Only verified artifact
   references feed downstream work. An existing output is never overwritten.

## Evidence exposure

`netconverter_read` accepts only discovered allowlisted reads and schema-valid
arguments. Raw target, unparsed source and non-knowledge fetches are refused.
Upstream report text stays in a private local artifact; the model receives known
verdicts/counts, exposure/completeness markers and artifact metadata. Do not open
private source/candidate files in model context as a workaround. Explicitly
authorized human local review remains possible.

Changing source bytes, executable, workspace, key, account reference, capabilities
or options invalidates the existing review. An account label is operator metadata,
not proof of a stable upstream tenant identity. No automatic account/route switch.
