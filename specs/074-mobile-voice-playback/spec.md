# Feature Specification: On-Device Voice Playback of Messages (Android + iOS)

**Feature Branch**: `074-mobile-voice-playback`
**Created**: 2026-07-29
**Status**: Clarified (session 2026-07-29) — ready for `/speckit.plan`
**Input**: User description: "working VOICE PLAYBACK to messages on android — where on the device it uses local TTS and plays back the message"

## Context: what exists today

The **phone** can already **listen** but cannot **speak**. Verified against `main` at `e02d679`:

- `pubspec.yaml` declares `speech_to_text: ^7.4.0` and **no** text-to-speech or audio-playback package (`flutter_tts`, `just_audio`, `audioplayers` all absent).
- No Dart-side synthesis exists anywhere in `lib/`. The only TTS in the repo is `ios/WatchApp Watch App/SpeechPlayback.swift`, which is watchOS-only and not reachable from Flutter — see the subsection below.
- `lib/ncfed/voice_transcription.dart` (feature 067, hardened by PR #195) is input-only: microphone → text → `edge_ask_client`.

So the voice loop is half-open **on the phone**: the operator can speak a request, but the answer is text-only and must be read on screen.

> **Correction.** An earlier draft of this section asserted that a sweep for TTS returned zero hits across `lib/`, `test/`, `android/` and `ios/`. That was true of the working tree it was run against, but that tree was 8 commits behind `origin/main` and the search pattern did not include `AVSpeechSynthesizer`. Watch-side synthesis did in fact already exist. The phone-side conclusion is unaffected.

There is also a pre-existing dead end this feature must consciously decide about: `MessageContentType.voice` already exists in `lib/ncfed/message_feed.dart:6`, and `lib/screens/feed_screen.dart:131-135` renders such a message as an inert `Chip(label: Text('Voice message'))`. The Border can therefore push base64 audio that the app can display but **physically cannot play**. See "Out of Scope" — this is adjacent but not the same capability.

### Relationship to `073-push-notifications-sync` (read this first)

**This spec was originally numbered 073 and has been renumbered to 074.** `specs/073-push-notifications-sync` was merged into `main` (PR #191, commit `5e9ecc1`) while this spec was being drafted, so two `073-*` spec directories briefly coexisted. That was not cosmetic: `.specify/scripts/bash/common.sh` resolves the feature directory by matching a branch's numeric prefix against `specs/<prefix>-*` and **hard-errors on multiple matches**, so every speckit command on a `073-*` branch failed with `ERROR: Multiple spec directories found with prefix '073'`. Renumbering to 074 fixes that.

Note that FR numbers are still **not** aligned between the two specs — both define an `FR-017`, meaning different things (here: never persist synthesised audio; there: the watch's read-aloud control). Always qualify which spec an FR belongs to.

**That feature already shipped voice playback — on the watch.** `mobile/netclaw-mobile/ios/WatchApp Watch App/SpeechPlayback.swift` wraps `AVSpeechSynthesizer` for the watch's Feed/History/Ask views (its US4, FR-017–FR-019). So "NetClaw can speak" is now partly true, and the earlier claim in this spec that watch playback was an unimplemented follow-on was wrong.

What that does **not** change: the **phone** still has no synthesis capability. The only dependency `5e9ecc1` added was `flutter_local_notifications`; there is still no Dart-side TTS package, and `SpeechPlayback.swift` is watchOS-only and unreachable from Flutter. Every claim in the section above holds for the phone, which is this spec's entire scope.

What it does change: the watch implementation is now **prior art with a deliberate design position**, and this spec must either match it or justify differing. See FR-012b and Out of Scope.

### Two speakable surfaces

| Surface | Source of text | Screen | Feature |
|---|---|---|---|
| Agent answer to a request | `ConversationTurn.answerText` (`lib/ncfed/conversation_store.dart:9`) | `chat_screen.dart` | 067 |
| Border-pushed message | `EdgeMessage.content` where `contentType == text` (`message_feed.dart:11-22`) | `feed_screen.dart` | 066 |

## Clarifications

### Session 2026-07-29

- Q: When speaking an answer, how should the app handle network-ops text and long machine output (routing tables, CLI dumps, dotted quads, `GigabitEthernet0/0/1`)? → A: Normalise prose phone-side for intelligibility, and skip fenced-code/tabular blocks entirely — announcing them rather than reading them. Keeps the feature mobile-only; no Border protocol work.
- Q: Must playback keep going when the app is backgrounded or the screen locks (the US2 "phone in pocket" case)? → A: No — foreground only for this iteration. Playback stops when the app leaves the foreground. Background playback is deferred to a follow-on rather than taking on an iOS background-audio entitlement and an Android foreground service now.
- Q: Should this feature also implement playback of Border-pushed `voice` audio (the inert Chip at `feed_screen.dart:131-135`)? → A: No — kept separate. Confirmed during clarification that the `voice` content type has **no producer anywhere in the codebase**: the daemon validates it (`bgp-daemon-v2.py:725`) but the only occurrence is a test fixture (`test_edge_push.py:156`), and the push-notification path handles `text` only (`push_notify.py:79`). The inert Chip stays; it deserves its own spec if a producer ever appears.
- Q: What should the settings surface include (FR-011)? → A: A single auto-speak toggle, defaulting to off. No in-app rate or voice picker — both platforms already expose a system-level TTS speech rate that the synthesiser honours when not overridden, so the app inherits the operator's existing OS preference.
- Q: Should voice playback be audible when the phone is on silent/vibrate? → A: Split by trigger — an explicit tap plays audibly even when silenced (the operator just asked for sound), while auto-speak stays silent on a silenced phone (they silenced it to avoid unrequested noise). Matches platform convention for deliberate media vs notification audio.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Hear an answer without looking at the phone (Priority: P1)

An operator with their hands and eyes occupied — up a ladder in a data centre, arms inside a rack, driving to a site, holding a console cable — asks NetClaw a question by voice and needs the answer **spoken back**. Today they must stop, find the phone, and read it, which defeats the purpose of having asked by voice.

**Why this priority**: This closes the voice loop that features 067/068 opened. Voice input without voice output is a half-feature: the hands-free scenario that justified speech-to-text is still not achievable. Everything else in this spec is an enhancement on top of this one capability.

**Independent Test**: Submit a request (typed or spoken) in Chat, wait for the answer to arrive, tap the speak control on that turn, and confirm the answer is audible with the screen not being read. Delivers the complete hands-free ask→hear cycle on its own.

**Acceptance Scenarios**:

1. **Given** a completed turn with a non-empty `answerText`, **When** the operator activates the speak control on that turn, **Then** the answer text is spoken aloud through the device's current audio route.
2. **Given** an answer is being spoken, **When** the operator activates the same control again, **Then** playback stops immediately and does not resume from where it left off.
3. **Given** a turn in `pending`/`working` state with no answer yet, **When** the operator looks at that turn, **Then** no speak control is offered (there is nothing to speak).
4. **Given** a turn whose state is `failed` or `cancelled`, **When** the operator looks at that turn, **Then** no speak control is offered.
5. **Given** the device has no usable TTS voice installed, **When** the operator activates the speak control, **Then** they are told why nothing was spoken and what to install — never a silent no-op.
6. **Given** the device is in silent/vibrate mode, **When** the operator activates the speak control, **Then** the answer is still audible (FR-012a).
7. **Given** an answer containing a fenced code block or table, **When** it is spoken, **Then** the surrounding prose is spoken and the block is announced with its size and location rather than read aloud (FR-009).
8. **Given** an answer is being spoken, **When** an incoming call takes audio focus and then ends, **Then** playback does not resume by itself and the item remains re-triggerable (FR-013).

---

### User Story 2 - Answers spoken automatically as they arrive (Priority: P2)

For genuinely hands-free operation the operator should not have to tap anything: having asked by voice, the answer should simply be read out when it lands. An agent turn can take a while, so the operator will typically have set the phone down — screen still on, app still open — and gone back to what they were doing.

**Scope boundary**: per the 2026-07-29 clarification this applies while the app is in the **foreground**. If the operator pockets the phone and the screen locks, playback stops (FR-007). The "answer arrives while the phone is in a pocket" case is deliberately deferred — see Out of Scope.

**Why this priority**: This is what makes the feature usable in the field rather than merely present. It is separated from US1 because auto-speaking is a behaviour change with real annoyance potential (speaking aloud in a meeting), so it must be operator-controlled and is therefore independently shippable behind a setting.

**Independent Test**: Enable the auto-speak setting, submit a request, set the phone down with the screen on, and confirm the answer is spoken on arrival with no interaction. Disable the setting and confirm silence.

**Acceptance Scenarios**:

1. **Given** auto-speak is enabled, **When** a turn transitions to `completed` with a non-empty answer, **Then** that answer is spoken without any operator interaction.
2. **Given** auto-speak is disabled (the default), **When** an answer arrives, **Then** nothing is spoken and the US1 manual control remains available.
3. **Given** auto-speak is enabled and an answer is already being spoken, **When** a second answer arrives, **Then** the answers are spoken one after another without overlapping or being dropped.
4. **Given** auto-speak is enabled, **When** the operator opens a historical turn from a previous session, **Then** old answers are not re-spoken on load.
5. **Given** auto-speak is enabled and the device is in silent/vibrate mode, **When** an answer arrives, **Then** it is **not** spoken, and the operator can still see that the answer arrived and was not read aloud (FR-012a, FR-014).
6. **Given** auto-speak is enabled and an answer is being spoken, **When** the app is backgrounded or the screen locks, **Then** playback stops (FR-007).
7. **Given** auto-speak is enabled on the phone and a paired Apple Watch is present, **When** an answer arrives and is auto-spoken on the phone, **Then** the watch speaks nothing — preserving `073-push-notifications-sync`'s FR-018 (FR-012b).

---

### User Story 3 - Hear a Border-pushed message (Priority: P3)

The Border pushes messages the operator did not ask for — alerts, notifications, a heads-up designated by another agent. These land in the Feed and are equally worth hearing when the operator cannot look.

**Why this priority**: Valuable but strictly additive; the Feed is a review surface rather than an interactive loop, and US1/US2 deliver the core value without it.

**Independent Test**: With a text message in the Feed, activate the speak control on that message and confirm it is audible.

**Acceptance Scenarios**:

1. **Given** a Feed message with `contentType == text`, **When** the operator activates its speak control, **Then** its content is spoken.
2. **Given** a Feed message with `contentType == image`, **When** the operator views it, **Then** no speak control is offered.

---

### Edge Cases

- **Microphone interlock (critical).** What happens if playback starts while the recogniser is listening? Spoken output would be captured as input, transcribing NetClaw's own answer back into the next request. `chat_screen.dart` already tracks `_listening` and `voice_transcription.dart` exposes `cancel()`/`finishNow()`, so the state needed for an interlock exists — the spec requires one (FR-006).
- **Domain text is hostile to naive TTS.** Answers routinely contain IP addresses, prefix lengths, MAC addresses, interface names (`GigabitEthernet0/0/1`), AS numbers, and pasted CLI/table output. A synthesiser reading `10.0.0.1/24` as "ten point zero point zero point one slash twenty-four" is tolerable; one reading a 40-line routing table verbatim is useless and cannot be interrupted fast enough to matter. See FR-008/FR-009.
- **Interruptions.** Incoming call, another app taking audio focus, alarm, navigation prompt — resolved by FR-013: yield, then stay stopped rather than resume.
- **Lifecycle.** App backgrounded, screen locked, or the screen disposed mid-utterance — resolved by FR-007: playback stops. `chat_screen.dart:58-67` already releases the mic on dispose; playback needs the equivalent.
- **Audio routing.** Bluetooth headset, wired headphones, car audio, speakerphone. Silent/vibrate is resolved by FR-012a (tap plays, auto-speak stays quiet); routing itself is left to the platform's current output selection.
- **Auto-speak while silenced.** The operator must be able to tell an answer arrived and was *not* spoken, rather than assuming the feature is broken (FR-012a + FR-014).
- **Very long answers.** Is there a ceiling, a summary, or is the whole thing read?
- **Empty/whitespace-only answer text.**
- **Rapid repeated activation** of the speak control.
- **Language mismatch** between the answer text and the installed voice.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST synthesise speech using the **device's local/on-device TTS capability**, not a network or cloud synthesis service.
- **FR-002**: The app MUST support voice playback on **both Android and iOS**. The Flutter codebase is shared and feature 071 has already ported it to iOS, so an Android-only capability would be an immediate parity regression.
- **FR-003**: Operators MUST be able to trigger playback of a completed answer's text on demand from the Chat screen.
- **FR-004**: Operators MUST be able to stop in-progress playback at any time.
- **FR-005**: The app MUST NOT offer a playback control where there is no speakable text (turns without an answer; non-text Feed content).
- **FR-006**: The app MUST NOT play synthesised audio while the microphone is open for speech recognition, so that output is never captured as input.
- **FR-007**: The app MUST stop playback when the owning screen is disposed and when the app leaves the foreground (including screen lock). Playback is a foreground-only capability in this iteration; the app MUST NOT declare an iOS background-audio mode or run an Android foreground service for playback. This mirrors the existing microphone discipline, where `chat_screen.dart:58-67` releases the mic on dispose.
- **FR-008**: The app MUST normalise answer text on the phone before synthesis so that network-operations identifiers are intelligible when heard — at minimum dotted-quad addresses, prefix lengths, and interface names must be spoken with pacing and grouping that a listener can transcribe back correctly without seeing the screen. Raw text MUST NOT be passed to the synthesiser unmodified.
- **FR-009**: The app MUST NOT read fenced-code or tabular blocks aloud. It MUST instead announce each such block's presence and size and state that it is available on screen (e.g. "routing table omitted, 40 lines, shown on screen"), then continue with the surrounding prose. Rationale: reading a 40-line table aloud is unusable and cannot be interrupted fast enough to matter, so the feature declines to do badly what it cannot do well.
- **FR-009a**: All normalisation and block-skipping MUST happen on the phone. This feature MUST NOT require any change to the Border's answer text or wire format. A Border-generated spoken summary was considered and deliberately rejected for this iteration as scope-widening; it remains a possible follow-on.
- **FR-010**: The app MUST report to the operator when playback cannot proceed (no voice/engine available, permission or platform failure) rather than failing silently. This follows the precedent set for the microphone, where a silent failure was explicitly called out as the worst outcome (`voice_transcription.dart`: *"tapped the mic and nothing whatsoever happened. Always say why."*).
- **FR-011**: Auto-speak (US2) MUST be operator-controllable via a single persisted toggle in Settings and MUST default to **off**, so no existing installation starts speaking aloud after an update.
- **FR-011a**: The app MUST NOT provide its own speech-rate or voice-selection controls, and MUST NOT override the platform's configured speech rate. Both platforms already expose a system-level TTS rate that the synthesiser honours when not overridden; the app inherits whatever the operator has already chosen there.
- **FR-012**: When multiple items are queued for playback, the app MUST speak them sequentially without overlap or loss.
- **FR-012a**: Playback audibility MUST depend on how it was triggered. An **operator-initiated** playback (US1/US3 tap) MUST be audible even when the device is in silent/vibrate mode. An **auto-spoken** answer (US2) MUST stay silent when the device is in silent/vibrate mode, surfacing only the FR-014 visual indicator. Rationale: a deliberate request for sound that produces silence looks broken, while unrequested speech from a phone the operator deliberately silenced is a trust problem.
- **FR-012b**: The phone's auto-speak (US2) MUST NOT cause the **watch** to speak. `073-push-notifications-sync`'s FR-018 requires that watch read-aloud "never trigger automatically", and the two devices share a conversation store via `WatchRelay` — so an auto-speak trigger that reached the watch through that shared path would violate that invariant from the outside. Auto-speak is a phone-local behaviour and MUST stay one.

  **Why the phone may auto-speak at all when the watch may not.** Both specs are protecting the same thing — the watch spec's stated reason for on-demand-only is "to avoid surprising or embarrassing the operator in a quiet room" — but they reach it differently, and the difference is justified by the device rather than being an oversight:

  - The **watch** is worn on the body and cannot be set down or silenced independently, so a blanket prohibition is the only reliable guarantee. It has no opt-in.
  - The **phone** reaches the same guarantee through two mechanisms the watch lacks: auto-speak is **off by default and opt-in** (FR-011), and even when enabled it is **suppressed entirely in silent/vibrate mode** (FR-012a). An operator who has not opted in, or who has silenced the device, gets exactly the watch's behaviour.

  This divergence is therefore deliberate. If it is ever judged to be inconsistency rather than device-appropriate design, the correct resolution is to drop US2 from this spec — not to relax the watch's FR-018.
- **FR-013**: The app MUST yield the audio session to higher-priority audio (calls, alarms, navigation). On regaining audio focus it MUST **stay stopped** rather than resume or restart, leaving the operator to re-trigger playback; automatic resumption after an interruption is the "surprising" behaviour this requirement exists to prevent. The partially-spoken item MUST remain re-triggerable from the UI.
- **FR-014**: Playback state MUST be visible in the UI, so the operator can tell what is speaking and that a control did something.

### Privacy Requirements

- **FR-015**: Synthesis MUST NOT transmit message text off the device. This is a **continuation of an existing commitment, not a new one**: `voice_transcription.dart` sets on-device recognition specifically because *"Spoken requests here carry hostnames, interface IDs and IP addresses, so the claim has to hold."* **Answers carry the same class of data and generally more of it** — sending them to a cloud voice would silently reopen the exact hole the input path was hardened against.
- **FR-016**: Where the platform can silently fall back to a network voice, the app MUST prefer a local voice and MUST surface the situation rather than degrading quietly. The input path documents this precise hazard — a plugin that "constructs the ordinary recogniser anyway. Silent, and nothing in its API reports which one was chosen" — and the same trap must be assumed to exist on the synthesis side until proven otherwise. **Planning must verify what on-device guarantee each platform actually offers; do not assume parity with the STT path's `EXTRA_PREFER_OFFLINE` enforcement.**
- **FR-017**: The app MUST NOT persist synthesised audio to disk.

### Key Entities

- **Speakable item**: a unit of text offered for playback, derived from either a `ConversationTurn.answerText` or a text `EdgeMessage.content`. Carries the text, a stable identity (so the UI can show *which* item is speaking), and its origin surface.
- **Playback session**: the app's single logical speaking channel — at most one utterance audible at a time, with a queue behind it and a well-defined interaction with the microphone.
- **Voice playback preference**: a single operator-set, persisted, per-installation boolean — the US2 auto-speak toggle, default off. Rate, pitch and voice are deliberately **not** app-level state; they are inherited from the platform (FR-011a).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can complete an entire ask→hear cycle — submit a request by voice and understand the answer — without reading the screen.
- **SC-002**: Playback begins within a short, consistent delay of activation, fast enough that the control feels responsive rather than ambiguous.
- **SC-003**: Playback stops promptly when the operator asks it to, on the first activation.
- **SC-004**: No message text leaves the device for synthesis, verifiable by observing that playback works with all network interfaces disabled.
- **SC-005**: Synthesised audio is never transcribed back into a subsequent request (zero self-capture across repeated voice ask→hear→ask cycles).
- **SC-006**: Answers containing IP addresses and interface names are intelligible to an operator hearing them for the first time, without needing the screen to disambiguate.
- **SC-007**: Behaviour is equivalent on Android and iOS for every acceptance scenario above.
- **SC-008**: An installation that does not enable auto-speak behaves exactly as it did before this feature.
- **SC-009**: An answer containing a routing table is spoken in bounded time proportional to its prose, not its table length — a table-heavy answer never produces minutes of unusable audio.
- **SC-010**: With auto-speak enabled and the phone silenced, no audio is produced across repeated answer arrivals, and the operator can still tell answers arrived.
- **SC-011**: The watch's existing on-demand read-aloud behaviour is unchanged by this feature — it still speaks only on an explicit tap, and never as a side effect of phone auto-speak.

## Out of Scope

- **Playback of `MessageContentType.voice` audio.** Confirmed out of scope in clarification. Playing Border-supplied base64 audio is *media playback*, not local synthesis — a different dependency and its own unanswered questions (codec, streaming vs download, caching, retention, which would collide with FR-017). Decisive factor: **the `voice` content type has no producer.** The daemon validates it at `bgp-daemon-v2.py:725`, but the only occurrence in the tree is a test fixture at `test_edge_push.py:156` (`"ZmFrZSB2b2ljZSBieXRlcw=="` — "fake voice bytes"), and the push-notification fallback handles `text` only (`push_notify.py:79`). The inert `Chip` therefore stays as-is; implementing a player for content nothing sends would be speculative. Worth its own spec if a producer ever appears.
- **Background / locked-screen playback.** Settled in clarification: playback is foreground-only here (FR-007). Continuing through backgrounding or screen lock would deliver US2's "answer arrives while the phone is in a pocket" case, but costs an iOS `UIBackgroundModes: audio` entitlement and an Android foreground service with a persistent notification and declared service type — app-review and battery consequences that should be taken on deliberately, once the field workflow has been validated, not speculatively. **This is the most likely follow-on to this feature.**
- **Voice playback on the Apple Watch — already implemented, not a follow-on.** Delivered by `073-push-notifications-sync` (US4/FR-017–FR-019, `SpeechPlayback.swift`) and merged in `5e9ecc1`. This spec does not touch it, must not regress it, and must not reach it via the shared conversation store (FR-012b). An earlier draft of this document listed watch playback as an unimplemented natural follow-on; that was incorrect and is corrected here.
- **Server/Border-side synthesis**, including the existing Twilio voice path (feature 043). This feature is strictly on-device.
- **Wake-word or fully conversational hands-free operation.**
- **Changes to speech-to-text.** The in-flight `voice_transcription.dart` work on `main` is a separate concern; this feature consumes the existing input path unchanged.

## Assumptions

- Operators run OS versions with a usable built-in TTS engine and at least one installed local voice. Absence is handled per FR-010 rather than by bundling a voice.
- English is the only language that must be supported for v1.
- The existing `ConversationStore` and `MessageFeedStore` are the sources of speakable text; **no new Border-side protocol work is required** (settled in clarification — see FR-009a).
- The Border's answer text is unchanged by this feature; any speech-oriented normalisation happens on the phone.
- No new push, enrollment, or federation behaviour is involved.

## Dependencies

- A Flutter TTS capability wrapping Android `TextToSpeech` and iOS `AVSpeechSynthesizer`. No such package is currently in `pubspec.yaml`; selecting one (and confirming its on-device guarantees per FR-016) is a Phase 0 research task.
- Existing: `ConversationStore`/`ConversationTurn` (067), `MessageFeedStore`/`EdgeMessage` (066), `VoiceTranscription` (067, for the FR-006 interlock), `chat_screen.dart`, `feed_screen.dart`, `settings_screen.dart` (for FR-011).
- **Must not regress**: `073-push-notifications-sync`'s watch read-aloud (`SpeechPlayback.swift`) and the `WatchRelay` path that feeds it (FR-012b, SC-011).

## Open Questions for Clarification

**None blocking.** All five questions raised in the initial draft were resolved in the 2026-07-29 clarification session:

| Question | Resolved by |
|---|---|
| Normalisation depth | FR-008 |
| Long machine output | FR-009, FR-009a |
| Background / locked-screen playback | FR-007, Out of Scope |
| Scope of `voice` audio playback | Out of Scope (no producer exists) |
| Settings surface | FR-011, FR-011a |
| Silent/vibrate mode | FR-012a |
| Audio-focus regain behaviour | FR-013 (resolved by decision, not asked) |
| Auto-speak vs the watch's never-automatic rule | FR-012b (raised after the session, on discovering the merged watch implementation) |

**Accepted 2026-07-29:** the phone/watch auto-speak divergence documented in FR-012b is confirmed as device-appropriate design, not an inconsistency. US2 stands. The watch's `073-push-notifications-sync` FR-018 prohibition remains untouched, and FR-012b's guard against phone auto-speak reaching the watch is binding.

**Renumbered 2026-07-29:** this spec moved from `073` to `074` (directory and branch), resolving the prefix collision that was breaking every speckit command.

Deferred to planning (Phase 0 research, not spec-level ambiguity):

- **Which TTS package**, and what on-device guarantee each platform actually provides (FR-016). The STT path's `EXTRA_PREFER_OFFLINE` enforcement must not be assumed to have a synthesis equivalent — this needs verifying against current platform behaviour before FR-001/FR-015 can be called satisfied.
- **Exact normalisation rules** for identifier classes beyond dotted-quad, prefix length and interface name (FR-008) — the requirement fixes the intent and the acceptance bar; the specific transformations are an implementation detail with test coverage.
- **Precise latency target** for SC-002.

Ready for `/speckit.plan`.
