# Spec — Dark Mode for NetClaw Mobile

**Status:** Draft for review
**Author:** NetClaw Border (`as65001-4.4.4.4`)
**Date:** 2026-07-27
**Target:** `netclaw_mobile` v1.0.0+1 — Flutter, Dart SDK ^3.12.2, Material 3
**Codebase surveyed:** 28 Dart files / 3,533 LOC in `lib/`, 24 unit tests + 1 integration test

---

## 1. Why this is cheap

The app is unusually well positioned for this. Total colour/theme references
across the entire `lib/` tree: **20**. Of those, **6 already resolve through
`Theme.of(context)`** and need no change at all.

That leaves **14 hardcoded colour references in 7 files** — the complete scope
of the visual work. There is no design-token layer to build, no stylesheet
refactor, no third-party theming dependency to add. Material 3 is already on
(`useMaterial3` is default-true in Flutter 3.x when `ColorScheme` is supplied).

Current theme, `lib/main.dart:43`:

```dart
theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFE65733))),
```

One seed colour — the claw-mark orange — and no `darkTheme`, no `themeMode`.
Because `ColorScheme.fromSeed` generates a full tonal palette from that seed,
the dark palette comes essentially free by passing
`brightness: Brightness.dark`. Brand identity is preserved automatically.

### Already correct (do not touch)

| Location | Reference |
|---|---|
| `feed_screen.dart:94` | `Theme.of(context).colorScheme` |
| `feed_screen.dart:111` | `Theme.of(context).textTheme.labelSmall` |
| `empty_state.dart:20` | `Theme.of(context).textTheme.bodyMedium` |
| `chat_screen.dart:270` | `Theme.of(context).colorScheme.error` |

These are the pattern to copy.

---

## 2. Scope

### In scope
- A dark `ColorScheme` derived from the existing brand seed.
- User-selectable theme mode: **System / Light / Dark**, persisted across launches.
- Replace all 14 hardcoded colours with scheme-derived equivalents.
- Android native launch-theme correctness (the splash currently forces light).
- Tests covering palette selection, persistence, and contrast.

### Out of scope
- Any redesign, new layout, or restyling beyond light/dark parity.
- Per-screen theme overrides or user-custom accent colours.
- True-black / OLED power-saving variant (note as possible follow-up).
- iOS native launch-screen darkening (see §6 — deliberately deferred).

---

## 3. Design

### 3.1 Theme definitions — new file `lib/theme/app_theme.dart`

Introduce a single source of truth. The seed colour moves here from
`main.dart` and stops being an inline literal.

```dart
import 'package:flutter/material.dart';

/// The claw mark's own orange (assets/icon/icon.png) — brand, not a
/// Material default. Single source of truth for both palettes.
const brandSeed = Color(0xFFE65733);

ThemeData lightTheme() => ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: brandSeed,
        brightness: Brightness.light,
      ),
    );

ThemeData darkTheme() => ThemeData(
      colorScheme: ColorScheme.fromSeed(
        seedColor: brandSeed,
        brightness: Brightness.dark,
      ),
    );
```

### 3.2 Wiring `MaterialApp`

`main.dart` gains `darkTheme` and a reactive `themeMode`. `NetClawMobileApp`
must become a `StatefulWidget` (currently `StatelessWidget`) — or wrap the
`MaterialApp` in a `ValueListenableBuilder` over the store, which is lighter
and avoids touching the widget's class:

```dart
return ValueListenableBuilder<ThemeMode>(
  valueListenable: themeModeStore.mode,
  builder: (context, mode, _) => MaterialApp(
    title: 'NetClaw Mobile',
    theme: lightTheme(),
    darkTheme: darkTheme(),
    themeMode: mode,
    home: const EnrollmentGate(),
  ),
);
```

`ThemeMode.system` is the default, so a fresh install follows the OS
immediately with no user action.

### 3.3 Persistence — new file `lib/ncfed/theme_mode_store.dart`

**Follow the existing storage convention, do not invent a new one.** The app
already persists via `path_provider` + a documents-directory-backed store
(`EnrollmentStore`, `ConversationStore`, `MessageFeedStore` all take a
`Directory`). `shared_preferences` is *not* currently a dependency and should
not be added for one enum — it would be the only mechanism of its kind in the
codebase.

```dart
class ThemeModeStore {
  final Directory dir;
  final ValueNotifier<ThemeMode> mode = ValueNotifier(ThemeMode.system);

  ThemeModeStore(this.dir);

  File get _file => File('${dir.path}/theme_mode');

  Future<void> load() async { /* read; tolerate missing/corrupt → system */ }
  Future<void> set(ThemeMode m) async { /* write + notify */ }
}
```

Note `flutter_secure_storage` is also present but is for credentials; a UI
preference does not belong there.

**Load-order constraint:** the store must be read *before* the first frame, or
the app flashes light then repaints dark on cold start. `main()` is currently
synchronous:

```dart
void main() {
  runApp(const NetClawMobileApp());
}
```

It becomes:

```dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final store = ThemeModeStore(await getApplicationDocumentsDirectory());
  await store.load();
  runApp(NetClawMobileApp(themeModeStore: store));
}
```

`WidgetsFlutterBinding.ensureInitialized()` is mandatory here — `path_provider`
uses a platform channel and will throw without it. Keep the store injectable so
tests never touch the real channel, matching the documented pattern already used
by `EnrollmentGate.documentsDirectory`, `VoiceTranscription`, and
`ReconnectSupervisor`.

### 3.4 Settings UI

Add to `settings_screen.dart`, below the existing `Divider()` and the push-status
`ListTile`. `SettingsScreen` already takes constructor-injected dependencies, so
add `ThemeModeStore` the same way — no global lookup, no singleton.

```
Appearance
  ○ System   ● Light   ○ Dark
```

A three-value `SegmentedButton<ThemeMode>` fits Material 3 and the screen's
existing `SwitchListTile` idiom. Label it **Appearance**, not "Dark Mode" —
the control has three states, and "Dark Mode: System" reads as a contradiction.

---

## 4. The 14 hardcoded colours

Grouped by fix. **`Colors.red.shade50` / `.shade900` and `Colors.black87` are
the real problems** — they are near-invisible or garish on a dark surface.

### Group A — Error banners → `colorScheme.errorContainer` / `onErrorContainer`

Identical duplicated block in two files:

| File:line | Current | Replace with |
|---|---|---|
| `settings_screen.dart:76` | `color: Colors.red.shade50` | `scheme.errorContainer` |
| `settings_screen.dart:78` | `TextStyle(color: Colors.red.shade900)` | `TextStyle(color: scheme.onErrorContainer)` |
| `approvals_screen.dart:63` | `color: Colors.red.shade50` | `scheme.errorContainer` |
| `approvals_screen.dart:65` | `TextStyle(color: Colors.red.shade900)` | `TextStyle(color: scheme.onErrorContainer)` |

These two banners are byte-identical. **Extract a shared `ErrorBanner` widget**
(`lib/screens/error_banner.dart`) rather than fixing the same code twice —
`empty_state.dart` already establishes the precedent for small shared
presentational widgets.

### Group B — Camera/scanner overlays → keep literal, justify in comment

| File:line | Current | Action |
|---|---|---|
| `device_scan_screen.dart:66` | `Colors.black87` | **Keep** |
| `device_scan_screen.dart:70` | `Colors.white` | **Keep** |
| `enrollment_screen.dart:89` | `backgroundColor: Colors.black54` | **Keep** |
| `enrollment_screen.dart:91` | `Colors.white` | **Keep** |
| `enrollment_screen.dart:101` | `Colors.black87` | **Keep** |
| `enrollment_screen.dart:105` | `Colors.white` | **Keep** |
| `enrollment_screen.dart:112` | `Colors.black45` | **Keep** |

**This is a deliberate exception and the most important judgement in the spec.**
These sit on top of a live camera preview (`mobile_scanner` QR view). The
backdrop is whatever the camera sees, not an app surface — so scheme colours
are *wrong* here. A scrim must stay dark and its text white in both modes to
remain legible against arbitrary camera input.

**Action:** leave the values, add a comment explaining why they are exempt, so
a future contributor doesn't "fix" them and break legibility. Consider naming
them `kCameraScrim` / `kOnCameraScrim` constants in `app_theme.dart` to make the
intent explicit and greppable.

### Group C — Inline text colours → scheme

| File:line | Current | Replace with |
|---|---|---|
| `manual_enrollment_screen.dart:163` | `TextStyle(color: Colors.red)` | `scheme.error` |
| `chat_screen.dart:374` | `TextStyle(color: Colors.red)` | `scheme.error` |
| `chat_screen.dart:347` | `TextStyle(color: Colors.grey)` — `[Photo unavailable]` | `scheme.onSurfaceVariant` |
| `chat_screen.dart:364` | `TextStyle(color: Colors.grey)` — `Cancelled` | `scheme.onSurfaceVariant` |

`Colors.grey` is the classic dark-mode failure — it has no relationship to the
surface it sits on. `onSurfaceVariant` is the M3 role for de-emphasised text and
adapts correctly.

Note `manual_enrollment_screen.dart:163` is *not* a camera overlay despite
living near the enrollment flow — it is a normal form field error. Verify during
implementation that it renders on a standard `Scaffold` surface, not over a
preview.

---

## 5. Testing

The repo has 24 unit tests and a real integration test; match that standard.

### New: `test/theme_mode_store_test.dart`
- Defaults to `ThemeMode.system` when no file exists.
- Round-trips each of the three values.
- Corrupt/garbage file contents fall back to `system` without throwing.
- Injected temp `Directory`; no platform channel.

### New: `test/app_theme_test.dart`
- `lightTheme().colorScheme.brightness == Brightness.light`; dark likewise.
- Both palettes derive from `brandSeed` — assert `primary` is non-default and
  the two schemes differ.
- **Contrast assertions** on the pairs that changed: `errorContainer` /
  `onErrorContainer` and `surface` / `onSurfaceVariant` must clear WCAG AA
  (4.5:1 body text) in *both* palettes. `ColorScheme.fromSeed` generally
  guarantees this, but assert it — this is the regression that would otherwise
  ship silently.

### Extend: `test/widget_test.dart`, `chat_screen_test.dart`, `settings_screen`
- Pump each screen under `darkTheme()` and assert no `Colors.grey`,
  `Colors.red.shade50`, or `Colors.black87` survives outside the Group B
  camera files.
- Golden tests are tempting but add binary churn; assert on resolved colour
  values instead unless the team already wants goldens.

### Manual QA matrix
Every screen — Enrollment, Manual enrollment, Device scan, Chat, Feed,
Approvals, Settings, plus the `reconnectFailed` state and the revocation
`SnackBar` — in **System / Light / Dark**, and an **in-flight OS toggle** while
the app is foregrounded (verify no stale colours and no rebuild crash).

---

## 6. Native platform work

### Android — a real bug already present
`values-night/styles.xml` **already exists** and correctly parents
`Theme.Black.NoTitleBar`, so the OS dark launch theme is wired up. But both
variants set:

```xml
<item name="android:forceDarkAllowed">false</item>
```

and `flutter_native_splash` in `pubspec.yaml` hardcodes light only:

```yaml
flutter_native_splash:
  color: "#FFFFFF"
  android_12:
    color: "#FFFFFF"
```

**Consequence:** on a dark-mode device the splash flashes **white** before the
Flutter UI paints dark. Add the `flutter_native_splash` `darkColor` /
`android_12.darkColor` keys and re-run `dart run flutter_native_splash:create`.
`forceDarkAllowed: false` is correct and should stay — we are supplying a real
dark theme, not asking the OS to auto-invert.

Also note `colors.xml` defines only `ic_launcher_background: #FFFFFF`, and
`pubspec.yaml` sets `adaptive_icon_background: "#FFFFFF"`. Launcher icons
don't follow app theme, so this is acceptable — flagged only so it isn't
mistaken for an oversight.

### iOS — deferred, with reason
`ios/Runner/Info.plist` exists but I did not inspect `LaunchScreen.storyboard`
or confirm whether `UIUserInterfaceStyle` is pinned. Flutter's Dart-side theming
works regardless; the risk is limited to a light launch-screen flash mirroring
the Android issue. **Do not assume it is fine** — check for a
`UIUserInterfaceStyle` key forcing `Light` and add a dark storyboard variant if
the flash reproduces on device. Feature `071-ios-mobile-port` exists in
`~/netclaw/specs/`, so the iOS surface may still be in flux; coordinate rather
than patching blind.

---

## 7. Effort & sequencing

| # | Task | Effort |
|---|---|---|
| 1 | `app_theme.dart` — seed + both palettes | 30 min |
| 2 | `ThemeModeStore` + async `main()` | 1–1.5 h |
| 3 | `MaterialApp` wiring via `ValueListenableBuilder` | 30 min |
| 4 | Settings **Appearance** segmented control | 1 h |
| 5 | Extract shared `ErrorBanner`, fix Group A | 45 min |
| 6 | Group C inline colours (4 refs) | 30 min |
| 7 | Group B comments / named scrim constants | 20 min |
| 8 | Unit tests (store, theme, contrast) | 1.5–2 h |
| 9 | Widget-test updates | 1 h |
| 10 | Android splash `darkColor` + regen | 30 min |
| 11 | iOS launch-screen check | 30 min–unknown |
| 12 | Manual QA across 8 screens × 3 modes | 1 h |

**Total ≈ 9–11 hours**, ~1.5 days including review. Item 11 is the only
open-ended one.

Suggested order: **1 → 3 → 6 → 5 → 2 → 4 → 8 → 9 → 10 → 11 → 12.** Doing the
palette and the visual fixes first (1, 3, 6, 5) yields a working dark mode that
follows the OS with no persistence layer at all — a demoable checkpoint, and
independently shippable if persistence slips.

---

## 8. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Camera overlays "fixed" to scheme colours → unreadable QR scanner | **High** | §4 Group B comments + named constants; call out explicitly in review |
| Light-flash on cold start (async store read) | Medium | `await store.load()` before `runApp`; verify on a real dark device |
| Android splash stays white in dark mode | Medium | `darkColor` keys + regenerate; already a latent bug |
| `main()` becoming async breaks `integration_test/enrollment_and_ask_test.dart` | Medium | It drives `EnrollmentGate` directly; verify, and keep the store injectable |
| Contrast regression on `onSurfaceVariant` for de-emphasised text | Low-Med | Assert WCAG AA in `app_theme_test.dart` |
| iOS launch screen pinned to light | Unknown | Inspect before estimating; coordinate with spec 071 |

---

## 9. Open questions

1. **True-black OLED variant** — worth a fourth mode later, or scope creep?
2. **Goldens** — does the team want golden tests, or are resolved-colour
   assertions sufficient? (Recommendation: the latter; less binary churn.)
3. **iOS timing** — should this land before or after `071-ios-mobile-port`?
4. **`shared_preferences`** — I deliberately avoided adding it. Confirm the team
   prefers the existing `path_provider` convention over introducing a second
   persistence mechanism.

---

## 10. Verification note

Everything above was read from the live working tree at
`/home/johncapobianco/netclaw/mobile/netclaw-mobile` on 2026-07-27, not
inferred: `pubspec.yaml`, all 28 files in `lib/`, the full text of `main.dart`
and `settings_screen.dart`, `android/app/src/main/res/values{,-night}/styles.xml`,
`colors.xml`, and the `test/` + `integration_test/` listings. The 14-reference
count is the exact `grep` result, enumerated in §4.

**Not verified:** `ios/Runner/LaunchScreen.storyboard` and the
`UIUserInterfaceStyle` key (§6), and whether `manual_enrollment_screen.dart:163`
renders over a camera preview (§4 Group C). Both are flagged inline rather than
assumed.
