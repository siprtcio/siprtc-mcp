from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..config import (
    phone_numbers_associate_path,
    phone_numbers_available_path,
    phone_numbers_buy_path,
    phone_numbers_get_path,
    phone_numbers_list_path,
    phone_numbers_release_path,
)


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_phone_numbers",
        description=(
            "List purchased phone numbers. You can pass optional query params (e.g., pagination). "
            "If your Siprtc account uses different endpoints, override endpoint_path."
        ),
    )
    def list_phone_numbers(
        params: dict | None = None,
        endpoint_path: str | None = None,
    ) -> Any:
        """
        List purchased phone numbers.

        Args:
          params: Optional query parameters for filtering or pagination.
          endpoint_path: Optional override path (relative to base URL).
        """
        client: SiprtcClient = client_factory()
        template = endpoint_path or phone_numbers_list_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("GET", path, params=params)

    @mcp.tool(
        name="siprtc.buy_phone_number",
        description=(
            "Purchase/buy a phone number by phone_number. "
            "If your Siprtc account uses different endpoints, override endpoint_path."
        ),
    )
    def buy_phone_number(
        phone_number: str,
        endpoint_path: str | None = None,
        payload: dict | None = None,
    ) -> Any:
        """
        Buy a phone number.

        Args:
          phone_number: Phone number to purchase.
          endpoint_path: Optional override path (relative to base URL).
          payload: Optional JSON body if required by the API.
        """
        client: SiprtcClient = client_factory()
        template = endpoint_path or phone_numbers_buy_path()
        path = format_path(template, auth_id=client.auth_id, phone_number=phone_number)
        return client.request("POST", path, json=payload)

    @mcp.tool(
        name="siprtc.release_phone_number",
        description=(
            "Release a purchased phone number. "
            "If your Siprtc account uses different endpoints, override endpoint_path."
        ),
    )
    def release_phone_number(
        phone_number: str,
        endpoint_path: str | None = None,
        payload: dict | None = None,
    ) -> Any:
        """
        Release a phone number.

        Args:
          phone_number: Phone number to release (E.164 without +, e.g., 15677654321).
          endpoint_path: Optional override path (relative to base URL).
          payload: Optional JSON body if the API requires it.
        """
        client: SiprtcClient = client_factory()
        template = endpoint_path or phone_numbers_release_path()
        path = format_path(template, auth_id=client.auth_id, phone_number=phone_number)
        return client.request("DELETE", path, json=payload)

    @mcp.tool(
        name="siprtc.get_phone_number",
        description="Get details of a purchased phone number by phone_number.",
    )
    def get_phone_number(
        phone_number: str,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or phone_numbers_get_path()
        path = format_path(template, auth_id=client.auth_id, phone_number=phone_number)
        return client.request("GET", path)

    @mcp.tool(
        name="siprtc.list_available_phone_numbers",
        description=(
            "List available phone numbers to purchase. "
            "Provide country_code (ISO 3166-1 alpha-2) and phone_type (tollfree/local/mobile)."
        ),
    )
    def list_available_phone_numbers(
        country_code: str,
        phone_type: str,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or phone_numbers_available_path()
        path = format_path(
            template, auth_id=client.auth_id, country_code=country_code, phone_type=phone_type
        )
        return client.request("GET", path)

    @mcp.tool(
        name="siprtc.associate_application_to_phone_number",
        description=(
            "Associate or de-associate an application with a phone number. "
            "Payload should include action and application_id."
        ),
    )
    def associate_application_to_phone_number(
        phone_number: str,
        payload: dict,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or phone_numbers_associate_path()
        path = format_path(template, auth_id=client.auth_id, phone_number=phone_number)
        return client.request("PATCH", path, json=payload)
