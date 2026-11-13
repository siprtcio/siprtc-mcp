"""Messaging channel connections (SMS providers, WhatsApp, Viber), the Facebook/Meta integration and
bring-your-own-carrier onboarding (Twilio, Plivo, Telnyx)."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ..client import compact
from ._common import ACCOUNT, api

CHANNELS = ACCOUNT + "/Integrations/Channels"
CHANNEL = CHANNELS + "/{connection_id}"
META = ACCOUNT + "/Integrations/Meta"
CARRIERS = ACCOUNT + "/Integrations/Carriers"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_channel_connections",
        description="List connected messaging channels (sms providers, whatsapp, viber), optionally for one channel.",
    )
    def list_channel_connections(channel: Literal["sms", "whatsapp", "viber"] | None = None) -> Any:
        return api(client_factory, "GET", CHANNELS, params={"channel": channel})

    @mcp.tool(name="siprtc.get_channel_connection", description="Fetch one channel connection by id.")
    def get_channel_connection(connection_id: str) -> Any:
        return api(client_factory, "GET", CHANNEL, connection_id=connection_id)

    @mcp.tool(
        name="siprtc.connect_channel",
        description=(
            "Connect a messaging channel with your own provider credentials. Pass phone_number or "
            "(sms only, send-only) sender_id. credentials by provider: twilio {account_sid, auth_token}, "
            "plivo {auth_id, auth_token}, movider {api_key, api_secret}, whatsapp {access_token, app_secret} "
            "plus phone_number_id and waba_id, viber {auth_token}. application_id is the SIPRTC "
            "application that handles inbound messages."
        ),
    )
    def connect_channel(
        channel: Literal["sms", "whatsapp", "viber"],
        display_name: str,
        application_id: int,
        country_codes: list[str],
        credentials: dict,
        provider: Literal["twilio", "plivo", "movider"] | None = None,
        phone_number: str | None = None,
        sender_id: str | None = None,
        phone_number_id: str | None = None,
        waba_id: str | None = None,
    ) -> Any:
        body = {
            "channel": channel,
            "display_name": display_name,
            "application_id": application_id,
            "country_codes": country_codes,
            "credentials": credentials,
            "provider": provider,
            "phone_number": phone_number,
            "sender_id": sender_id,
            "phone_number_id": phone_number_id,
            "waba_id": waba_id,
        }
        return api(client_factory, "POST", CHANNELS, json=body)

    @mcp.tool(
        name="siprtc.update_channel_connection",
        description="Rename a channel connection, point it at another application, or change its countries.",
    )
    def update_channel_connection(
        connection_id: str,
        display_name: str | None = None,
        application_id: int | None = None,
        country_codes: list[str] | None = None,
    ) -> Any:
        body = {"display_name": display_name, "application_id": application_id, "country_codes": country_codes}
        return api(client_factory, "PATCH", CHANNEL, json=body, connection_id=connection_id)

    @mcp.tool(
        name="siprtc.update_channel_credentials",
        description="Replace a channel connection's provider credentials (same keys as connect_channel).",
    )
    def update_channel_credentials(connection_id: str, credentials: dict) -> Any:
        return api(client_factory, "PUT", CHANNEL + "/Credentials", json=credentials, connection_id=connection_id)

    @mcp.tool(
        name="siprtc.verify_channel_connection",
        description="Check a channel connection's credentials against the provider and report the result.",
    )
    def verify_channel_connection(connection_id: str) -> Any:
        return api(client_factory, "POST", CHANNEL + "/Verify", connection_id=connection_id)

    @mcp.tool(
        name="siprtc.disconnect_channel",
        description="Disconnect (delete) a channel connection. Messages on it stop flowing.",
    )
    def disconnect_channel(connection_id: str) -> Any:
        return api(client_factory, "DELETE", CHANNEL, connection_id=connection_id)

    @mcp.tool(
        name="siprtc.get_meta_integration",
        description="Show the account's Facebook/Meta integration and its connected pages (404 when none is connected).",
    )
    def get_meta_integration() -> Any:
        return api(client_factory, "GET", META)

    @mcp.tool(
        name="siprtc.get_meta_authorization_url",
        description=(
            "Get the Facebook login URL that connects a Meta (Facebook) account to this SIPRTC account. "
            "A person must open it in a browser and approve; the pages appear in get_meta_integration afterwards."
        ),
    )
    def get_meta_authorization_url(return_url: str | None = None) -> Any:
        return api(client_factory, "GET", META + "/Authorization", params={"return_url": return_url})

    @mcp.tool(
        name="siprtc.list_meta_pages",
        description="List the Facebook pages the connected Meta integration can message from, optionally for one Facebook user.",
    )
    def list_meta_pages(provider_user_id: str | None = None) -> Any:
        return api(
            client_factory, "GET", META + "/Pages", params={"provider_user_id": provider_user_id}, empty_as="pages"
        )

    @mcp.tool(
        name="siprtc.remove_meta_page",
        description="Stop using one Facebook page: messages to it no longer reach this account.",
    )
    def remove_meta_page(page_id: str) -> Any:
        return api(client_factory, "DELETE", META + "/Pages/{page_id}", page_id=page_id)

    @mcp.tool(
        name="siprtc.remove_meta_user",
        description="Remove one connected Facebook user and the pages that came with them.",
    )
    def remove_meta_user(provider_user_id: str) -> Any:
        return api(client_factory, "DELETE", META + "/Users/{provider_user_id}", provider_user_id=provider_user_id)

    @mcp.tool(
        name="siprtc.disconnect_meta_integration",
        description="Disconnect the whole Facebook/Meta integration: every page and user. Messenger stops working.",
    )
    def disconnect_meta_integration() -> Any:
        return api(client_factory, "DELETE", META)

    @mcp.tool(
        name="siprtc.list_carrier_numbers",
        description=(
            "Check a Twilio, Plivo or Telnyx account's credentials and list its phone numbers, before moving "
            "them here with onboard_carrier. Changes nothing. account_id is the Twilio Account SID or Plivo "
            "Auth ID (not needed for Telnyx); secret is the auth token, API key secret or Telnyx API key; "
            "key_id is a Twilio API key SID when not using the auth token."
        ),
    )
    def list_carrier_numbers(
        provider: Literal["twilio", "plivo", "telnyx"],
        secret: str,
        account_id: str | None = None,
        key_id: str | None = None,
    ) -> Any:
        credentials = {"account_id": account_id, "key_id": key_id, "secret": secret}
        return api(
            client_factory,
            "POST",
            CARRIERS + "/Numbers",
            json={"provider": provider, "credentials": compact(credentials)},
        )

    @mcp.tool(
        name="siprtc.onboard_carrier",
        description=(
            "Bring your own carrier: connect a Twilio, Plivo or Telnyx account and route the chosen numbers "
            "(up to 100, from list_carrier_numbers) through SIPRTC. It sets up a SIP trunk on the carrier's "
            "side and ours and repoints those numbers, which changes how calls to them are handled. Needs "
            "the account owner's credentials and the ISO country codes (e.g. ['US']) calls will go to."
        ),
    )
    def onboard_carrier(
        provider: Literal["twilio", "plivo", "telnyx"],
        secret: str,
        countries: list[str],
        numbers: list[str] | None = None,
        account_id: str | None = None,
        key_id: str | None = None,
    ) -> Any:
        if not countries:
            raise ToolError("Pass at least one ISO country code in countries, e.g. ['US'].")
        if numbers and len(numbers) > 100:
            raise ToolError("Onboard at most 100 numbers at a time.")
        credentials = {"account_id": account_id, "key_id": key_id, "secret": secret}
        body = {
            "provider": provider,
            "credentials": compact(credentials),
            "numbers": numbers or [],
            "countries": [code.upper() for code in countries],
        }
        return api(client_factory, "POST", CARRIERS, json=body)

    @mcp.tool(
        name="siprtc.send_messenger_message",
        description="Send a Facebook Messenger message from a connected page to a user (recipient_id is their page-scoped id).",
    )
    def send_messenger_message(recipient_id: str, message: str, page_id: str) -> Any:
        body = {"recipientId": recipient_id, "message": message, "pageId": page_id}
        return api(client_factory, "POST", META + "/Messenger/Messages", json=body)
