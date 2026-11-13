from __future__ import annotations

import base64
import json

import httpx
import pytest
import respx
from fastmcp import Client

from siprtc_mcp.auth import SiprtcCredentialTokenVerifier, decode_bearer_token
from siprtc_mcp.config import TOOLSETS, ConfigError, Settings, get_settings
from siprtc_mcp.server import create_server
from siprtc_mcp.toolset import COST_TOOLS, classify

from .conftest import BASE


async def tools():
    async with Client(create_server()) as c:
        return {t.name: t for t in await c.list_tools()}


# --- tool surface --------------------------------------------------------------------------


async def test_every_tool_is_namespaced_described_and_annotated():
    found = await tools()
    assert len(found) > 150
    for name, tool in found.items():
        assert name.startswith("siprtc."), name
        assert tool.description and len(tool.description) >= 15, name
        hints = tool.annotations
        assert hints is not None, name
        kind = classify(name.split(".", 1)[1])
        assert hints.read_only_hint == (kind == "read"), name
        assert hints.destructive_hint == (kind == "destructive"), name


async def test_no_tool_takes_a_raw_endpoint_path():
    for name, tool in (await tools()).items():
        assert "endpoint_path" not in tool.input_schema.get("properties", {}), name


async def test_destructive_and_billed_tools_are_marked():
    found = await tools()
    for name in ("delete_application", "release_phone_number", "hangup_call", "delete_recording", "disconnect_channel"):
        assert found[f"siprtc.{name}"].annotations.destructive_hint, name
    for name in COST_TOOLS:
        assert "billed" in found[f"siprtc.{name}"].description, name


async def test_domains_tools_are_gone():
    assert not [n for n in await tools() if "domain" in n and "sip_domain" not in n]


async def test_read_only_mode_drops_every_write(monkeypatch):
    monkeypatch.setenv("SIPRTC_READ_ONLY", "true")
    get_settings.cache_clear()
    found = await tools()
    assert found and all(t.annotations.read_only_hint for t in found.values())
    assert "siprtc.make_call" not in found and "siprtc.list_calls" in found


async def test_toolsets_limit_the_surface(monkeypatch):
    monkeypatch.setenv("SIPRTC_TOOLSETS", "voice,messaging")
    get_settings.cache_clear()
    found = await tools()
    assert "siprtc.make_call" in found and "siprtc.send_sms" in found
    assert "siprtc.list_workspaces" not in found and "siprtc.get_balance" not in found


# --- calling tools -------------------------------------------------------------------------


@respx.mock
async def test_tool_call_reaches_the_api_with_digits_only_numbers():
    route = respx.get(f"{BASE}/Accounts/AC0000000000000TEST0/PhoneNumbers/14155550100").mock(
        return_value=httpx.Response(200, json={"phone_number": "+14155550100"})
    )
    async with Client(create_server()) as c:
        result = await c.call_tool("siprtc.get_phone_number", {"phone_number": "+1 (415) 555-0100"})
    assert route.called
    assert json.loads(result.content[0].text)["phone_number"] == "+14155550100"


@respx.mock
async def test_api_errors_reach_the_model_with_the_reason():
    respx.post(f"{BASE}/Accounts/AC0000000000000TEST0/Calls").mock(
        return_value=httpx.Response(400, json={"code": 21211, "message": "The phone number is not valid."})
    )
    async with Client(create_server()) as c:
        result = await c.call_tool(
            "siprtc.make_call", {"call": {"To": "1", "From": "2", "speak": "hi"}}, raise_on_error=False
        )
    assert result.is_error
    assert "not valid" in result.content[0].text


@respx.mock
async def test_hangup_ends_the_call_through_the_update_route():
    route = respx.post(f"{BASE}/Accounts/AC0000000000000TEST0/Calls/CA1").mock(
        return_value=httpx.Response(200, json={"sid": "CA1", "status": "completed"})
    )
    async with Client(create_server()) as c:
        await c.call_tool("siprtc.hangup_call", {"call_id": "CA1"})
    assert json.loads(route.calls.last.request.content) == {"Status": "completed"}


@respx.mock
async def test_make_call_sends_lowercase_play_and_speak():
    route = respx.post(f"{BASE}/Accounts/AC0000000000000TEST0/Calls").mock(
        return_value=httpx.Response(201, json={"sid": "x"})
    )
    async with Client(create_server()) as c:
        await c.call_tool("siprtc.make_call", {"call": {"To": "+14155550100", "From": "+14155550101", "speak": "hi"}})
    assert json.loads(route.calls.last.request.content) == {"To": "+14155550100", "From": "+14155550101", "speak": "hi"}


@respx.mock
async def test_send_sms_sets_the_channel():
    route = respx.post(f"{BASE}/Accounts/AC0000000000000TEST0/Messages").mock(
        return_value=httpx.Response(201, json={"sid": "m"})
    )
    async with Client(create_server()) as c:
        await c.call_tool("siprtc.send_sms", {"sms": {"To": "+14155550100", "Body": "hi", "From": "+14155550101"}})
    assert json.loads(route.calls.last.request.content)["channel"] == "sms"


@respx.mock
async def test_update_application_keeps_fields_it_was_not_given():
    sid = "4d7757e8-1592-4a59-89a9-f98453e0ca14"
    url = f"{BASE}/Accounts/AC0000000000000TEST0/Applications/{sid}"
    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            json={"friendly_name": "Main", "status": "active", "voice_url": "https://a/v", "sms_url": "https://a/s"},
        )
    )
    put = respx.put(url).mock(return_value=httpx.Response(200, json={"status": "success"}))
    async with Client(create_server()) as c:
        await c.call_tool("siprtc.update_application", {"application_id": sid, "voice_url": "https://b/v"})
    body = json.loads(put.calls.last.request.content)
    assert body == {"FriendlyName": "Main", "Status": "active", "VoiceUrl": "https://b/v", "SmsUrl": "https://a/s"}


@respx.mock
async def test_not_found_lists_are_empty_not_errors():
    respx.get(f"{BASE}/Accounts/AC0000000000000TEST0/VerifiedPhoneNumbers").mock(
        return_value=httpx.Response(404, json={"message": "No verified phone number found"})
    )
    async with Client(create_server()) as c:
        result = await c.call_tool("siprtc.list_verified_phone_numbers", {})
    assert json.loads(result.content[0].text)["verified_phone_numbers"] == []


async def test_argument_checks_reach_the_model():
    async with Client(create_server()) as c:
        result = await c.call_tool("siprtc.update_call", {"call_id": "CA1"}, raise_on_error=False)
    assert result.is_error and "Pass at least one change" in result.content[0].text


async def test_missing_credentials_are_explained(monkeypatch):
    monkeypatch.delenv("SIPRTC_AUTH_ID")
    async with Client(create_server()) as c:
        result = await c.call_tool("siprtc.get_balance", {}, raise_on_error=False)
    assert result.is_error and "SIPRTC_AUTH_ID" in result.content[0].text


# --- auth ----------------------------------------------------------------------------------


def token(auth_id="AC0000000000000TEST0", secret="s3cret"):
    return base64.urlsafe_b64encode(f"{auth_id}:{secret}".encode()).decode()


def test_decode_bearer_token_accepts_unpadded_tokens():
    assert decode_bearer_token(token().rstrip("=")) == ("AC0000000000000TEST0", "s3cret")


@pytest.mark.parametrize("bad", ["", "not base64!", base64.b64encode(b"nocolon").decode(), token("bad/id"), "A" * 2000])
def test_decode_bearer_token_rejects_bad_tokens(bad):
    with pytest.raises(ValueError):
        decode_bearer_token(bad)


@respx.mock
async def test_verifier_checks_tokens_against_siprtc_and_caches():
    route = respx.get(f"{BASE}/Accounts/AC0000000000000TEST0/Balance").mock(return_value=httpx.Response(200, json={}))
    verifier = SiprtcCredentialTokenVerifier(verify_remote=True)
    assert await verifier.verify_token(token()) is not None
    assert await verifier.verify_token(token()) is not None
    assert route.call_count == 1


@respx.mock
async def test_verifier_refuses_wrong_credentials():
    respx.get(f"{BASE}/Accounts/AC0000000000000TEST0/Balance").mock(return_value=httpx.Response(401))
    assert await SiprtcCredentialTokenVerifier(verify_remote=True).verify_token(token()) is None


@respx.mock
async def test_verifier_refuses_when_siprtc_is_unreachable():
    respx.get(f"{BASE}/Accounts/AC0000000000000TEST0/Balance").mock(side_effect=httpx.ConnectError("down"))
    assert await SiprtcCredentialTokenVerifier(verify_remote=True).verify_token(token()) is None


async def test_verifier_without_remote_check_only_decodes():
    verifier = SiprtcCredentialTokenVerifier(verify_remote=False)
    assert (await verifier.verify_token(token())).client_id == "AC0000000000000TEST0"
    assert await verifier.verify_token("garbage") is None


# --- configuration -------------------------------------------------------------------------


def test_plain_http_is_refused_unless_allowed(monkeypatch):
    monkeypatch.setenv("SIPRTC_BASE_URL", "http://api.example.com/v1")
    with pytest.raises(ConfigError):
        Settings.from_env()
    monkeypatch.setenv("SIPRTC_ALLOW_INSECURE_HTTP", "true")
    assert Settings.from_env().base_url == "http://api.example.com/v1"


def test_localhost_http_is_fine(monkeypatch):
    monkeypatch.setenv("SIPRTC_BASE_URL", "http://localhost:8080/v1/")
    assert Settings.from_env().base_url == "http://localhost:8080/v1"


@pytest.mark.parametrize(
    "name,value",
    [
        ("SIPRTC_TOOLSETS", "voice,nope"),
        ("SIPRTC_READ_ONLY", "maybe"),
        ("SIPRTC_TIMEOUT", "0"),
        ("MCP_TRANSPORT", "sse"),
        ("SIPRTC_BASE_URL", "ftp://x"),
    ],
)
def test_bad_settings_are_refused(monkeypatch, name, value):
    monkeypatch.setenv(name, value)
    with pytest.raises(ConfigError):
        Settings.from_env()


def test_toolsets_cover_every_module():
    from siprtc_mcp.server import MODULES

    assert tuple(MODULES) == TOOLSETS


async def test_health_route():
    import asyncio

    mcp = create_server()
    app = mcp.http_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        response = await asyncio.wait_for(http.get("/healthz"), 10)
    assert response.status_code == 200 and response.json()["status"] == "ok"
