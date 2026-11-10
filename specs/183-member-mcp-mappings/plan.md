# Plan

- Audit each `PROFILE_MATCHERS` profile against `workspace/skills/`, the catalog's
  `skills[].servers` binding and each SKILL.md's server section and tool names
  (research.md).
- Rewrite `MCP_SERVERS` in `scripts/in2n-profiles.py` from the audit, grouped as
  `PROFILE_MATCHERS` is, and replace the misleading comment.
- Move the member-home server filter into `scoped_mcp_servers(servers, member, prof)` in
  `scripts/in2n-member-home.py`; `main()` calls it. No behaviour change.
- `tests/n2n/test_member_mcp_mappings_183.py`: registration, keys, corrected mappings,
  unchanged uncertain profiles, catalog drift with recorded exceptions, the scoping
  function on a minimal template, and `in2n-member-home.py` run end to end on a fixture
  Border config.
- `in2n-profiles.py`: `member_servers(profile, servers)` (the kept set, now also used by
  `scoped_mcp_servers`), `server_env_refs(entry)` (every `${NAME}` in an entry), and
  `env_slice_keys(profile, env_keys, servers=None)` adding the kept servers' names.
- `in2n-migrate.py` reads the Border template's `mcp.servers` (the selected runtime config,
  the same default `in2n-member-home.py` uses) and passes it to `env_slice_keys`.
- Tests: for every profile, every name its kept servers reference is in the slice; the slice
  holds only prefix keys and kept-server names and never comms secrets; a server not kept
  contributes nothing; `${NAME:-default}` and url/header references parse; migrate run end to
  end writes the catalyst-center member's `CATALYST_CENTER_*` and not Slack or GitLab tokens.
- Review round 1: `in2n-profiles.py` gains `DERIVED_DENY_PREFIXES`, `DERIVED_DENY_KEYS` (from
  comms.json) and `derived_ref_allowed`; `scoped_mcp_servers(..., home, member_env)` rewrites
  runtime paths, `copy_runtime_records` copies interpreter records, and `--member-env` selects
  the member's file; `in2n-migrate.py` warns on a missing or invalid Border config, creates the
  staged `.env` 0600 with `os.open`, and counts Convergence's written `.env`. Tests build the
  fixture Border with `install-mcp-config.py` itself.
- Review round 2: `_require_member_env` refuses before anything is written; `member_home_command`
  is printed by migrate and written as runbook step 2b; `scoped_mcp_servers(..., border_root)`
  sets `PYATS_VENV` for entries without a runtime root; `copy_runtime_records` opens records
  `O_NOFOLLOW` 0600 and refuses a symlinked target; the pyATS change root stays per member
  (research.md).
- Review round 3: `_require_member_env` refuses the Border's `.env` (samefile), `_refuse_border_home`
  refuses the Border's home, and `_member_path` makes `--member-env`/`--home` absolute without
  following symlinks.
