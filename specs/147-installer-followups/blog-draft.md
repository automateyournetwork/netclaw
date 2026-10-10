# Draft: Make installation results mean something

NetClaw's macOS and Linux feedback showed why an installer must check more than
files on disk. A component could appear installed while the agent lacked its
registration, launched a different Python, or failed its first protocol handshake.

Spec 147 builds on Nick's host-preflight and Zabbix fix. It adds native registrations
for the twelve reported missing components, shares launch bindings with existing
skills, tightens Node/npm bootstrap checks and records discovery separately from
endpoint readiness. Remote Ollama is checked at its configured host rather than
assuming it requires a local executable.

The most useful test result was an HTTP probe that exited successfully without
exposing a tool. The new check examines the result itself. Real OpenClaw discovery
also passed for four component catalogs in disposable environments, and a calculator
canary returned the expected TEST-NET subnet.

These checks do not certify every external appliance or every model's answers.
They make the evidence and remaining gaps visible, so the next failure has a place
to start. User credentials, persona files and approval controls remain preserved.

Draft for John's review. WordPress was unavailable in this session; not published.
