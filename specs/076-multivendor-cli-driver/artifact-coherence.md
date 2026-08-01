# Artifact Coherence Checklist — spec 076 (R1)

Constitution Principle XI (NON-NEGOTIABLE). Run 2026-07-31.

Unlike spec 075, this feature genuinely adds capability, so every touchpoint applies.

```
[X] README.md updated (description, architecture, counts 202 skills / 150 integrations)
[X] scripts/lib/catalog.sh updated — "multivendor-cli" entry, Device Automation
[X] scripts/lib/install-steps.sh updated — component_install_multivendor_cli()
[X] scripts/verify-catalog-coverage.py passes — zero unexplained gaps
[X] ui/netclaw-visual/ updated — annotation entry with env vars, files, notes
[X] SOUL.md updated — capability counts
[X] workspace/skills/*/SKILL.md created — 3 skills (device-query, raw-cli, fleet-ops)
[X] .env.example updated — 8 MULTIVENDOR_* + 4 SERVICENOW_* names, no values
[X] TOOLS.md updated — tool inventory and routing rule
[X] config/openclaw.json updated — registered, repo-relative interpreter path
[X] mcp-servers/multivendor-cli-mcp/README.md created — tools, env, transport, install
[X] GAIT session log recorded
[X] Existing skills verified unbroken — 18 pyATS + 1 Junos, 0 files changed vs main
[ ] WordPress blog post drafted — draft written, AWAITING JOHN'S REVIEW before publishing
```

## Notes

**Install function uses `virtualenv`, not `python3 -m venv`.** Python 3.14 has no `ensurepip` on the
development host (`python3.14-venv` absent), so `venv` fails outright. Documented in the function with
a graceful skip if `virtualenv` is missing.

**Registration is repo-relative.** `mcp-servers/multivendor-cli-mcp/.venv/bin/python`, so
`normalize-mcp-cwd.py` supplies the correct absolute `cwd` per machine. Spec 075 found three
registrations hardcoded to a foreign home directory; `reconcile-mcp.py` now fails on that.

**Counts were caught twice by R0's gate** — 149→150 on registering the server, then 199→202 as skills
were added. Exactly the step `docs/ADDING-AN-MCP.md` warns is most often forgotten.

**Blog post is the one open item**, deliberately: Principle XVII requires John's review before
publishing, so it cannot be self-certified complete.
