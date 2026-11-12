# Verification

No credentials are recorded here. Run on the development host (Ubuntu 24.04, Python 3.12,
Node 24) against `main` at 150fd24d.

## Checks

- `node scripts/build-catalog.mjs --check` and `python3 scripts/build-catalog.py --check`:
  PASS (242 skills) after regeneration. Only the three skills' `sha256` and the
  `scripts/lib/catalog.sh` catalog digest changed.
- `python3 scripts/check-catalog-metadata.py`: PASS (114 components, 242 skills).
- `python3 scripts/verify-catalog-coverage.py`: PASS.
- `python3 -m unittest discover -s tests -p test_setup_catalog.py`: OK.
- `python3 scripts/check-skill-limits.py`: ok, 242 shipped skills within the limits
  (descriptions unchanged, FR-004).
- `python3 scripts/verify-spec-artifacts.py`: PASS.
- `python3 scripts/prepare-release.py --check`: PASS (1.22.1); `python3 scripts/test-prepare-release.py`: OK.
- `python3 scripts/reconcile-mcp.py` with the release surfaces (catalog, dependencies, docs,
  meraki-ids, packages, portability): exit 0.
- `pytest tests/n2n/test_convergence_member_164.py tests/unit/test_jev_border.py
  tests/skill-limits tests/netconverter/test_installation.py`: 39 passed, 1 failed. The
  failure (`test_installed_interpreter_passes_real_owned_dependency_observation`,
  `setup_state.Conflict: unsafe_parent`) also fails on unchanged `main` on this host.
- `python3 scripts/reconcile-mcp.py`: exit 1 on this branch and on unchanged `main`, with
  the same failing surface (`startup`, servers not installed on this host).

## Live

The three rules, in slightly different wording, have been in an operator Border's
workspace copies of these skills since October 2026. That shows they load and coexist
with the rest of each skill, not that they change a decision; no incident is claimed.

## Not verified

An evaluation of agent decisions with and without the rules; macOS.
