from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError

from ..config import (
    phone_numbers_associate_path,
    phone_numbers_available_path,
    phone_numbers_buy_path,
    phone_numbers_get_path,
    phone_numbers_list_path,
    phone_numbers_release_path,
)
from ._common import ACCOUNT, api, digits

VERIFIED = ACCOUNT + "/VerifiedPhoneNumbers"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_phone_numbers",
        description=(
            "List the phone numbers on the account. Filters: status (default active), phone_number, "
            "country_code, type (local/mobile/tollfree), capability. Paged with page and page_size."
        ),
    )
    def list_phone_numbers(
        status: str | None = None,
        phone_number: str | None = None,
        country_code: str | None = None,
        type: str | None = None,
        capability: str | None = None,
        application_id: int | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        query = {
            "status": status,
            "phoneNumber": phone_number,
            "countryCode": country_code,
            "type": type,
            "capability": capability,
            "applicationId": application_id,
            "page": page,
            "pageSize": page_size,
        }
        return api(client_factory, "GET", phone_numbers_list_path(), params=query)

    @mcp.tool(
        name="siprtc.list_available_phone_numbers",
        description=(
            "Search numbers available to buy. country_code is ISO 3166-1 alpha-2 (or 'all'); "
            "phone_type is local, mobile, tollfree or all."
        ),
    )
    def list_available_phone_numbers(
        country_code: str,
        phone_type: str,
        capability: str | None = None,
        contains: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {"capability": capability, "phoneNumber": contains, "page": page, "pageSize": page_size}
        return api(
            client_factory,
            "GET",
            phone_numbers_available_path(),
            params=params,
            country_code=country_code,
            phone_type=phone_type,
        )

    @mcp.tool(
        name="siprtc.get_phone_number",
        description="Fetch one number on the account, with its rates, capability and application.",
    )
    def get_phone_number(phone_number: str) -> Any:
        return api(client_factory, "GET", phone_numbers_get_path(), phone_number=digits(phone_number))

    @mcp.tool(
        name="siprtc.buy_phone_number",
        description=(
            "Buy a number from the available list (billed: setup plus monthly charge; 402 when the "
            "balance is too low). Returns the purchased number."
        ),
    )
    def buy_phone_number(
        phone_number: str,
        application_type: str | None = None,
    ) -> Any:
        body = {"application_type": application_type} if application_type else None
        return api(
            client_factory,
            "POST",
            phone_numbers_buy_path(),
            json=body,
            phone_number=digits(phone_number),
        )

    @mcp.tool(
        name="siprtc.release_phone_number",
        description="Release a number from the account. Inbound calls and messages to it stop.",
    )
    def release_phone_number(phone_number: str) -> Any:
        return api(client_factory, "DELETE", phone_numbers_release_path(), phone_number=digits(phone_number))

    @mcp.tool(
        name="siprtc.associate_application_to_phone_number",
        description=(
            "Attach an application to a number (it then handles the number's inbound calls/messages), "
            "or detach it with associate=false."
        ),
    )
    def associate_application_to_phone_number(
        phone_number: str,
        application_id: int,
        associate: bool = True,
    ) -> Any:
        body = {
            "action": "number_app_association" if associate else "number_app_deassociation",
            "application_id": application_id,
        }
        return api(
            client_factory,
            "PATCH",
            phone_numbers_associate_path(),
            json=body,
            phone_number=digits(phone_number),
        )

    @mcp.tool(
        name="siprtc.update_phone_number_routing",
        description=(
            "Set how a number's inbound traffic is routed in the contact centre: an AI agent "
            "(ai_enabled + ai_agent), an IVR, or a taskrouter workspace/workflow/task queue."
        ),
    )
    def update_phone_number_routing(
        phone_number: str,
        ai_enabled: bool | None = None,
        ai_agent: str | None = None,
        ivr: str | None = None,
        workspace: str | None = None,
        workflow: str | None = None,
        task_queue_sid: str | None = None,
        channel: str | None = None,
        moh_id: str | None = None,
    ) -> Any:
        body = {
            "ai_enabled": ai_enabled,
            "ai_agent": ai_agent,
            "ivr": ivr,
            "workspace": workspace,
            "workflow": workflow,
            "task_queue_sid": task_queue_sid,
            "channel": channel,
            "moh_id": moh_id,
        }
        if all(value is None for value in body.values()):
            raise ToolError("Pass at least one routing field.")
        return api(
            client_factory,
            "PATCH",
            ACCOUNT + "/PhoneNumbers/MetaData/{phone_number}",
            json=body,
            phone_number=digits(phone_number),
        )

    @mcp.tool(
        name="siprtc.check_caller_id",
        description=(
            "Check whether a number may be used as caller ID (From) on outbound calls. Returns the "
            "number's record, or null when caller-ID checks are off for the account."
        ),
    )
    def check_caller_id(phone_number: str) -> Any:
        return api(client_factory, "GET", ACCOUNT + "/CallerIds/{phone_number}", phone_number=digits(phone_number))

    @mcp.tool(
        name="siprtc.list_verified_phone_numbers",
        description="List outside numbers verified for use as caller ID (404 when there are none).",
    )
    def list_verified_phone_numbers(page: int | None = None) -> Any:
        return api(client_factory, "GET", VERIFIED, params={"page": page}, empty_as="verified_phone_numbers")

    @mcp.tool(name="siprtc.get_verified_phone_number", description="Fetch one verified caller-ID number.")
    def get_verified_phone_number(phone_number: str) -> Any:
        return api(client_factory, "GET", VERIFIED + "/{phone_number}", phone_number=digits(phone_number))

    @mcp.tool(name="siprtc.delete_verified_phone_number", description="Remove a verified caller-ID number.")
    def delete_verified_phone_number(phone_number: str) -> Any:
        return api(client_factory, "DELETE", VERIFIED + "/{phone_number}", phone_number=digits(phone_number))
