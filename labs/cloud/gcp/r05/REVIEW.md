# R05 isolated cloud member — maintainer preparation

This module adapts the accepted R04 member foundation. It creates eight foundation
resources: VPC, subnet, service account without project IAM/scopes, reserved IPv4,
IAP22 firewall, private-egress deny, default-egress deny and one Shielded
`e2-standard-2` (2vCPU/8GiB) with40GiB auto-delete standard boot disk. It creates
no Border, DNS, provider secret, public application/model ingress or startup script.
`network_activated=true` adds exactly two rules: member egress to the selected
Border IPv4/port, and a separate R05-owned ingress rule on the explicitly selected
Border network, targeted only to its service account and sourced only from this
member's reserved /32. Both rules use the same port. Existing Border rules remain
unchanged. Activation requires the observed Border network/service-account bindings
in the selected project; empty values are accepted only while inactive.

The retained Border was observed with2GiB RAM/~1GiB available and no Docker; it
cannot accommodate the qualified CPU profile's4,416MiB member headroom. Keep that usable deployment
and its four historical operation rows intact. This member uses fresh source,
identity, enrollment, runtime state and owned model store. Public model/image bytes
may be reused only after hash verification; old authorities/plans may not.

Use external0700 state/evidence and0600 inputs/receipts. Plan and inspect exact
creates before approval; initialize no existing R01/R03/R04 state in this module.
No apply has been authorized by this file. The human must review the exact
resource/cost/lifetime packet under the existing roadmap gate. Alerts are not caps.
Keep the December1 maximum lifetime, and account for disk/IP after VM stop.

After source/runtime qualification, prepare a separate single-use activation
packet for native binaries/Docker, root-owned source, isolated Python, namespaces,
new member identity and existing Border source/capability changes. Assets are
transferred through IAP; no general model/provider egress is needed. Verify
application/guard/model identities, actual kernel rules, exact source/profile and
signed execution before accepting this member. No service starts from Terraform.

Cleanup is a separately inspected saved destroy plan containing only this fresh
state's owned resources, executed after evidence export and intended-retention
review. Verify VM, disk, address, firewall, subnet, network and service-account
inventories afterward. Preserve existing owner Border, original budgets and all
other installations. Source/test proof does not qualify an unexecuted deployment.

The saved planning packet lives outside source under the owner's private R05
`cloud-plan/` directory. Its selected expiry is December1 at00:00UTC; it also
records the48-hour cost alternative. The actual retained Border listener is
iN2N42101, established from the November5 socket observation; historical R04
42102 values are not reused. The initial saved plan keeps network activation false.
OpenTofu1.13.2 and the checked-in Google8.9.0 dependency lock produced exactly
eight creates, zero updates and zero destroys. Apply-time expiry remains an
unresolved plan-time check and must pass at execution. This is plan evidence only.

The owner selected the48-hour option after the initial December1 proposal. The
authoritative R05 state and selected expiry remain in the private`cloud-plan-48h/`
packet. Network activation uses that same backend/lineage and adds only the two
firewall rules; state copies are evidence only. Full cleanup of this R05 state
also removes its narrow ingress rule from the existing Border network, without
removing or modifying that network or its original transport rule.
