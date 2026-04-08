from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..config import sip_user_path, sip_users_path


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_sip_users",
        description=(
            "List SIP users/endpoints. Optionally pass query params and override endpoint_path if needed."
        ),
    )
    def list_sip_users(
        params: dict | None = None,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or sip_users_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("GET", path, params=params)

    @mcp.tool(
        name="siprtc.create_sip_user",
        description=(
            "Create a SIP user/endpoint. Provide payload required by Siprtc. "
            "Override endpoint_path if your account uses a different path."
        ),
    )
    def create_sip_user(
        payload: dict,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or sip_users_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("POST", path, json=payload)

    @mcp.tool(
        name="siprtc.update_sip_user",
        description=(
            "Delete a SIP user/endpoint by endpoint_id. "
            "Siprtc uses PUT for delete on this resource. Override endpoint_path if needed."
        ),
    )
    def delete_sip_user(
        endpoint_id: str,
        payload: dict | None = None,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or sip_user_path()
        path = format_path(template, auth_id=client.auth_id, endpoint_id=endpoint_id)
        return client.request("PUT", path, json=payload)

    @mcp.tool(
        name="siprtc.associate_sip_user_application",
        description=(
            "Associate or de-associate an application with a SIP user. "
            "Payload should include action and application_id."
        ),
    )
    def associate_sip_user_application(
        endpoint_id: str,
        payload: dict,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or sip_user_path()
        path = format_path(template, auth_id=client.auth_id, endpoint_id=endpoint_id)
        return client.request("PATCH", path, json=payload)
