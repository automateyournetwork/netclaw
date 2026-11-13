# Tasks

- [x] Trace owner issuance, installation selection, cookie normalization, proxy ingress, existing read revalidation and profile exclusions.
- [x] Define the operation map, owner handle lifetime, origin/CSRF checks and asynchronous response boundary.
- [ ] Obtain maintainer agreement on this interface and the local and dedicated HTTPS reviewer profiles.
- [ ] Implement guarded registration, disabled and unsupported modes, strict request framing, owner-context derivation and lifecycle checks.
- [ ] Exercise real HTTP entry points with absent/duplicate/wrong installation, legacy and duplicate cookies, stale owners, malformed paths, oversized input, wrong origin, missing CSRF, HEAD, role-independent denials and timeouts. Check that the fixture handler sees zero calls when the host rejects a request.
- [ ] Verify two owners, adapter isolation, process restart, revoke during a paused read, and ambiguous writes. Exercise classic and React through local proxy ingress plus attempted remote/protected/public access. Test that standalone preview emits zero requests.
- [ ] Exercise a separately bound HTTPS reviewer origin, trusted certificates, explicit registration and restricted assets. Use two independent browsers and synthetic accounts, attack session fixation, wrong origin, forged forwarded headers and cross-site case access. Verify logout, role downgrade, audit attribution and rejection of all generic HUD routes and upgrades. Complete ingress bypass and integrated browser checks.
- [ ] Verify the stock HUD suite and stock build, disable the adapter and check removal, package the interface, and coordinate the completed feature release.
