"""Platform push-notification fallback for a disconnected NCFED edge node
(feature 066, US3/T031/FR-011). Sends via Firebase Cloud Messaging (Android)
or Apple Push Notification service (iOS) depending on the member's
registered `push_platform`/`push_token` (RiskManager.register_push).

Both vendor integrations are implemented for real (JWT construction, OAuth2
token exchange, the actual HTTPS request) but are UNVERIFIED against a real
Firebase project or Apple Developer account — there is no way to test an
actually-delivered notification in this environment. Review the credential
wiring below against the current FCM/APNs docs before relying on it in
production.
"""

import base64
import json
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger("n2n.push_notify")

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
_fcm_token_cache: dict = {"token": None, "expires_at": 0.0}


def _b64url(data: bytes) -> bytes:
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def _fcm_service_account() -> Optional[dict]:
    path = os.environ.get("FCM_SERVICE_ACCOUNT_JSON")
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


async def _fcm_access_token(sa: dict) -> str:
    """Exchanges the service account's RS256-signed JWT assertion for a
    short-lived OAuth2 access token (Google's JWT Bearer flow) — cached
    until shortly before expiry."""
    now = time.time()
    if _fcm_token_cache["token"] and now < _fcm_token_cache["expires_at"] - 60:
        return _fcm_token_cache["token"]
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    header = _b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    iat = int(now)
    exp = iat + 3600
    claims = _b64url(json.dumps({
        "iss": sa["client_email"],
        "scope": FCM_SCOPE,
        "aud": sa["token_uri"],
        "iat": iat,
        "exp": exp,
    }, separators=(",", ":")).encode())
    signing_input = header + b"." + claims
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    assertion = signing_input + b"." + _b64url(signature)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(sa["token_uri"], data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": assertion.decode(),
        })
        resp.raise_for_status()
        data = resp.json()
    _fcm_token_cache["token"] = data["access_token"]
    _fcm_token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return _fcm_token_cache["token"]


def _preview(content: dict) -> str:
    if content.get("content_type") != "text":
        return f"[{content.get('content_type')}] new message"
    return str(content.get("content", ""))[:200]


async def send_fcm(token: str, content: dict) -> dict:
    """Sends one FCM v1 data+notification message. `content` is the same
    dict push_to_edge would have delivered over n2n/edge/message."""
    sa = _fcm_service_account()
    if not sa:
        raise RuntimeError("FCM_SERVICE_ACCOUNT_JSON not configured")
    access_token = await _fcm_access_token(sa)
    project_id = sa["project_id"]
    message = {
        "message": {
            "token": token,
            "notification": {"title": "NetClaw", "body": _preview(content)},
            "data": {k: str(v) for k, v in content.items()},
        }
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(
            f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send",
            headers={"Authorization": f"Bearer {access_token}"},
            json=message)
        resp.raise_for_status()
        return resp.json()


def _apns_jwt() -> str:
    """Builds the ES256 JWT APNs provider token (RFC 7515 JWS with a raw
    r||s signature — ECDSA.sign() produces DER, which APNs will not accept,
    so it's decoded back into fixed-width r/s)."""
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec, utils

    key_path = os.environ["APNS_KEY_PATH"]
    key_id = os.environ["APNS_KEY_ID"]
    team_id = os.environ["APNS_TEAM_ID"]
    with open(key_path) as f:
        key = serialization.load_pem_private_key(f.read().encode(), password=None)

    header = _b64url(json.dumps({"alg": "ES256", "kid": key_id}, separators=(",", ":")).encode())
    claims = _b64url(json.dumps({"iss": team_id, "iat": int(time.time())},
                                separators=(",", ":")).encode())
    signing_input = header + b"." + claims
    der_sig = key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r, s = utils.decode_dss_signature(der_sig)
    raw_sig = r.to_bytes(32, "big") + s.to_bytes(32, "big")
    return (signing_input + b"." + _b64url(raw_sig)).decode()


async def send_apns(token: str, content: dict) -> dict:
    """Sends one APNs notification over HTTP/2 (mandatory for APNs)."""
    bundle_id = os.environ.get("APNS_BUNDLE_ID")
    if not bundle_id or "APNS_KEY_PATH" not in os.environ:
        raise RuntimeError(
            "APNS_KEY_PATH/APNS_KEY_ID/APNS_TEAM_ID/APNS_BUNDLE_ID not configured")
    use_sandbox = os.environ.get("APNS_USE_SANDBOX", "").lower() in ("1", "true", "yes")
    host = "api.sandbox.push.apple.com" if use_sandbox else "api.push.apple.com"
    payload = {"aps": {"alert": {"title": "NetClaw", "body": _preview(content)}}}
    jwt = _apns_jwt()
    async with httpx.AsyncClient(http2=True, timeout=15.0) as client:
        resp = await client.post(
            f"https://{host}/3/device/{token}",
            headers={
                "authorization": f"bearer {jwt}",
                "apns-topic": bundle_id,
                "apns-push-type": "alert",
            },
            json=payload)
        resp.raise_for_status()
        return {"apns_id": resp.headers.get("apns-id")}


async def send_push_notification(member: dict, content: dict) -> dict:
    """Dispatches to FCM or APNs based on the member's registered platform.
    Raises if the member never registered a push token (nothing to fall
    back to) or the platform isn't configured."""
    platform = member.get("push_platform")
    token = member.get("push_token")
    if not platform or not token:
        raise RuntimeError(f"{member.get('member_id')} has no registered push token")
    if platform == "fcm":
        return await send_fcm(token, content)
    if platform == "apns":
        return await send_apns(token, content)
    raise RuntimeError(f"unsupported push platform {platform!r}")
