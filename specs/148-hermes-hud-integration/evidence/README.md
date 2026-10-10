# Spec 148 acceptance evidence — 2026-10-10

These are sanitized results; scopes and open cases are recorded in ../validation.md.
Live provider evidence ran on commit 9f26dfa. Earlier automated checks ran on its
working changes based on 28cbc67; the real-agent restart log was rerun successfully
on a45225a. The full 366 HUD tests and build were rerun after the readiness badge fix. Browser test refinements are recorded in later branch commits.
No credentials, owner configuration or raw private transcripts are included.

Mac return reports reference implementation `9b65b3b`. See ../closure.md for the
completed Mac live, browser, fault, upgrade and OpenClaw checks and the owner-approved
Mac/WSL qualification scope. Historical WSL commits above remain unchanged.

The deterministic provider is separate from the paid Anthropic result. A test's passing
status applies only to its assertions. Ubuntu 24.04 and native Windows OpenClaw remain
unverified outside the approved release scope; no historical test result is relabeled.
