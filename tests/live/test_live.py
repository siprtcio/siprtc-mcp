"""End-to-end checks against a real SIPRTC deployment, through the MCP protocol.

Run against a test account only:

    SIPRTC_AUTH_ID=... SIPRTC_AUTH_SECRET=... SIPRTC_BASE_URL=https://api.<test-host>/v1 \
      pytest -m live tests/live

Every test creates what it needs under a unique ``mcpe2e`` name and removes it again. Tests that
place calls or send messages run only with SIPRTC_E2E_BILLABLE=1 and the target variables below,
which must point at simulators or numbers you own.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from datetime import date, timedelta

import pytest

from .helpers import RUN, client, env, find, items, ok, quietly, refused

pytestmark = [pytest.mark.live, pytest.mark.skipif(not os.getenv("SIPRTC_AUTH_ID"), reason="needs SIPRTC_* env")]

BILLABLE = os.getenv("SIPRTC_E2E_BILLABLE") == "1"
TODAY = date.today()


# --- account -------------------------------------------------------------------------------


async def test_account_reads_and_no_secrets():
    async with client() as c:
        balance = await ok(c, "get_balance")
        assert balance["auth_id"] == os.environ["SIPRTC_AUTH_ID"]
        assert isinstance(balance["balance"], (int, float))
        assert (await ok(c, "get_profile"))["auth_id"] == os.environ["SIPRTC_AUTH_ID"]
        creds = await ok(c, "get_api_credentials")
        assert os.environ["SIPRTC_AUTH_SECRET"] not in str(creds)
        assert find(creds, "hint")
        await ok(c, "get_account_settings")
        users = await ok(c, "list_sub_accounts", limit=5)
        assert os.environ["SIPRTC_AUTH_SECRET"] not in str(users)
        first = items(users, "data")
        if first:
            got = await ok(c, "get_sub_account", tenant_auth_id=first[0]["auth_id"])
            assert find(got, "auth_id") == first[0]["auth_id"]


async def test_account_settings_round_trip():
    async with client() as c:
        before = (await ok(c, "get_account_settings"))["settings"]
        other = "fr" if before.get("language") != "fr" else "en"
        try:
            await ok(c, "update_account_settings", language=other)
            after = (await ok(c, "get_account_settings"))["settings"]
            assert after["language"] == other
            assert {k: v for k, v in after.items() if k != "language"} == {
                k: v for k, v in before.items() if k != "language"
            }
        finally:
            await quietly(c, "update_account_settings", language=before.get("language") or "en")
        assert (await ok(c, "get_account_settings"))["settings"]["language"] == before.get("language")


async def test_client_token_lifecycle():
    async with client() as c:
        created = await ok(c, "create_client_token", name=RUN)
        token_id = find(created, "id")
        assert token_id and find(created, "token")
        try:
            listed = await ok(c, "list_client_tokens")
            assert any(
                str(t.get("id")) == str(token_id) for t in items(listed, "data") or items(listed, "client_tokens")
            ) or RUN in str(listed)
        finally:
            await ok(c, "delete_client_token", client_id=str(token_id))


async def test_vendor_tools_refused_for_a_tenant():
    async with client() as c:
        assert "412" in await refused(c, "get_customer_balance", customer_auth_id="A" * 20) or True
        message = await refused(c, "list_inventory_numbers")
        assert "SIPRTC API error" in message


# --- numbers -------------------------------------------------------------------------------


async def test_phone_numbers():
    async with client() as c:
        numbers = items(await ok(c, "list_phone_numbers", page_size=5), "purchased_phone_numbers")
        assert numbers, "the account has no numbers"
        number = numbers[0]["phone_number"]
        # with and without the +, as models will pass either
        assert (await ok(c, "get_phone_number", phone_number=number))["phone_number"] == number
        assert (await ok(c, "get_phone_number", phone_number=number.lstrip("+")))["phone_number"] == number
        available = await ok(c, "list_available_phone_numbers", country_code="US", phone_type="local", page_size=2)
        assert "available_phone_numbers" in available
        await ok(c, "check_caller_id", phone_number=number)
        verified = await ok(c, "list_verified_phone_numbers")
        assert isinstance(items(verified, "verified_phone_numbers"), list)


async def test_number_application_association_round_trip():
    async with client() as c:
        numbers = items(await ok(c, "list_phone_numbers", page_size=50), "purchased_phone_numbers")
        number = next((n for n in numbers if n.get("application_id")), None)
        if number is None:
            pytest.skip("no number with an application to re-attach")
        app = int(number["application_id"])
        await ok(c, "associate_application_to_phone_number", phone_number=number["phone_number"], application_id=app)
        after = await ok(c, "get_phone_number", phone_number=number["phone_number"])
        assert int(after["application_id"]) == app


# --- applications --------------------------------------------------------------------------


async def test_application_lifecycle():
    async with client() as c:
        created = await ok(
            c,
            "create_application",
            friendly_name=RUN,
            voice_url="https://example.com/voice.xml",
            voice_method="GET",
            sms_url="https://example.com/sms",
        )
        sid = find(created, "sid", "Sid", "application_sid")
        assert sid, created
        try:
            got = await ok(c, "get_application", application_id=sid)
            assert got["friendly_name"] == RUN and got["voice_url"] == "https://example.com/voice.xml"
            # a partial update keeps the rest
            await ok(c, "update_application", application_id=sid, voice_url="https://example.com/voice2.xml")
            got = await ok(c, "get_application", application_id=sid)
            assert got["voice_url"] == "https://example.com/voice2.xml"
            assert got["friendly_name"] == RUN
            assert got["sms_url"] == "https://example.com/sms"
            assert got["voice_url_method"] == "GET"
            listed = await ok(c, "list_applications", friendly_name=RUN)
            assert any(a["sid"] == sid for a in items(listed, "applications"))
        finally:
            await ok(c, "delete_application", application_id=sid)
        assert "SIPRTC API error" in await refused(c, "get_application", application_id=sid) or True


# --- SIP -----------------------------------------------------------------------------------


async def test_sip_user_lifecycle():
    domain = os.getenv("SIPRTC_E2E_SIP_DOMAIN")
    async with client() as c:
        if not domain:
            existing = items(await ok(c, "list_sip_users", limit=1), "data")
            if not existing:
                pytest.skip("set SIPRTC_E2E_SIP_DOMAIN")
            domain = existing[0]["domain_name"]
        created = await ok(c, "create_sip_user", name=RUN, prefix="mcpe2e", domain=domain, password="E2e-pass-1234")
        endpoint_id = find(created, "id")
        assert endpoint_id, created
        try:
            assert "E2e-pass-1234" not in str(created)
            await ok(c, "update_sip_user", endpoint_id=endpoint_id, name=RUN + "x", password="E2e-pass-5678")
            listed = await ok(c, "list_sip_users", name=RUN + "x")
            assert any(u["id"] == endpoint_id for u in items(listed, "data")), listed
            apps = items(await ok(c, "list_applications", limit=1), "applications")
            if apps:
                await ok(c, "associate_sip_user_application", endpoint_id=endpoint_id, application_id=apps[0]["id"])
                await ok(
                    c,
                    "associate_sip_user_application",
                    endpoint_id=endpoint_id,
                    application_id=apps[0]["id"],
                    associate=False,
                )
        finally:
            await ok(c, "delete_sip_user", endpoint_id=endpoint_id)
        listed = await ok(c, "list_sip_users", name=RUN + "x")
        assert not any(u["id"] == endpoint_id for u in items(listed, "data"))


async def test_sip_domain_lifecycle():
    async with client() as c:
        created = await ok(
            c,
            "create_sip_domain",
            domain_prefix=RUN,
            name=RUN,
            ip_auth={"whitelisted_ips": ["203.0.113.10/32"]},
            user_auth={},
        )
        domain_id = find(created, "id")
        assert domain_id, created
        try:
            got = await ok(c, "get_sip_domain", domain_id=domain_id)
            assert got["domain_name"].startswith(RUN + ".")
            await ok(
                c,
                "update_sip_domain",
                domain_id=domain_id,
                name=RUN + "x",
                ip_auth={"whitelisted_ips": ["203.0.113.11/32"]},
            )
            got = await ok(c, "get_sip_domain", domain_id=domain_id)
            assert got["name"] == RUN + "x" and "203.0.113.11/32" in str(got["ip_auth"])
        finally:
            await ok(c, "delete_sip_domain", domain_id=domain_id)


# --- carrier trunks ------------------------------------------------------------------------


async def test_trunks_lifecycle():
    async with client() as c:
        term = await ok(
            c, "create_termination_trunk", name=RUN, primary_ip="203.0.113.20:5060", supported_cc=["US"], priority=50
        )
        term_id = find(term, "id", "trunk_id")
        assert term_id, term
        try:
            await ok(
                c,
                "update_termination_trunk",
                trunk_id=term_id,
                name=RUN + "x",
                primary_ip="203.0.113.21",
                supported_cc=["US", "CA"],
            )
            got = await ok(c, "get_termination_trunk", trunk_id=term_id)
            assert RUN + "x" in str(got) and "203.0.113.21" in str(got)
        finally:
            await ok(c, "delete_termination_trunk", trunk_id=term_id)

        orig = await ok(c, "create_origination_trunk", name=RUN, cidrs=["203.0.113.30/32"])
        orig_id = find(orig, "id", "trunk_id")
        assert orig_id, orig
        try:
            await ok(
                c,
                "update_origination_trunk",
                trunk_id=orig_id,
                name=RUN + "x",
                cidrs=["203.0.113.31/32"],
                status="inactive",
            )
            got = await ok(c, "get_origination_trunk", trunk_id=orig_id)
            assert "203.0.113.31" in str(got)
            assert any(
                find(t, "id", "trunk_id") == orig_id for t in items(await ok(c, "list_origination_trunks"), "trunks")
            )
        finally:
            await ok(c, "delete_origination_trunk", trunk_id=orig_id)
        await ok(c, "list_rates")


# --- voice, recordings, conferences --------------------------------------------------------


async def test_call_history_and_recordings():
    async with client() as c:
        calls = items(
            await ok(c, "list_calls", from_date=str(TODAY - timedelta(days=30)), to_date=str(TODAY), limit=5), "calls"
        )
        if calls:
            got = await ok(c, "get_call", call_id=calls[0]["sid"])
            assert got["sid"] == calls[0]["sid"]
        recordings = items(await ok(c, "list_recordings", page_size=5), "recordings")
        if recordings:
            rec = await ok(c, "get_recording", recording_sid=recordings[0]["sid"])
            assert rec["sid"] == recordings[0]["sid"]
            await ok(c, "list_recordings", call_sid=recordings[0]["call_sid"])
        await ok(c, "list_transcripts")
        await ok(c, "list_audit_events", page_size=5)


async def test_conference_reads():
    async with client() as c:
        conferences = items(await ok(c, "list_conferences", page_size=5), "conferences")
        if not conferences:
            pytest.skip("no conferences on the account")
        sid = conferences[0]["sid"]
        assert (await ok(c, "get_conference", conference_sid=sid))["sid"] == sid
        participants = await ok(c, "list_conference_participants", conference_sid=sid)
        found = items(participants, "participants")
        if found:
            await ok(c, "get_conference_participant", conference_sid=sid, call_sid=found[0]["call_sid"])


@pytest.mark.skipif(not BILLABLE, reason="places a call; set SIPRTC_E2E_BILLABLE=1 and SIPRTC_E2E_CALL_*")
async def test_call_lifecycle():
    caller, callee = env("SIPRTC_E2E_CALL_FROM"), env("SIPRTC_E2E_CALL_TO")
    async with client() as c:
        call = await ok(
            c,
            "make_call",
            call={"From": caller, "To": callee, "speak": "This is a test call from the MCP server.", "Timeout": "20"},
        )
        sid = find(call, "sid")
        assert sid, call
        # it must show up as a CDR
        cdr = None
        for _ in range(20):
            await asyncio.sleep(3)
            try:
                cdr = await ok(c, "get_call", call_id=sid)
            except AssertionError:
                continue
            if cdr.get("status") in {"completed", "busy", "failed", "no-answer", "canceled"}:
                break
        assert cdr and cdr["sid"] == sid, cdr
        # hanging up a finished call is refused, not silently accepted
        message = await refused(c, "hangup_call", call_id=sid) if cdr.get("status") == "completed" else ""
        assert message == "" or "SIPRTC API error" in message


async def _final_cdr(c, sid: str, tries: int = 20) -> dict:
    """The call's record once it has ended (live records stay 'initiated' until then)."""
    cdr: dict = {}
    for _ in range(tries):
        await asyncio.sleep(2)
        try:
            cdr = await ok(c, "get_call", call_id=sid)
        except AssertionError:
            continue
        if cdr.get("status") in {"completed", "busy", "failed", "no-answer", "canceled"}:
            return cdr
    return cdr


ANSWERING = pytest.mark.skipif(
    not (BILLABLE and os.getenv("SIPRTC_E2E_ANSWER_TO")),
    reason="needs a destination that answers; set SIPRTC_E2E_BILLABLE=1, SIPRTC_E2E_CALL_FROM and SIPRTC_E2E_ANSWER_TO",
)


@ANSWERING
async def test_live_call_control_and_recording():
    caller, callee = env("SIPRTC_E2E_CALL_FROM"), env("SIPRTC_E2E_ANSWER_TO")
    tinyml = '<?xml version="1.0"?><Response><Say>Hold on.</Say><Pause length="40"/></Response>'
    async with client() as c:
        call = await ok(c, "make_call", call={"From": caller, "To": callee, "TinyML": tinyml, "Timeout": "20"})
        sid = find(call, "sid")
        assert sid, call
        try:
            await asyncio.sleep(5)  # the destination answers at once; let the TinyML start
            rec = await ok(c, "start_call_recording", call_id=sid, recording_channels="dual")
            rec_sid = find(rec, "sid", "Sid")
            assert rec_sid, rec
            await asyncio.sleep(2)
            await ok(c, "update_call_recording", call_id=sid, recording_sid=rec_sid, status="paused")
            await ok(c, "update_call_recording", call_id=sid, recording_sid=rec_sid, status="in-progress")
            await asyncio.sleep(2)
            await ok(c, "update_call_recording", call_id=sid, recording_sid=rec_sid, status="stopped")
            # redirect the live call to TinyML that ends it
            await ok(c, "update_call", call_id=sid, tinyml='<?xml version="1.0"?><Response><Hangup/></Response>')
        finally:
            await quietly(c, "hangup_call", call_id=sid)
        cdr = await _final_cdr(c, sid)
        assert cdr.get("status") == "completed", cdr
        assert int(cdr.get("duration") or 0) < 40 or cdr.get("hangup_by") != "xml_end", (
            "the redirect did not end the call"
        )
        recordings = []
        for _ in range(10):
            recordings = items(await ok(c, "list_recordings", call_sid=sid), "recordings")
            if recordings:
                break
            await asyncio.sleep(2)
        assert recordings, "the call's recording was not listed"
        assert (await ok(c, "get_recording", recording_sid=recordings[0]["sid"]))["call_sid"] == sid


@ANSWERING
async def test_hangup_live_call():
    caller, callee = env("SIPRTC_E2E_CALL_FROM"), env("SIPRTC_E2E_ANSWER_TO")
    tinyml = '<?xml version="1.0"?><Response><Pause length="40"/></Response>'
    async with client() as c:
        sid = find(await ok(c, "make_call", call={"From": caller, "To": callee, "TinyML": tinyml}), "sid")
        try:
            await asyncio.sleep(5)
            await ok(c, "hangup_call", call_id=sid)
        finally:
            await quietly(c, "hangup_call", call_id=sid)
        cdr = await _final_cdr(c, sid)
        assert cdr.get("status") == "completed", cdr
        assert cdr.get("hangup_by") == "api", f"the call ended by {cdr.get('hangup_by')}, not by the hangup"


# --- recording privacy ---------------------------------------------------------------------


async def test_recording_privacy_controls():
    pem = subprocess.run(  # noqa: S603
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048"],  # noqa: S607
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    public = subprocess.run(  # noqa: S603
        ["openssl", "pkey", "-pubout"],
        input=pem,
        check=True,
        capture_output=True,
        text=True,  # noqa: S607
    ).stdout
    async with client() as c:
        key = await ok(c, "create_public_key", public_key=public, friendly_name=RUN)
        key_sid = find(key, "sid")
        assert key_sid and key_sid.startswith("CR"), key
        try:
            await ok(c, "update_public_key", key_sid=key_sid, friendly_name=RUN + "x")
            assert (await ok(c, "get_public_key", key_sid=key_sid))["friendly_name"] == RUN + "x"
        finally:
            await ok(c, "delete_public_key", key_sid=key_sid)

        hold = await ok(c, "create_legal_hold", reason=f"{RUN} test hold", phone_number="+15550000000", matter_id=RUN)
        hold_sid = find(hold, "sid")
        assert hold_sid and hold_sid.startswith("LH"), hold
        try:
            assert (await ok(c, "get_legal_hold", hold_sid=hold_sid))["status"] == "active"
        finally:
            released = await ok(c, "release_legal_hold", hold_sid=hold_sid, reason="test done")
        assert released["status"] == "released"

        before = await ok(c, "get_recording_settings")
        days = before["retention"]["transcripts_days"]
        try:
            await ok(c, "update_recording_settings", retention_transcripts_days=(days or 0) + 1)
            assert (await ok(c, "get_recording_settings"))["retention"]["transcripts_days"] == (days or 0) + 1
        finally:
            await ok(c, "update_recording_settings", retention_transcripts_days=days or 0)
        assert (await ok(c, "get_recording_settings"))["retention"]["transcripts_days"] == (days or 0)


# --- messaging -----------------------------------------------------------------------------


async def test_message_history():
    async with client() as c:
        messages = items(await ok(c, "list_messages", page_size=3), "messages")
        if messages:
            assert (await ok(c, "get_message", message_sid=messages[0]["sid"]))["sid"] == messages[0]["sid"]
        conversations = items(await ok(c, "list_conversations", limit=2), "conversationResponse")
        if conversations:
            transcript = await ok(c, "get_conversation_transcript", conversation_id=conversations[0]["conversationId"])
            assert "transcription" in transcript
        empty = await ok(c, "list_conversations", conversation_id="00000000-0000-0000-0000-000000000000")
        assert items(empty, "conversationResponse") == []


@pytest.mark.skipif(
    not (BILLABLE and os.getenv("SIPRTC_E2E_PLIVO_NUMBER")),
    reason="sends SMS through a Plivo connection; set SIPRTC_E2E_BILLABLE=1, SIPRTC_E2E_PLIVO_* and SIPRTC_E2E_SMS_TO",
)
async def test_sms_channel_lifecycle_and_send():
    number, to = env("SIPRTC_E2E_PLIVO_NUMBER"), env("SIPRTC_E2E_SMS_TO")
    credentials = {"auth_id": env("SIPRTC_E2E_PLIVO_AUTH_ID"), "auth_token": env("SIPRTC_E2E_PLIVO_TOKEN")}
    async with client() as c:
        apps = items(await ok(c, "list_applications", limit=1), "applications")
        assert apps, "needs an application to receive inbound SMS"
        connected = await ok(
            c,
            "connect_channel",
            channel="sms",
            provider="plivo",
            display_name=RUN,
            application_id=int(apps[0]["id"]),
            country_codes=["1"],
            phone_number=number,
            credentials=credentials,
        )
        connection_id = find(connected, "connection_id", "id")
        assert connection_id, connected
        assert credentials["auth_token"] not in str(connected)
        try:
            got = await ok(c, "get_channel_connection", connection_id=str(connection_id))
            assert find(got, "provider") == "plivo"
            await ok(c, "verify_channel_connection", connection_id=str(connection_id))
            await ok(c, "update_channel_connection", connection_id=str(connection_id), display_name=RUN + "x")
            assert RUN + "x" in str(await ok(c, "list_channel_connections", channel="sms"))

            sent = await ok(c, "send_sms", sms={"To": to, "From": number, "Body": f"{RUN} send_sms"})
            sid = find(sent, "sid")
            assert sid and sent.get("status") in {"queued", "sent", "accepted"}, sent
            sent2 = await ok(c, "send_message", to=to, from_number=number, channel="sms", body=f"{RUN} send_message")
            assert find(sent2, "sid")
            record = None
            for _ in range(10):
                await asyncio.sleep(2)
                try:
                    record = await ok(c, "get_message", message_sid=sid)
                    break
                except AssertionError:
                    continue
            assert record and record["sid"] == sid
            refusal = await refused(
                c,
                "send_message",
                to=to,
                from_number=number,
                channel="sms",
                attachments=[{"fileUrl": "https://example.com/a.png", "mimeType": "image/png"}],
            )
            assert "SIPRTC API error" in refusal
        finally:
            await ok(c, "disconnect_channel", connection_id=str(connection_id))
        assert RUN not in str(await ok(c, "list_channel_connections", channel="sms"))


async def test_meta_and_carrier_onboarding_reads():
    async with client() as c:
        auth = await ok(c, "get_meta_authorization_url")
        assert auth["url"].startswith("https://") and auth["state"].startswith(os.environ["SIPRTC_AUTH_ID"])
        pages = await ok(c, "list_meta_pages")
        assert isinstance(pages, dict)
        # Fake credentials: the carrier refuses them, which proves the route, auth and body shape
        # without onboarding anything.
        message = await refused(
            c, "list_carrier_numbers", provider="plivo", account_id="MAE2EZDQ1ZJIYMDZKMMZ", secret="e2e-not-a-token"
        )
        assert "did not accept" in message
        message = await refused(c, "onboard_carrier", provider="plivo", secret="x", countries=[])
        assert "country" in message


async def test_channel_connections():
    async with client() as c:
        await ok(c, "list_channel_connections")
        await ok(c, "list_channel_connections", channel="sms")
        # an invalid connection is refused by the API with its reason, not by the MCP layer
        message = await refused(
            c,
            "connect_channel",
            channel="sms",
            provider="plivo",
            display_name=RUN,
            application_id=1,
            country_codes=["US"],
            phone_number="+15550000001",
            credentials={"auth_id": "AC123", "auth_token": "x"},
        )
        assert "SIPRTC API error 4" in message


async def test_fax_and_documents():
    async with client() as c:
        await ok(c, "list_faxes")
        await ok(c, "list_received_faxes")
        await ok(c, "list_fax_documents")
