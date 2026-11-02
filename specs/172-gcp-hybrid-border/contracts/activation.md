# Role activation and cloud packet contract

A provider-neutral role contract selects an owned installation/home and pinned
source, profile and interpreter. For R03 Border: runtime metadata OpenClaw,
protected mode mandatory, role persisted before start, control-only executor=None,
no provider/device key inputs, no Docker/gateway/model/tool services. Startup env
is an explicit allowlist, not inherited repository `.env`. Private startup secret
projection contains only Border identity/owner/bridge/federation material.

Separate non-root federation and HUD services bind only required listeners. Keep
admin/routing/broker interfaces loopback and eN2N registered but loopback/dormant;
public direct iN2N is distinct. System units use UMask0077, NoNewPrivileges,
PrivateTmp, ProtectSystem=strict, ProtectHome and precise writable state paths,
no capabilities and bounded resources. Actual systemd inspection/restart is
required; templates alone are not qualification.

GCP IaC lives in `labs/cloud/gcp/r03`, uses explicit project and fresh private state,
unique names/labels/expiry, VPC/subnet/VM/disk/IP/workload identity/scoped secret and
only reviewed firewall ingress. No R01 import/change, no cloud-to-LAN routes,
public MCP/model/routing/admin, new build service or shared credential bundle.
Admin SSH uses IAP. DNS A/TTL/HTTPS source and binary hashes are separately named.

Before apply: frozen saved-plan digest/resource diff, cost/actual-charge visibility,
48h-or-shorter expiry, finite traffic controls and residual costs, rollback and
exact reviewed teardown scope. Source implementation grants no cloud mutation.
Before runtime activation: exact source/secret/key/transfer/unit/DNS operations and
approved repairs/restarts. Before destroy: verified exported evidence and exact
R03-only destroy plan. A prior R01 delegation is not a new R03 delegation.

R03's launcher qualifies only the control-only Border role. It explicitly refuses
cloud-member activation, which remains R04; the provider-neutral role concept is
not a claim that every role can already launch. On-prem qualification reuses R02's
protected execution runner with fresh selected homes and the device selector.

Bootstrap uses a clean environment and `/usr/bin/python3 -I -S -B` (stdlib only)
to verify the closed source bundle and immutable Python environment manifest,
including pyvenv.cfg, site-packages, directories and explicit symlinks. Only then
may it exec the pinned venv with `-I -B`; the daemon retains isolation flags.
The manifest excludes system site packages and rejects unpinned import files.
Source/runtime directories are root-owned and non-writable by the service on
the pinned GCP image. This does not qualify arbitrary host Python installations.
Full profile drift, including the Border authority binding, latches the member
selector until restart, including the final reread after effect authorization.

Fresh member enrollment is a separate trusted-native preparation step. It MUST
construct the service in protected mode from the outset, with no executor,
model/gateway/runtime start, legacy execution or public listener. The explicit
approved Border binding and strict dial registration are verified before any
enrollment token is sent; the attested hub key must match that binding. After
one enrollment, close the channel, retain the actual generation and finish the
private profile. Ordinary member start then validates the complete profile.

No temporary executable profile and no protected-mode-off bootstrap are allowed.
The enrollment-only API is not exposed over HUD/MCP/peer routes. A private durable
one-use attempt record precedes network admission; uncertain outcomes are not
replayed. Recovery inspects retained local/Border evidence and may finish profile
preparation without another enrollment. Reconnect uses the existing key/generation.
This adds no permission for a model/tool/provider/device effect during onboarding.
