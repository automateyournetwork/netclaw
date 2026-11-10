# Contract: disposition table (filled by evidence)

| Component | Target | If target fails | Evidence |
|---|---|---|---|
| Border role | inside sandbox | hybrid floor: hardened systemd, documented | E3 |
| HUD ingress | inside sandbox (forward 7443/7444/8443, host 443 redirect) | hardened systemd | E4 |
| Workspace backend + chat gateway | inside sandbox, key injected by OpenShell | n/a (must hold) | acceptance |
| DefenseClaw sidecar | inside sandbox, action mode | n/a (must hold) | acceptance |
| etcd voter / witness | outside (host network), container policy | n/a | documented |
| Member executor (Docker socket) | outside, existing container confinement + guard | n/a | documented |
