"""SIP users (endpoints that register to SIPRTC) and SIP domains (PBXs/trunks sending calls in)."""

from __future__ import annotations

from typing import Any

from ..config import sip_user_path, sip_users_path
from ._common import ACCOUNT, api

DOMAINS = ACCOUNT + "/Sips/Domains"
DOMAIN = DOMAINS + "/{domain_id}"


def _association(associate: bool, application_id: int) -> dict:
    return {
        "action": "sip_app_association" if associate else "sip_app_deassociation",
        "application_id": application_id,
    }


def register(mcp, client_factory):
    # --- SIP users --------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_users",
        description="List SIP users (endpoints), optionally filtered by name, SIP username or status.",
    )
    def list_sip_users(
        name: str | None = None,
        sip_user: str | None = None,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {"name": name, "sipUser": sip_user, "status": status, "page": page, "limit": limit}
        return api(client_factory, "GET", sip_users_path(), params=params)

    @mcp.tool(
        name="siprtc.list_available_sip_users",
        description="List SIP users in a taskrouter workspace that are not yet bound to an agent (worker).",
    )
    def list_available_sip_users(workspace_id: str, name: str | None = None) -> Any:
        return api(
            client_factory, "GET", sip_users_path() + "/available", params={"workspace_id": workspace_id, "name": name}
        )

    @mcp.tool(
        name="siprtc.create_sip_user",
        description=(
            "Create a SIP user. name: letters/digits; prefix: 3-8 letters/digits (the SIP username "
            "becomes prefix + a timestamp); domain: the SIP domain FQDN to register on; password: 6+ chars."
        ),
    )
    def create_sip_user(
        name: str,
        prefix: str,
        domain: str,
        password: str,
        codec_list: str | None = None,
        status: bool | None = None,
        presence: bool | None = None,
    ) -> Any:
        body = {
            "name": name,
            "prefix": prefix,
            "domain": domain,
            "password": password,
            "codec_list": codec_list,
            "status": status,
            "presence": presence,
        }
        return api(client_factory, "POST", sip_users_path(), json=body)

    @mcp.tool(
        name="siprtc.update_sip_user",
        description="Update a SIP user: its name and password (both required by the API), codecs, status or presence.",
    )
    def update_sip_user(
        endpoint_id: int,
        name: str,
        password: str,
        codec_list: str | None = None,
        status: bool | None = None,
        presence: bool | None = None,
    ) -> Any:
        body = {"name": name, "password": password, "codec_list": codec_list, "status": status, "presence": presence}
        return api(client_factory, "PUT", sip_user_path(), json=body, endpoint_id=endpoint_id)

    @mcp.tool(name="siprtc.delete_sip_user", description="Delete a SIP user. Devices registered with it stop working.")
    def delete_sip_user(endpoint_id: int) -> Any:
        return api(client_factory, "DELETE", sip_user_path(), endpoint_id=endpoint_id)

    @mcp.tool(
        name="siprtc.associate_sip_user_application",
        description="Attach an application to a SIP user (it handles the user's outbound calls), or detach it with associate=false.",
    )
    def associate_sip_user_application(endpoint_id: int, application_id: int, associate: bool = True) -> Any:
        return api(
            client_factory,
            "PATCH",
            sip_user_path(),
            json=_association(associate, application_id),
            endpoint_id=endpoint_id,
        )

    # --- SIP domains ------------------------------------------------------------------------
    @mcp.tool(name="siprtc.list_sip_domains", description="List SIP domains (where PBXs and SIP trunks send calls in).")
    def list_sip_domains(name: str | None = None, page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", DOMAINS, params={"name": name, "page": page, "limit": limit})

    @mcp.tool(name="siprtc.get_sip_domain", description="Fetch one SIP domain by numeric id.")
    def get_sip_domain(domain_id: int) -> Any:
        return api(client_factory, "GET", DOMAIN, domain_id=domain_id)

    @mcp.tool(
        name="siprtc.create_sip_domain",
        description=(
            "Create a SIP domain <domain_prefix>.sip.<platform>. ip_auth e.g. "
            '{"whitelisted_ips": ["203.0.113.10/32"]}; user_auth e.g. {"enabled": false}.'
        ),
    )
    def create_sip_domain(
        domain_prefix: str,
        ip_auth: dict,
        user_auth: dict,
        name: str | None = None,
        application_id: int | None = None,
        status: bool | None = None,
    ) -> Any:
        body = {
            "domain_prefix": domain_prefix,
            "ip_auth": ip_auth,
            "user_auth": user_auth,
            "name": name,
            "application_id": application_id,
            "status": status,
        }
        return api(client_factory, "POST", DOMAINS, json=body)

    @mcp.tool(name="siprtc.update_sip_domain", description="Update a SIP domain's name, IP or user auth, or status.")
    def update_sip_domain(
        domain_id: int,
        name: str | None = None,
        ip_auth: dict | None = None,
        user_auth: dict | None = None,
        status: bool | None = None,
    ) -> Any:
        body = {"name": name, "ip_auth": ip_auth, "user_auth": user_auth, "status": status}
        return api(client_factory, "PUT", DOMAIN, json=body, domain_id=domain_id)

    @mcp.tool(
        name="siprtc.associate_sip_domain_application",
        description="Attach an application to a SIP domain (it handles calls arriving there), or detach it with associate=false.",
    )
    def associate_sip_domain_application(domain_id: int, application_id: int, associate: bool = True) -> Any:
        return api(client_factory, "PATCH", DOMAIN, json=_association(associate, application_id), domain_id=domain_id)

    @mcp.tool(
        name="siprtc.delete_sip_domain", description="Delete a SIP domain. Calls sent to it are refused afterwards."
    )
    def delete_sip_domain(domain_id: int) -> Any:
        return api(client_factory, "DELETE", DOMAIN, domain_id=domain_id)
