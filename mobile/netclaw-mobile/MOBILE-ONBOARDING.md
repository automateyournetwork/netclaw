# Securely onboarding a mobile Claw

How to enroll a phone as an **NCFED edge node** against *your* Border Claw.

NetClaw Mobile is a generic client for the NCFED Edge Node profile. It is not
built for, tied to, or preconfigured with any particular Border — the app ships
with no hostnames, no tokens, and no credentials. Every install starts unbound
and is pointed at whichever Border enrolls it. `netclaw.automateyournetwork.ca`
appears in this repo only as the maintainer's own test Border; substitute your
own domain everywhere.

Two sides, in order: **the Claw side** issues a single-use enrollment token,
then **the phone side** consumes it. Neither works without the other.

---

## What the phone becomes

An enrolled phone is a `node_type='edge'` member of your risk — a peer that can
ask your Border questions and receive pushes, *not* an admin console. It gets
no shell, no filesystem, and no ability to enroll anyone else. Everything it
can do routes through your Border's existing authorization and audit path, so a
phone is exactly as privileged as the scope you grant it and no more.

---

## Security model — what protects what

| Concern | Mechanism |
|---|---|
| **Who may enroll** | A single-use enrollment token (`in2n_…`, 24 random bytes). The Border stores only its SHA-256 hash — the raw token exists once, in the output you hand over. |
| **Replay of a token** | `consume_token()` marks the row `spent_at` / `spent_by_member_id` on first use. A second attempt with the same token is rejected. |
| **Phone identity** | The app generates an EC P-256 keypair **inside the phone's hardware keystore** (Android Keystore / iOS Secure Enclave) at enrollment. The private key never leaves the device and is never transmitted — the app has no code path that can export it. |
| **Impersonation after enrollment** | Trust-on-first-use pinning: the Border records the phone's public key and fingerprint on the member row at enrollment. Later connections must sign a challenge with that exact key. |
| **Server impersonation** | The phone dials `wss://` and validates the Border's domain-verified TLS certificate. A phone enrolled for `border.example.com` will not complete a handshake against anything else. |
| **Revocation** | Removing the member unpins the key. The Border then answers that device with `-32023` (not trusted), which drops the app back to its enrollment screen instead of retrying forever. |
| **Audit** | Every request a phone originates is recorded in the Border's normal GAIT audit trail, attributed to that member ID. |

**The enrollment token is the one genuinely sensitive artifact in this flow.**
It is bearer credentials: anyone who has it before your tester does can enroll
their own device in their place. Treat it like a password — see *Handing over
the token* below.

---

## Claw side (Border operator)

### 1. One-time: expose the edge listener

The edge WebSocket listener is separate from the agent/service listeners. Two
settings are required, in the runtime env the mesh daemon reads
(`~/.openclaw/mesh.systemd.env` for the durable systemd units, or
`~/.openclaw/.env`):

```properties
N2N_CLAW_DOMAIN=border.example.com   # must match your TLS certificate
N2N_EDGE_WS_PORT=8443
```

Restart the daemon, then confirm the listener came up:

```bash
systemctl --user restart netclaw-mesh.service
journalctl --user -u netclaw-mesh.service -n 50 --no-pager | grep -i "Edge"
# → Edge (NetClaw Mobile) WS listener on 0.0.0.0:8443 (risk=<your-risk>)
```

`N2N_CLAW_DOMAIN` must resolve publicly and match the certificate the Border
presents — phones validate it. A self-signed or mismatched cert fails the
handshake with no override in the app, by design.

Make sure the port is actually reachable from outside your network (firewall,
NAT, security group). A phone on cellular is not on your LAN.

### 2. Per device: issue an enrollment token

One token per device. Label it so you can tell members apart later:

```bash
./scripts/netclaw risk token --edge alice-pixel8
```

This prints an ASCII QR code plus a raw JSON fallback:

```json
{"border_host":"border.example.com","border_port":8443,
 "claw_domain":"border.example.com","enrollment_token":"in2n_…"}
```

The QR and the JSON carry identical data — the QR is only a transport for it.

> **Tokens do not expire by default.** `issue_token()` sets `expires_at` only
> when given an explicit TTL, and the CLI does not pass one. An unused token
> stays valid indefinitely. Issue tokens close to when they'll be used, and
> treat an unclaimed one as live credentials until it is spent or the member
> is removed.

### 3. Confirm and scope the device

After the phone enrolls, it appears as a member:

```bash
./scripts/netclaw risk members
```

Verify the label and fingerprint match the device you expect **before** the
phone is used for anything real — TOFU means the first key wins, so this is
the moment to catch a wrong device having claimed the token.

### 4. Revoke when needed

```bash
./scripts/netclaw risk remove <member_id>
```

Do this immediately for a lost or stolen phone, when a person leaves, or if a
token may have been intercepted. Revocation is server-side and takes effect on
the device's next connection attempt — you do not need access to the phone.

---

## Phone side (the person holding the device)

### 1. Install the app

Until it is published, the app is sideloaded. **[`SIDELOAD.md`](SIDELOAD.md) is
the full procedure** for both platforms — building the artifact, getting it onto
the device, and the warnings the person will see. In short: Android takes an APK
sent by any means; iOS has no equivalent and needs TestFlight, an Ad Hoc build,
or a cabled Mac.

See [`README.md`](README.md#building-a-release) for producing a signed build,
and [`PLAY-STORE-ROADMAP.md`](PLAY-STORE-ROADMAP.md) /
[`APP-STORE-ROADMAP.md`](APP-STORE-ROADMAP.md) for the publication paths.

### 2. Enroll

On first launch the app opens on the enrollment screen. Two equivalent paths:

- **Scan the QR** — "Scan Border QR Code", point the camera at the QR the
  operator issued. Grant the camera permission when prompted.
- **Type it in** — "Can't scan? Enter manually", then fill in:

  | Field | Value |
  |---|---|
  | Border domain | `border.example.com` (`claw_domain` from the payload) |
  | Port | `8443` (`border_port`) |
  | Enrollment token | `in2n_…` (`enrollment_token`) |

  This builds exactly the payload a scan would produce, so it is a genuine
  equivalent — useful on an emulator or any device whose camera can't focus on
  a screen.

Enrollment then happens without further input: the app generates its hardware
keystore keypair, dials the Border over `wss://`, presents the token and its
public key, and the Border pins that key to a new member row.

### 3. After enrollment

The token is now spent and worthless — it cannot be reused, including by the
same device. Enrollment persists, so the app reconnects by itself on restart
and after a dropped connection; the operator does not need to issue a second
token.

If the Border revokes the device, the app returns to the enrollment screen
rather than retrying a dead identity. Re-enrolling requires a fresh token.

---

## Handing over the token

The token is bearer credentials in transit. Send it over a channel you already
trust for secrets — a password manager share, an encrypted DM, or in person.
Avoid email and plaintext SMS.

If the phone is in front of you, **displaying the QR on your screen and
scanning it is the safest option**: the token never leaves your machine.

If anything about a token's handling is uncertain, don't reuse it — revoke the
member if it was already claimed, and issue a fresh one. Tokens are free.

---

## Troubleshooting

| Symptom | Cause |
|---|---|
| `netclaw risk token --edge` exits with no output | `N2N_CLAW_DOMAIN` or `N2N_EDGE_WS_PORT` missing from the runtime env — see step 1. |
| `qrcode not installed` | `pip install -r mcp-servers/protocol-mcp/requirements.txt`. The JSON fallback and manual entry still work without it. |
| Phone times out connecting | Port not reachable from outside your network, or the daemon's edge listener never started — check the `journalctl` line in step 1. |
| TLS / certificate error on the phone | `N2N_CLAW_DOMAIN` doesn't match the served certificate, or the cert isn't publicly trusted. There is no bypass in the app. |
| "Token already used" | Tokens are single-use. Issue a new one. |
| App drops back to the enrollment screen | The Border revoked this device (`-32023`). Issue a fresh token to re-enroll. |
