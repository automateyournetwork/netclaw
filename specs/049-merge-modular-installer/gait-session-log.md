
## 2026-10-09 — macOS installer keyboard investigation

Local branch: `codex/fix-macos-installer-arrows`, base `95bb17e`. GAIT MCP/CLI
is unavailable in this session; this append-only file records the work rather
than claiming a GAIT tool run. No network devices or services were operated.

Request: investigate Greg's report that arrows skip the runtime prompt and
default to OpenClaw. Reproduced Bash 3.2's rejected fractional read timeout,
identified swallowed runtime cancellation, updated the existing modular TUI
spec before implementation, patched both paths, and added PTY regressions.
All 10 focused tests and repository reconciliation checks pass. See
verification.md for commands, regression evidence, environment limitations and
the explicit Hermes CLI workaround. Changes remain local and uncommitted.

### Follow-up: commit authorization

The user requested committing the verified fix to the repository. Prepared
the installer changes, PTY regression tests and spec 049 follow-up artifacts
for a local commit on `codex/fix-macos-installer-arrows`. No push requested.

## 2026-10-09 — Python prerequisites/retry follow-up

Greg's next log confirmed uv missing and showed dependency resolution failures
under Apple's python3/pip. Source/package metadata exposed absent Python
minimum checks and blind reuse of old managed venvs. Updated spec/plan/tasks
before implementation, added early minimum and uv checks, preserved old
automatic runtimes while recovering into a separate compatible target, and
documented the Homebrew remedy. 57 focused tests and declaration checks pass;
real Python 3.9-to-3.12 retry verified with an offline fixture wheel.

Greg's exact version remains unconfirmed; no full fleet installation claimed.
Original PR 284 is merged. Prepared a separate follow-up commit/PR on
`codex/fix-installer-python-prerequisites` from c2cc6d4. GAIT tools remain
unavailable; this file records the session. No devices or credentials accessed.

## 2026-10-09 — received full installer logs

User supplied the full install archive after confirming Python 3.9.6. Read
104 component/core logs locally without extracting the archive. Classified
resolver/editable/missing-uv failures and verified distinct gtrace, certificate
and multivendor defects. Updated spec, research, plan and tasks before code.
Added isolated pip refresh, preserved dedicated source-runtime recovery,
success-recorded canonical launch binding, accurate component failures and
portable version/release parsing. Operator guidance distinguishes external
service/platform prerequisites from Python recovery.

124 focused tests and declaration/syntax checks pass. Installer contract
checks install and discover four temporary MCP runtimes; optional fwrule
checkout absent. Existing draft PR285 is the authorized publication target.
Raw logs/private analysis remain local. No live services or network devices
were operated, and no messages were sent to Greg. GAIT tools remain unavailable;
this append-only record and daily memory document the session.


## 2026-10-09 — platform/component preflight and Zabbix correction

User explicitly authorized fixing Zabbix, implementing OS detection/component
preflight, testing, committing, pushing and updating the PR. PR285 is merged;
new codex/fix-installer-preflight is based on main aa90e7d for a linked follow-up.
Read the second archive locally; no raw logs, private analysis or credentials
are part of the commit. Extended spec artifacts before implementation.

Restored Zabbix's requirement cwd, added shared host/component policy and bounded
read-only preflight before install side effects, chose existing Python 3.12 by
default, enforced component bounds during recovery, disabled unsupported picker
rows and separated per-run logs. Updated operator guidance and regression tests.
197 focused tests, real temporary Zabbix install/discovery, four-server installer
contracts and required declaration/artifact checks pass. Endpoint tests require
live credentials; optional fwrule checkout absent. Temporary install runtimes were
removed. No global tools/runtimes installed; no device or vendor endpoint calls.
GAIT tools remain unavailable; this append-only session record and ignored daily
memory preserve the audit. Draft release coordination remains with maintainers.

Publication: implementation commit 09b4db7 pushed to
`calcuttin:codex/fix-installer-preflight`; follow-up draft
[PR287](https://github.com/automateyournetwork/netclaw/pull/287) links merged PR285
and records the final scope, verification and release-coordination plan.
