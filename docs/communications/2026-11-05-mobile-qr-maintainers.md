# Maintainer note — Mobile QR enrollment

NetClaw 1.18.6 brings Mobile enrollment into the HUD and VS Code extension 1.6.1.
Open Mobile, generate a QR, and scan it on the phone. The shared service removes
the hidden CLI-token step from ordinary onboarding while preserving single-use
expiry, installation binding and retained device identity.

All four HUD/editor enrollment paths passed on an iPhone simulator. A real signed
read and cold/background recovery completed without repeating execution. Physical
camera and Secure Enclave qualification remain separate.

- [Source release](https://github.com/automateyournetwork/netclaw/releases/tag/v1.18.6)
- [VS Code extension](https://marketplace.visualstudio.com/items?itemName=NetClaw.netclaw)
- [Enrollment guide and throwaway QR screenshot](../MOBILE-ENROLLMENT.md)
- [NetClaw Mobile on the App Store](https://apps.apple.com/us/app/netclaw/id6800859524) — 1.0.4 (7) is submitted and waiting for Apple review; automatic release follows approval.
- [Mobile distribution and release evidence](../../specs/175-cloud-mobile-enrollment/release-verification.md)

The accompanying article is seeded as a draft in the owner's `modern_website`
project. R04b is complete; work stops before R05. This note is prepared for the
maintainer and has not been sent to external channels.
