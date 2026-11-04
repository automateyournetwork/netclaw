# Plan

T001 Diagnose on the operator Risk: scope against each member's own `openclaw skills
check`, and how the CLI chooses gateway or local evaluation.
T002 `member_inventory.py`: `check_skills()` runs the check locally in the member's
environment; `skill_report()` turns it into scoped, unloadable skills with a reason;
`project_unavailable()` keeps names only; `unavailable_skills()` reads a stored report.
T003 `service.py`: the member sends the report as a second `n2n/inventory` after
connecting, only on its current Border channel; the Border logs each skill.
`router.py` and `inventory.py` leave reported skills out of routing, the routable list and
the peer card. `docs/ADDING-AN-MCP.md`: how to read the report.
T004 Tests: `tests/n2n/test_member_skill_status_174.py`.
T005 Live: backport to the operator Risk, restart, read the reports, route an unloadable
and a loadable skill. Release 1.18.5, PR.
