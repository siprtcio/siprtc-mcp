"""Shared plumbing for tool modules: one call = one SIPRTC API request on the caller's account."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..client import SiprtcApiError, SiprtcClient, compact, format_path

ClientFactory = Callable[[], SiprtcClient]

ACCOUNT = "/Accounts/{auth_id}"


def api(
    client_factory: ClientFactory,
    method: str,
    template: str,
    *,
    params: dict | None = None,
    json: Any | None = None,
    data: dict | None = None,
    files: dict | None = None,
    empty_as: str | None = None,
    **path: Any,
) -> Any:
    """Fill ``template`` (``{auth_id}`` comes from the credentials) and send the request.

    ``None`` values are dropped from ``params``, ``data`` and a dict ``json`` body, so a tool
    can pass every optional argument straight through. Some list endpoints answer 404 when
    nothing matches; with ``empty_as`` that becomes ``{empty_as: []}`` instead of an error.
    """
    client = client_factory()
    url = format_path(template, auth_id=client.auth_id, **path)
    if isinstance(json, dict):
        json = compact(json)
    try:
        return client.request(method, url, params=params, json=json, data=data, files=files)
    except SiprtcApiError as exc:
        if empty_as and exc.status_code == 404:
            return {empty_as: [], "message": "none found"}
        raise


def digits(phone_number: str) -> str:
    """Phone numbers in SIPRTC paths are digits with the country code and no '+'."""
    return "".join(ch for ch in str(phone_number) if ch.isdigit())


def merge(body: dict, extra: dict | None) -> dict:
    """Named arguments plus an ``extra`` dict for fields the tool does not name."""
    merged = dict(extra or {})
    merged.update(compact(body) or {})
    return merged
