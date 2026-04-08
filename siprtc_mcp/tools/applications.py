from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..config import application_path, applications_path


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_applications",
        description="List applications. Optionally pass query params or override endpoint_path.",
    )
    def list_applications(
        params: dict | None = None,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or applications_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("GET", path, params=params)

    @mcp.tool(
        name="siprtc.create_application",
        description="Create an application. Provide payload and optionally override endpoint_path.",
    )
    def create_application(
        payload: dict,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or applications_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("POST", path, json=payload)

    @mcp.tool(
        name="siprtc.update_application",
        description=(
            "Update an application by application_id. Provide payload and optional method (PUT/PATCH)."
        ),
    )
    def update_application(
        application_id: str,
        payload: dict,
        method: str = "PUT",
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or application_path()
        path = format_path(template, auth_id=client.auth_id, application_sid=application_id)
        return client.request(method.upper(), path, json=payload)

    @mcp.tool(
        name="siprtc.delete_application",
        description="Delete an application by application_id. Override endpoint_path if needed.",
    )
    def delete_application(
        application_id: str,
        endpoint_path: str | None = None,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        template = endpoint_path or application_path()
        path = format_path(template, auth_id=client.auth_id, application_sid=application_id)
        return client.request("DELETE", path)
