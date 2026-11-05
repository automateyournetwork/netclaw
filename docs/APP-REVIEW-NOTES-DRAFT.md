# App Review notes — Mobile 1.0.4

Submitted on November 5, 2026 with build 7. The version is waiting for Apple review.
Contact information remains private in App Store Connect.

NetClaw Mobile is a companion for NetClaw software that an operator runs on their own infrastructure. It does not provide a hosted service or username/password sign-in.

Enrollment in version 1.0.4:
1. Open the operator's NetClaw HUD, or the Mobile section of the NetClaw VS Code extension.
2. Select the intended Border and generate a fresh mobile enrollment QR code.
3. Open NetClaw Mobile and scan that code. Review the Border identity and complete enrollment.
4. Available features depend on the selected Border and its advertised capabilities; supported views include Chat, approval review, activity/history, settings and the existing Apple Watch companion.

QR codes expire and are single use. A screenshot of an old enrollment QR code cannot provide reviewer access. The operator generates a fresh code from their own installation; scanning it creates a device identity scoped to that Border.

The app's onboarding explains the companion requirement. Existing App Store screenshots show the actual enrolled app. There is no public reviewer endpoint supplied with this submission, and the app may remain at onboarding without an operator-managed Border. This release makes enrollment available directly in the HUD and VS Code and improves identity checks, enrollment errors, and reconnect recovery.

See [release evidence](../specs/175-cloud-mobile-enrollment/release-verification.md)
for the exact archive, submission state and qualification limits.
