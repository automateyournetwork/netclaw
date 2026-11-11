"""Spec 190: read/write access class on per-peer grants (issue #344).

Decision matrix, backward compatibility, classification sources, skill delegation,
approval/limit/card/knowledge interactions, daemon routes.
"""
import asyncio
import importlib.util
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

from bgp.federation import invocation
from bgp.federation.authorization import Authorizer
from bgp.federation.channel import RpcError, ERR_NOT_ALLOWLISTED
from bgp.federation.manager import FederationManager, peer_identity
from bgp.federation.service import FederationService

T_READ, T_WRITE, T_UNK = "cml-mcp/list_labs", "cml-mcp/start_lab", "cml-mcp/mystery"


def _federated(manager, asn=65007, rid="7.7.7.7"):
    manager.local_consent(asn, rid)
    manager.remote_consent(asn, rid)
    return peer_identity(asn, rid)


class _Audit:
    def __init__(self):
        self.rows = []

    def record(self, **kw):
        self.rows.append(kw)
        return len(self.rows)


@pytest.fixture
def authz(manager):
    a = Authorizer(manager)
    a.audit = _Audit()
    a.rate_per_min = 1000
    a.classify("tool", T_READ, "read")
    a.classify("tool", T_WRITE, "write")
    return a


@pytest.fixture
def ident(manager):
    return _federated(manager)


# ------------------------------------------------ US1/US2: matrix + defaults

@pytest.mark.parametrize("grant_class,target,allowed", [
    ("read", T_READ, True), ("read", T_WRITE, False), ("read", T_UNK, False),
    ("read_write", T_READ, True), ("read_write", T_WRITE, True), ("read_write", T_UNK, True),
])
def test_tool_matrix(authz, ident, grant_class, target, allowed):
    authz.grant(ident, "tool", target, access_class=grant_class)
    d = authz.authorize(ident, "tool", target)
    assert d.allowed is allowed
    if not allowed:
        assert d.code == "not_allowlisted"
        assert d.audit_code == "access_class_denied"
        # same reason text as an ungranted target: no classification oracle
        ungranted = authz.authorize(ident, "tool", "cml-mcp/never_granted")
        assert d.reason.replace(target, "X") == ungranted.reason.replace("cml-mcp/never_granted", "X")


@pytest.mark.parametrize("ttype", ["knowledge", "knowledge_replica"])
def test_knowledge_targets_are_intrinsically_read(authz, ident, ttype):
    authz.grant(ident, ttype, "knowledge:docs", access_class="read")
    assert authz.authorize(ident, ttype, "knowledge:docs").allowed


def test_knowledge_grant_does_not_imply_replica(authz, ident):
    authz.grant(ident, "knowledge", "knowledge:docs", access_class="read")
    d = authz.authorize(ident, "knowledge_replica", "knowledge:docs")
    assert not d.allowed and d.audit_code is None   # plain not_allowlisted, unchanged


def test_unknown_target_type_with_read_grant_is_refused(authz, ident):
    authz.grant(ident, "widget", "w1", access_class="read")
    assert not authz.authorize(ident, "widget", "w1").allowed


def test_legacy_rows_and_omitted_class_are_read_write(manager, authz, ident):
    # a row written by pre-190 code (no access_class column value given)
    manager._conn.execute(
        "INSERT INTO invocation_grant (peer_identity,target_type,target_name,requires_approval,created_at) "
        "VALUES (?,?,?,0,'2020-01-01T00:00:00Z')", (ident, "tool", T_UNK))
    manager._conn.commit()
    assert authz.list_grants(ident)[0]["access_class"] == "read_write"
    assert authz.authorize(ident, "tool", T_UNK).allowed
    gid = authz.grant(ident, "tool", T_WRITE)
    assert [g for g in authz.list_grants(ident) if g["id"] == gid][0]["access_class"] == "read_write"
    assert authz.authorize(ident, "tool", T_WRITE).allowed


def test_old_database_without_column_migrates(tmp_path):
    base = tmp_path / "n2n"
    m = FederationManager(base_dir=str(base))
    m._conn.execute("DROP TABLE invocation_grant")
    m._conn.execute("CREATE TABLE invocation_grant (id INTEGER PRIMARY KEY AUTOINCREMENT, peer_identity TEXT NOT NULL,"
                    " target_type TEXT NOT NULL, target_name TEXT NOT NULL, requires_approval INTEGER NOT NULL DEFAULT 0,"
                    " timeout_s INTEGER, created_at TEXT NOT NULL, revoked_at TEXT)")
    m._conn.execute("INSERT INTO invocation_grant (peer_identity,target_type,target_name,created_at) "
                    "VALUES ('p','tool','a/b','2020')")
    m._conn.commit()
    m.close()
    m2 = FederationManager(base_dir=str(base))
    try:
        assert Authorizer(m2).list_grants("p")[0]["access_class"] == "read_write"
    finally:
        m2.close()


def test_node_default_applies_only_to_new_grants(manager, authz, ident, monkeypatch):
    old = authz.grant(ident, "tool", T_READ)
    monkeypatch.setenv("N2N_GRANT_DEFAULT_ACCESS", "read")
    a2 = Authorizer(manager)
    new = a2.grant(ident, "tool", T_WRITE)
    by_id = {g["id"]: g["access_class"] for g in a2.list_grants(ident)}
    assert by_id[old] == "read_write" and by_id[new] == "read"
    monkeypatch.setenv("N2N_GRANT_DEFAULT_ACCESS", "bogus")
    assert Authorizer(manager).default_access_class == "read_write"


def test_invalid_class_rejected_nothing_stored(authz, ident):
    with pytest.raises(ValueError):
        authz.grant(ident, "tool", T_READ, access_class="admin")
    assert authz.list_grants(ident) == []


def test_different_class_supersedes_same_class_does_not(authz, ident):
    g1 = authz.grant(ident, "tool", T_READ, access_class="read_write")
    g2 = authz.grant(ident, "tool", T_READ, access_class="read")
    active = authz.list_grants(ident)
    assert [g["id"] for g in active] == [g2] and g1 != g2
    g3 = authz.grant(ident, "tool", T_READ, access_class="read")
    assert len(authz.list_grants(ident)) == 2 and g3 != g2   # same class: pre-190 insertion behavior


# ------------------------------------------------ refusals are free (SC-004)

def test_refusal_debits_nothing_and_never_triggers_limit_action(authz, ident):
    authz.set_policy(ident, action="teardown", rate_per_min=1, daily_requests=1)
    closed = []
    authz.teardown_hook = lambda p, r: closed.append(p)
    authz.grant(ident, "tool", T_WRITE, access_class="read")
    for _ in range(5):
        d = authz.authorize(ident, "tool", T_WRITE)
        assert d.code == "not_allowlisted" and not d.teardown
    assert authz.budget_status(ident)["requests_used"] == 0
    assert authz.limit_status(ident)["rate_used"] == 0
    assert closed == [] and authz.hold_down_remaining(ident) == 0
    # a permitted read still gets its full single rate slot / request unit
    authz.grant(ident, "tool", T_READ, access_class="read")
    d = authz.authorize(ident, "tool", T_READ)
    assert d.allowed
    assert authz.admit(ident, "tool", T_READ, d).allowed
    assert authz.budget_status(ident)["requests_used"] == 1


# ------------------------------------------------ US3: classification sources

def test_annotation_mapping_and_override_precedence(manager, ident):
    a = Authorizer(manager)
    out = a.import_annotations("cml-mcp", [
        {"name": "list_labs", "annotations": {"readOnlyHint": True}},
        {"name": "start_lab", "annotations": {"readOnlyHint": False}},
        {"name": "mystery", "annotations": {}},
        {"name": "bare"}])
    assert out == {"imported": 2, "skipped": 2}
    assert a.effective_class("tool", T_READ) == "read"
    assert a.effective_class("tool", T_WRITE) == "write"
    assert a.effective_class("tool", T_UNK) == "unclassified"
    a.classify("tool", T_READ, "write")                 # operator beats annotation
    assert a.effective_class("tool", T_READ) == "write"
    a.classify("tool", T_READ, None)                    # clear -> annotation again
    assert a.effective_class("tool", T_READ) == "read"
    sources = {(r["target_name"], r["source"]) for r in a.list_classifications()}
    assert (T_READ, "annotation") in sources


def test_classification_validation_changes_nothing(manager):
    a = Authorizer(manager)
    for bad in (lambda: a.classify("tool", "x/y", "admin"), lambda: a.classify("knowledge", "x", "read"),
                lambda: a.import_annotations("cml-mcp", [{"name": "a", "annotations": {"readOnlyHint": "yes"}}]),
                lambda: a.import_annotations("cml-mcp", "nope"),
                lambda: a.import_annotations("bad/server", [])):
        with pytest.raises(ValueError):
            bad()
    assert a.list_classifications() == []


def test_classification_changes_are_audited(authz):
    authz.classify("skill", "s1", "read")
    authz.classify("skill", "s1", None)
    authz.import_annotations("srv", [{"name": "t", "annotations": {"readOnlyHint": True}}])
    decisions = [r["decision"] for r in authz.audit.rows if r["target_type"] == "classification"]
    assert decisions[-3:] == ["classified", "classification_cleared", "classification_imported"]


# ------------------------------------------------ admission revalidation / approvals

def test_reclassification_during_wait_is_caught_at_admit(authz, ident):
    authz.grant(ident, "tool", T_READ, access_class="read")
    d = authz.authorize(ident, "tool", T_READ)
    assert d.allowed
    authz.classify("tool", T_READ, "write")             # operator reclassifies mid-flight
    out = authz.admit(ident, "tool", T_READ, d)
    assert not out.allowed and out.code == "not_allowlisted"
    assert authz.budget_status(ident)["requests_used"] == 0


def test_reclassification_during_approval_wait(authz, ident):
    authz.grant(ident, "tool", T_READ, requires_approval=True, access_class="read")
    d = authz.authorize(ident, "tool", T_READ)
    assert d.code == "approval_required"
    authz.classify("tool", T_READ, "write")
    out = authz.admit(ident, "tool", T_READ, d)
    assert not out.allowed and out.code == "not_allowlisted"


def test_read_grant_with_approval_on_write_target_creates_no_approval(authz, ident):
    authz.grant(ident, "tool", T_WRITE, requires_approval=True, access_class="read")
    d = authz.authorize(ident, "tool", T_WRITE)
    assert d.code == "not_allowlisted" and d.approval_id is None
    assert authz.pending_approvals() == []


def test_read_grant_with_approval_on_read_target_requires_approval_not_widened(authz, ident):
    authz.grant(ident, "tool", T_READ, requires_approval=True, access_class="read")
    assert authz.authorize(ident, "tool", T_READ).code == "approval_required"
    # approval does not widen: a write target under the same class stays refused
    authz.grant(ident, "tool", T_WRITE, requires_approval=True, access_class="read")
    assert authz.authorize(ident, "tool", T_WRITE).code == "not_allowlisted"


def test_superseding_grant_invalidates_pending_approval(authz, ident):
    authz.grant(ident, "tool", T_READ, requires_approval=True, access_class="read_write")
    d = authz.authorize(ident, "tool", T_READ)
    assert d.code == "approval_required"
    authz.grant(ident, "tool", T_READ, requires_approval=True, access_class="read")   # supersedes
    out = authz.admit(ident, "tool", T_READ, d)
    assert not out.allowed and out.code == "not_allowlisted"


def test_already_trusted_internal_channel_same_check(authz):
    authz.grant("risk/member1", "tool", T_WRITE, access_class="read")
    authz.grant("risk/member1", "tool", T_READ, access_class="read")
    assert not authz.authorize("risk/member1", "tool", T_WRITE, already_trusted=True).allowed
    assert authz.authorize("risk/member1", "tool", T_READ, already_trusted=True).allowed


# ------------------------------------------------ US4: skill delegation through the handlers

def _svc(tmp_path, monkeypatch):
    monkeypatch.setattr(invocation, "_security_mode", lambda: "hobby")
    svc = FederationService(local_as=65001, router_id="4.4.4.4", display_name="fixture",
                            manager=FederationManager(base_dir=str(tmp_path)))
    ident = _federated(svc.manager)
    svc.authz.rate_per_min = 1000
    return svc, SimpleNamespace(peer_identity=ident, attestation="possession")


def test_skill_delegation_text_never_decides_class(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    ran = []

    async def skill(*a, **k):
        ran.append(1)
        return "out", 1
    svc.invoker._exec_skill_gateway = skill
    svc.authz.grant(ch.peer_identity, "skill", "cml-lab-lifecycle", access_class="read")

    async def submit(text):
        return await svc.invoker.handle_task_submit(ch, {"skill": "cml-lab-lifecycle", "input_text": text})

    async def run():
        for text in ("list my labs", "stop lab 3 and wipe it", ""):
            with pytest.raises(RpcError) as e:
                await submit(text)
            assert e.value.code == ERR_NOT_ALLOWLISTED
        assert ran == []
        assert svc.manager._conn.execute("SELECT COUNT(*) FROM delegated_task").fetchone()[0] == 0
        svc.authz.classify("skill", "cml-lab-lifecycle", "read")
        for text in ("list my labs", "stop lab 3 and wipe it"):
            sub = await submit(text)
            await asyncio.gather(*list(svc.tasks._workers.values()))
            assert sub["task_id"]
        assert len(ran) == 2
        rows = [r for r in svc.audit.recent(peer_identity=ch.peer_identity)]
        assert any(r["decision"] == "access_class_denied" and r["outcome"] == "denied" for r in rows)
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()


def test_tools_call_refusal_wire_code_and_audit(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    ran = []

    async def tool(*a, **k):
        ran.append(1)
        return {}
    svc.invoker._exec_tool_stdio = tool
    svc.authz.classify("tool", T_WRITE, "write")
    svc.authz.grant(ch.peer_identity, "tool", T_WRITE, access_class="read")

    async def run():
        with pytest.raises(RpcError) as e:
            await svc.invoker.handle_tools_call(ch, {"tool": T_WRITE})
        assert e.value.code == ERR_NOT_ALLOWLISTED and ran == []
        assert svc.authz.budget_status(ch.peer_identity)["requests_used"] == 0
    try:
        asyncio.run(run())
        rows = svc.audit.recent(peer_identity=ch.peer_identity)
        assert [r["decision"] for r in rows if r["target_name"] == T_WRITE] == ["access_class_denied"]
    finally:
        svc.manager.close()


# ------------------------------------------------ card hints (advisory)

def test_card_carries_advisory_hints_and_visibility_unchanged(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    inv = svc.inventory
    monkeypatch.setattr(inv, "_load_mcp_servers", lambda: [
        {"name": "cml-mcp", "tools": ["list_labs", "start_lab", "mystery"],
         "invocable_tools": ["list_labs"], "qualification": "configured"},
        {"name": "hidden-mcp", "tools": ["x"], "invocable_tools": [], "qualification": "configured"}])
    monkeypatch.setattr(inv, "_load_skills", lambda: [{"name": "cml-lab-lifecycle", "description": "d"}])
    svc.authz.classify("tool", T_READ, "read")
    svc.authz.classify("tool", T_WRITE, "write")
    svc.authz.classify("skill", "cml-lab-lifecycle", "read")
    svc.manager._conn.execute("INSERT INTO visibility_setting VALUES ('mcp_server','hidden-mcp','hidden',NULL)")
    svc.manager._conn.commit()
    try:
        card = inv.build(ch.peer_identity)
        names = [s["name"] for s in card["mcp_servers"]]
        assert names == ["cml-mcp"]                       # visibility untouched
        assert card["mcp_servers"][0]["tool_access"] == {"list_labs": "read", "start_lab": "write"}
        assert [s.get("access") for s in card["skills"]] == ["read"]
        # hints never authorize: a read grant on the advertised-read tool is still checked locally
        svc.authz.classify("tool", T_READ, "write")
        svc.authz.grant(ch.peer_identity, "tool", T_READ, access_class="read")
        assert not svc.authz.authorize(ch.peer_identity, "tool", T_READ).allowed
    finally:
        svc.manager.close()


def test_card_without_classifications_has_no_new_members(tmp_path, monkeypatch):
    svc, ch = _svc(tmp_path, monkeypatch)
    monkeypatch.setattr(svc.inventory, "_load_mcp_servers", lambda: [
        {"name": "cml-mcp", "tools": ["list_labs"], "invocable_tools": [], "qualification": "configured"}])
    monkeypatch.setattr(svc.inventory, "_load_skills", lambda: [{"name": "s", "description": ""}])
    try:
        card = svc.inventory.build(ch.peer_identity)
        assert "tool_access" not in card["mcp_servers"][0] and "access" not in card["skills"][0]
    finally:
        svc.manager.close()


# ------------------------------------------------ daemon routes

def test_daemon_grant_and_classification_routes(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[2] / "mcp-servers/protocol-mcp/bgp-daemon-v2.py"
    spec = importlib.util.spec_from_file_location("grant_daemon_190", path)
    daemon = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daemon)
    svc, ch = _svc(tmp_path, monkeypatch)
    ident = ch.peer_identity
    daemon._federation = svc

    async def run():
        code, out = await daemon.handle_n2n("POST", "/n2n/grants", {
            "peer": ident, "target_type": "tool", "target_name": T_READ, "access_class": "read"})
        assert code == 200 and out["access_class"] == "read"
        code, out = await daemon.handle_n2n("POST", "/n2n/grants", {
            "peer": ident, "target_type": "tool", "target_name": T_WRITE})
        assert code == 200 and out["access_class"] == "read_write"
        code, out = await daemon.handle_n2n("POST", "/n2n/grants", {
            "peer": ident, "target_type": "tool", "target_name": "a/b", "access_class": "root"})
        assert code == 400 and len(svc.authz.list_grants(ident)) == 2
        code, out = await daemon.handle_n2n("GET", "/n2n/grants", {"peer": ident})
        assert {g["access_class"] for g in out["grants"]} == {"read", "read_write"}
        code, out = await daemon.handle_n2n("POST", "/n2n/classifications", {
            "target_type": "tool", "target_name": T_READ, "access": "read"})
        assert code == 200 and out["class"] == "read"
        code, out = await daemon.handle_n2n("POST", "/n2n/classifications", {
            "server": "cml-mcp", "tools": [{"name": "start_lab", "annotations": {"readOnlyHint": False}}]})
        assert code == 200 and out["imported"] == 1
        code, out = await daemon.handle_n2n("POST", "/n2n/classifications", {
            "target_type": "tool", "target_name": T_READ, "access": "bogus"})
        assert code == 400
        code, out = await daemon.handle_n2n("POST", "/n2n/classifications", {
            "target_type": "tool", "target_name": T_READ, "clear": True})
        assert code == 200 and out["class"] == "unclassified"
        code, out = await daemon.handle_n2n("GET", "/n2n/classifications", {})
        assert [c["target_name"] for c in out["classifications"]] == [T_WRITE]
        code, out = await daemon.handle_n2n("POST", "/n2n/trust", {"peer": ident, "tools": [T_UNK], "access_class": "x"})
        assert code == 400
        code, out = await daemon.handle_n2n("POST", "/n2n/trust", {"peer": ident, "tools": [T_UNK], "access_class": "read"})
        assert code == 200
        assert [g for g in svc.authz.list_grants(ident) if g["target_name"] == T_UNK][0]["access_class"] == "read"
        audit = svc.audit.recent(peer_identity=ident)
        assert any(r["decision"] == "granted" and r["outcome"] == "success:read" for r in audit)
    try:
        asyncio.run(run())
    finally:
        svc.manager.close()
