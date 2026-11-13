from __future__ import annotations

import httpx
import pytest
import respx
from fastmcp.exceptions import ToolError

from siprtc_mcp.client import REDACTED, SiprtcApiError, SiprtcClient, format_path, redact

from .conftest import BASE


def make() -> SiprtcClient:
    return SiprtcClient(auth_id="AC0000000000000TEST0", auth_secret="unit-test-secret")


@respx.mock
def test_sends_basic_auth_and_returns_json():
    route = respx.get(f"{BASE}/Accounts/A/Balance").mock(return_value=httpx.Response(200, json={"balance": 5}))
    assert make().request("GET", "/Accounts/A/Balance") == {"balance": 5}
    request = route.calls.last.request
    assert request.headers["authorization"].startswith("Basic ")
    assert request.headers["user-agent"].startswith("siprtc-mcp/")


@respx.mock
def test_drops_none_query_params():
    route = respx.get(f"{BASE}/x").mock(return_value=httpx.Response(200, json={}))
    make().request("GET", "/x", params={"a": 1, "b": None})
    assert str(route.calls.last.request.url).endswith("/x?a=1")


@respx.mock
def test_error_carries_status_api_message_and_hint():
    respx.get(f"{BASE}/x").mock(return_value=httpx.Response(404, json={"message": "cdr not found"}))
    with pytest.raises(SiprtcApiError) as exc:
        make().request("GET", "/x")
    message = str(exc.value)
    assert "404" in message and "cdr not found" in message and "Not found" in message
    assert exc.value.status_code == 404
    assert isinstance(exc.value, ToolError)


@respx.mock
def test_error_message_never_echoes_secrets():
    respx.post(f"{BASE}/x").mock(return_value=httpx.Response(400, json={"password": "hunter2", "message": "bad"}))
    with pytest.raises(SiprtcApiError) as exc:
        make().request("POST", "/x", json={})
    assert "hunter2" not in str(exc.value)


@respx.mock
def test_get_retries_on_503_then_succeeds():
    route = respx.get(f"{BASE}/x").mock(
        side_effect=[httpx.Response(503), httpx.Response(503), httpx.Response(200, json={"ok": True})]
    )
    assert make().request("GET", "/x") == {"ok": True}
    assert route.call_count == 3


@respx.mock
def test_post_is_not_retried_on_503():
    route = respx.post(f"{BASE}/x").mock(return_value=httpx.Response(503))
    with pytest.raises(SiprtcApiError):
        make().request("POST", "/x", json={})
    assert route.call_count == 1


@respx.mock
def test_post_is_retried_on_429():
    route = respx.post(f"{BASE}/x").mock(
        side_effect=[httpx.Response(429, headers={"Retry-After": "0"}), httpx.Response(201, json={})]
    )
    make().request("POST", "/x", json={})
    assert route.call_count == 2


@respx.mock
def test_retries_stop_at_the_limit():
    route = respx.get(f"{BASE}/x").mock(return_value=httpx.Response(502))
    with pytest.raises(SiprtcApiError):
        make().request("GET", "/x")
    assert route.call_count == 3  # first try + SIPRTC_MAX_RETRIES=2


@respx.mock
def test_connect_errors_are_retried_for_any_method():
    route = respx.post(f"{BASE}/x").mock(
        side_effect=[httpx.ConnectError("down"), httpx.Response(201, json={"sid": "1"})]
    )
    assert make().request("POST", "/x", json={}) == {"sid": "1"}
    assert route.call_count == 2


@respx.mock
def test_read_timeout_on_a_write_says_it_may_have_happened():
    respx.post(f"{BASE}/x").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(SiprtcApiError) as exc:
        make().request("POST", "/x", json={})
    assert "may still have been carried out" in str(exc.value)


@respx.mock
def test_empty_body_is_a_success_object():
    respx.delete(f"{BASE}/x").mock(return_value=httpx.Response(204))
    assert make().request("DELETE", "/x") == {"status": "success", "http_status": 204}


@respx.mock
def test_redirects_are_not_followed():
    respx.get(f"{BASE}/x").mock(return_value=httpx.Response(302, headers={"location": "https://elsewhere.invalid/"}))
    with pytest.raises(SiprtcApiError):
        make().request("GET", "/x")


@respx.mock
def test_responses_are_redacted():
    respx.get(f"{BASE}/x").mock(
        return_value=httpx.Response(
            200, json={"data": [{"name": "a", "password": "p", "Auth_Secret": "s", "token": "keep"}]}
        )
    )
    row = make().request("GET", "/x")["data"][0]
    assert row["password"] == REDACTED and row["Auth_Secret"] == REDACTED and row["token"] == "keep"


def test_redact_leaves_empty_values_alone():
    assert redact({"password": "", "nested": [{"api_key": None}]}) == {"password": "", "nested": [{"api_key": None}]}


def test_repr_hides_the_secret():
    assert "unit-test-secret" not in repr(make())


@pytest.mark.parametrize("value", ["", ".", "..", "a\nb", "x" * 300])
def test_format_path_rejects_unsafe_values(value):
    with pytest.raises(ToolError):
        format_path("/Calls/{sid}", sid=value)


def test_format_path_keeps_values_in_one_segment():
    assert format_path("/Calls/{sid}", sid="../../Balance") == "/Calls/..%2F..%2FBalance"
    assert format_path("/N/{n}", n="+1 415") == "/N/%2B1%20415"
