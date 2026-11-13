"""HTTP access to the SIPRTC API: one pooled connection pool, bounded retries, and answers that are
safe to hand to a model (errors carry the API's message; secrets are masked)."""

from __future__ import annotations

import json as jsonlib
import logging
import random
import threading
import time
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

# Keys whose values never go back to the model, wherever they appear in a response.
SECRET_KEYS = {
    "auth_secret",
    "auth_secret_id",
    "auth_secret_i_d",
    "secondary_secret",
    "password",
    "sip_password",
    "auth_token",
    "access_token",
    "refresh_token",
    "app_secret",
    "api_secret",
    "api_key",
    "private_key",
    "client_secret",
}
REDACTED = "[redacted]"


class SiprtcApiError(ToolError):
    """An error answer from the SIPRTC API, phrased for the model that made the call."""

    def __init__(self, message: str, status_code: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                REDACTED
                if isinstance(key, str) and key.lower() in SECRET_KEYS and item not in (None, "")
                else redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def compact(values: dict | None) -> dict | None:
    """Drop keys whose value is None, so optional tool arguments are not sent."""
    if values is None:
        return None
    return {key: value for key, value in values.items() if value is not None}


def _describe(payload: Any) -> str:
    if payload is None or payload == "":
        return ""
    text = payload if isinstance(payload, str) else jsonlib.dumps(redact(payload), ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= 800 else text[:800] + "…"


_HINTS = {
    401: "The Auth ID / secret were rejected.",
    402: "The account balance is too low.",
    403: "This account is not allowed to do that (plan, role or ownership).",
    404: "Not found (or nothing matched).",
    429: "Rate limited; try again later.",
}


def _retry_after(response: httpx.Response) -> float | None:
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


_pool: httpx.Client | None = None
_pool_lock = threading.Lock()


def _shared_client() -> httpx.Client:
    """One connection pool for the process; credentials are passed per request."""
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
                )
    return _pool


def close_shared_client() -> None:
    global _pool
    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


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
    ) -> Any:
        method = method.upper()
        http = self.http or _shared_client()
        retries = get_settings().max_retries if self.max_retries is None else self.max_retries
        params = compact(params) or None
        data = compact(data) if data is not None else None

        attempt = 0
        while True:
            started = time.monotonic()
            try:
                response = http.request(
                    method,
                    path,
                    json=json,
                    params=params,
                    data=data,
                    files=files,
                    auth=(self.auth_id, self.auth_secret),
                )
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                # Nothing reached the server, so any method may be retried.
                if attempt < retries:
                    attempt += 1
                    self._sleep(attempt, None)
                    continue
                raise SiprtcApiError(
                    f"Could not reach the SIPRTC API ({method} {path}): {exc.__class__.__name__}."
                ) from exc
            except httpx.TimeoutException as exc:
                if method in IDEMPOTENT_METHODS and attempt < retries:
                    attempt += 1
                    self._sleep(attempt, None)
                    continue
                raise SiprtcApiError(
                    f"The SIPRTC API did not answer in time ({method} {path}). "
                    + (
                        ""
                        if method in IDEMPOTENT_METHODS
                        else "The request may still have been carried out; check before retrying."
                    )
                ) from exc
            except httpx.HTTPError as exc:
                raise SiprtcApiError(f"SIPRTC API request failed ({method} {path}): {exc.__class__.__name__}.") from exc

            log.info(
                "siprtc api %s %s -> %s in %.0fms",
                method,
                path,
                response.status_code,
                (time.monotonic() - started) * 1000,
            )
            if (
                response.status_code in RETRY_STATUSES
                and attempt < retries
                and (method in IDEMPOTENT_METHODS or response.status_code == 429)
            ):
                attempt += 1
                self._sleep(attempt, _retry_after(response))
                continue
            return self._result(method, path, response)

    @staticmethod
    def _sleep(attempt: int, retry_after: float | None) -> None:
        delay = retry_after if retry_after is not None else min(MAX_BACKOFF, 0.5 * 2 ** (attempt - 1))
        time.sleep(min(MAX_BACKOFF, delay) + random.uniform(0, 0.25))

    @staticmethod
    def _result(method: str, path: str, response: httpx.Response) -> Any:
        if response.status_code >= 400 or 300 <= response.status_code < 400:
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            detail = _describe(payload)
            hint = _HINTS.get(response.status_code, "")
            message = f"SIPRTC API error {response.status_code} on {method} {path}."
            if hint:
                message += f" {hint}"
            if detail:
                message += f" API said: {detail}"
            raise SiprtcApiError(message, status_code=response.status_code, payload=payload)

        if not response.content:
            return {"status": "success", "http_status": response.status_code}
        try:
            body = response.json()
        except ValueError:
            return response.text
        return redact(body)


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
