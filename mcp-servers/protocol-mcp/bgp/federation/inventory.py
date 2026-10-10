"""Capability inventory: build, visibility-filter, no-secrets guard, exchange.

Local inventory is built from config/openclaw.json (MCP servers + tools) and
workspace/skills/*/SKILL.md (skills), tagged with capability badges. It is
visibility-filtered (FR-006) and secret-scanned (FR-007) before advertisement.
Remote inventories are cached per peer with received-at metadata for staleness
(FR-008/FR-009).
"""

import json
import calendar
import shlex
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
        from .runtime import selected
        self.runtime=selected()
        self.config_path = Path(openclaw_config or (self.repo_root/'config/openclaw.json' if repo_root else self.runtime.config))
        self.skills_dir = self.repo_root/'workspace/skills' if repo_root else self.runtime.skills
        self.env_path = Path(env_path or self.runtime.env_file)
        self._version = 0

    # ---- build --------------------------------------------------------

    def _load_mcp_servers(self) -> list:
        try:
            if self.runtime.kind=='hermes':
                import yaml
                cfg=yaml.safe_load(self.config_path.read_text()) or {}
            else:cfg = json.loads(self.config_path.read_text())
        except Exception as e:
            logger.warning("Cannot read openclaw.json: %s", e)
            return []
        servers = cfg.get('mcp_servers') if self.runtime.kind=='hermes' else (cfg.get('mcp') or {}).get('servers') or cfg.get("mcpServers")
        servers=servers or {}
        qualified={}
        if self.runtime.kind=='hermes':
            from .runtime import ROOT
            import sys
            sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
            from policy import qualified_servers
            qualified,_=qualified_servers(cfg,home=self.runtime.home)
        out = []
        for name, spec in servers.items():
            tools = spec.get("tools") if isinstance(spec, dict) else None
            if isinstance(tools,dict):tools=tools.get('include',[])
            approved=(qualified.get(name,{}).get('tools') or {}).get('include',[])
            out.append({"name": name, "tools": tools or approved or [],'invocable_tools':approved if self.runtime.kind=='hermes' else tools or [],
                        'qualification':'source-reviewed' if name in qualified else 'configured'})
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

    def _member_aggregate_skills(self, existing_names: set) -> list:
        """iN2N (056/FR-016): on a Border, advertise the UNION of member SPECIALTY
        capabilities under the risk identity — capability NAMES only, never member
        ids/endpoints/topology. Lets a peer learn 'this risk can do CML/pyATS/…'
        without seeing the internal member structure."""
        conn = self.manager._conn
        try:
            r = conn.execute("SELECT role FROM risk WHERE id=1").fetchone()
            if not r or r["role"] != "border":
                return []
            rows = conn.execute(
                "SELECT scope FROM member WHERE state NOT IN ('removed','quarantined')"
            ).fetchall()
        except Exception:
            return []   # risk table absent (pre-056) or unreadable — no aggregate
        # A member's scope may be a list of {name,tier} dicts (structured, from
        # add_member) OR a flat list of skill-name strings (a member's advertised
        # list). Handle both — a string entry carries no tier, so classify it as a
        # specialty unless it is one of the mandatory base-floor skills.
        try:
            from .risk import BASE_FLOOR
            base_names = {b["name"] for b in BASE_FLOOR}
        except Exception:
            base_names = set()
        names = set()
        for row in rows:
            try:
                for e in json.loads(row["scope"] or "[]"):
                    if isinstance(e, dict):
                        name, tier = e.get("name"), e.get("tier")
                    elif isinstance(e, str):
                        name, tier = e, ("base" if e in base_names else "specialty")
                    else:
                        continue
                    if tier == "specialty" and name and name not in existing_names:
                        names.add(name)
            except (ValueError, TypeError):
                continue
        return [{"name": n, "invocable": self.runtime.kind!='hermes' or n=='subnet-calculator', "risk_aggregate": True} for n in sorted(names)]

    def build(self, peer_identity: str, posture: Optional[dict] = None) -> dict:
        """Build the inventory (A2A capability card) to advertise to a peer.

        Feature 057: the card carries the risk's PRODUCTION POSTURE + security
        flags so a peer (or member) knows whether this risk is enforcing (sandbox
        + model-guard + immutable audit) or degraded/testing — visibility applied
        to capabilities as before, no secrets ever."""
        self._version += 1
        all_servers = self._load_mcp_servers()
        skills = [s for s in self._load_skills()
                  if self._visibility("skill", s["name"], peer_identity)]
        for s in skills:
            s["invocable"] = self.runtime.kind!='hermes'
            if self.runtime.kind=='hermes' and s['name']=='subnet-calculator':
                from .runtime import ROOT
                import sys
                sys.path.insert(0,str(ROOT/'mcp-servers/hermes-hud-mcp'))
                from policy import qualified_skills
                record=self.runtime.home/'python-runtimes/records/subnet-calc'
                interpreter=Path(record.read_text().strip()) if record.is_file() else None
                dependency=any(server['name']=='subnet-calc-mcp' and 'subnet_calculator' in server.get('invocable_tools',[]) for server in all_servers)
                s['invocable']=bool(dependency and interpreter and interpreter.is_file() and qualified_skills(self.runtime.home))
        # Border: fold in member specialties as risk-level capabilities (FR-016).
        skills += [s for s in self._member_aggregate_skills({s["name"] for s in skills})
                   if self._visibility("skill", s["name"], peer_identity)]
        servers = [s for s in all_servers
                   if self._visibility("mcp_server", s["name"], peer_identity)]
        badges = _derive_badges([s["name"] for s in servers])
        # Feature 064: advertise local RAG collections as content-free knowledge
        # entries (one per collection), visibility-filtered per peer and secret-
        # scanned. Advertised by default (FR-003); collection hidden via
        # visibility_setting item_type "knowledge".
        knowledge = self._load_knowledge(peer_identity)
        inv = {
            "identity": self._local_identity(),
            "issued_at": _now(),
            "version": self._version,
            "skills": skills,
            "mcp_servers": [{"name": s["name"], "tools": s["tools"],
                             "invocable_tools": s['invocable_tools'],'qualification':s['qualification']} for s in servers],
            "knowledge": knowledge,
            "badges": badges,
            "posture": self._posture_card(posture),
            "llm": self._llm_card(),
            'harness':self._harness_card(),
        }
        self._assert_no_secrets(inv)
        return inv

    def _harness_card(self):
        from .runtime import local_harness
        return {**local_harness(self.runtime),'observed_at':_now()}

    def _load_knowledge(self, peer_identity: str) -> list:
        """Build the per-peer visible knowledge entries (feature 064). The
        collection name is the visibility key: an operator hides a collection
        from a peer with visibility_setting(item_type="knowledge",
        item_name=<collection>). Each entry is asserted content-free (FR-002)."""
        from . import knowledge as _knowledge
        out = []
        for entry in _knowledge.build_entries():
            collection = entry["collection_id"].split(":", 1)[-1]
            if not self._visibility("knowledge", collection, peer_identity):
                continue
            _knowledge.assert_entry_clean(entry)
            out.append(entry)
        return out

    def _posture_card(self, posture: Optional[dict]) -> dict:
        """Compact security posture for the A2A card (feature 057). Uses the live
        cached posture when provided, else a sync snapshot. Peers/members learn
        whether this risk is enforcing or testing/degraded."""
        from . import controls
        if posture:
            return {"mode": posture.get("mode"), "state": posture.get("state"),
                    "summary": posture.get("summary"),
                    "controls": {c["name"]: c["available"]
                                 for c in posture.get("controls", [])}}
        return {"mode": "production" if controls.is_production() else "testing",
                "state": "unknown",
                "summary": "production" if controls.is_production() else "testing",
                "controls": {}}

    def _llm_card(self) -> dict:
        """Advertise the claw's LLM capability (family/tier + whether guarded) so a
        peer understands the reasoning capability of its neighbour (feature 057).
        NO credentials — just the model id and guard status; a Border notes that its
        members run their own tiered models (topology stays hidden, FR-016)."""
        from . import controls
        model = self._local_primary_model()
        guarded = str(model).startswith("defenseclaw/")  # guardrail-proxy prefix
        underlying = model.split("/", 1)[1] if guarded and "/" in model else model
        card = {"primary_model": underlying or None, "guarded": bool(guarded)}
        try:
            if self.manager and hasattr(self.manager, "_conn"):
                r = self.manager._conn.execute(
                    "SELECT role FROM risk WHERE id=1").fetchone()
                if r and r[0] == "border":
                    card["note"] = ("Border reasoning model; member claws run their "
                                    "own per-specialty tiered models")
        except Exception:
            pass
        return card

    def _local_primary_model(self) -> str:
        """Read this claw's primary model from the OpenClaw config (no secrets)."""
        import json as _json
        if self.runtime.kind=='hermes':
            try:
                import yaml
                value=(yaml.safe_load(self.config_path.read_text()) or {}).get('model')
                return (value.get('default') or value.get('model') or '') if isinstance(value,dict) else value or ''
            except (OSError,ValueError):return ''
        for p in (self.config_path,):
            try:
                cfg = _json.loads(p.read_text())
                ag = (cfg.get("agents") or {}).get("defaults") or {}
                m = ag.get("model")
                if isinstance(m, dict):
                    return m.get("primary") or ""
                if isinstance(m, str):
                    return m
            except Exception:
                continue
        return ""

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
        values = dict(os.environ)
        try:
            text = self.env_path.read_text()
        except FileNotFoundError:
            text = ""
        except OSError as error:
            raise ValueError("Inventory secret source is unreadable") from error
        for line in text.splitlines():
            match = re.match(r'^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line.strip())
            if not match or not self._SECRET_KEY_RE.search(match[1]):
                continue
            raw = match[2]
            try:
                try:
                    val = json.loads(raw) if raw.startswith('"') else None
                except ValueError:
                    val = None
                if not isinstance(val, str):
                    val = ' '.join(shlex.split(raw, comments=True))
            except ValueError as error:
                raise ValueError("Inventory secret source is malformed") from error
            # Scan both configured and effective values if they differ.
            if len(val) >= 8:
                secrets.add(val)
        for key, val in values.items():
            if self._SECRET_KEY_RE.search(key) and len(val) >= 8:
                secrets.add(val)
        return secrets

    def _assert_no_secrets(self, inv: dict):
        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for key, item in value.items():
                    yield str(key)
                    yield from strings(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    yield from strings(item)
        contents = list(strings(inv))
        for secret in self._load_secret_values():
            if any(secret in value for value in contents):
                raise ValueError("Inventory build aborted: a secret value "
                                 "appeared in the advertised inventory (FR-007)")

    # ---- remote cache (FR-008/FR-009) ----------------------------------

    def _cache_base(self, peer_identity):
        if not isinstance(peer_identity, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,199}", peer_identity):
            raise ValueError("Invalid inventory peer identity")
        base = self.manager.base_dir / "inventories"
        if base.is_symlink():
            raise ValueError("Inventory cache directory must not be a symlink")
        for suffix in (".json", ".meta.json"):
            path = base / (peer_identity + suffix)
            if path.is_symlink() or (path.exists() and not path.is_file()):
                raise ValueError("Inventory cache must be a regular file")
        return base

    def cache_remote(self, peer_identity: str, inventory: dict):
        from .certs import _write_secret
        base = self._cache_base(peer_identity)
        _write_secret(base / f"{peer_identity}.json", json.dumps(inventory, indent=2))
        _write_secret(base / f"{peer_identity}.meta.json",
            json.dumps({"received_at": _now(), "version": inventory.get("version")}))

    def load_remote(self, peer_identity: str, refresh_s: int = 21600) -> Optional[dict]:
        base = self._cache_base(peer_identity)
        inv_path = base / f"{peer_identity}.json"
        if not inv_path.is_file():
            return None
        inv = json.loads(inv_path.read_text())
        received_at = None
        try:
            received_at = json.loads((base / f"{peer_identity}.meta.json").read_text()).get("received_at")
        except Exception:
            pass
        stale = True
        if received_at:
            try:
                age = time.time() - calendar.timegm(time.strptime(received_at, "%Y-%m-%dT%H:%M:%SZ"))
                stale = age < 0 or age > (2 * refresh_s)
            except Exception:
                pass
        from .runtime import project_harness
        inv['harness']=project_harness(inv.get('harness'),observed_at=received_at)
        return {"inventory": inv, "received_at": received_at, "stale": stale}
