# Quickstart (administrator, no AI required)

```bash
# Enable (region mandatory; key read from stdin or hidden prompt, never argv)
printf '%s' "$KEY" | scripts/cisco-iq-enable.sh enable --region us --key-stdin
scripts/cisco-iq-enable.sh enable --region us --dry-run      # preview, redacted
scripts/cisco-iq-enable.sh status
scripts/cisco-iq-enable.sh diagnose            # offline checks
scripts/cisco-iq-enable.sh diagnose --live     # opt-in network check
printf '%s' "$NEWKEY" | scripts/cisco-iq-enable.sh rotate --key-stdin
scripts/cisco-iq-enable.sh update --region emea
scripts/cisco-iq-enable.sh policy-check --live  # or --tools-file tools.json
scripts/cisco-iq-enable.sh disable [--purge-credential]
```
Validate offline: `bash tests/cisco-iq/run-tests.sh` and `python3 scripts/reconcile-mcp.py`.
Key must be owned by a user principal; service-account keys expose no tools.
