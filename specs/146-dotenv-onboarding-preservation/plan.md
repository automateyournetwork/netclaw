# Implementation plan

Follow Spec Kit's checked-in workflow manually (agent slash commands unavailable): specify, clarify, research/plan, tasks, analyze, implement, verify. The existing branch was created before this spec; do not recreate it.

1. Add a standard-library dotenv importer with preview/apply, a template-derived allowlist, literal one-line parsing, placeholder diagnostics, conflict preservation and atomic 0600 output.
2. Call it from shared installer helpers before runtime onboarding and platform setup. Align selected state/config paths for onboarding, and propagate wizard failures.
3. Document first install, existing-install repair, precedence, supported syntax and the remaining purpose of onboarding.
4. Test actual helper/installer paths in temporary directories with stub CLIs, including failure, repeat runs, custom paths, hostile input and secret-free output. Repeat the actual installed OpenClaw loader experiment using imported dummy data.
5. Record verification and prepare a patch release proposal once local acceptance passes.

Constitution review: local installation fix, no new MCP, skill, tool or HUD capability; catalog, SOUL, TOOLS and device change control require no changes. No dependency added or runtime config rewritten. Network credentials remain local. Required surfaces are installer, template, README, tests and spec/release artifacts.
