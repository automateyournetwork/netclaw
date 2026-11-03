# Research

- Operator Risk, member `byrns-risk/viz` (`ollama/gemma4:31b-cloud`), three `markmap-viz`
  tasks on 2026-11-01, transcripts read from a copy of the member's agent database:
  - 350311a9: 360 events, ended by writing a fixed SVG with `fs.writeFileSync` and
    returning its path.
  - 6f85a22d: 174 events, same outcome.
  - 4d275639: 934 events over 1 h 43 min, 300k input tokens, 268 `process poll` calls on a
    `find /home/ubuntu -name "*markmap*"` it had started, and `npm install -g jsdom`.
    It finally reported the error.
  - The mesh audit recorded each as `skill/markmap-viz → in_scope/success`.
- Cause of the tool failure: `markmap_generate`, `markmap_from_outline`,
  `markmap_render_file` and `markmap_customize` all return
  `Error: ResizeObserver is not defined`. markmap-view needs a browser: it measures
  rendered HTML, observes resizes and draws on animation frames. The server runs it in
  JSDOM. With `ResizeObserver` stubbed it next fails on `requestAnimationFrame`,
  asynchronously, crashing the process. The repository's own test report (`Agent
  Output/markmap_test_report.md`) records the same failure. Only `markmap_get_structure`
  works.
- Cause of the search: the member's environment had neither `MCP_CALL` nor
  `MARKMAP_MCP_SCRIPT`. `in2n-profiles.py` gives `viz` `MARKMAP_` and every member
  `MCP_CALL`. Both come from the Border's runtime `.env`, which `install-steps.sh` and
  `setup_generated.py` populate; that operator Border's older `.env` lacked them.
- Both request prompts are built in two places: `service.py` (member, embedded turn) and
  `invocation.py` `_exec_skill_gateway` (peer, gateway turn). Neither had any failure
  instruction. No test pins their wording.
