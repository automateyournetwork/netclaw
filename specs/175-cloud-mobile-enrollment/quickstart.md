# Maintainer verification sequence

This is qualification guidance, not public cloud deployment instructions.

1. Verify clean source and active pilot identity; capture private authority/source/config baseline. Preserve old R04a operations and member keys.
2. Run backend, HUD, extension and Mobile focused tests; build affected clients. Review exact deployment delta (no new resource by default), rollback and ingress before applying.
3. Run isolated local Border. In browser Mobile choose Enroll mobile device; record QR issuance without logging token. Decode actual QR image in native simulator through production handler. Confirm same-key hello reconnect.
4. Repeat local generation in the actual VS Code Mobile view, then cloud HUD and cloud VS Code. Use deliberate separate offers/devices or fresh explicit replacement; never reuse spent QR. Record each surface separately.
5. Run wrong-domain/key/installation, expired/spent token, cross-device/unauthorized method and lost-reply cases. Verify protected legacy execution remains unavailable.
6. Review one exact existing bounded read, approve once from enrolled simulator, correlate signed result and durable ACK with actual native/member effect counts.
7. Background/restart/reconnect and recover the same reference. Verify zero additional prepare/decision/provider/MCP effects, existing owner history unchanged.
8. Export sanitized receipts, clear expired QR from views, retire only disposable local test resources; retain usable cloud pilot and lifetime. Record simulator/physical limitations, GAIT and human handoff. No release, version bump, R05 or public rollout.
