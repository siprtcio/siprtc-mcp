from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..config import domain_path, domains_path


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_domains",
        description="List SIP domains. Optionally pass query params or override endpoint_path.",
    )
    def list_domains(
        params: dict | None = None,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or domains_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("GET", path, params=params)

    @mcp.tool(
        name="siprtc.create_domain",
        description="Create a SIP domain. Provide payload and optionally override endpoint_path.",
    )
    def create_domain(
        payload: dict,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or domains_path()
        path = format_path(template, auth_id=client.auth_id)
        return client.request("POST", path, json=payload)

    @mcp.tool(
        name="siprtc.get_domain",
        description="Fetch a SIP domain by domain_id. Override endpoint_path if needed.",
    )
    def get_domain(
        domain_id: str,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or domain_path()
        path = format_path(template, auth_id=client.auth_id, domain_id=domain_id)
        return client.request("GET", path)

    @mcp.tool(
        name="siprtc.update_domain",
        description=(
            "Update a SIP domain by domain_id. Provide payload and optional method (PUT/PATCH)."
        ),
    )
    def update_domain(
        domain_id: str,
        payload: dict,
        method: str = "PUT",
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or domain_path()
        path = format_path(template, auth_id=client.auth_id, domain_id=domain_id)
        return client.request(method.upper(), path, json=payload)

    @mcp.tool(
        name="siprtc.delete_domain",
        description="Delete a SIP domain by domain_id. Override endpoint_path if needed.",
    )
    def delete_domain(
        domain_id: str,
        endpoint_path: str | None = None,
    ) -> Any:
        client: SiprtcClient = client_factory()
        template = endpoint_path or domain_path()
        path = format_path(template, auth_id=client.auth_id, domain_id=domain_id)
        return client.request("DELETE", path)
