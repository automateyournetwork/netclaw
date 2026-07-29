# Visual assets needed for NetClaw Mobile

Right now both platforms ship the stock Flutter template icon
(`android/app/src/main/res/mipmap-*/ic_launcher.png`, `ios/Runner/Assets.xcassets/
AppIcon.appiconset/*`) and the app's `MaterialApp` theme is seeded with an arbitrary
`Colors.deepPurple` (`lib/main.dart`) — neither matches NetClaw's actual brand. Every
*functional* icon in the app (chat/mic/camera/send/settings/approve/deny/QR-scan) is a
plain Material icon and needs no custom art at all; the only things genuinely missing
are the app's own identity marks.

## Existing brand references (for consistency — don't invent a third style)

NetClaw already has two visual languages in this repo, neither of which is app-icon-ready
as-is:

1. **The mascot** — `netclaw.jpg` (repo root) / `ui/netclaw-visual/logos/netclaw.png`: a
   photorealistic orange/red lobster gripping a bundle of colorful network patch cables,
   wearing a "CCIE AI0001 AGENT" badge, in a server-room aisle. This is the literal
   "NetClaw = claw + network" pun made visual. Too detailed/busy to read at 48×48 — needs
   simplifying into a flat mark, not reusing directly.
2. **The HUD** — `ui/netclaw-visual/logos/netclawvisualhud.png`: a dark navy sci-fi
   dashboard with cyan/teal glowing nodes and monospace labels. A completely different,
   more "technical console" feel from the mascot.

**Recommendation**: use the mascot's claw motif (it's the actual brand pun) but redraw it
as a simplified, flat-color icon mark — not the photorealistic version, and not the HUD's
cyan console aesthetic (that's a desktop-dashboard identity, not a mobile-app one). Pick
ONE accent color family and use it everywhere below and in `main.dart`'s
`ColorScheme.fromSeed` (currently arbitrary `Colors.deepPurple`) — either the mascot's
orange/red (~`#D2461E`), or a cooler neutral if orange/red feels too "food" for an
enterprise tool. That color decision should happen once, before generating anything below,
so every asset matches.

## Required assets

### 1. Master icon mark (do this first — everything else derives from it)

One square artwork, simple enough to read at 48×48px, that becomes every launcher icon.

> A flat, minimal vector-style icon of a single lobster/crab claw (pincer) gripping an
> Ethernet/network connector or a small network node (a dot with a few connecting lines),
> centered, bold silhouette, 2-3 colors maximum, no photorealism, no gradients, no text,
> no badge — must stay legible shrunk to the size of a thumbnail. Solid [ORANGE-RED #D2461E
> or your chosen brand color] claw on a transparent background. Square canvas, generous
> padding on all sides (the subject should fill roughly the center 70% of the frame).

Export as a single **1024×1024 PNG, transparent background** — this is the only file you
actually need to draw by hand or generate; everything else is produced FROM it.

### 2. Wire it up with `flutter_launcher_icons` (no manual per-size exports needed)

Once you have the 1024×1024 master PNG, don't hand-place it into every `mipmap-*`/
`Assets.xcassets` size yourself — add the generator and let it do that:

```yaml
# pubspec.yaml
dev_dependencies:
  flutter_launcher_icons: ^0.14.0

flutter_launcher_icons:
  android: true
  ios: true
  image_path: "assets/icon/icon.png"          # your 1024x1024 master
  min_sdk_android: 21
  adaptive_icon_background: "#0B1220"          # or a flat brand color — Android 8+ adaptive icon plate
  adaptive_icon_foreground: "assets/icon/icon_foreground.png"  # see #3 below
```

Then: `flutter pub get && flutter pub run flutter_launcher_icons`. This regenerates every
Android `mipmap-*` density AND every iOS `AppIcon.appiconset` size (including the 1024×1024
App Store icon, which — unlike Android — must NOT have transparency; the tool flattens it
onto a background automatically).

### 3. Android adaptive icon foreground layer (only if you want a proper adaptive icon)

Same claw mark as #1, but with NO background fill at all (fully transparent) and slightly
more padding — Android's adaptive-icon system crops/masks this layer into circles, squircles,
etc. per launcher, so anything near the edges gets clipped on some devices.

> The same claw-and-network-node mark from the master icon prompt above, isolated on a
> fully transparent background, with extra margin — at least 20% empty padding on every
> side — since the outer edge may be cropped into a circle or rounded square by the OS.

### 4. Splash screen (optional, but the app currently shows a blank white flash on cold start)

```yaml
dev_dependencies:
  flutter_native_splash: ^2.4.0

flutter_native_splash:
  color: "#0B1220"                     # brand background
  image: assets/icon/icon_splash.png   # simplified mark, centered
  android_12:
    color: "#0B1220"
    image: assets/icon/icon_splash.png
```

> The claw mark from #1, but simplified further to a single flat color (white or your
> brand accent) with no secondary details — splash screens render for a fraction of a
> second, fine detail won't register. Centered, transparent background, generous padding
> (Android 12+'s splash system scales it into a fixed-size circle).

Then: `flutter pub run flutter_native_splash:create`.

### 5. Push-notification small icon (needed once Firebase/APNs credentials exist — see
   the "serious outstanding" note in the main README about push registration not being
   wired yet)

Android's status bar can ONLY render a flat white silhouette with transparency — no
color, no gradient, or it'll render as a white blob:

> The same claw mark, redrawn as a single-color pure white silhouette (alpha channel
> only — white where visible, transparent everywhere else), no outline, no shading,
> simplified enough that the pincer shape is still recognizable at 24×24px.

Save as `android/app/src/main/res/drawable/ic_notification.png` (and density variants),
referenced from the FCM payload's `notification.android_channel_id`/`icon` field once
push is actually wired up.

### 6. Optional polish — empty-state illustrations

Not required (both screens already show clear plain-text empty states), but if you want
something friendlier than text:

- **Feed screen, no messages yet**: a small illustration of the claw mark reaching toward
  an empty speech bubble or an inbox tray, muted/monochrome so it doesn't compete with the
  brand color used for actual content.
- **Approvals screen, no pending approvals**: the claw mark next to a checkmark or a
  "clear" shield shape — communicates "nothing needs you right now," not "broken."

Both should be simple line-art/flat-color, sized around 120-160px square, since they sit
inside a `Center(child: Text(...))` today and would just replace/accompany that text.

## What does NOT need custom art

Every interactive control already uses a stock Material icon and should stay that way —
custom art here would just fight Android's/iOS's own design language for no benefit:
chat (`Icons.chat`), voice (`Icons.mic`), camera (`Icons.camera_alt`), send (`Icons.send`),
QR scan (`Icons.qr_code_scanner`), approvals (`Icons.verified_user`), settings
(`Icons.settings`), feed (`Icons.notifications`).
