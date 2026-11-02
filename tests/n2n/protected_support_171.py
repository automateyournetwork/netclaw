"""Independent synthetic inputs for Spec171 boundary tests; never live evidence.

The optional source override lets this isolated verification worktree exercise a
production sibling without editing either sibling or copying its implementation.
"""

import base64
import copy
import datetime
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import uuid
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID


REPO = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get("NETCLAW_171_TEST_SOURCE", REPO)).resolve()
sys.path.insert(0, str(SOURCE / "mcp-servers" / "protocol-mcp"))

APPROVAL = "netclaw.execution.approval.v1"
RESULT = "netclaw.execution.result.v1"
ACK = "netclaw.execution.ack.v1"
NOW = 1_800_000_000_000


def module(name):
    return importlib.import_module("bgp.federation." + name)


def runtime_module():
    root = Path(os.environ.get("NETCLAW_171_RUNTIME_SOURCE", SOURCE)).resolve()
    path = root / "mcp-servers/protocol-mcp/bgp/federation/protected_runtime.py"
    return file_module("bgp.federation.protected_runtime", path)


def pyats_module():
    root = Path(os.environ.get("NETCLAW_171_RUNTIME_SOURCE", SOURCE)).resolve()
    return file_module("independent_protected_pyats_171", root / "scripts/lib/protected_pyats.py")


def docker_module():
    runtime_module()
    root = Path(os.environ.get("NETCLAW_171_RUNTIME_SOURCE", SOURCE)).resolve()
    return file_module("bgp.federation.protected_docker", root / "mcp-servers/protocol-mcp/bgp/federation/protected_docker.py")


def relay_module():
    root = Path(os.environ.get("NETCLAW_171_RUNTIME_SOURCE", SOURCE)).resolve()
    return file_module("independent_protected_relay_171", root / "scripts/protected-inference.py")


def file_module(name, path):
    import importlib.util
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        loaded = importlib.util.module_from_spec(spec)
        sys.modules[name] = loaded
        spec.loader.exec_module(loaded)
    return sys.modules[name]


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def identity(label):
    """Generate test-only keys without using production signing helpers."""
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(serialization.Encoding.DER,
                                          serialization.PublicFormat.SubjectPublicKeyInfo)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)])
    before = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(before).not_valid_after(before + datetime.timedelta(days=3650))
            .sign(key, hashes.SHA256()))
    return {
        "key": key,
        "key_pem": key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
        "cert_pem": cert.public_bytes(serialization.Encoding.PEM).decode(),
        "key_id": hashlib.sha256(public).hexdigest(),
    }


def wire_sign(schema, payload, signer):
    """Sign an intentionally unvalidated message for adversarial wire tests."""
    body = canonical({"schema": schema, "payload": payload})
    message = b"netclaw.r02/" + schema.encode("ascii") + b"\0" + body
    signature = signer["key"].sign(message, ec.ECDSA(hashes.SHA256()))
    return {"schema": schema, "payload": copy.deepcopy(payload), "signature": {
        "algorithm": "ecdsa-p256-sha256", "key_id": signer["key_id"],
        "value": base64.urlsafe_b64encode(signature).decode().rstrip("="),
    }}


def approval(border_signer, member_signer, *, now=NOW):
    arguments = {"device_name": "fixture-router", "command": "show version",
                 "timeout": 30, "retries": 1}
    review = {
        "principal": {"issuer": "local", "subject": str(uuid.uuid4()),
                      "display_name": "Owner Montréal", "roles": ["owner"]},
        "border": {"installation_id": str(uuid.uuid4()), "identity": "fixture/border",
                   "key_id": border_signer["key_id"], "authority_generation": "border-generation-1"},
        "member": {"installation_id": str(uuid.uuid4()), "member_id": "fixture/member",
                   "key_id": member_signer["key_id"], "enrollment_generation": "member-generation-1"},
        "model_profile": {"profile_id": "fixture-sonnet", "profile_revision": "1",
                          "runtime_kind": "openclaw", "runtime_version": "fixture-1",
                          "provider": "anthropic", "model": "fixture-sonnet",
                          "guard_policy_sha256": "a" * 64},
        "tool_call": {"tool": "pyats_run_show_command", "tool_schema_sha256": "b" * 64,
                      "arguments": arguments, "arguments_sha256": sha(arguments),
                      "device_ref": "fixture-router", "inventory_revision": "1",
                      "endpoint_sha256": "c" * 64},
        "limits": {"expires_at_ms": now + 60_000, "inference_timeout_ms": 30_000,
                   "tool_timeout_ms": 30_000, "max_inference_calls": 2,
                   "max_tool_calls": 1, "max_output_bytes": 512 * 1024},
        "change_request_ref": None,
    }
    return {"approval_id": str(uuid.uuid4()), "operation_id": str(uuid.uuid4()),
            "nonce": base64.urlsafe_b64encode(os.urandom(32)).decode().rstrip("="),
            "issued_at_ms": now, **review,
            "review_sha256": sha(review)}


class OperationPair:
    """Two real protocol services over an explicitly synthetic authenticated link.

    This verifies message/ledger authority, not network authentication, Docker
    containment, a provider or a device. Those need independent live acceptance.
    """
    def __init__(self, directory):
        self.directory = Path(directory)
        self.now = NOW
        self.border_signer, self.member_signer = identity("border"), identity("member")
        self.template = approval(self.border_signer, self.member_signer)
        self.managers = {}
        for role in ("border", "member"):
            path = self.directory / role
            path.mkdir(parents=True, mode=0o700)
            self.managers[role] = SimpleNamespace(base_dir=str(path), db_path=str(path / "federation.db"))
        self.owner = module("protected_owner").OwnerAuthority(
            self.directory / "border" / "owner", self.template["border"]["installation_id"], clock_ms=lambda: self.now)
        self.principal = self.owner.init("Synthetic owner", subject=self.template["principal"]["subject"])
        self.auth = self.login()
        self.catalog_entry = {"member": self.template["member"],
            "model_profiles": [self.template["model_profile"]],
            "tools": [{**self.template["tool_call"], "limits": self.template["limits"]}]}
        self.transport_calls, self.audit_events, self.effects = [], [], []
        self.executor_calls = 0
        self.failed_audits = set()
        self.drop_submit_reply = False
        self.drop_ack_reply = False
        self.mutate_receipt = None
        self.executor_error = None
        self.before_gate = None
        self.accepted_bindings = [self.template["border"], self.template["member"]]
        self._build()

    def login(self):
        self.session = self.owner.login(self.owner.ticket())
        return {key: self.session[key] for key in ("principal", "auth_generation", "session_hash")}

    def _build(self):
        contract, service = module("protected_contract"), module("protected_service")
        def trust(binding, historical=False):
            if binding not in self.accepted_bindings:
                raise contract.ProtectedError("fixture_authority_revoked", 403)
            return self.border_signer["cert_pem"] if binding == self.template["border"] else self.member_signer["cert_pem"]
        def audit(event, record):
            if event in self.failed_audits:
                return None
            self.audit_events.append((event, copy.deepcopy(record)))
            return "fixture-audit-" + str(len(self.audit_events))
        self.to_member = SimpleNamespace(strict=True, trusted=True, attestation="possession",
            protected_peer_binding=self.template["border"], authority_current=lambda: True)
        self.to_border = SimpleNamespace(strict=True, trusted=True, attestation="possession",
            protected_peer_binding=self.template["member"], authority_current=lambda: True)
        async def effect_authorize(method, params):
            assert method == "execution/effect-authorize"
            return await self.border.effect_authorize(self.to_border, params)
        self.to_member.call = effect_authorize
        async def transport(member, method, params):
            import asyncio
            await asyncio.sleep(0)  # Real transports yield; expose stale concurrent snapshots.
            assert member == self.template["member"]["member_id"]
            self.transport_calls.append((method, copy.deepcopy(params)))
            handler = {"execution/submit": self.member.submit, "execution/status": self.member.member_status,
                       "execution/result": self.member.member_result, "execution/ack": self.member.acknowledge}[method]
            result = await handler(self.to_member, params)
            if method == "execution/submit" and self.drop_submit_reply:
                raise ConnectionError("synthetic lost submit reply")
            if method == "execution/ack" and self.drop_ack_reply:
                raise ConnectionError("synthetic lost ACK reply")
            if method == "execution/result" and self.mutate_receipt:
                result = copy.deepcopy(result)
                self.mutate_receipt(result)
            return result
        parent = self
        class Executor:
            async def run(self, payload, gate):
                parent.executor_calls += 1
                if parent.executor_error:
                    raise parent.executor_error
                if parent.before_gate:
                    await parent.before_gate(payload)
                async def effect():
                    evidence = {"device": payload["tool_call"]["device_ref"],
                        "command": "show version", "parsed": True,
                        "output": {"version": {"version": "synthetic-evidence"}}}
                    parent.effects.append(copy.deepcopy(evidence))
                    return evidence
                evidence = await gate(copy.deepcopy(payload["tool_call"]), effect)
                return {"output": {"tool_evidence": evidence, "answer": "Synthetic answer"},
                    "tool_evidence": evidence, "usage": {"available": False},
                    "effective_model_profile": payload["model_profile"]}
        common = {"trust_resolver": trust, "audit_writer": audit, "clock_ms": lambda: self.now}
        self.member = service.ProtectedOperations(self.managers["member"], role="member",
            identity=self.template["member"], signer=lambda schema, payload: wire_sign(schema, payload, self.member_signer),
            catalog_provider=lambda: copy.deepcopy(self.catalog_entry), executor=Executor(), **common)
        self.border = service.ProtectedOperations(self.managers["border"], role="border",
            identity=self.template["border"], signer=lambda schema, payload: wire_sign(schema, payload, self.border_signer),
            catalog_provider=lambda: [copy.deepcopy(self.catalog_entry)], owner=self.owner, transport=transport, **common)

    async def prepare(self, *, nonce="fixture-request"):
        catalog = await self.border.catalog({"auth_context": self.auth})
        return await self.border.prepare({"auth_context": self.auth, "client_nonce": nonce,
            "catalog_revision": catalog["revision"], "member_id": self.template["member"]["member_id"],
            "model_profile_id": self.template["model_profile"]["profile_id"],
            "tool": self.template["tool_call"]["tool"], "arguments": self.template["tool_call"]["arguments"]})

    async def decide(self, prepared, decision="approve"):
        return await self.border.decision({"auth_context": self.auth,
            "operation_id": prepared["operation_id"], "revision": prepared["revision"],
            "review_digest": prepared["review_digest"], "decision": decision})

    async def drain(self):
        import asyncio
        if self.member.workers:
            await asyncio.gather(*tuple(self.member.workers))

    async def reconcile(self, operation):
        return await self.border.reconcile({"auth_context": self.auth, "operation_id": operation})

    async def restart(self):
        await self.border.close()
        await self.member.close()
        self._build()
        await self.border.start()
        await self.member.start()
