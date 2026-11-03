# Plan

T001 Diagnose on the operator Risk: member transcripts, audit, environment, and the
markmap server reproduced directly through `scripts/mcp-call.py`.
T002 `gateway.py`: `SKILL_FAILURE_RULE`. `service.py` (member) and `invocation.py` (peer)
place it after "return only the result" and before the request text.
T003 Tests: new `tests/n2n/test_skill_failure_reporting_171.py` for the peer request;
`test_member_delegation.py` asserts the rule reaches the member's turn.
T004 Live: apply to the operator Risk with the member's missing paths and the fixed
markmap server; repeat the mind-map request through the Border. Release 1.18.4, PR.
