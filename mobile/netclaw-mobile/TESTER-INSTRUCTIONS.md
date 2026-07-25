# NetClaw Mobile — Android tester instructions

Copy the **"Send this to your tester"** section below verbatim. Do the
operator steps first — the tester can't do anything without the QR.

---

## Operator steps (you, before sending anything)

**1. Confirm the edge listener is up and reachable.**

```bash
journalctl --user -u netclaw-mesh.service -n 50 --no-pager | grep -i "Edge"
# → Edge (NetClaw Mobile) WS listener on 0.0.0.0:8443 (risk=johns-risk)
```

Your tester will be on their own network or cellular, so port 8443 must be
reachable from the public internet — not just your LAN. Verify from outside
before blaming the app.

**2. Issue a fresh single-use token, labelled for that person.**

```bash
./scripts/netclaw risk token --edge <their-name>-android
```

Screenshot the QR block it prints. Do **not** reuse a token from an earlier
run — they are single-use, and any token that has been pasted into a chat log
or terminal transcript should be considered spent.

**3. Send them the APK and the QR** (see the handout below).

**4. After they enroll, confirm the device is really theirs:**

```bash
./scripts/netclaw risk members
```

Check the label and key fingerprint before the device is used for anything
real. Trust-on-first-use means whoever claims the token first wins the
identity — this is the step that catches a wrong claim.

**5. When testing is done, or immediately if the phone is lost:**

```bash
./scripts/netclaw risk remove <member_id>
```

Revocation is server-side; you don't need the phone back.

> **The APK is signed with the Android debug key.** That's fine for sideloading
> and expected at this stage, but it is not a Play-uploadable artifact and the
> tester's phone will warn them it's from an unknown developer. See
> `PLAY-STORE-ROADMAP.md`.

---

## Send this to your tester

> **Testing NetClaw Mobile — about 5 minutes**
>
> This is an early Android build of NetClaw Mobile. It turns your phone into a
> secure remote for my NetClaw network-automation agent — you ask it a question
> in plain English, it does the work on my side and sends the answer back.
>
> You'll need the APK file and the QR code image I sent alongside this.
>
> **1. Install the app**
>
> - Tap the `app-release.apk` file I sent you.
> - Android will say installs from this source aren't allowed — tap
>   **Settings**, turn on **Allow from this source**, then go back and tap
>   **Install**.
> - You may get a "scan app / unsafe app blocked" warning from Play Protect.
>   This is expected for an app that isn't on the Play Store yet — choose
>   **Install anyway** / **More details → Install anyway**.
> - Open **NetClaw** from your app drawer.
>
> **2. Enroll it against my server**
>
> The app opens on a screen with a **Scan Border QR Code** button.
>
> - Tap it and allow camera access when asked.
> - Point the camera at the QR code image I sent. Displaying it full-screen on
>   a computer monitor works best.
>
> If the camera won't focus or the scan doesn't catch, tap **"Can't scan? Enter
> manually"** and type in the three values I sent with the QR (Border domain,
> Port, Enrollment token). That does exactly the same thing.
>
> It should connect within a few seconds and take you to the main screen with
> tabs along the bottom: **Chat**, **Feed**, **Approvals**, **Settings**.
>
> **3. Try it**
>
> On the **Chat** tab, send:
>
> ```
> Check the CML lab R1 interfaces and report back
> ```
>
> It takes about **2 minutes** — the request goes to my Border, which farms the
> work out to the lab tooling and sends the answer back. You'll see it working
> while it runs. You should get a table of interfaces and their status.
>
> Then try one of your own, anything about the network.
>
> **4. Tell me**
>
> - Did the install and QR scan work, or did you have to type it manually?
> - Did the answer come back? Roughly how long?
> - Anything confusing, ugly, or broken — including wording and layout.
> - Phone model and Android version.
>
> **A few things to know**
>
> - The QR contains a **single-use token**. It only works once, so don't share
>   it — if the install fails partway, tell me and I'll issue a new one.
> - The app can only ask my agent questions. It has no access to your phone's
>   files, contacts, or anything else, and it can't be used to reach anything
>   other than my server.
> - Push notifications aren't wired up yet, so answers only arrive while the
>   app is open.
> - I can cut this phone off from my end at any time — just say when you're
>   done and I'll revoke it.

---

## Known rough edges (don't be surprised when they're reported)

| Behavior | Status |
|---|---|
| Play Protect warns on install | Expected — unsigned-for-Play debug key |
| No push notifications | Firebase not configured; `_tryRegisterPush()` fails silently by design |
| Tapping a notification doesn't deep-link | Wired but inert until Firebase exists |
| Biometric approval untested on real hardware | Never exercised outside an emulator without enrolled biometrics |
| Camera capture untested on real hardware | Emulator only produced a synthetic test pattern |
| Voice input untested on real hardware | Never exercised against a real microphone |

A real device exercising biometrics, camera, and voice is the single most
valuable thing this tester can give you — those are the three features with no
real-hardware verification at all.
