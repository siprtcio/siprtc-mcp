"""Security properties: who a request acts as, what leaves the server, and what a model may do."""

from __future__ import annotations

import asyncio
import base64
import json

import httpx
import pytest
import respx
from fastmcp import Client
from fastmcp.exceptions import ToolError
from fastmcp.server.context import reset_transport, set_transport

from siprtc_mcp import auth as auth_module
from siprtc_mcp.auth import SiprtcCredentialTokenVerifier, decode_bearer_token, resolve_request_auth
from siprtc_mcp.client import REDACTED, SiprtcApiError, SiprtcClient, redact, redact_text
from siprtc_mcp.config import ConfigError, get_settings
from siprtc_mcp.server import create_server, http_app_options
from siprtc_mcp.toolset import COST_TOOLS, KIND_OVERRIDES, SENSITIVE_TOOLS

from .conftest import BASE

ME = "AC0000000000000TEST0"
ACCOUNT = f"{BASE}/Accounts/{ME}"


def token(auth_id=ME, secret="s3cret", alphabet="url"):
    raw = f"{auth_id}:{secret}".encode()
    return (base64.urlsafe_b64encode(raw) if alphabet == "url" else base64.b64encode(raw)).decode()


async def tools() -> dict:
    async with Client(create_server()) as c:
        return {t.name: t for t in await c.list_tools()}


async def call(name: str, args: dict | None = None):
    async with Client(create_server()) as c:
        return await c.call_tool(f"siprtc.{name}", args or {}, raise_on_error=False)


# --- bearer tokens -------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    [
        token("ＡＢ١٢"),  # non-ASCII letters and digits
        token("A" * 65),
        token(secret="line\nbreak"),
        token().rstrip("=") + "!!",  # characters outside the alphabet are not silently dropped
    ],
)
def test_bearer_tokens_are_decoded_strictly(bad):
    with pytest.raises(ValueError):
        decode_bearer_token(bad)


def test_standard_and_url_safe_base64_both_decode():
    secret = "a?b>c~"  # encodes to '+' / '/' or '-' / '_' depending on the alphabet
    assert decode_bearer_token(token(secret=secret)) == (ME, secret)
    assert decode_bearer_token(token(secret=secret, alphabet="std")) == (ME, secret)


@respx.mock
@pytest.mark.parametrize("status", [429, 500, 502, 503])
async def test_verifier_lets_no_one_in_when_siprtc_cannot_prove_the_credentials(status):
    route = respx.get(f"{ACCOUNT}/Balance").mock(return_value=httpx.Response(status))
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    assert await verifier.verify_token(token()) is None
    assert await verifier.verify_token(token()) is None
    assert route.call_count == 2  # not cached: the next attempt asks again


@respx.mock
@pytest.mark.parametrize("status", [200, 402, 403, 404])
async def test_verifier_accepts_answers_that_prove_the_caller(status):
    respx.get(f"{ACCOUNT}/Balance").mock(return_value=httpx.Response(status, json={}))
    assert await SiprtcCredentialTokenVerifier(verify_remote=True).verify_token(token()) is not None


@respx.mock
async def test_wrong_secrets_from_one_client_are_throttled_without_locking_out_others(monkeypatch):
    route = respx.get(f"{ACCOUNT}/Balance")
    route.mock(
        side_effect=lambda request: httpx.Response(
            200 if b"right" in base64.b64decode(request.headers["authorization"].split()[1]) else 401, json={}
        )
    )
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    monkeypatch.setattr(auth_module, "_client_address", lambda: "203.0.113.9")  # the attacker
    for attempt in range(auth_module.MAX_FAILURES_PER_CLIENT_AND_ID + 3):
        assert await verifier.verify_token(token(secret=f"guess-{attempt}")) is None
    assert route.call_count == auth_module.MAX_FAILURES_PER_CLIENT_AND_ID
    # The account's owner, from elsewhere, still gets in.
    monkeypatch.setattr(auth_module, "_client_address", lambda: "198.51.100.7")
    assert await verifier.verify_token(token(secret="right")) is not None


@respx.mock
async def test_one_client_guessing_across_accounts_is_throttled(monkeypatch):
    route = respx.get(url__regex=rf"{BASE}/Accounts/\w+/Balance").mock(return_value=httpx.Response(401))
    monkeypatch.setattr(auth_module, "_client_address", lambda: "203.0.113.9")
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    for i in range(auth_module.MAX_FAILURES_PER_CLIENT + 5):
        await verifier.verify_token(token(auth_id=f"ACCOUNT{i:04d}"))
    assert route.call_count == auth_module.MAX_FAILURES_PER_CLIENT


@respx.mock
async def test_siprtc_outages_do_not_count_as_guesses(monkeypatch):
    route = respx.get(f"{ACCOUNT}/Balance").mock(return_value=httpx.Response(503))
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    for _ in range(auth_module.MAX_FAILURES_PER_CLIENT + 5):
        assert await verifier.verify_token(token()) is None
    route.mock(return_value=httpx.Response(200, json={}))
    assert await verifier.verify_token(token()) is not None


@respx.mock
async def test_concurrent_checks_of_one_token_ask_siprtc_once():
    route = respx.get(f"{ACCOUNT}/Balance").mock(return_value=httpx.Response(200, json={}))
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    results = await asyncio.gather(*(verifier.verify_token(token()) for _ in range(10)))
    assert all(results) and route.call_count == 1


@respx.mock
async def test_a_401_during_a_tool_call_forgets_the_cached_credentials():
    balance = respx.get(f"{ACCOUNT}/Balance").mock(return_value=httpx.Response(200, json={}))
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    assert await verifier.verify_token(token()) is not None
    balance.mock(return_value=httpx.Response(401))  # the secret was rotated
    with pytest.raises(SiprtcApiError):
        SiprtcClient(auth_id=ME, auth_secret="s3cret").request("GET", f"/Accounts/{ME}/Balance")
    assert await verifier.verify_token(token()) is None


def test_the_credential_cache_is_bounded():
    cache = auth_module._CredentialCache(maxsize=3)
    for i in range(10):
        cache.put(str(i), True)
    assert cache.get("0") is None and cache.get("9") is True


def test_http_requests_never_fall_back_to_environment_credentials():
    marker = set_transport("streamable-http")
    try:
        with pytest.raises(ToolError, match="Not authenticated"):
            resolve_request_auth()
    finally:
        reset_transport(marker)
    assert resolve_request_auth() == (ME, "unit-test-secret")  # stdio / in-process


async def test_every_http_app_demands_a_bearer_token():
    app = create_server().http_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as http:
        response = await http.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("host", "origin", "allowed"),
    [
        ("127.0.0.1:8000", None, True),
        ("localhost:8000", None, True),
        ("mcp.example.com", None, True),
        ("evil.example", None, False),  # DNS rebinding: a foreign Host
        ("127.0.0.1:8000", "https://evil.example", False),  # a foreign page in a browser
    ],
)
async def test_host_and_origin_are_checked(monkeypatch, host, origin, allowed):
    monkeypatch.setenv("MCP_ALLOWED_HOSTS", "mcp.example.com")
    get_settings.cache_clear()
    app = create_server().http_app(**http_app_options(get_settings()))
    headers = {"host": host, **({"origin": origin} if origin else {})}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as http:
        response = await http.get("/healthz", headers=headers)
    assert (response.status_code == 200) is allowed, response.status_code


async def test_health_route_says_nothing_about_the_configuration():
    app = create_server().http_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://127.0.0.1") as http:
        response = await http.get("/healthz")
    assert response.json() == {"status": "ok"}


# --- what leaves the server ----------------------------------------------------------------


def test_secret_looking_keys_are_redacted_however_they_are_spelled():
    body = {
        "verify_token": "v",
        "pageAccessToken": "p",
        "SipAuthPassword": "s",
        "apiKey": "k",
        "api-key": "k",
        "credentials": {"account_id": "MA1", "secret": "x"},
        "token_expires_at": "2026-01-01",
        "has_password": True,
        "token_count": 3,
        "name": "ok",
    }
    out = redact(body)
    for key in ("verify_token", "pageAccessToken", "SipAuthPassword", "apiKey", "api-key"):
        assert out[key] == REDACTED, key
    assert out["credentials"] == {"account_id": "MA1", "secret": REDACTED}
    assert out["token_expires_at"] == "2026-01-01" and out["has_password"] is True and out["token_count"] == 3


def test_plain_text_bodies_are_redacted():
    text = 'bad request: password=hunter2&user=a, {"auth_token": "abc"} api_key: zzz'
    out = redact_text(text)
    assert "hunter2" not in out and "abc" not in out and "zzz" not in out and "user=a" in out


@respx.mock
def test_error_bodies_in_plain_text_are_redacted():
    respx.post(f"{BASE}/x").mock(return_value=httpx.Response(400, text="invalid secret=topsecret"))
    with pytest.raises(SiprtcApiError) as exc:
        SiprtcClient(auth_id=ME, auth_secret="s").request("POST", "/x", json={})
    assert "topsecret" not in str(exc.value)


@respx.mock
def test_cookies_from_one_tenant_never_reach_another():
    route = respx.get(f"{BASE}/x").mock(
        return_value=httpx.Response(200, json={}, headers={"set-cookie": "session=TENANT_A; Path=/"})
    )
    SiprtcClient(auth_id="TENANTA", auth_secret="a").request("GET", "/x")
    SiprtcClient(auth_id="TENANTB", auth_secret="b").request("GET", "/x")
    assert "cookie" not in route.calls.last.request.headers


@respx.mock
def test_oversized_api_answers_are_not_read(monkeypatch):
    monkeypatch.setenv("SIPRTC_MAX_API_RESPONSE_BYTES", "100000")
    get_settings.cache_clear()
    respx.get(f"{BASE}/x").mock(return_value=httpx.Response(200, content=b"x" * 200_000))
    with pytest.raises(SiprtcApiError) as exc:
        SiprtcClient(auth_id=ME, auth_secret="s").request("GET", "/x")
    assert exc.value.status_code == 413 and "Narrow the query" in str(exc.value)


@respx.mock
def test_an_oversized_answer_to_a_write_says_the_write_happened(monkeypatch):
    monkeypatch.setenv("SIPRTC_MAX_API_RESPONSE_BYTES", "100000")
    get_settings.cache_clear()
    respx.post(f"{BASE}/x").mock(return_value=httpx.Response(201, content=b"x" * 200_000))
    with pytest.raises(SiprtcApiError) as exc:
        SiprtcClient(auth_id=ME, auth_secret="s").request("POST", "/x", json={})
    assert "was carried out" in str(exc.value)


@respx.mock
async def test_tool_results_are_capped(monkeypatch):
    monkeypatch.setenv("SIPRTC_MAX_RESULT_BYTES", "10000")
    get_settings.cache_clear()
    respx.get(f"{ACCOUNT}/Calls").mock(return_value=httpx.Response(200, json={"calls": ["x" * 100] * 1000}))
    result = await call("list_calls")
    assert len(result.content[0].text.encode()) <= 10_000 and "truncated" in result.content[0].text


@respx.mock
async def test_page_sizes_are_capped():
    route = respx.get(f"{ACCOUNT}/Calls").mock(return_value=httpx.Response(200, json={}))
    await call("list_calls", {"limit": 100000})
    assert route.calls.last.request.url.params["limit"] == "100"


async def test_log_lines_show_the_route_not_the_numbers(caplog):
    with respx.mock:
        respx.get(f"{ACCOUNT}/PhoneNumbers/14155550100").mock(return_value=httpx.Response(200, json={}))
        with caplog.at_level("INFO", logger="siprtc_mcp.client"):
            await call("get_phone_number", {"phone_number": "+14155550100"})
    assert "14155550100" not in caplog.text and "{phone_number}" in caplog.text


# --- client tokens: the API's list is not scoped to the caller ------------------------------


@respx.mock
async def test_client_token_list_shows_only_this_account_and_no_token_values():
    respx.get(f"{ACCOUNT}/ClientToken").mock(
        return_value=httpx.Response(
            200,
            json={
                "data": [
                    {"id": "1", "name": "mine", "auth_id": ME, "token": "t-mine"},
                    {"id": "2", "name": "theirs", "auth_id": "OTHERACCOUNT00000000", "token": "t-theirs"},
                    {"id": "3", "name": "unknown", "token": "t-unknown"},
                ],
                "total_results": 3,
            },
        )
    )
    result = await call("list_client_tokens")
    body = json.loads(result.content[0].text)
    assert [row["id"] for row in body["data"]] == ["1"]
    assert "t-mine" not in result.content[0].text and "t-theirs" not in result.content[0].text
    assert "total_results" not in body


@respx.mock
async def test_client_token_list_reads_every_page_of_the_shared_table():
    def page(request):
        number = int(request.url.params["page"])
        rows = [{"id": f"{number}-{i}", "auth_id": "OTHERACCOUNT00000000"} for i in range(100)]
        if number == 3:
            rows = [{"id": "mine-on-page-3", "auth_id": ME}]
        return httpx.Response(200, json={"data": rows})

    route = respx.get(f"{ACCOUNT}/ClientToken").mock(side_effect=page)
    body = json.loads((await call("list_client_tokens")).content[0].text)
    assert [row["id"] for row in body["data"]] == ["mine-on-page-3"] and route.call_count == 3


@respx.mock
async def test_deleting_another_accounts_client_token_is_refused():
    respx.get(f"{ACCOUNT}/ClientToken").mock(
        return_value=httpx.Response(200, json={"data": [{"id": "2", "auth_id": "OTHERACCOUNT00000000"}]})
    )
    delete = respx.delete(f"{ACCOUNT}/ClientToken/2").mock(return_value=httpx.Response(200, json={}))
    result = await call("delete_client_token", {"client_id": "2"})
    assert result.is_error and not delete.called


@respx.mock
async def test_a_new_client_token_is_returned_to_the_caller():
    respx.post(f"{ACCOUNT}/ClientToken").mock(return_value=httpx.Response(201, json={"id": "9", "token": "t-new"}))
    result = await call("create_client_token", {"name": "sdk"})
    assert json.loads(result.content[0].text)["token"] == "t-new"


# --- what a model may do -------------------------------------------------------------------


async def test_extra_fields_may_not_pick_an_account():
    for key in ("auth_id", "AccountSid", "customer_id", "tenantId"):
        result = await call("create_application", {"friendly_name": "x", "extra": {key: "OTHERACCOUNT00000000"}})
        assert result.is_error and "account" in result.content[0].text, key


async def test_request_models_refuse_unknown_fields():
    result = await call("make_call", {"call": {"To": "+1", "From": "+2", "speak": "hi", "auth_id": "OTHER"}})
    assert result.is_error


async def test_policy_tables_name_real_tools():
    names = {name.split(".", 1)[1] for name in await tools()}
    for table in (COST_TOOLS, SENSITIVE_TOOLS, set(KIND_OVERRIDES)):
        assert set(table) <= names, set(table) - names


async def test_sensitive_tools_ask_for_confirmation():
    found = await tools()
    for name in SENSITIVE_TOOLS:
        hints = found[f"siprtc.{name}"].annotations
        assert hints.destructive_hint and not hints.idempotent_hint, name
        assert "Sensitive" in found[f"siprtc.{name}"].description, name


async def test_read_only_mode_keeps_carrier_credentials_out(monkeypatch):
    monkeypatch.setenv("SIPRTC_READ_ONLY", "true")
    get_settings.cache_clear()
    assert "siprtc.list_carrier_numbers" not in await tools()


@pytest.mark.parametrize(
    ("deny", "gone", "kept"),
    [
        ("cost", "make_call", "hangup_call"),
        ("sensitive", "update_application", "create_application"),
        ("destructive", "delete_recording", "start_call_recording"),
        ("write", "create_application", "list_applications"),
        ("siprtc.send_sms,release_phone_number", "release_phone_number", "send_message"),
    ],
)
async def test_deny_list_removes_tools(monkeypatch, deny, gone, kept):
    monkeypatch.setenv("SIPRTC_DENY", deny)
    get_settings.cache_clear()
    found = await tools()
    assert f"siprtc.{gone}" not in found and f"siprtc.{kept}" in found


def test_deny_list_typos_stop_the_server(monkeypatch):
    monkeypatch.setenv("SIPRTC_DENY", "send_smss")
    get_settings.cache_clear()
    with pytest.raises(ConfigError, match="send_smss"):
        create_server()


@respx.mock
async def test_tool_calls_are_rate_limited_per_account(monkeypatch):
    monkeypatch.setenv("SIPRTC_RATE_LIMIT", "0.1")  # a burst of one call, then one every 10 s
    get_settings.cache_clear()
    respx.get(f"{ACCOUNT}/Balance").mock(return_value=httpx.Response(200, json={"balance": 1}))
    async with Client(create_server()) as c:
        assert len(await c.list_tools()) > 100  # listings are not limited
        first = await c.call_tool("siprtc.get_balance", {}, raise_on_error=False)
        second = await c.call_tool("siprtc.get_balance", {}, raise_on_error=False)
    assert not first.is_error
    assert second.is_error and "Too many tool calls" in second.content[0].text


def test_readme_marks_destructive_tools():
    import pathlib

    readme = (pathlib.Path(__file__).parents[1] / "README.md").read_text()
    for name in ("hangup_call", "delete_recording", "release_phone_number"):
        line = next(line for line in readme.splitlines() if f"`siprtc.{name}`" in line)
        assert "⚠️" in line, line
