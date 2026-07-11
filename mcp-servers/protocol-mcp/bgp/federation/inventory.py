"""Capability inventory: build, visibility-filter, no-secrets guard, exchange.

Local inventory is built from config/openclaw.json (MCP servers + tools) and
workspace/skills/*/SKILL.md (skills), tagged with capability badges. It is
visibility-filtered (FR-006) and secret-scanned (FR-007) before advertisement.
Remote inventories are cached per peer with received-at metadata for staleness
(FR-008/FR-009).
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger("n2n.inventory")

# Badge derivation from MCP server id prefixes (research.md R7). Extend in the
# same PR that adds a server (Constitution XI).
BADGE_RULES = [
    ("CML", ("cml-", "cml_mcp", "virl")),
    ("pyATS", ("pyats", "genie", "testbed")),
    ("Meraki", ("meraki",)),
    ("NetBox", ("netbox",)),
    ("Nautobot", ("nautobot",)),
    ("Azure", ("azure",)),
    ("AWS", ("aws",)),
    ("Check Point", ("checkpoint", "chkp")),
    ("SuzieQ", ("suzieq",)),
    ("Batfish", ("batfish",)),
    ("gNMI", ("gnmi",)),
    ("GNS3", ("gns3",)),
    ("Forward", ("forward",)),
]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _derive_badges(server_ids) -> list:
    badges = []
    low = [s.lower() for s in server_ids]
    for badge, prefixes in BADGE_RULES:
        if any(any(sid.startswith(p) or p in sid for p in prefixes) for sid in low):
            badges.append(badge)
    return sorted(set(badges))


class InventoryBuilder:
    def __init__(self, manager, *, repo_root: Optional[str] = None,
                 openclaw_config: Optional[str] = None, env_path: Optional[str] = None):
        self.manager = manager
        # protocol-mcp/bgp/federation/inventory.py → repo root is 4 levels up
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[4])
        self.config_path = Path(openclaw_config or (self.repo_root / "config" / "openclaw.json"))
        self.skills_dir = self.repo_root / "workspace" / "skills"
        self.env_path = Path(env_path or os.path.expanduser("~/.openclaw/.env"))
        self._version = 0

    # ---- build --------------------------------------------------------

    def _load_mcp_servers(self) -> list:
        try:
            cfg = json.loads(self.config_path.read_text())
        except Exception as e:
            logger.warning("Cannot read openclaw.json: %s", e)
            return []
        servers = cfg.get("mcpServers") or {}
        out = []
        for name, spec in servers.items():
            tools = spec.get("tools") if isinstance(spec, dict) else None
            out.append({"name": name, "tools": tools or []})
        return out

    def _load_skills(self) -> list:
        out = []
        if not self.skills_dir.is_dir():
            return out
        for skill_dir in sorted(self.skills_dir.iterdir()):
            md = skill_dir / "SKILL.md"
            if not md.is_file():
                continue
            desc = ""
            try:
                for line in md.read_text().splitlines():
                    s = line.strip()
                    if s and not s.startswith("#") and not s.startswith("---") and not s.startswith("name:"):
                        desc = s
                        break
            except Exception:
                pass
            out.append({"name": skill_dir.name, "description": desc[:200]})
        return out

    def _visibility(self, item_type: str, item_name: str, peer_identity: str) -> bool:
        row = self.manager._conn.execute(
            "SELECT visibility, peer_list FROM visibility_setting WHERE item_type=? AND item_name=?",
            (item_type, item_name)).fetchone()
        if row is None:
            # Default: advertise both skills and MCP servers to federated peers.
            # Inventories carry only names/descriptions/tool-names — never
            # credentials or secrets (FR-007 guard still applies) — so peers see
            # each other's full capability surface by default. Operators can hide
            # specific skills or servers with n2n_set_visibility.
            return True
        vis = row["visibility"]
        if vis == "hidden":
            return False
        if vis == "all_federated":
            return True
        if vis == "selected_peers":
            try:
                return peer_identity in json.loads(row["peer_list"] or "[]")
            except Exception:
                return False
        return False

    def build(self, peer_identity: str) -> dict:
        """Build the inventory to advertise to a specific peer (visibility applied)."""
        self._version += 1
        skills = [s for s in self._load_skills()
                  if self._visibility("skill", s["name"], peer_identity)]
        for s in skills:
            s["invocable"] = True
        all_servers = self._load_mcp_servers()
        servers = [s for s in all_servers
                   if self._visibility("mcp_server", s["name"], peer_identity)]
        badges = _derive_badges([s["name"] for s in servers])
        inv = {
            "identity": self._local_identity(),
            "issued_at": _now(),
            "version": self._version,
            "skills": skills,
            "mcp_servers": [{"name": s["name"], "tools": s["tools"],
                             "invocable_tools": s["tools"]} for s in servers],
            "badges": badges,
        }
        self._assert_no_secrets(inv)
        return inv

    def _local_identity(self) -> str:
        return os.environ.get("N2N_LOCAL_IDENTITY", "")

    # ---- no-secrets guard (FR-007, SC-004) -----------------------------

    # Only values of keys whose NAME signals a secret are scanned. Scanning
    # every env value caused false positives — a benign hostname, path, URL, or
    # feature flag would collide with legitimate inventory text and abort the
    # whole advertisement. Real credentials live under these key patterns.
    _SECRET_KEY_RE = re.compile(
        r"(PASSWORD|PASSWD|SECRET|TOKEN|CREDENTIAL|PRIVATE_KEY|APIKEY|API_KEY|"
        r"ACCESS_KEY|CLIENT_SECRET|AUTH|BEARER|SESSION|COOKIE)", re.IGNORECASE)

    def _load_secret_values(self) -> set:
        secrets = set()
        try:
            for line in self.env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                val = val.strip().strip('"').strip("'")
                # Scan only secret-named keys, and only non-trivial values.
                if self._SECRET_KEY_RE.search(key) and len(val) >= 8:
                    secrets.add(val)
        except Exception:
            pass
        return secrets

    def _assert_no_secrets(self, inv: dict):
        blob = json.dumps(inv)
        for secret in self._load_secret_values():
            if secret in blob:
                raise ValueError("Inventory build aborted: a secret value from .env "
                                 "appeared in the advertised inventory (FR-007)")

    # ---- remote cache (FR-008/FR-009) ----------------------------------

    def cache_remote(self, peer_identity: str, inventory: dict):
        base = self.manager.base_dir / "inventories"
        (base / f"{peer_identity}.json").write_text(json.dumps(inventory, indent=2))
        (base / f"{peer_identity}.meta.json").write_text(
            json.dumps({"received_at": _now(), "version": inventory.get("version")}))

    def load_remote(self, peer_identity: str, refresh_s: int = 21600) -> Optional[dict]:
        base = self.manager.base_dir / "inventories"
        inv_path = base / f"{peer_identity}.json"
        if not inv_path.is_file():
            return None
        inv = json.loads(inv_path.read_text())
        received_at = None
        try:
            received_at = json.loads((base / f"{peer_identity}.meta.json").read_text()).get("received_at")
        except Exception:
            pass
        stale = False
        if received_at:
            try:
                age = time.time() - time.mktime(time.strptime(received_at, "%Y-%m-%dT%H:%M:%SZ"))
                stale = age > (2 * refresh_s)
            except Exception:
                pass
        return {"inventory": inv, "received_at": received_at, "stale": stale}
