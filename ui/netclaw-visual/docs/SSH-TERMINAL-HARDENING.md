# HUD SSH terminal — device-side hardening

Read this before enabling the terminal panel against production switches.

Everything here is **yours to apply**. Per `network-change-safety`, I don't push
config to these devices. Each step below is additive and reversible; none of it
touches the Vlan3 SVI, its VRF, or any route.

Verified against `HomeSwitch01` (`show run`, WS-C3850-48P, IOS-XE 16.12) on
2026-07-29.

---

## Why the app-layer guard is not the weak link

The HUD terminal will ship with an input filter that blocks config mode. It is
worth having, but on these switches it is **not** a security boundary, because
the devices already accept far weaker access from anywhere on VLAN 3:

| Finding | Config line | Consequence |
|---|---|---|
| Cleartext, guessable privilege-15 creds | `username cisco privilege 15 password 0 cisco`<br>`username admin privilege 15 password 0 admin` | Anyone reaching `192.168.3.2` gets full config with `admin`/`admin`. No brute force needed. |
| SNMP read-write, weak community | `snmp-server community private RW` | Full config read **and write** over SNMP, bypassing vty entirely. Also `@Vitron123 RO`, `public RO`. |
| vty sessions never expire | `line vty 0 4` → `exec-timeout 0 0` | An abandoned session stays authenticated indefinitely. |
| No enable secret | (absent) | Nothing gates privilege escalation locally. See the caveat in step 2. |
| Passwords stored unencrypted | `password 0 …`, no `service password-encryption` | Anyone with read access to the config gets working credentials. |

So: locking down the HUD terminal while `admin`/`admin` works from the whole
management VLAN buys very little. **Fix the credentials first** — that is the
change with real impact. The terminal guard is defence in depth on top.

Priority order I'd suggest:

1. Replace the two privilege-15 cleartext accounts with `secret`-hashed ones and
   strong passwords.
2. Remove or rename `private RW` (and ideally drop RW SNMP entirely — the
   observability stack only needs RO).
3. Set a sane `exec-timeout` on the vty lines.
4. Then the read-only account below, for the terminal.

---

## Step 1 — read-only account for the terminal (additive, safe)

```
! HUD terminal account. privilege 1 = show/ping/traceroute only.
! Uses `secret` (type-9 hash), not `password 0`.
username hud-ro privilege 1 secret <STRONG-PASSWORD-HERE>
```

Nothing else changes. Existing `admin` / `cisco` access is untouched, so there
is no lockout risk. Reversible with `no username hud-ro`.

Then point the HUD at it (host `.env`, not the device):

```
HUD_SSH_USERNAME=hud-ro
HUD_SSH_PASSWORD=<STRONG-PASSWORD-HERE>
```

If these are unset the terminal falls back to `NETCLAW_USERNAME` /
`NETCLAW_PASSWORD` — which today is a **privilege 15** account, so the terminal
would have full config rights. Set them.

## Step 2 — verify the privilege actually sticks

This matters, and it is why I'm not claiming step 1 is sufficient on its own.
The config has:

```
line vty 5 15
 privilege level 15      <-- auto-elevates whoever lands on these lines
 login local
```

Lines 5–15 raise the session to privilege 15. Whether the `username`'s
privilege 1 or the line's `privilege level 15` wins for local auth is version
and platform dependent, and I'm not going to guess on your production switch.
Verify empirically:

```bash
ssh hud-ro@192.168.3.2
show privilege          # want: "Current privilege level is 1"
configure terminal      # want: rejected / invalid input
```

- **Reports 1, `configure terminal` refused** → device-side enforcement works.
  Done; the terminal is genuinely read-only.
- **Reports 15** → the line config is winning, and step 1 alone is not enough.

### If it reports 15

The obvious fix — deleting `privilege level 15` from `line vty 5 15` — is **not
safe to apply blind here**, because there is no `enable secret` in the running
config. Today `admin` and `cisco` arrive at level 15 automatically. Remove the
auto-elevation without first setting an enable secret and they land at level 1
with no way up, over SSH, on a VLAN 3 management path. That is exactly the
console-trip scenario the safety rules exist to prevent.

Correct order if you go down this route:

```
! 1. establish an escalation path FIRST
enable secret <STRONG-ENABLE-SECRET>

! 2. confirm it works, in a SECOND session, keeping the first one open:
!      ssh admin@192.168.3.2 ; enable ; show privilege   -> 15
!    do not proceed until that succeeds

! 3. only then drop the blanket auto-elevation
line vty 5 15
 no privilege level 15
```

Keep the original session open throughout so a mistake never locks you out.

Until step 2 verifies clean, treat the terminal as **config-capable** and leave
`HUD_SSH_ALLOW_CONFIG` unset (the app filter stays on).

---

## What the app-layer guard does

In `server.local.js`, so it survives upstream merges:

- **Input filter, default on.** Rejects `configure`/`conf t`, `write`, `erase`,
  `reload`, `delete`, `format`, `copy`, and bare `no …`, plus anything matching
  `vlan 3` / `Vlan3` / `interface Vlan3` regardless of mode.
  Honest limitation: this is best-effort on an interactive stream. Abbreviations,
  `do`, pasted blocks, `tclsh`, and EEM applets can route around line-oriented
  matching. It raises the bar; it is not a boundary. Device-side privilege is.
  Lift with `HUD_SSH_ALLOW_CONFIG=1` once you've accepted the risk.
- **Access gate.** `/api/ssh/*` reuses `requireTrustedClient` and additionally
  requires `HUD_API_TOKEN` when set.
- **Audit log.** Every submitted line, with device, source IP and timestamp, to
  `~/.openclaw/hud-ssh-audit.log`.
- **Idle timeout** (`HUD_SSH_IDLE_S`, default 900) and a concurrent session cap
  (`HUD_SSH_MAX_SESSIONS`, default 4).
- **Credentials never reach the browser.** The client sends a device id; the
  server resolves host and credentials from `testbed.yaml` + env. Consistent
  with `/api/graph` already reporting `"ip": "N/A"`.

## Rollback

```
no username hud-ro
```
and unset `HUD_SSH_*`. Deleting `server.local.js` removes the whole feature.
