"""HTTP access to the SIPRTC API: one pooled connection pool, bounded retries, and answers that are
safe to hand to a model (errors carry the API's message; secrets are masked; size is capped).

The pool is shared by every tenant using this process, so it keeps no state between requests:
credentials go with each request and cookies are never stored.
"""

from __future__ import annotations

import http.cookiejar
import json as jsonlib
import logging
import random
import re
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp.exceptions import ToolError

from . import __version__
from .config import get_settings

log = logging.getLogger("siprtc_mcp.client")

RETRY_STATUSES = {429, 502, 503, 504}
IDEMPOTENT_METHODS = {"GET", "HEAD", "OPTIONS"}
MAX_BACKOFF = 8.0

# A key whose normalised form (lower case, no "_" or "-") contains one of these holds a secret.
SECRET_MARKERS = ("secret", "password", "passwd", "token", "apikey", "privatekey")
# Secret-looking keys that are not secrets.
NOT_SECRET_KEYS = frozenset({"tokenexpiresat", "tokentype", "tokenexpiry", "secretrotatedat", "passwordupdatedat"})
REDACTED = "[redacted]"
# key=value / "key": "value" pairs in plain-text bodies; quoted values run to their closing quote.
_TEXT_SECRET_RE = re.compile(
    r"""(?ix)
    (?P<key>["']?[\w-]*(?:secret|password|passwd|token|api[_-]?key|private[_-]?key)[\w-]*["']?)
    (?P<sep>\s*[:=]\s*)
    (?P<value>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[^\s"',&;}]+)
    """
)
# Credentials in an echoed Authorization header.
_AUTH_HEADER_RE = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")


class SiprtcApiError(ToolError):
    """An error answer from the SIPRTC API, phrased for the model that made the call."""

    def __init__(self, message: str, status_code: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def _normalise(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "")


def is_secret_key(key: Any, keep: frozenset[str] = frozenset()) -> bool:
    if not isinstance(key, str):
        return False
    norm = _normalise(key)
    if norm in NOT_SECRET_KEYS or norm in keep:
        return False
    return any(marker in norm for marker in SECRET_MARKERS)


def redact(value: Any, keep: Iterable[str] = ()) -> Any:
    """Mask secret string values wherever they appear. ``keep`` names keys a tool returns on purpose."""
    keep_set = frozenset(_normalise(k) for k in keep)
    return _redact(value, keep_set)


def _redact(value: Any, keep: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED if is_secret_key(key, keep) and isinstance(item, str) and item != "" else _redact(item, keep)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item, keep) for item in value]
    return value


def _redact_pair(match: re.Match) -> str:
    key, sep, value = match.group("key"), match.group("sep"), match.group("value")
    norm = _normalise(key.strip("\"'"))
    if norm in NOT_SECRET_KEYS or norm.endswith(("tokens", "count", "length")):
        return match.group(0)  # max_tokens=100, token_count: 3
    quote = value[0] if value[:1] in {'"', "'"} else ""
    return f"{key}{sep}{quote}{REDACTED}{quote}"


def redact_text(text: str) -> str:
    text = _TEXT_SECRET_RE.sub(_redact_pair, text)
    return _AUTH_HEADER_RE.sub(lambda m: f"{m.group(1)} {REDACTED}", text)


def compact(values: dict | None) -> dict | None:
    """Drop keys whose value is None, so optional tool arguments are not sent."""
    if values is None:
        return None
    return {key: value for key, value in values.items() if value is not None}


def _describe(payload: Any) -> str:
    if payload is None or payload == "":
        return ""
    text = redact_text(payload) if isinstance(payload, str) else jsonlib.dumps(redact(payload), ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= 800 else text[:800] + "…"


_HINTS = {
    401: "The Auth ID / secret were rejected.",
    402: "The account balance is too low.",
    403: "This account is not allowed to do that (plan, role or ownership).",
    404: "Not found (or nothing matched).",
    429: "Rate limited; try again later.",
}


def _retry_after(response: Any) -> float | None:
    value = response.headers.get("retry-after")
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            return max(0.0, parsedate_to_datetime(value).timestamp() - time.time())
        except Exception:
            return None


class _NoCookies(http.cookiejar.DefaultCookiePolicy):
    def set_ok(self, cookie, request):  # noqa: ANN001 - stdlib signature
        return False

    def return_ok(self, cookie, request):  # noqa: ANN001 - stdlib signature
        return False


_pool: httpx.Client | None = None
_pool_lock = threading.Lock()


def _shared_client() -> httpx.Client:
    """One connection pool for the process; credentials are passed per request, cookies never kept."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                settings = get_settings()
                _pool = httpx.Client(
                    base_url=settings.base_url,
                    headers={"Accept": "application/json", "User-Agent": f"siprtc-mcp/{__version__}"},
                    timeout=httpx.Timeout(settings.timeout, connect=min(10.0, settings.timeout)),
                    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
                    follow_redirects=False,
                    cookies=http.cookiejar.CookieJar(policy=_NoCookies()),
                )
    return _pool


def close_shared_client() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


@dataclass
class _Answer:
    status_code: int
    headers: httpx.Headers
    content: bytes
    encoding: str = "utf-8"
    too_large: bool = False

    def json(self) -> Any:
        return jsonlib.loads(self.content)

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding, errors="replace")
        except LookupError:
            return self.content.decode("utf-8", errors="replace")


@dataclass
class SiprtcClient:
    auth_id: str
    auth_secret: str
    http: httpx.Client | None = None
    max_retries: int | None = None

    def __repr__(self) -> str:  # never print the secret
        return f"SiprtcClient(auth_id={self.auth_id!r})"

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
        label: str | None = None,
        keep: Iterable[str] = (),
    ) -> Any:
        """Send one request. ``label`` is what the log shows instead of the filled-in path (no ids,
        numbers or emails); ``keep`` names response keys a tool returns on purpose (a new token)."""
        method = method.upper()
        http = self.http or _shared_client()
        settings = get_settings()
        retries = settings.max_retries if self.max_retries is None else self.max_retries
        params = compact(params) or None
        data = compact(data) if data is not None else None
        shown = label or path

        attempt = 0
        while True:
            started = time.monotonic()
            try:
                answer = self._send(http, method, path, settings.max_api_response_bytes, json, params, data, files)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                # Nothing reached the server, so any method may be retried.
                if attempt < retries:
                    attempt += 1
                    self._sleep(attempt, None)
                    continue
                raise SiprtcApiError(
                    f"Could not reach the SIPRTC API ({method} {shown}): {exc.__class__.__name__}."
                ) from exc
            except httpx.TimeoutException as exc:
                if method in IDEMPOTENT_METHODS and attempt < retries:
                    attempt += 1
                    self._sleep(attempt, None)
                    continue
                raise SiprtcApiError(
                    f"The SIPRTC API did not answer in time ({method} {shown}). "
                    + (
                        ""
                        if method in IDEMPOTENT_METHODS
                        else "The request may still have been carried out; check before retrying."
                    )
                ) from exc
            except httpx.HTTPError as exc:
                raise SiprtcApiError(
                    f"SIPRTC API request failed ({method} {shown}): {exc.__class__.__name__}."
                ) from exc

            log.info(
                "siprtc api %s %s -> %s in %.0fms",
                method,
                shown,
                answer.status_code,
                (time.monotonic() - started) * 1000,
            )
            # A 429 means SIPRTC turned the request away without acting on it, so any method may
            # be retried; other retryable statuses only for reads.
            if (
                answer.status_code in RETRY_STATUSES
                and attempt < retries
                and (method in IDEMPOTENT_METHODS or answer.status_code == 429)
            ):
                attempt += 1
                self._sleep(attempt, _retry_after(answer))
                continue
            if answer.too_large:
                raise SiprtcApiError(
                    f"The SIPRTC API answer to {method} {shown} was larger than "
                    f"{settings.max_api_response_bytes} bytes and was not read. "
                    + (
                        "Narrow the query (dates, filters) or ask for a smaller page."
                        if method in IDEMPOTENT_METHODS
                        else "The request was carried out; check its result with a read before retrying."
                    ),
                    status_code=413,
                )
            if answer.status_code == 401:
                from .auth import forget_credentials  # local import: auth imports this module's config

                forget_credentials(self.auth_id, self.auth_secret)
            return self._result(method, shown, answer, keep)

    def _send(
        self,
        http: httpx.Client,
        method: str,
        path: str,
        limit: int,
        json: Any,
        params: dict | None,
        data: dict | None,
        files: dict | None,
    ) -> _Answer:
        """Send the request and read at most ``limit`` bytes of the answer."""
        request = http.build_request(method, path, json=json, params=params, data=data, files=files)
        response = http.send(request, auth=(self.auth_id, self.auth_secret), stream=True)
        try:
            declared = response.headers.get("content-length")
            if declared and declared.isdigit() and int(declared) > limit:
                return _too_large(response, limit)
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_bytes():
                size += len(chunk)
                if size > limit:
                    return _too_large(response, limit)
                chunks.append(chunk)
            return _Answer(
                response.status_code, response.headers, b"".join(chunks), response.charset_encoding or "utf-8"
            )
        finally:
            response.close()

    def _sleep(self, attempt: int, retry_after: float | None) -> None:
        delay = retry_after if retry_after is not None else min(MAX_BACKOFF, 0.5 * 2 ** (attempt - 1))
        time.sleep(min(MAX_BACKOFF, delay) + random.uniform(0, 0.25))

    @staticmethod
    def _result(method: str, shown: str, answer: _Answer, keep: Iterable[str]) -> Any:
        if answer.status_code >= 300:
            try:
                payload = answer.json()
            except ValueError:
                payload = answer.text
            detail = _describe(payload)
            hint = _HINTS.get(answer.status_code, "")
            message = f"SIPRTC API error {answer.status_code} on {method} {shown}."
            if hint:
                message += f" {hint}"
            if detail:
                message += f" API said: {detail}"
            raise SiprtcApiError(message, status_code=answer.status_code, payload=redact(payload))

        if not answer.content:
            return {"status": "success", "http_status": answer.status_code}
        try:
            body = answer.json()
        except ValueError:
            return redact_text(answer.text)
        return redact(body, keep)


def _too_large(response: httpx.Response, limit: int) -> _Answer:
    log.warning("siprtc api answer over %d bytes dropped (status %s)", limit, response.status_code)
    return _Answer(response.status_code, response.headers, b"", too_large=True)


def format_path(path_template: str, **values: Any) -> str:
    """Fill a path template, URL-encoding each value so it stays one path segment."""
    encoded = {}
    for key, value in values.items():
        text = str(value).strip()
        if text in {"", ".", ".."} or any(ch in text for ch in "\r\n\t\x00"):
            raise ToolError(f"Invalid value for {key}: {value!r}.")
        if len(text) > 256:
            raise ToolError(f"Value for {key} is too long.")
        encoded[key] = quote(text, safe="")
    return path_template.format(**encoded)
