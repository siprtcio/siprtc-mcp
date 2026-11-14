"""Shared plumbing for tool modules: one call = one SIPRTC API request on the caller's account."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from fastmcp.exceptions import ToolError

from ..client import SiprtcApiError, SiprtcClient, compact, format_path

ClientFactory = Callable[[], SiprtcClient]

ACCOUNT = "/Accounts/{auth_id}"

# Page sizes above this are lowered: a model never needs more rows at once, and huge pages are
# slow for SIPRTC and fill the model's context.
MAX_PAGE_SIZE = 100
_PAGE_SIZE_KEYS = frozenset({"limit", "pagesize", "perpage"})

# Free-form fields (``extra``) may not name an account: the account is always the caller's,
# from the credentials, and never a body or query value.
_ACCOUNT_KEYS = frozenset(
    {
        "authid",
        "account",
        "accountauthid",
        "accountid",
        "accountsid",
        "accid",
        "customerid",
        "customer",
        "tenantid",
        "tenantauthid",
        "tenant",
        "parentauthid",
        "parentid",
        "resellerid",
        "owner",
        "companyid",
        "vendorid",
        "ownerid",
        "userid",
    }
)


def _norm(key: str) -> str:
    return key.lower().replace("_", "").replace("-", "")


def _cap_page_size(params: dict | None) -> dict | None:
    if not params:
        return params
    capped = dict(params)
    for key, value in params.items():
        if _norm(key) in _PAGE_SIZE_KEYS and isinstance(value, int) and value > MAX_PAGE_SIZE:
            capped[key] = MAX_PAGE_SIZE
    return capped


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
    keep: Iterable[str] = (),
    **path: Any,
) -> Any:
    """Fill ``template`` (``{auth_id}`` comes from the credentials) and send the request.

    ``None`` values are dropped from ``params``, ``data`` and a dict ``json`` body, so a tool
    can pass every optional argument straight through. Some list endpoints answer 404 when
    nothing matches; with ``empty_as`` that becomes ``{empty_as: []}`` instead of an error.
    ``keep`` names secret-looking response keys the tool exists to return.
    """
    client = client_factory()
    url = format_path(template, auth_id=client.auth_id, **path)
    if isinstance(json, dict):
        json = compact(json)
    try:
        return client.request(
            method,
            url,
            params=_cap_page_size(params),
            json=json,
            data=data,
            files=files,
            label=template,
            keep=keep,
        )
    except SiprtcApiError as exc:
        if empty_as and exc.status_code == 404:
            return {empty_as: [], "message": "none found"}
        raise


def checked_extra(extra: dict | None) -> dict:
    """An ``extra`` dict of API fields the tool does not name, refusing any that pick an account."""
    if not extra:
        return {}
    if not isinstance(extra, dict):
        raise ToolError("extra must be an object of API field names to values.")
    refused = sorted(key for key in extra if not isinstance(key, str) or _norm(key) in _ACCOUNT_KEYS)
    if refused:
        raise ToolError(
            f"extra may not set {', '.join(map(str, refused))}: the account is always the one these credentials belong to."
        )
    return dict(extra)


def digits(phone_number: str) -> str:
    """Phone numbers in SIPRTC paths are digits with the country code and no '+'."""
    return "".join(ch for ch in str(phone_number) if ch.isdigit())


def merge(body: dict, extra: dict | None) -> dict:
    """Named arguments plus an ``extra`` dict for fields the tool does not name."""
    merged = checked_extra(extra)
    merged.update(compact(body) or {})
    return merged
