# R03 maintainer handoff — 2026-11-03

R03 technical qualification is complete. A fresh control-only Border in GCP
Montréal served the authenticated owner HUD over trusted HTTPS and dispatched
four independently approved reads to an outbound-connected on-prem pyATS member.
R1, R2, SW1 and SW2 each returned IOS 17.18.2 from exactly one `show version`, using
OpenClaw/Sonnet. Signed approvals/results/ACKs and GAIT correlate end to end.
Lost replies, service/member restart and browser recovery preserved all four
operation IDs with no repeated device/model execution. 62 browser/auth checks
and actual credential/IAM/network confinement checks passed.

All 13 temporary GCP resources, DNS and the temporary SSH key were removed after
private evidence export; zero R03 billable residues remain. Local workers and
owned operation containers/networks are also removed. R01 remains unchanged and
available. Source 1.18.3 / extension 1.5.0 and the entire-roadmap release hold remain:
this is maintainer evidence, not a general cloud deployment release. Hermes cloud,
arbitrary providers, writes and multi-user controls are not qualified by this run.

R01/R02 are accepted; R03 is 35/36 pending human acceptance in T036. After that
gate, R04 covers cloud NetBox/subnet members with a hosted model; R05 adds Ollama
members. See [verification](verification.md) for exact evidence and limitations,
and [resume](resume.md) for private preservation and the next gate.
