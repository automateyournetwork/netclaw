# Feature Specification: iOS Port Verification and App Store Roadmap for NetClaw Mobile

**Feature Branch**: `071-ios-mobile-port`
**Created**: 2026-07-25
**Status**: Draft
**Input**: User description: "iOS port verification for NetClaw Mobile (the Flutter NCFED edge-node app under mobile/netclaw-mobile/, cross-platform features 066/067/068). The Dart/UI layer is already shared and considered done; this feature is about the iOS-native side, which was written without access to a Mac and has never been built or run. Scope covers Secure Enclave EdgeIdentity, X.509 cert builder, Face ID, camera/mic capture, outstanding manual verification tasks from 066/067, README updates, and a companion App Store publication roadmap. Push notifications are explicitly out of scope."

## Clarifications

### Session 2026-07-25

- Q: This spec assumes a real, physical iPhone is available for Secure Enclave/Face ID verification (Simulator can't exercise either). Is one actually available for this work? → A: Yes, a real iPhone is available — User Stories 1 and 2 keep full real-device acceptance criteria, no rescoping to Simulator-only.
- Q: Edge Cases says pre-existing defects found on iOS (e.g. `ReconnectSupervisor` ignoring revocation) are out of scope "unless trivial" — an undefined threshold. How should that be handled? → A: Fix only if genuinely trivial (a one-line/obvious fix applied inline); anything nontrivial is documented and deferred to its own feature/PR, not fixed here.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enroll and operate the app on a real iPhone (Priority: P1)

An operator installs NetClaw Mobile on a real iPhone, enrolls it against their Border (via QR or manual entry), and uses it to ask a question and receive an answer — the same core loop already proven on Android.

**Why this priority**: This is the whole point of an iOS port. If the app cannot generate a device identity, sign a challenge, and complete the enrollment + ask/answer round trip on iOS, nothing else in this feature matters. It is the iOS equivalent of the round trip already proven end-to-end on Android (2026-07-25, 2m13s).

**Independent Test**: Install a build on a real iPhone, enroll against a live Border, ask a question, and confirm an answer is delivered — without touching Secure Enclave internals, Face ID, or capture separately.

**Acceptance Scenarios**:

1. **Given** a fresh install of NetClaw Mobile on a real iPhone, **When** the operator scans a Border-issued enrollment QR code, **Then** the app generates a device identity, signs the challenge, and completes enrollment successfully.
2. **Given** an iOS Simulator with no usable camera, **When** the operator chooses "Can't scan? Enter manually" and types the domain/port/token, **Then** enrollment completes the same as a QR scan would.
3. **Given** an enrolled iPhone, **When** the operator types a question and sends it, **Then** the app displays the Border's answer once delegation/routing completes.
4. **Given** an enrolled iPhone that loses and regains network connectivity, **When** the connection drops, **Then** the app automatically redials and resumes without requiring re-enrollment.

---

### User Story 2 - Prove device-native security features actually work (Priority: P1)

An operator confirms that the iOS-specific security surface — Secure Enclave key generation/signing and Face ID — genuinely works on a real device, since this code was written without Mac access and has never been executed.

**Why this priority**: Device identity is the trust anchor for the whole enrollment protocol, and biometric approval (feature 068) gates sensitive actions. Both are unverified placeholders until exercised on real hardware; shipping without this proof risks an app that builds but cannot actually establish trust or gate approvals.

**Independent Test**: On a real iPhone (not Simulator), trigger identity generation and confirm a real Secure Enclave key is created and used to sign a challenge; separately, trigger an approval and confirm a real Face ID prompt appears and its result is honored.

**Acceptance Scenarios**:

1. **Given** a real iPhone during first enrollment, **When** the app requests a new device identity, **Then** a Secure Enclave-backed key pair is generated (not a software-only fallback) and a self-signed certificate is built from it.
2. **Given** an existing device identity, **When** the Border sends a challenge nonce, **Then** the app signs it with the Secure Enclave key and the Border accepts the signature.
3. **Given** a pending Border-triggered approval on a real device with Face ID enrolled, **When** the operator opens the approval, **Then** a real Face ID prompt appears and a successful scan resolves the approval.
4. **Given** a real device where Face ID authentication fails or is cancelled, **When** the operator retries or dismisses, **Then** the approval remains unresolved and no false-positive approval is recorded.

---

### User Story 3 - Use camera/mic capture on iOS (Priority: P2)

An operator attaches a photo to their own request, and separately fulfills a Border-requested capture, both from a real iPhone.

**Why this priority**: Feature 068's capture flows are pure-Dart plus platform camera/mic permissions; they are lower risk than Secure Enclave/Face ID but still unverified on iOS and needed for feature parity with Android.

**Independent Test**: From a real device or Simulator, initiate a photo attach to an outgoing request, and — from the Border side — request a capture from the device, confirming the resulting photo/audio round-trips correctly.

**Acceptance Scenarios**:

1. **Given** an enrolled device with camera permission granted, **When** the operator attaches a photo to a question, **Then** the photo is captured, attached, and delivered with the request.
2. **Given** an enrolled device, **When** the Border requests a capture, **Then** the operator is prompted, and a successful capture is delivered back to the Border.
3. **Given** a device where camera or microphone permission has been denied, **When** a capture is attempted, **Then** the app shows a clear message explaining the permission is required, without crashing.

---

### User Story 4 - Publish the app to the App Store (Priority: P3)

The operator, who intends to publish NetClaw Mobile publicly, has a clear, sequenced roadmap for iOS App Store submission that accounts for irreversible decisions and this repo's current (incomplete) iOS release configuration — mirroring the existing Android/Play Store roadmap.

**Why this priority**: Publication readiness matters, but it is meaningless until the app actually runs correctly on iOS (User Stories 1–3). It is scoped as its own story because it is a planning/documentation deliverable, not code, and can be produced independently once the verification work clarifies what is actually shippable.

**Independent Test**: Read the roadmap document standalone and confirm it identifies every irreversible pre-publication decision, the current gap between "builds" and "shippable," and a concrete ordered checklist — without needing to touch the app itself.

**Acceptance Scenarios**:

1. **Given** the roadmap document, **When** an operator with no prior App Store experience reads it, **Then** they can identify which decisions are permanent once made (bundle identifier, certain account/signing choices) and must be made first.
2. **Given** the repo's current iOS build configuration, **When** the roadmap is compared against it, **Then** every gap between current state and "App Store ready" (signing, provisioning, data-safety disclosures, listing assets) is called out explicitly with its current status.
3. **Given** the roadmap's sequenced checklist, **When** followed in order, **Then** each step's prerequisites have already been satisfied by an earlier step.

---

### Edge Cases

- What happens when a device has no Secure Enclave support at all (e.g., unusual hardware/OS combination)? The app must fail enrollment with a clear, actionable error rather than silently falling back to a weaker (non-hardware-backed) identity, since the Border's trust model assumes hardware-backed keys.
- What happens when Face ID is not enrolled on the device at all (no biometrics set up)? The approval flow must offer a clear fallback or clear failure message, not a silent hang.
- What happens when the operator revokes a device from the Border while the iOS app is mid-session? The app must detect the revocation and return to the enrollment gate rather than retrying a dead connection indefinitely (this is a known pre-existing defect on both platforms — verification should confirm it reproduces on iOS too. Fixing it is out of scope for this feature unless the fix is genuinely trivial, i.e. a one-line/obvious change; anything nontrivial is documented and deferred to its own feature/PR).
- What happens if Xcode's build fails outright on first attempt due to Swift/plugin issues never compiled before? This is the expected starting state for User Story 1/2 work, not an edge case to design around — it is the reason this feature exists.
- What happens when the operator attempts to change the bundle identifier after the roadmap has already been followed partway? The roadmap must flag this decision as made-once-and-permanent, matching the equivalent Android `applicationId` warning.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The iOS build MUST compile and link successfully in Xcode, including the Secure Enclave identity plugin and the manual X.509 certificate builder.
- **FR-002**: On a real iPhone, device identity generation MUST produce a Secure Enclave-backed key pair (not a software-only key) and a valid self-signed certificate derived from it.
- **FR-003**: The app MUST use the Secure Enclave key to sign Border-issued challenge nonces during enrollment and re-authentication, and the Border MUST accept the resulting signature.
- **FR-004**: Enrollment MUST succeed via both QR-code scan (on hardware with a camera) and manual entry (domain/port/token), matching the existing manual-enrollment fallback already implemented in the shared Dart layer.
- **FR-005**: On a real device with Face ID enrolled, triggering an approval MUST present a genuine Face ID prompt, and the approval's outcome MUST reflect the actual biometric result (success resolves it, failure/cancel leaves it unresolved).
- **FR-006**: The app MUST support photon/audio capture on iOS for both directions already implemented in the shared layer: operator-initiated attach-to-request, and Border-requested capture-and-return.
- **FR-007**: The app MUST request camera, microphone, and Face ID usage permissions with the existing `Info.plist` usage-description strings, and MUST degrade gracefully (clear message, no crash) when a permission is denied.
- **FR-008**: The verification effort MUST determine and document whether `AppDelegate`/`SceneDelegate` requires any structural change analogous to Android's `FlutterActivity` → `FlutterFragmentActivity` change for biometric auth, and apply it if required.
- **FR-009**: The verification effort MUST attempt to close the two outstanding manual-verification tasks carried over from specs 066 and 067 (066 quickstart walkthrough against a live Border; 067 federated-peer attribution check) using iOS as the test platform, network conditions permitting, and MUST document the outcome (closed, or blocked with a stated reason) either way.
- **FR-010**: `mobile/netclaw-mobile/README.md`'s iOS section MUST be updated to state precisely what has been verified on real hardware/Simulator versus what remains assumed or unverified, at the same level of specificity as the existing Android section.
- **FR-011**: A companion App Store publication roadmap document MUST be produced, structurally comparable to `PLAY-STORE-ROADMAP.md`, covering at minimum: the bundle identifier decision and its permanence, code signing and provisioning profile setup, TestFlight beta distribution, and App Store Connect listing requirements (privacy policy URL, App Privacy / data-safety disclosures covering camera, microphone, biometric, and any location use, and age rating).
- **FR-012**: The roadmap MUST be sequenced against this repo's actual current iOS build configuration (as found in `ios/Runner/` and `pubspec.yaml`), explicitly calling out each gap between current state and "submission ready," not a generic App Store checklist.
- **FR-013**: Push notifications (APNs/Firebase) MUST remain explicitly out of scope for this feature; the roadmap and README updates MAY note that push is unfinished but MUST NOT require finishing it as a condition of this feature's completion.
- **FR-014**: This feature MUST NOT modify or reimplement any of the shared Dart/UI layer's behavior (enrollment flow, ask/chat, approvals logic, capability registration, heartbeat) — only the iOS-native platform layer, its build configuration, and documentation.
- **FR-015**: Pre-existing defects discovered during iOS verification (e.g. revocation not interrupting `ReconnectSupervisor`'s retry loop) MUST be documented, not silently ignored; a fix MAY be applied inline only if it is a one-line/obvious change, and MUST otherwise be left undone and deferred to its own feature/PR.

### Key Entities

- **Device Identity (iOS)**: The Secure Enclave-backed key pair and derived self-signed X.509 certificate that uniquely and verifiably identifies an enrolled iPhone to a Border; the iOS counterpart to Android's AndroidKeyStore-backed identity.
- **Verification Record**: The documented outcome (verified / assumed / blocked, with evidence) for each capability in scope — device identity, Face ID, capture, manual verification tasks — captured in the updated README and used to judge feature completion.
- **App Store Publication Roadmap**: A standalone planning document sequencing every decision and task required to take the current iOS build to a public App Store listing, mirroring the structure and rigor of the existing Play Store roadmap.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can go from a fresh install to a delivered answer on a real iPhone (enroll → ask → receive answer) in a single sitting, with no manual workarounds beyond what the app's UI already offers.
- **SC-002**: Device-identity generation and challenge signing succeed on 100% of attempts on a real, supported iPhone during verification testing, with zero silent fallbacks to non-hardware-backed keys.
- **SC-003**: A real Face ID prompt is observed and correctly gates at least one approval during verification testing, with both a success and a failure/cancel path exercised.
- **SC-004**: At least one photo capture completes successfully in each direction (operator-attached, Border-requested) during verification testing.
- **SC-005**: The updated README's iOS section contains no claim that cannot be traced to a specific verification step performed during this feature's work (i.e., no carried-over "unverified" claims are silently reworded as "verified").
- **SC-006**: The App Store roadmap document identifies 100% of the irreversible pre-publication decisions (at minimum: bundle identifier, signing/provisioning approach) before any reversible task in its sequencing.
- **SC-007**: A reader unfamiliar with this codebase can determine, from the roadmap alone, the next concrete action to take toward App Store submission without needing to ask a follow-up question.

## Assumptions

- A real iPhone (not just the Simulator) is confirmed available for the Secure Enclave, Face ID, and camera/mic verification steps, since the Simulator cannot exercise any of these.
- A Mac with a working Xcode installation and a valid Apple Developer identity for code signing (even if only a personal/free-tier signing identity) is available to build and run on a real device. As of this spec's writing, the target Mac has only Xcode Command Line Tools and no Flutter SDK installed — getting both installed is this feature's own Phase 1 Setup work, not a precondition that must already be satisfied before the feature can start.
- The operator's Border remains reachable during verification the same way it was for the Android pass (per `MAC-IOS-HANDOFF.md`, `N2N_EDGE_WS_PORT=8443` was confirmed live as of 2026-07-25); if it is not reachable when this work happens, verification steps requiring it are documented as blocked rather than skipped silently.
- Closing the two outstanding manual-verification tasks from specs 066/067 is best-effort: if the required federated peers or live Border are unavailable, this feature still completes provided the blocker is documented (per FR-009), since those tasks were already open before this feature and are not solely blocking this feature's scope.
- The App Store roadmap is a planning document only; actually enrolling in the Apple Developer Program, generating certificates, or submitting a build for review is out of scope for this feature and left to the operator to execute afterward.
- Push notifications, App Store screenshots/marketing assets, and any UI redesign are out of scope, consistent with `MAC-IOS-HANDOFF.md`'s framing of push as a separate work item.
