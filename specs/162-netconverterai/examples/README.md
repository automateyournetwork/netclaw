# Synthetic OSPF conversion input

`iosxe-ospf-synthetic.cfg` is an authored, unexecuted IOS-XE routing fixture. It is
not collected from the owner's devices and is not a NetConverter result. It uses
documentation addresses, contains no credentials and has not been submitted or
applied. No generated Junos output is included: that artifact must come from the
actual conversion job.

Intended scope: router ID/loopback `192.0.2.1`, isolated point-to-point area-0 link
`198.51.100.1/30`, OSPF cost 10, passive loopback and one active peer interface.
The separately prepared stable peer would use `198.51.100.2/30` and advertise
`192.0.2.2/32`. The negative-control prefix `203.0.113.254/32` is not advertised.

Interface `GigabitEthernet1` is a proposed mapping, not a discovered lab port.
Management, authentication and bootstrap are intentionally outside this routing
fragment and need their own reviewed scope. Qualify the actual source image and
format, capture a real baseline, map interfaces and preserve management before
any authorized source-twin application. If the source changes, prepare and review
the exact resulting file again. An authored fragment cannot establish source
behavior; actual source/target assertions remain pending.

Once the account is enabled, the guard must discover its offered IOS-XE router →
Junos router path and prepare this file (or a later real source collection). The
human reviews the resulting exact digest/account/destination before any hosted
transfer. Repository inclusion is not transfer approval.
