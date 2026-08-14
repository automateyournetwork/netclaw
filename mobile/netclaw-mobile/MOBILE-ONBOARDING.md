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

### What this exposes

Be deliberate about it: enrolling a phone means **a public inbound TLS listener
into whatever network segment the Border sits on**. That is a posture change, not
a default, and it deserves a decision rather than a shrug.

What carries it: domain-verified TLS the app validates with no bypass; single-use
enrollment tokens stored only as hashes; and hardware-rooted device identity
whose private key cannot be exported. What you should still do: tighten the
firewall's source addresses if the client population is predictable, audit the
WAN policy logs periodically, and after any host-level change (a kernel reboot
especially) confirm the mesh service, Border role, port forward, and listener all
came back — `netclaw risk edge-check` covers the last three.

**The enrollment token is the one genuinely sensitive artifact in this flow.**
It is bearer credentials: anyone who has it before your tester does can enroll
their own device in their place. Treat it like a password — see *Handing over
the token* below.

---

## Fast path

If you just want the commands, in order. Every one of these is a step a real
first install got stuck on — the long-form sections below explain why.

```bash
netclaw risk edge-check                      # 0. what's missing? (checks all of the below)
netclaw risk role border <risk-name> in2n    # 1. standalone → Border, in2n stack on
systemctl --user restart netclaw-mesh.service # 2. apply
netclaw risk edge-check                      # 3. confirm green before going further
netclaw risk token --edge <device-label>     # 4. mint the QR
netclaw risk members                         # 5. verify the device that claimed it
```

`netclaw risk edge-check` is the one command worth remembering. It checks role,
stack, both env vars, the mesh daemon's Python dependencies, whether the
listener actually bound, the live socket, and DNS — and prints the remedy for
whatever is wrong. It exists because the first real-world install cleared **five
independent blockers, each of which masked the next**, and none of which named
itself in its own error message.

---

## Claw side (Border operator)

### 0. One-time: you must be a Border, with the `in2n` stack enabled

At install you chose **standalone**, **Border**, or **Member**. Only a Border
issues mobile enrollment tokens:

```bash
netclaw risk status
#   role : standalone
netclaw risk token --edge my-phone
#   error: only a Border can issue enrollment tokens
```

> **"Standalone is a risk of one, its own Border" does not mean Border features
> work.** Standalone is its own Border for federation *identity* only. It issues
> no enrollment tokens and starts no mobile edge listener. This wording has
> misled at least one installer; `risk status` now says so explicitly.

Promote in place — **no reinstall is needed**, the role is a field in the
federation database:

```bash
netclaw risk role border <risk-name> in2n
systemctl --user restart netclaw-mesh.service
netclaw risk status          # role : border
```

**The `in2n` stack matters as much as the role.** The edge listener is gated on
`is_border()` **and** `stack_enabled("in2n")` — a Border with no stack enabled
starts no listener, so the promote looks successful and the phone still cannot
connect. `netclaw risk role border <name>` defaults the stack to `in2n` for
exactly this reason; pass `both` instead if you also want external (eN2N)
federation peering.

> **Historical note — if you are following an older copy of these instructions:**
> there was no `netclaw risk role` subcommand, and the documented promote was a
> raw `curl` against `/n2n/risk`. Written without the scheme and port
> (`127.0.0.1/n2n/risk` rather than `http://127.0.0.1:8179/n2n/risk`) it never
> reaches the daemon and **silently no-ops** — no error, role unchanged. If you
> must use curl, use `-i` so a missing `200` is visible. The subcommand exists
> so you don't have to.

### 0b. The mesh daemon needs `websockets` and `qrcode`

The edge listener imports `websockets`; the token command renders with `qrcode`.
Both are declared in `mcp-servers/protocol-mcp/requirements.txt`, but that file
is installed by the optional **Protocol** component — so an install that
selected N2N without it gets a mesh daemon that starts, looks healthy, and
cannot bind the edge listener. (Fixed in the installer as of spec 105; this
section is for boxes installed before that.)

The trap is *which* interpreter: the mesh runs under the `ExecStart` in
`netclaw-mesh.service`, which is `/usr/bin/python3` — a virtualenv will not be
consulted, and on modern Ubuntu a plain `pip install` there is refused by
PEP 668 (`externally-managed-environment`).

```bash
/usr/bin/python3 -c "import websockets, qrcode"        # the only test that counts
sudo apt install -y python3-websockets python3-qrcode  # PEP-668-clean
# or: /usr/bin/python3 -m pip install --break-system-packages websockets qrcode
systemctl --user restart netclaw-mesh.service
```

`netclaw risk edge-check` performs this import test against the interpreter it
reads out of the unit file, not against whatever `python3` means in your shell.

### 1. One-time: expose the edge listener

The edge WebSocket listener is separate from the agent/service listeners. Two
settings are required, in the runtime env the mesh daemon reads
(`~/.openclaw/mesh.systemd.env` for the durable systemd units, or
`~/.openclaw/.env`):

```properties
N2N_CLAW_DOMAIN=border.example.com   # must match your TLS certificate
N2N_EDGE_WS_PORT=8443
```

Restart the daemon, then confirm the listener came up — **and read the port in
the log line, don't assume it**:

```bash
systemctl --user restart netclaw-mesh.service
journalctl --user -u netclaw-mesh.service --since "1 min ago" | grep -i "Edge"
# → Edge (NetClaw Mobile) WS listener on 0.0.0.0:8443 (risk=<your-risk>)
ss -tlnp | grep 8443          # the live socket, not a log claim
```

Two things that have each cost real time here:

- **Use `--since "1 min ago"`** (not `-n 50`). Old `ERROR` lines from before a
  fix stay in the journal forever and read exactly like a current failure. More
  than one already-solved problem has been re-chased this way.
- **A transposed port survives a careless edit.** One install ran with
  `N2N_EDGE_WS_PORT=1443` and bound `0.0.0.0:1443` perfectly happily while the
  app dialled 8443. Check for a *duplicate* `N2N_EDGE_WS_PORT` line too — with
  two lines the last one wins, and it may not be the one you just edited:
  ```bash
  grep -n N2N_EDGE_WS_PORT ~/.openclaw/.env    # expect exactly one line
  ```

`N2N_CLAW_DOMAIN` must resolve publicly and match the certificate the Border
presents — phones validate it. A self-signed or mismatched cert fails the
handshake with no override in the app, by design.

```bash
dig +short <your-claw-domain>     # must be the public IP the phone will reach
```

### 1b. Forward the port from the internet

The listener binding `0.0.0.0:8443` proves nothing about reachability. **A phone
on cellular is not on your LAN**, and a healthy listener behind an
un-forwarded firewall port times out identically to a dead one — this is the
blocker most likely to be mistaken for an app bug.

Forward public `:8443` → `<box>:8443` however your edge device does it, then
**verify with a live packet trace while the phone actually tries to connect**.
A completed handshake (SYN in → SYN/ACK out → ACK → data) is the only proof:

```bash
# FortiGate
diagnose sniffer packet <wan-interface> 'port 8443' 4
```

<details>
<summary><b>FortiGate in Central NAT mode</b> — the VIP is not the policy's <code>dstaddr</code></summary>

Check your mode first — if `show firewall central-snat-map` has entries, you are
in Central NAT, and the usual "put the VIP in the policy's destination" recipe
**will never work**. That is a policy-NAT-mode construct. In Central NAT the VIP
carries the DNAT itself and the policy uses `dstaddr all`. Getting this wrong
throws `entry not found in datasource` even after the VIP exists, which reads
like a missing object rather than a mode mismatch.

Order matters: the VIP must exist before any policy references it.

```
# 1. Service object
config firewall service custom
    edit "HTTPS_8443"
        set tcp-portrange 8443
    next
end

# 2. VIP — this is what performs the DNAT
config firewall vip
    edit "netclaw-mobile-8443"
        set extip <WAN-IP>
        set extintf "<wan-interface>"
        set portforward enable
        set protocol tcp
        set extport 8443
        set mappedip <box-internal-IP>
        set mappedport 8443
    next
end

# 3. Policy — dstaddr is ALL, *not* the VIP name
config firewall policy
    edit 0
        set name "netclaw-mobile-in"
        set srcintf "<wan-interface>"
        set dstintf "<box-vlan-interface>"
        set srcaddr "all"
        set dstaddr "all"
        set action accept
        set schedule "always"
        set service "HTTPS_8443"
        set logtraffic all
    next
end
```

If the client population is predictable, tighten `srcaddr` rather than leaving
it `all`.
</details>

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

**Start with `netclaw risk edge-check`.** It diagnoses every row in the first
half of this table and prints the fix. The table is here for the reasoning.

| Symptom | Cause |
|---|---|
| `error: only a Border can issue enrollment tokens` | Usually the literal truth — `netclaw risk status` shows `standalone`; promote with `netclaw risk role border <name> in2n`. **But this message has also appeared with the role already correct**, when the listener died for an unrelated reason (missing `websockets`). It names the role because that is the check the token route performs; it is not proof the role is wrong. Run `edge-check`. |
| `netclaw risk token --edge` exits with no output | `N2N_CLAW_DOMAIN` or `N2N_EDGE_WS_PORT` missing from the runtime env — see step 1. |
| Promote appeared to work but `risk status` still says `standalone` | A `curl` to `/n2n/risk` without `http://` and `:8179` never reaches the daemon and no-ops silently. Use `netclaw risk role`, or add `-i` to the curl. |
| Listener bound, but on the wrong port | Mistyped or duplicated `N2N_EDGE_WS_PORT`. `grep -n N2N_EDGE_WS_PORT ~/.openclaw/.env` — expect one line. |
| `ERROR Edge WS start error: No module named 'websockets'` | The mesh daemon's interpreter (`/usr/bin/python3`, per the unit's `ExecStart`) lacks it. `sudo apt install python3-websockets python3-qrcode`. A venv does not help — the unit calls the absolute path. |
| `qrcode not installed` | Same interpreter problem as above. The JSON fallback and manual entry still work without it. |
| Journal shows an error you already fixed | You are reading a stale line. Always `journalctl --user -u netclaw-mesh.service --since "1 min ago"`. |
| Phone times out connecting | Listener not bound, or public `:8443` not forwarded to the box. Confirm the socket with `ss -tlnp \| grep 8443`, then prove reachability with a packet trace while the phone tries — see step 1b. |
| FortiGate: `entry not found in datasource` on the policy | Central NAT mode — the VIP performs the DNAT and the policy's `dstaddr` must be `all`, not the VIP name. See step 1b. |
| TLS / certificate error on the phone | `N2N_CLAW_DOMAIN` doesn't match the served certificate, or the cert isn't publicly trusted, or DNS points somewhere other than the forwarded public IP. There is no bypass in the app. |
| "Token already used" | Tokens are single-use — a failed or partial attempt spends one. Issue a new one; they're free. |
| App drops back to the enrollment screen | The Border revoked this device (`-32023`). Issue a fresh token to re-enroll. |

### Debugging posture

The pattern that cleared all five first-install blockers: **stop trusting the
surface error, find the actual state, fix the real cause.** Every one of them
either failed silently or pointed at the wrong layer. Ask the system what it
is — `risk status`, `ss -tlnp`, a packet trace, an `import` under the daemon's
own interpreter — rather than inferring from the message you were given.
