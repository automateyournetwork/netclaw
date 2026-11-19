# Plan

- `workspace/skills/percepxion-oob/SKILL.md`: rewrite. Frontmatter description says when to use the
  skill and its nearest neighbours; body keeps the device identities, server routing, eight rules,
  the workflow index with W2 inline, reaching a console, and related skills. Version 1.1.0; drop
  `uv` from `requires.bins` (the installer uses a venv).
- `references/setup.md`: install, registration, both servers' variables, credential providers,
  CLI policy, roles and `organization_id`, capability split.
- `references/workflows.md`: W1 to W8 with corrected parameters.
- `references/source-of-truth.md`: the public integrations, fields read, W9 (NetBox and Nautobot),
  W10, gate reasons, Percepxion events, refreshing the source of truth.
- README, TOOLS.md, SOUL.md, `config/components/catalog.json`:
  tool count and short capability text (FR-008). Regenerate the catalog with
  `node scripts/build-catalog.mjs` and `python3 scripts/build-catalog.py`.
- Release 1.25.0 (minor: new skill workflows W9 and W10), via `scripts/prepare-release.py`.

## Key decisions

- References over a longer skill: the skill limit counts descriptions, but every load reads the body.
- The skill reads NetBox and Nautobot only. Writing stays with the Lantronix plugins and playbooks,
  which have their own permission models.
- No change to the installer's reviewed revisions in this spec; that touches spec 141's patch set and
  needs its own verification.
