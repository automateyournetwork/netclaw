"""Platform push-notification fallback for a disconnected NCFED edge node
(feature 066, US3/T031/FR-011). Sends via Firebase Cloud Messaging for **every**
platform, including iOS — Firebase relays to APNs internally using the APNs auth
key uploaded to the Firebase project, so the Border never speaks Apple's raw
HTTP/2 API. See send_push_notification() for why (spec 103, decision 2026-08-10).

Status: the FCM path is **verified against a real device** — delivered to the
enrolled Android on 2026-08-10 16:56. A direct-to-APNs implementation used to
live here and was removed unexecuted: it required the raw APNs device token,
while the client registers an FCM registration token, so it could only ever have
returned `BadDeviceToken`.

Middle tier of three. Live WebSocket delivery is preferred (FederationService.
push_to_edge); if the device is disconnected this runs; if this also fails the
content is queued and replayed on next connect (edge_queue.py). No tier is
load-bearing alone — a phone with no working push transport still loses nothing.
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


def _looks_like_raw_apns_token(token: str) -> bool:
    """A raw APNs device token is hex, 64 chars (older) or 160 (newer). An FCM
    registration token is much longer and contains ':' plus non-hex characters."""
    t = token.strip()
    if len(t) not in (64, 160):
        return False
    try:
        int(t, 16)
    except ValueError:
        return False
    return True


async def send_push_notification(member: dict, content: dict) -> dict:
    """Sends one push via FCM, whatever the device's platform.

    **Every platform goes through FCM, including iOS** (decision 2026-08-10,
    spec 103). Firebase relays to APNs internally using the APNs auth key
    uploaded to the Firebase project's Cloud Messaging config, so the Border
    never talks to Apple's raw API.

    Why not direct-to-APNs: the client registers
    `FirebaseMessaging.instance.getToken()`, which is an **FCM registration
    token**, not the raw APNs device token that
    `https://api.push.apple.com/3/device/{token}` requires — posting one to the
    other returns `BadDeviceToken`. Confirmed empirically: the enrolled iPhone
    had `push_platform='apns'` with a 142-char `<instanceID>:APA91b…` FCM token.
    Rather than add a second delivery mechanism (and put ~60 lines of never-
    executed ES256/JWT code into production), iOS consolidates onto the FCM path
    that was already a dependency of this feature and already verified working
    against a real device.

    `platform='apns'` is still accepted so a device enrolled before that decision
    keeps working without re-registering — its token is an FCM token regardless.
    A genuinely raw APNs token is rejected loudly rather than being sent to FCM,
    which would otherwise fail as an opaque vendor error.
    """
    platform = member.get("push_platform")
    token = member.get("push_token")
    member_id = member.get("member_id")
    if not platform or not token:
        raise RuntimeError(f"{member_id} has no registered push token")
    if platform not in ("fcm", "apns"):
        raise RuntimeError(f"unsupported push platform {platform!r}")
    if _looks_like_raw_apns_token(token):
        raise RuntimeError(
            f"{member_id} registered a raw APNs device token, but this Border "
            f"delivers iOS pushes via FCM (spec 103, decision A). The client must "
            f"register FirebaseMessaging.instance.getToken(), not getAPNSToken().")
    if platform == "apns":
        logger.info("%s registered as 'apns'; delivering via FCM (its token is an "
                    "FCM registration token). Harmless — see send_push_notification.",
                    member_id)
    return await send_fcm(token, content)
