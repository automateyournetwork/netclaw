# R04a source integration and VS Code 1.6.0

## Authorization and acceptance — November 4, 2026

After the final native verification handoff, the owner requested all work committed,
a PR, quiet merge, return to main, production VS Code packaging/publication and a
short collaborator write-up. This accepts R04a and closes T017: **22/22 tasks**.
It supersedes the previous extension version/Marketplace hold for this update.
It does not authorize a source release/tag, public cloud deployment, announcement,
existing runtime upgrade or execution of R04b/R05.

Upstream PR325 was merged cleanly at a21bd268. Source VERSION remains **1.18.5**;
Mobile remains **1.0.3+6**. Both `174-cloud-client-integration` and upstream
`174-member-skill-status` retain their historical names. Official Marketplace
metadata confirmed extension1.5.0 before this update; the new extension is1.6.0.
Publisher credential verification succeeded without exposing the credential.

## Combined source checks

- Independent review found that upstream member skill reporting could invoke an
  ambient host OpenClaw process for a protected member whose actual runtime is
  frozen in an execution profile. The integration fix skips scheduling and direct
  invocation of that host check for protected members, preserving ordinary member
  reporting. Actual protected enrollment and direct-call regressions cover it.
  A stale owner-bridge test fixture explicitly sets `open_lab=False`; production
  authorization behavior is unchanged. Original review commit7eaf1c0c was
  integrated asbc226ef5.
- Combined Python suite: **611 passed**. Affected HUD suite: **149 passed**;
  Vite build: **167 modules**, passed. Independent source/privacy review passed.
- Extension1.6.0 TypeScript check/build and complete suite: **190 tests,
  187 passed, three existing optional skips, zero failures**. Extension production
  dependency audit: **zero vulnerabilities**. Three moderate development-only
  advisories are retained in the private audit receipt; no dependency upgrade or
  toolchain downgrade was hidden in the version change.

The separately installed HUD test dependency tree reports seven existing
advisories (one critical, five high, one moderate). A bounded bundle review found
the affected HUD packages absent from the VSIX; the bundled Zod4.6.7 is newer than
the affected range. This does not clear the separate HUD dependency findings or
upgrade its running service. The exact audit and package-scope receipts are private.

Review receipt SHA256:
`0c3e51f3a237de571c1396102fdaaf0da426f018bae8b3ab6d0329316e765d3d`.
Release preparation original commitcb5031be was integrated as4b51a350.
Private source/test/package/publication receipts are under
`~/.local/share/netclaw/roadmap-r04a-release-20261104/` (not part of any package).
The package/PR/publication outcome will be recorded below after actual completion.

## Qualification retained

The installed-client proof is in [verification](verification.md) and
[owner delivery](owner-delivery.md). It used frozen private1.5.0 client payloads
and the cloud backend e68b4951 plus7856e856, with protected federation7f7df355.
This source integration and packaging do not redeploy that runtime or repeat the
native/provider workload. The production archive receives source/build/package
checks; live evidence is not relabeled as a test of the final merged source.

The Mac result covers the normal workspace, real Chat, cited RAG/Canvas and
protected NetBox read/result/ACK recovery with unchanged execution counts. Native
file-picker automation did not complete selection; the approved upload used the
production client. The final recovery click was not captured; its GET route is
source-derived, not packet-traced. Windows/Linux cloud editors, physical Mobile,
QR enrollment, other cloud/harness combinations and general deployment remain
unqualified. A compatible backend must advertise R04a `remoteHud` schema1;
source1.18.5 alone does not establish that capability. No user login was added.

## Collaborator write-up and next step

R04a makes the existing Cloud Border usable from the normal NetClaw VS Code
workspace: add a name and HTTPS URL, then use Overview, Chat, Canvas, RAG and
supported operation panels. Protected member reads retain exact approval, signed
results, durable acknowledgements and recovery without duplicate execution.

Recommended next is **R04b: cloud HUD Mobile QR enrollment**, reusing the current
scanner/device keys with a bounded single-use QR issuer, trusted WSS enrollment
and reconnect, and protected-operation evidence. It does not introduce user login;
users/SSO/RBAC remain R15–R17. Then **R05** adds guarded Ollama cloud IPv6/on-prem
IPv4 subnet members with separate VS Code/Mobile integration checks. Neither
follow-up is started by this release.
