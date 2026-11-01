# Research

VM (Ubuntu 24.04, systemd 255): polkitd 124 (JavaScript rules); /etc/polkit-1/rules.d
is root:polkitd 0750 (unreadable to the operator, so presence cannot be checked by
reading); org.freedesktop.systemd1.manage-units defaults auth_admin. systemd passes
`unit` and `verb` details to polkit for manage-units, so a rule can restrict both.
polkit honours caller-supplied details only for trusted callers, so `pkcheck
--detail` cannot prove the rule as the operator; verify by starting a reserved
no-op instance instead. Spec165 verified a system unit with User=<operator> and the
full hardening runs embedded OpenClaw 2026.10.9.
