---
name: aap-lint
description: "ansible-lint playbook and role validation — syntax checking, best practice enforcement, project-wide analysis, rule filtering. Use when validating Ansible playbooks, checking code quality, or enforcing automation best practices before deployment."
version: 1.0.0
license: Apache-2.0
tags: [ansible, lint, quality, validation, best-practices, playbook]
metadata:
  { "openclaw": { "requires": { "bins": ["python3", "ansible-lint"] } } }
---

# Ansible Lint Operations

## MCP Server

- **Repository**: [sibilleb/AAP-Enterprise-MCP-Server](https://github.com/sibilleb/AAP-Enterprise-MCP-Server)
- **Transport**: stdio (Python via `uv run ansible-lint.py`)
- **Install**: `git clone` + `uv sync` (or `pip install -e .`)
- **Requires**: `ansible-lint` installed

## Available Tools (9)

| Tool | What It Does |
|------|-------------|
| `lint_playbook` | Lint playbook content with configurable profiles and output formats |
| `lint_file` | Lint a specific Ansible file at a given path |
| `lint_role` | Comprehensive linting of an Ansible role directory |
| `list_rules` | Display available ansible-lint rules with optional tag filtering |
| `list_tags` | Show all tags for categorizing lint rules |
| `validate_syntax` | Quick syntax validation using syntax-specific rules |
| `check_best_practices` | Evaluate content against best practices with severity categorization |
| `analyze_project` | Comprehensive report on an entire Ansible project structure |
| `get_ansible_lint_version` | Return installed ansible-lint version |

## Key Concepts

| Concept | What It Means |
|---------|---------------|
| **Profile** | Lint strictness level (min, basic, moderate, safety, shared, production) |
| **Rule** | Individual lint check (e.g., `yaml[truthy]`, `no-changed-when`, `fqcn`) |
| **Tag** | Rule category for filtering (e.g., `command-shell`, `formatting`, `idiom`) |
| **FQCN** | Fully Qualified Collection Name — required in production profiles |

## Workflow: Pre-Deployment Playbook Validation

1. **Syntax check**: `validate_syntax` — catch YAML and Ansible syntax errors
2. **Best practices**: `check_best_practices` — evaluate against standards
3. **Full lint**: `lint_playbook` with production profile — comprehensive check
4. **Review rules**: `list_rules` — understand which rules triggered violations
5. **Report**: Pass/fail with specific violations and remediation guidance

## Workflow: Project-Wide Quality Audit

1. **Analyze project**: `analyze_project` — scan entire Ansible project structure
2. **Review findings**: Group violations by file, rule, and severity
3. **Check roles**: `lint_role` for each role directory
4. **Report**: Project quality scorecard with violation counts and trends

## Integration with Other Skills

| Skill | How They Work Together |
|-------|----------------------|
| `aap-automation` | Validate playbooks before running them through AAP job templates |
| `aap-eda` | Lint rulebook playbook actions before EDA activation |
| `github-ops` | CI/CD lint checks on PR playbook changes |
| `gait-session-tracking` | Audit trail for lint results and quality gate decisions |

## Important Rules

- **Lint before deploy** — always validate playbooks before AAP job execution
- **Profile selection** — use `production` profile for production deployments, `basic` for development
- **No credentials in playbooks** — lint catches hardcoded secrets; use AAP credential management instead
