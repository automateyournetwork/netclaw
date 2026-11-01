# Plan

T001 Fetch the DefenseClaw installer for a pinned release, read it, and record what it
downloads/changes; install on the VM. Run `setup guardrail` (observe first) and
record the OpenClaw config diff; determine Ollama Cloud routing (registry / custom
provider) and whether NetClaw's guarded_model_route accepts the result.
T002 Switch the Risk to production; regenerate member/cold-start units with the
production mode; reach and record posture; fail-closed checks (proxy down, template
removed).
T003 Production qualification runs (S1/S2/S3 rubric), counting each provider turn,
with DefenseClaw audit evidence.
T004 Fix any NetClaw-side gaps found (docs, enable script pinning, controls) with tests
and independent review; commit, push, upstream PR stacked on #313.
