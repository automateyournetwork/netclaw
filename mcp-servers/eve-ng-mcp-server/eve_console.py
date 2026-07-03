"""
EVE-NG console engine — raw Telnet sessions and OS-specific drivers.

Supports: IOS/IOL/IOS-XE, Junos, Arista EOS, Cisco NX-OS, VPCS.
"""

import os
import re
import socket
import time

from eve_client import EVEError

EVE_CONSOLE_USER     = os.getenv("EVE_CONSOLE_USER", "")
EVE_CONSOLE_PASSWORD = os.getenv("EVE_CONSOLE_PASSWORD", "")

READ_CHUNK = 65535

IOS_PROMPT_RE  = re.compile(r'(?P<prompt>[A-Za-z0-9_.-]+(?:\([^\r\n)]*\))?[>#])\s*$')
VPCS_PROMPT_RE = re.compile(r'VPCS>\s*$')
JUNOS_OP_RE    = re.compile(r'(?m)^[^\r\n\s>]+>\s*$')
JUNOS_CFG_RE   = re.compile(r'(?m)^\[[^\r\n]+\]\s*\n[^\r\n\s#]+#\s*$')
EOS_PROMPT_RE  = re.compile(r'(?P<prompt>[A-Za-z0-9_.-]+(?:\([^\r\n)]*\))?[>#])\s*$')
NXOS_PROMPT_RE = re.compile(r'(?P<prompt>[A-Za-z0-9_.-]+(?:\([^\r\n)]*\))?[>#])\s*$')
IOS_SETUP_RE   = re.compile(r'(Would you like to enter the initial configuration dialog\? \[yes/no\]:|[A-Za-z0-9_.-]+(?:\([^\r\n)]*\))?[>#]\s*$)')


class TelnetSession:
    """Raw telnet session for EVE-NG console access."""

    def __init__(self, host: str, port: int, timeout: float = 1.5):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock: socket.socket | None = None

    def __enter__(self):
        self.sock = socket.socket()
        self.sock.settimeout(self.timeout)
        try:
            self.sock.connect((self.host, self.port))
        except (ConnectionRefusedError, OSError) as exc:
            raise EVEError("EVE_CONSOLE_TIMEOUT",
                           f"Cannot connect to console {self.host}:{self.port}: {exc}", -2)
        return self

    def __exit__(self, *_):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def recv_all(self, wait: float = 0.7, loops: int = 4) -> str:
        time.sleep(wait)
        out = ""
        for _ in range(loops):
            try:
                data = self.sock.recv(READ_CHUNK)
                if not data:
                    break
                out += data.decode("utf-8", "ignore")
                if len(data) < READ_CHUNK:
                    break
            except Exception:
                break
        return out

    def recv_until(self, pattern, timeout: float = 10.0, poll: float = 0.2) -> str:
        end = time.time() + timeout
        out = ""
        while time.time() < end:
            try:
                data = self.sock.recv(READ_CHUNK)
                if data:
                    out += data.decode("utf-8", "ignore")
                    if pattern.search(out):
                        return out
                    continue
            except socket.timeout:
                pass
            except Exception:
                break
            time.sleep(poll)
        return out

    def send(self, command: str, wait: float = 0.7) -> str:
        self.sock.sendall((command + "\r").encode())
        return self.recv_all(wait=wait)

    def send_until(self, command: str, pattern, timeout: float = 10.0) -> str:
        self.sock.sendall((command + "\r").encode())
        return self.recv_until(pattern, timeout=timeout)


# --- IOS / IOL / IOS-XE ---

def detect_ios_mode(text: str) -> dict:
    for line in reversed([l.strip() for l in text.splitlines() if l.strip()]):
        m = IOS_PROMPT_RE.search(line)
        if not m:
            continue
        p = m.group("prompt")
        if "(config-router)" in p: return {"prompt": p, "mode": "config-router"}
        if "(config-subif)" in p:  return {"prompt": p, "mode": "config-subif"}
        if "(config-if)" in p:     return {"prompt": p, "mode": "config-if"}
        if "(config)" in p:        return {"prompt": p, "mode": "config"}
        if p.endswith("#"):        return {"prompt": p, "mode": "privileged"}
        if p.endswith(">"):        return {"prompt": p, "mode": "exec"}
    return {"prompt": None, "mode": "unknown"}


def bootstrap_ios(session: TelnetSession) -> list:
    transcript = []
    text = session.recv_all(wait=1.0, loops=6)
    if detect_ios_mode(text)["mode"] == "unknown":
        # Bounded wake/read; IOL may show setup before EVE imports config.
        text += session.send("", wait=1.0)
        text += session.recv_all(wait=1.0, loops=8)
    transcript.append({"command": None, "output": text, "mode_after": detect_ios_mode(text)})
    if "%SYS-5-CONFIG_I" in text or "Configured from unix:startup-config" in text:
        text = session.send("", wait=1.0)
        transcript.append({"command": "", "output": text, "mode_after": detect_ios_mode(text)})
    elif "initial configuration dialog" in text or "Would you like to enter" in text:
        text = session.send("no", wait=1.0)
        transcript.append({"command": "no", "output": text, "mode_after": detect_ios_mode(text)})
    if "terminate autoinstall" in text:
        text = session.send("yes", wait=0.8)
        transcript.append({"command": "yes", "output": text, "mode_after": detect_ios_mode(text)})
    if "Press RETURN to get started" in text:
        text = session.send("", wait=1.0)
        transcript.append({"command": "", "output": text, "mode_after": detect_ios_mode(text)})
    return transcript


def ensure_ios_privileged(session: TelnetSession) -> list:
    transcript = []
    wake = session.send("", wait=0.8)
    mode = detect_ios_mode(wake)
    transcript.append({"command": "", "output": wake, "mode_after": mode})
    if mode["mode"] in ("config-router", "config-subif", "config-if", "config"):
        out = session.send("end", wait=0.7)
        mode = detect_ios_mode(out)
        transcript.append({"command": "end", "output": out, "mode_after": mode})
    if mode["mode"] == "exec":
        out = session.send("enable", wait=0.7)
        mode = detect_ios_mode(out)
        transcript.append({"command": "enable", "output": out, "mode_after": mode})
    out = session.send("terminal length 0", wait=0.7)
    transcript.append({"command": "terminal length 0", "output": out, "mode_after": detect_ios_mode(out)})
    return transcript


def ensure_ios_config(session: TelnetSession) -> list:
    transcript = ensure_ios_privileged(session)
    out = session.send("configure terminal", wait=0.7)
    transcript.append({"command": "configure terminal", "output": out, "mode_after": detect_ios_mode(out)})
    return transcript


def run_ios_command(session: TelnetSession, cmd: str, wait: float = 0.8, timeout: float = 15.0) -> str:
    lower = cmd.strip().lower()
    if lower.startswith("ping ") or lower.startswith("traceroute "):
        return session.send_until(cmd, IOS_PROMPT_RE, timeout=timeout)
    return session.send(cmd, wait=wait)


# --- Junos ---

def detect_junos_mode(text: str) -> dict:
    if JUNOS_CFG_RE.search(text):
        lines = [l.rstrip() for l in text.splitlines() if l.strip()]
        return {"prompt": lines[-1] if lines else None, "mode": "config"}
    m = JUNOS_OP_RE.search(text)
    if m:
        return {"prompt": m.group(0).strip(), "mode": "operational"}
    return {"prompt": None, "mode": "unknown"}


def ensure_junos_operational(session: TelnetSession) -> list:
    transcript = []
    wake = session.send("", wait=0.7)
    mode = detect_junos_mode(wake)
    transcript.append({"command": "", "output": wake, "mode_after": mode})
    if "login:" in wake:
        out = session.send("root", wait=0.8)
        transcript.append({"command": "root", "output": out, "mode_after": detect_junos_mode(out)})
        if "Password:" in out:
            out = session.send("eve-ng", wait=1.0)
            mode = detect_junos_mode(out)
            transcript.append({"command": "<password>", "output": out, "mode_after": mode})
            wake = out
    if wake.strip().endswith("%") or wake.strip().endswith("$"):
        out = session.send("cli", wait=1.0)
        mode = detect_junos_mode(out)
        transcript.append({"command": "cli", "output": out, "mode_after": mode})
    elif mode["mode"] == "config":
        out = session.send("exit configuration-mode", wait=0.8)
        transcript.append({"command": "exit configuration-mode", "output": out,
                            "mode_after": detect_junos_mode(out)})
    out = session.send("set cli screen-length 0", wait=0.8)
    transcript.append({"command": "set cli screen-length 0", "output": out,
                        "mode_after": detect_junos_mode(out)})
    out = session.send("set cli screen-width 0", wait=0.8)
    transcript.append({"command": "set cli screen-width 0", "output": out,
                        "mode_after": detect_junos_mode(out)})
    return transcript


def run_junos_command(session: TelnetSession, cmd: str, timeout: float = 15.0) -> str:
    normalized = cmd.strip()
    lower = normalized.lower()
    if lower.startswith("show ") and "| no-more" not in lower:
        normalized += " | no-more"
    return session.send_until(normalized, JUNOS_OP_RE, timeout=timeout)


# --- Arista EOS ---

def detect_eos_mode(text: str) -> dict:
    for line in reversed([l.strip() for l in text.splitlines() if l.strip()]):
        m = EOS_PROMPT_RE.search(line)
        if not m:
            continue
        p = m.group("prompt")
        if "(config-" in p: return {"prompt": p, "mode": "config-sub"}
        if "(config)" in p:  return {"prompt": p, "mode": "config"}
        if p.endswith("#"):  return {"prompt": p, "mode": "privileged"}
        if p.endswith(">"):  return {"prompt": p, "mode": "exec"}
    return {"prompt": None, "mode": "unknown"}


def ensure_eos_privileged(session: TelnetSession) -> list:
    transcript = []
    wake = session.send("", wait=0.7)
    mode = detect_eos_mode(wake)
    transcript.append({"command": "", "output": wake, "mode_after": mode})
    if ("login:" in wake or "Username:" in wake) and EVE_CONSOLE_USER:
        out = session.send(EVE_CONSOLE_USER, wait=0.8)
        transcript.append({"command": "<username>", "output": out, "mode_after": detect_eos_mode(out)})
    if mode["mode"] in ("config", "config-sub"):
        out = session.send("end", wait=0.7)
        mode = detect_eos_mode(out)
        transcript.append({"command": "end", "output": out, "mode_after": mode})
    if mode["mode"] == "exec":
        out = session.send("enable", wait=0.7)
        mode = detect_eos_mode(out)
        transcript.append({"command": "enable", "output": out, "mode_after": mode})
    out = session.send("terminal length 0", wait=0.7)
    transcript.append({"command": "terminal length 0", "output": out, "mode_after": detect_eos_mode(out)})
    out = session.send("terminal width 512", wait=0.7)
    transcript.append({"command": "terminal width 512", "output": out, "mode_after": detect_eos_mode(out)})
    return transcript


def ensure_eos_config(session: TelnetSession) -> list:
    transcript = ensure_eos_privileged(session)
    out = session.send("configure terminal", wait=0.7)
    transcript.append({"command": "configure terminal", "output": out, "mode_after": detect_eos_mode(out)})
    return transcript


def run_eos_command(session: TelnetSession, cmd: str, wait: float = 0.8, timeout: float = 15.0) -> str:
    lower = cmd.strip().lower()
    if lower.startswith("ping ") or lower.startswith("traceroute "):
        return session.send_until(cmd, EOS_PROMPT_RE, timeout=timeout)
    return session.send(cmd, wait=wait)


# --- Cisco NX-OS ---

def detect_nxos_mode(text: str) -> dict:
    for line in reversed([l.strip() for l in text.splitlines() if l.strip()]):
        m = NXOS_PROMPT_RE.search(line)
        if not m:
            continue
        p = m.group("prompt")
        if "(config-" in p: return {"prompt": p, "mode": "config-sub"}
        if "(config)" in p:  return {"prompt": p, "mode": "config"}
        if p.endswith("#"):  return {"prompt": p, "mode": "privileged"}
        if p.endswith(">"):  return {"prompt": p, "mode": "exec"}
    return {"prompt": None, "mode": "unknown"}


def ensure_nxos_privileged(session: TelnetSession) -> list:
    transcript = []
    wake = session.send("", wait=1.0)
    mode = detect_nxos_mode(wake)
    transcript.append({"command": "", "output": wake, "mode_after": mode})
    if ("login:" in wake or "Login:" in wake) and EVE_CONSOLE_USER:
        out = session.send(EVE_CONSOLE_USER, wait=1.0)
        transcript.append({"command": "<username>", "output": out, "mode_after": detect_nxos_mode(out)})
        if "Password:" in out and EVE_CONSOLE_PASSWORD:
            out = session.send(EVE_CONSOLE_PASSWORD, wait=1.0)
            transcript.append({"command": "<password>", "output": out, "mode_after": detect_nxos_mode(out)})
    # Dismiss first-boot setup wizard
    if ("Do you want to enforce secure password" in wake
            or "Would you like to enter the basic configuration" in wake):
        out = session.send("no", wait=1.0)
        transcript.append({"command": "no", "output": out, "mode_after": detect_nxos_mode(out)})
    if mode["mode"] in ("config", "config-sub"):
        out = session.send("end", wait=0.7)
        mode = detect_nxos_mode(out)
        transcript.append({"command": "end", "output": out, "mode_after": mode})
    out = session.send("terminal length 0", wait=0.7)
    transcript.append({"command": "terminal length 0", "output": out, "mode_after": detect_nxos_mode(out)})
    out = session.send("terminal width 511", wait=0.7)
    transcript.append({"command": "terminal width 511", "output": out, "mode_after": detect_nxos_mode(out)})
    return transcript


def ensure_nxos_config(session: TelnetSession) -> list:
    transcript = ensure_nxos_privileged(session)
    out = session.send("configure terminal", wait=0.7)
    transcript.append({"command": "configure terminal", "output": out, "mode_after": detect_nxos_mode(out)})
    return transcript


def run_nxos_command(session: TelnetSession, cmd: str, wait: float = 0.8, timeout: float = 15.0) -> str:
    lower = cmd.strip().lower()
    if lower.startswith("ping ") or lower.startswith("traceroute "):
        return session.send_until(cmd, NXOS_PROMPT_RE, timeout=timeout)
    return session.send(cmd, wait=wait)
