"""Credentials for each tool call: the HTTP request's bearer token, or the environment for stdio.

A bearer token is ``base64url(auth_id:auth_secret)``. With ``SIPRTC_VERIFY_BEARER`` on (the
default) a new token is checked once against SIPRTC and the answer cached briefly, so a wrong
token is refused when the client connects rather than on every tool call.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import threading
import time

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token

from . import __version__
from .config import get_settings, resolve_env_auth

log = logging.getLogger("siprtc_mcp.auth")

VALID_TTL = 300.0
INVALID_TTL = 30.0
CACHE_MAX = 2048
MAX_TOKEN_LENGTH = 1024


def decode_bearer_token(token: str) -> tuple[str, str]:
    token = (token or "").strip()
    if not token:
        raise ValueError("Missing bearer token.")
    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError("Invalid bearer token.")
    padded = token + "=" * (-len(token) % 4)
    try:
        decoded = base64.urlsafe_b64decode(padded).decode("utf-8")
        auth_id, auth_secret = decoded.split(":", 1)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Invalid bearer token.") from exc
    auth_id, auth_secret = auth_id.strip(), auth_secret.strip()
    if not auth_id or not auth_secret:
        raise ValueError("Bearer token must decode to 'auth_id:auth_secret'.")
    if not auth_id.isalnum():
        raise ValueError("Invalid Auth ID in bearer token.")
    return auth_id, auth_secret


class SiprtcCredentialTokenVerifier(TokenVerifier):
    """Accept bearer tokens that decode to ``auth_id:auth_secret`` (checked against SIPRTC when enabled)."""

    def __init__(self, verify_remote: bool | None = None) -> None:
        super().__init__()
        self._verify_remote = verify_remote
        self._cache: dict[str, tuple[float, bool]] = {}
        self._lock = threading.Lock()

    @property
    def verify_remote(self) -> bool:
        return get_settings().verify_bearer if self._verify_remote is None else self._verify_remote

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            auth_id, auth_secret = decode_bearer_token(token)
        except ValueError:
            return None
        if self.verify_remote and not await self._valid(token, auth_id, auth_secret):
            return None
        return AccessToken(token=token, client_id=auth_id, scopes=["siprtc"], claims={"siprtc_auth_id": auth_id})

    async def _valid(self, token: str, auth_id: str, auth_secret: str) -> bool:
        key = hashlib.sha256(token.encode()).hexdigest()
        now = time.monotonic()
        with self._lock:
            cached = self._cache.get(key)
            if cached and cached[0] > now:
                return cached[1]
        settings = get_settings()
        try:
            async with httpx.AsyncClient(
                base_url=settings.base_url,
                timeout=min(15.0, settings.timeout),
                headers={"Accept": "application/json", "User-Agent": f"siprtc-mcp/{__version__}"},
            ) as http:
                response = await http.get(f"/Accounts/{auth_id}/Balance", auth=(auth_id, auth_secret))
        except httpx.HTTPError as exc:
            # SIPRTC unreachable: don't cache, and don't let the client in on an unchecked token.
            log.warning("could not verify bearer token for %s: %s", auth_id, exc.__class__.__name__)
            return False
        # 401 means wrong credentials; anything else means SIPRTC accepted who the caller is.
        ok = response.status_code != 401
        with self._lock:
            if len(self._cache) >= CACHE_MAX:
                self._cache.clear()
            self._cache[key] = (now + (VALID_TTL if ok else INVALID_TTL), ok)
        if not ok:
            log.info("bearer token refused for %s", auth_id)
        return ok


def resolve_request_auth() -> tuple[str, str]:
    access_token = get_access_token()
    try:
        if access_token is None:
            return resolve_env_auth()
        return decode_bearer_token(access_token.token)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
