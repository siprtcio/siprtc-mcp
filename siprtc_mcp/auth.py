"""Credentials for each tool call: the HTTP request's bearer token, or the environment for stdio.

A bearer token is ``base64url(auth_id:auth_secret)``. With ``SIPRTC_VERIFY_BEARER`` on (the
default) a new token is checked once against SIPRTC and the answer cached briefly, so a wrong
token is refused when the client connects rather than on every tool call.

The verifier must not become a way to guess secrets, to get in while SIPRTC is unhealthy, or to
lock other people out:

- SIPRTC's gateway answers 401 to wrong credentials before any service sees the request, so an
  answer from the service behind it (2xx, 402, 403, 404) proves the credentials and lets the
  token in. A 401 refuses it. Anything else (429, 5xx, no answer) refuses it without caching
  and without counting against anyone, so the next attempt simply asks again.
- Wrong secrets (401s) are throttled per client address, and per client address and Auth ID,
  before SIPRTC is asked again. Nothing is throttled globally or per Auth ID alone, so one
  client's guesses cannot lock out other clients or the account's owner.
- The cache is a bounded LRU keyed by a hash of the credentials, and a 401 seen during a tool
  call evicts the entry, so a rotated secret stops working at once.
- Environment credentials are used only for stdio (or in-process) sessions, never for a request
  that arrived over HTTP without a token.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import logging
import re
import threading
import time
from collections import OrderedDict, deque

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.context import _current_transport
from fastmcp.server.dependencies import get_access_token, get_http_request

from . import __version__
from .config import get_settings, resolve_env_auth

log = logging.getLogger("siprtc_mcp.auth")

VALID_TTL = 300.0
INVALID_TTL = 30.0
CACHE_MAX = 2048
MAX_TOKEN_LENGTH = 1024
MAX_SECRET_LENGTH = 512

# Wrong secrets allowed per window: from one client address for one Auth ID, and from one
# client address in all.
FAILURE_WINDOW = 60.0
MAX_FAILURES_PER_CLIENT_AND_ID = 5
MAX_FAILURES_PER_CLIENT = 20
# Upstream verifications in flight at once.
MAX_CONCURRENT_VERIFICATIONS = 8

AUTH_ID_RE = re.compile(r"[A-Za-z0-9]{1,64}")
_PROVEN = {402, 403, 404}


def decode_bearer_token(token: str) -> tuple[str, str]:
    token = (token or "").strip()
    if not token:
        raise ValueError("Missing bearer token.")
    if len(token) > MAX_TOKEN_LENGTH:
        raise ValueError("Invalid bearer token.")
    padded = token + "=" * (-len(token) % 4)
    altchars = b"-_" if ("-" in token or "_" in token) else None
    try:
        decoded = base64.b64decode(padded, altchars=altchars, validate=True).decode("utf-8")
        auth_id, auth_secret = decoded.split(":", 1)
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Invalid bearer token.") from exc
    # `echo 'id:secret' | base64` encodes a trailing newline; accept it like before.
    auth_id, auth_secret = auth_id.strip(), auth_secret.rstrip("\r\n")
    if not AUTH_ID_RE.fullmatch(auth_id):
        raise ValueError("Invalid Auth ID in bearer token.")
    if not auth_secret or len(auth_secret) > MAX_SECRET_LENGTH or not auth_secret.isprintable():
        raise ValueError("Bearer token must decode to 'auth_id:auth_secret'.")
    return auth_id, auth_secret


def _key(auth_id: str, auth_secret: str) -> str:
    return hashlib.sha256(f"{auth_id}:{auth_secret}".encode()).hexdigest()


class _CredentialCache:
    """Process-wide LRU of verification answers, shared by every verifier and the HTTP client."""

    def __init__(self, maxsize: int = CACHE_MAX) -> None:
        self._entries: OrderedDict[str, tuple[float, bool]] = OrderedDict()
        self._maxsize = maxsize
        self._lock = threading.Lock()

    def get(self, key: str) -> bool | None:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            if entry[0] <= now:
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return entry[1]

    def put(self, key: str, ok: bool) -> None:
        with self._lock:
            self._entries[key] = (time.monotonic() + (VALID_TTL if ok else INVALID_TTL), ok)
            self._entries.move_to_end(key)
            while len(self._entries) > self._maxsize:
                self._entries.popitem(last=False)

    def forget(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


class _FailureThrottle:
    """Sliding-window counts of wrong secrets, by client address and by (address, Auth ID)."""

    def __init__(self) -> None:
        self._windows: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def _count(self, key: str, now: float) -> int:
        times = self._windows.get(key)
        if times is None:
            return 0
        while times and times[0] <= now - FAILURE_WINDOW:
            times.popleft()
        if not times:
            del self._windows[key]
            return 0
        return len(times)

    def blocked(self, client: str, auth_id: str) -> bool:
        now = time.monotonic()
        with self._lock:
            return (
                self._count(f"c:{client}", now) >= MAX_FAILURES_PER_CLIENT
                or self._count(f"ci:{client}:{auth_id}", now) >= MAX_FAILURES_PER_CLIENT_AND_ID
            )

    def record(self, client: str, auth_id: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in (f"c:{client}", f"ci:{client}:{auth_id}"):
                self._windows.setdefault(key, deque()).append(now)
                self._windows.move_to_end(key)
            while len(self._windows) > 4 * CACHE_MAX:  # bounded: drop the least recently used
                self._windows.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._windows.clear()


CACHE = _CredentialCache()
THROTTLE = _FailureThrottle()


def forget_credentials(auth_id: str, auth_secret: str) -> None:
    """Drop a cached verification, e.g. after SIPRTC refused the credentials during a tool call."""
    CACHE.forget(_key(auth_id, auth_secret))


def _client_address() -> str:
    try:
        client = get_http_request().client
    except RuntimeError:
        return "local"
    return client.host if client and client.host else "unknown"


class SiprtcCredentialTokenVerifier(TokenVerifier):
    """Accept bearer tokens that decode to ``auth_id:auth_secret`` (checked against SIPRTC when enabled)."""

    def __init__(self, verify_remote: bool | None = None) -> None:
        super().__init__()
        self._verify_remote = verify_remote
        self._inflight: dict[str, asyncio.Future[bool]] = {}
        self._slots: asyncio.Semaphore | None = None

    @property
    def verify_remote(self) -> bool:
        return get_settings().verify_bearer if self._verify_remote is None else self._verify_remote

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            auth_id, auth_secret = decode_bearer_token(token)
        except ValueError:
            return None
        if self.verify_remote and not await self._valid(auth_id, auth_secret):
            return None
        return AccessToken(token=token, client_id=auth_id, scopes=["siprtc"], claims={"siprtc_auth_id": auth_id})

    async def _valid(self, auth_id: str, auth_secret: str) -> bool:
        key = _key(auth_id, auth_secret)
        cached = CACHE.get(key)
        if cached is not None:
            return cached
        client = _client_address()
        if THROTTLE.blocked(client, auth_id):
            log.warning("bearer verification throttled for %s from %s", auth_id, client)
            return False
        # Single flight: concurrent checks of the same credentials share one upstream request.
        pending = self._inflight.get(key)
        if pending is not None:
            return await asyncio.shield(pending)
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        self._inflight[key] = future
        try:
            ok = await self._check(key, client, auth_id, auth_secret)
            future.set_result(ok)
            return ok
        except BaseException as exc:
            future.set_exception(exc)
            future.exception()  # mark retrieved for waiters that never came
            raise
        finally:
            self._inflight.pop(key, None)

    async def _check(self, key: str, client: str, auth_id: str, auth_secret: str) -> bool:
        if self._slots is None:
            self._slots = asyncio.Semaphore(MAX_CONCURRENT_VERIFICATIONS)
        async with self._slots:
            status = await self._ask_siprtc(auth_id, auth_secret)
        if status is not None and (200 <= status < 300 or status in _PROVEN):
            CACHE.put(key, True)
            return True
        if status == 401:
            CACHE.put(key, False)
            THROTTLE.record(client, auth_id)
            log.info("bearer token refused for %s from %s", auth_id, client)
        else:
            log.warning("could not verify bearer token for %s (status %s); refused, not cached", auth_id, status)
        return False

    @staticmethod
    async def _ask_siprtc(auth_id: str, auth_secret: str) -> int | None:
        settings = get_settings()
        try:
            async with (
                httpx.AsyncClient(
                    base_url=settings.base_url,
                    timeout=min(15.0, settings.timeout),
                    headers={"Accept": "application/json", "User-Agent": f"siprtc-mcp/{__version__}"},
                    follow_redirects=False,
                ) as http,
                http.stream("GET", f"/Accounts/{auth_id}/Balance", auth=(auth_id, auth_secret)) as response,
            ):
                return response.status_code  # the body is never read
        except httpx.HTTPError as exc:
            log.warning("could not reach SIPRTC to verify %s: %s", auth_id, exc.__class__.__name__)
            return None


def _over_http() -> bool:
    return _current_transport.get() in {"streamable-http", "sse"}


def resolve_request_auth() -> tuple[str, str]:
    access_token = get_access_token()
    try:
        if access_token is not None:
            return decode_bearer_token(access_token.token)
        if _over_http():
            # A request that reached a tool over HTTP without a token must never borrow the
            # server's own environment credentials.
            raise ValueError("Not authenticated: send 'Authorization: Bearer <base64url(auth_id:auth_secret)>'.")
        return resolve_env_auth()
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
