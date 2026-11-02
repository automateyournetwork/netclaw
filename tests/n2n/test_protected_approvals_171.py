"""Owner/session and signed admission attacks; synthetic authorities only."""

import asyncio
import copy
import multiprocessing
import uuid

import pytest

from protected_support_171 import APPROVAL, NOW, OperationPair, module, sha, wire_sign


def new_owner(tmp_path):
    now = [NOW]
    owner = module("protected_owner").OwnerAuthority(tmp_path / "owner", "fixture-installation", clock_ms=lambda: now[0])
    owner.init("Synthetic owner")
    return owner, now


def test_owner_ticket_is_one_use_and_raw_credentials_are_not_persisted(tmp_path):
    owner, _ = new_owner(tmp_path)
    ticket = owner.ticket()
    session = owner.login(ticket)
    with pytest.raises(module("protected_contract").ProtectedError):
        owner.login(ticket)
    database = owner.db_path.read_bytes()
    assert ticket.encode() not in database and session["cookie"].encode() not in database
    assert owner.session(session["cookie"])["session_hash"] == session["session_hash"]


@pytest.mark.parametrize("elapsed", [30 * 60 * 1000, 8 * 60 * 60 * 1000])
def test_owner_session_idle_and_absolute_expiry(tmp_path, elapsed):
    owner, now = new_owner(tmp_path)
    session = owner.login(owner.ticket())
    now[0] += elapsed
    with pytest.raises(module("protected_contract").ProtectedError):
        owner.session(session["cookie"])


def test_logout_requires_correct_csrf_and_revokes_existing_context(tmp_path):
    owner, _ = new_owner(tmp_path)
    session = owner.login(owner.ticket())
    context = {key: session[key] for key in ("principal", "auth_generation", "session_hash")}
    with pytest.raises(module("protected_contract").ProtectedError):
        owner.logout(session["cookie"], "wrong")
    with owner.authorize(context):
        pass
    owner.logout(session["cookie"], session["csrf_token"])
    with pytest.raises(module("protected_contract").ProtectedError):
        with owner.authorize(context):
            pytest.fail("revoked context became authority")


def test_generation_revokes_both_unused_tickets_and_existing_sessions(tmp_path):
    owner, _ = new_owner(tmp_path)
    old_ticket = owner.ticket()
    session = owner.login(owner.ticket())
    owner.revoke()
    for call in [lambda: owner.login(old_ticket), lambda: owner.session(session["cookie"])]:
        with pytest.raises(module("protected_contract").ProtectedError):
            call()
    assert owner.login(owner.ticket())["auth_generation"] == session["auth_generation"] + 1


def login_worker(path, ticket, ready, start, output):
    owner = module("protected_owner").OwnerAuthority(path, "fixture-installation", clock_ms=lambda: NOW)
    ready.put(True)
    start.wait(15)
    try:
        output.put(("accepted", owner.login(ticket)["session_hash"]))
    except module("protected_contract").ProtectedError as exc:
        output.put(("refused", exc.code))


def test_separate_processes_cannot_reuse_one_owner_ticket(tmp_path):
    owner, _ = new_owner(tmp_path)
    ticket = owner.ticket()
    context = multiprocessing.get_context("spawn")
    ready, output, start = context.Queue(), context.Queue(), context.Event()
    workers = [context.Process(target=login_worker, args=(str(owner.directory), ticket, ready, start, output)) for _ in range(6)]
    try:
        for worker in workers: worker.start()
        for _ in workers: ready.get(timeout=20)
        start.set()
        results = [output.get(timeout=20) for _ in workers]
        for worker in workers:
            worker.join(timeout=10)
            assert worker.exitcode == 0
        assert sum(status == "accepted" for status, _ in results) == 1
        assert sum(status == "refused" for status, _ in results) == 5
    finally:
        start.set()
        for worker in workers:
            if worker.is_alive():
                worker.terminate(); worker.join(timeout=5)


@pytest.mark.parametrize("field,value", [("auth_generation", 99), ("session_hash", "0" * 64),
    ("principal", {"issuer": "local", "subject": str(uuid.uuid4()), "display_name": "Attacker", "roles": ["owner"]})])
def test_client_identity_substitution_cannot_establish_owner(tmp_path, field, value):
    async def run():
        pair = OperationPair(tmp_path)
        context = copy.deepcopy(pair.auth)
        context[field] = value
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.border.catalog({"auth_context": context})
        assert pair.transport_calls == [] and pair.effects == []
    asyncio.run(run())


def resign_modified(pair, mutation):
    payload = copy.deepcopy(pair.template)
    payload["principal"] = pair.principal
    mutation(payload)
    payload["tool_call"]["arguments_sha256"] = sha(payload["tool_call"]["arguments"])
    payload["review_sha256"] = sha({key: payload[key] for key in (
        "principal", "border", "member", "model_profile", "tool_call", "limits", "change_request_ref")})
    return wire_sign(APPROVAL, payload, pair.border_signer)


@pytest.mark.parametrize("mutation", [
    lambda p: p["tool_call"]["arguments"].update(device_name="foreign-router"),
    lambda p: p["tool_call"]["arguments"].update(command="show running-config"),
    lambda p: p["tool_call"].update(endpoint_sha256="f" * 64),
    lambda p: p["tool_call"].update(inventory_revision="changed"),
    lambda p: p["model_profile"].update(runtime_kind="hermes"),
    lambda p: p["model_profile"].update(model="foreign-model"),
    lambda p: p["member"].update(enrollment_generation="replaced-generation"),
    lambda p: p["limits"].update(expires_at_ms=NOW),
])
def test_valid_signature_cannot_widen_current_member_catalog(tmp_path, mutation):
    async def run():
        pair = OperationPair(tmp_path)
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.member.submit(pair.to_member, {"approval": resign_modified(pair, mutation)})
        await pair.drain()
        assert pair.executor_calls == 0 and pair.effects == []
    asyncio.run(run())


def test_hermes_profile_cannot_be_substituted_with_openclaw(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        pair.template["model_profile"]["runtime_kind"] = "hermes"
        envelope = resign_modified(pair, lambda p: p["model_profile"].update(runtime_kind="openclaw"))
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.member.submit(pair.to_member, {"approval": envelope})
        assert pair.executor_calls == 0 and pair.effects == []
    asyncio.run(run())


def test_revocation_during_inference_prevents_effect(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        prepared = await pair.prepare()
        async def revoke(payload):
            await pair.border.revoke({"auth_context": pair.auth, "operation_id": prepared["operation_id"]})
        pair.before_gate = revoke
        await pair.decide(prepared)
        await pair.drain()
        assert pair.executor_calls == 1 and pair.effects == []
        assert not pair.member.store.get("member", prepared["operation_id"])["effect_claimed"]
    asyncio.run(run())


def test_owner_revoked_during_catalog_io_receives_no_private_catalog(tmp_path):
    async def run():
        pair = OperationPair(tmp_path)
        async def revoke_and_return():
            pair.owner.revoke()
            return [pair.catalog_entry]
        pair.border.catalog_provider = revoke_and_return
        with pytest.raises(module("protected_contract").ProtectedError):
            await pair.border.catalog({"auth_context": pair.auth})
    asyncio.run(run())
