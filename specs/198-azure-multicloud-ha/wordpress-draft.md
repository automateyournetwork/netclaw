# DRAFT FOR OWNER REVIEW ONLY. Never publish without explicit approval (constitution XVII).

## NetClaw goes multi-cloud: six sandboxed Borders across Azure and GCP

We stood up two three-Border HA groups, one on Azure (Canada Central, East US 2, Sweden Central) and one on GCP
(Montréal, Belgium, Singapore). Every Border runs inside an OpenShell sandbox with DefenseClaw guarding the model path
(Landlock a hard requirement, guard in action mode). Each group keeps its own TLS etcd with RBAC and its own authority epoch.

What worked on the live run: trusted HTTPS HUDs on all six Borders; real hosted-Sonnet operations through members with durable
acknowledgements; a Border takeover (authority epoch 33 to 85) with the survivors still serving; certificate rotation with a new TLS
serial; and protected cross-group federation: every Border lists the other group's members through a signed, pinned-mTLS catalog,
and an operation entered on one cloud ran on a member of the other, authorized in the receiving group's own ledger with the origin recorded.

What we learned the hard way: a follower Border signed a null authority epoch (found live, fixed with a regression test); a stale
Docker network and an unstable Wi-Fi link made member-executed operations flaky; and members pick the lowest-id Border for
admission, which is far away in one group. Honest status: the cross-cloud call completed in one direction; the reverse relays and
authorizes correctly but did not finish on this run. Everything was torn down and verified empty afterwards.
