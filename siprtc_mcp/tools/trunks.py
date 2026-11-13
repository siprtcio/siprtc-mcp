"""Bring-your-own-carrier trunks: termination (outbound calls leave through your carrier) and
origination (your carrier or PBX sends calls in), plus the outbound rates that apply."""

from __future__ import annotations

from typing import Any, Literal

from ._common import ACCOUNT, api

TERMINATION = ACCOUNT + "/Trunks/Termination"
ORIGINATION = ACCOUNT + "/Trunks/Origination"


def register(mcp, client_factory):
    @mcp.tool(name="siprtc.list_termination_trunks", description="List outbound (termination) carrier trunks.")
    def list_termination_trunks() -> Any:
        return api(client_factory, "GET", TERMINATION)

    @mcp.tool(name="siprtc.get_termination_trunk", description="Fetch one outbound carrier trunk by id.")
    def get_termination_trunk(trunk_id: int) -> Any:
        return api(client_factory, "GET", TERMINATION + "/{trunk_id}", trunk_id=trunk_id)

    def termination_body(
        name,
        primary_ip,
        supported_cc,
        secondary_ip,
        except_cc,
        priority,
        username,
        password,
        trunk_prefix,
        remove_prefix,
        codecs,
    ) -> dict:
        return {
            "name": name,
            "primary_ip": primary_ip,
            "supported_cc": supported_cc,
            "secondary_ip": secondary_ip,
            "except_cc": except_cc,
            "priority": priority,
            "username": username,
            "password": password,
            "trunk_prefix": trunk_prefix,
            "remove_prefix": remove_prefix,
            "codecs": codecs,
        }

    @mcp.tool(
        name="siprtc.create_termination_trunk",
        description=(
            "Add an outbound carrier trunk. primary_ip: carrier SIP host[:port]; supported_cc: ISO "
            "country codes it carries, or ['ALL']; priority 0-100 (lower first); optional digest "
            "username/password and prefix rewriting."
        ),
    )
    def create_termination_trunk(
        name: str,
        primary_ip: str,
        supported_cc: list[str],
        secondary_ip: str | None = None,
        except_cc: list[str] | None = None,
        priority: int | None = None,
        username: str | None = None,
        password: str | None = None,
        trunk_prefix: str | None = None,
        remove_prefix: str | None = None,
        codecs: str | None = None,
    ) -> Any:
        body = termination_body(
            name,
            primary_ip,
            supported_cc,
            secondary_ip,
            except_cc,
            priority,
            username,
            password,
            trunk_prefix,
            remove_prefix,
            codecs,
        )
        return api(client_factory, "POST", TERMINATION, json=body)

    @mcp.tool(
        name="siprtc.update_termination_trunk",
        description="Replace an outbound carrier trunk's settings (name, primary_ip and supported_cc are required).",
    )
    def update_termination_trunk(
        trunk_id: int,
        name: str,
        primary_ip: str,
        supported_cc: list[str],
        secondary_ip: str | None = None,
        except_cc: list[str] | None = None,
        priority: int | None = None,
        username: str | None = None,
        password: str | None = None,
        trunk_prefix: str | None = None,
        remove_prefix: str | None = None,
        codecs: str | None = None,
    ) -> Any:
        body = termination_body(
            name,
            primary_ip,
            supported_cc,
            secondary_ip,
            except_cc,
            priority,
            username,
            password,
            trunk_prefix,
            remove_prefix,
            codecs,
        )
        return api(client_factory, "PUT", TERMINATION + "/{trunk_id}", json=body, trunk_id=trunk_id)

    @mcp.tool(name="siprtc.delete_termination_trunk", description="Delete an outbound carrier trunk.")
    def delete_termination_trunk(trunk_id: int) -> Any:
        return api(client_factory, "DELETE", TERMINATION + "/{trunk_id}", trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.list_origination_trunks",
        description="List inbound (origination) trunks, and the SIP domain carriers send calls to (auth_domain).",
    )
    def list_origination_trunks() -> Any:
        return api(client_factory, "GET", ORIGINATION)

    @mcp.tool(name="siprtc.get_origination_trunk", description="Fetch one inbound trunk by id.")
    def get_origination_trunk(trunk_id: int) -> Any:
        return api(client_factory, "GET", ORIGINATION + "/{trunk_id}", trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.create_origination_trunk",
        description=(
            "Add an inbound trunk: calls are accepted from the listed cidrs (IP or CIDR), or with a "
            "username (letters/digits) and password (8+ chars)."
        ),
    )
    def create_origination_trunk(
        name: str,
        cidrs: list[str] | None = None,
        username: str | None = None,
        password: str | None = None,
        status: Literal["active", "inactive"] | None = None,
    ) -> Any:
        body = {"name": name, "cidrs": cidrs, "username": username, "password": password, "status": status}
        return api(client_factory, "POST", ORIGINATION, json=body)

    @mcp.tool(
        name="siprtc.update_origination_trunk", description="Replace an inbound trunk's settings (name is required)."
    )
    def update_origination_trunk(
        trunk_id: int,
        name: str,
        cidrs: list[str] | None = None,
        username: str | None = None,
        password: str | None = None,
        status: Literal["active", "inactive"] | None = None,
    ) -> Any:
        body = {"name": name, "cidrs": cidrs, "username": username, "password": password, "status": status}
        return api(client_factory, "PUT", ORIGINATION + "/{trunk_id}", json=body, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.delete_origination_trunk", description="Delete an inbound trunk; its carrier's calls are refused."
    )
    def delete_origination_trunk(trunk_id: int) -> Any:
        return api(client_factory, "DELETE", ORIGINATION + "/{trunk_id}", trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.list_rates",
        description="List the outbound voice rates that apply to the account, optionally for one dial prefix.",
    )
    def list_rates(prefix: str | None = None, page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", ACCOUNT + "/Rates", params={"prefix": prefix, "page": page, "limit": limit})
