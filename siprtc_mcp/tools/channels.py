"""Messaging channel connections (SMS providers, WhatsApp, Viber) and the Facebook/Meta integration."""

from __future__ import annotations

from typing import Any, Literal

from ._common import ACCOUNT, api

CHANNELS = ACCOUNT + "/Integrations/Channels"
CHANNEL = CHANNELS + "/{connection_id}"
META = ACCOUNT + "/Integrations/Meta"


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
        name="siprtc.send_messenger_message",
        description="Send a Facebook Messenger message from a connected page to a user (recipient_id is their page-scoped id).",
    )
    def send_messenger_message(recipient_id: str, message: str, page_id: str) -> Any:
        body = {"recipientId": recipient_id, "message": message, "pageId": page_id}
        return api(client_factory, "POST", META + "/Messenger/Messages", json=body)
