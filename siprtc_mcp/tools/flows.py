"""Flows: hosted low-code call/message flows, each running in its own container."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api

FLOWS = ACCOUNT + "/Flows"
FLOW = FLOWS + "/{flow_id}"


def register(mcp, client_factory):
    @mcp.tool(name="siprtc.list_flows", description="List the account's flows.")
    def list_flows() -> Any:
        return api(client_factory, "GET", FLOWS)

    @mcp.tool(name="siprtc.get_flow", description="Fetch one flow, including its URL.")
    def get_flow(flow_id: str) -> Any:
        return api(client_factory, "GET", FLOW, flow_id=flow_id)

    @mcp.tool(
        name="siprtc.get_flow_status",
        description="Show whether a flow's container is running (status, phase, replicas).",
    )
    def get_flow_status(flow_id: str) -> Any:
        return api(client_factory, "GET", FLOW + "/status", flow_id=flow_id)

    @mcp.tool(
        name="siprtc.create_flow",
        description=(
            "Create a flow; its container starts and the response carries the flow URL and secret. "
            "Accounts have a small flow quota (409 when it is used up)."
        ),
    )
    def create_flow(
        name: str,
        time_zone: str | None = None,
        status_url: str | None = None,
        status_url_method: Literal["GET", "POST"] | None = None,
    ) -> Any:
        body = {"name": name, "time_zone": time_zone, "status_url": status_url, "status_url_method": status_url_method}
        return api(client_factory, "POST", FLOWS, json=body)

    @mcp.tool(
        name="siprtc.update_flow",
        description="Rename a flow, change its time zone or status callback, or attach it to an application.",
    )
    def update_flow(
        flow_id: str,
        name: str | None = None,
        time_zone: str | None = None,
        status_url: str | None = None,
        status_url_method: Literal["GET", "POST"] | None = None,
        application_id: str | None = None,
    ) -> Any:
        body = {
            "name": name,
            "time_zone": time_zone,
            "status_url": status_url,
            "status_url_method": status_url_method,
            "application_id": application_id,
        }
        if all(value is None for value in body.values()):
            raise ToolError("Pass at least one field to change.")
        return api(client_factory, "PUT", FLOW, json=body, flow_id=flow_id)

    @mcp.tool(name="siprtc.restart_flow", description="Start or restart a flow's container.")
    def restart_flow(flow_id: str, action: Literal["start", "restart"] = "restart") -> Any:
        return api(client_factory, "POST", FLOW + "/" + action, flow_id=flow_id)

    @mcp.tool(
        name="siprtc.stop_flow",
        description="Stop a flow's container; calls and messages routed to it fail until it starts again.",
    )
    def stop_flow(flow_id: str) -> Any:
        return api(client_factory, "POST", FLOW + "/stop", flow_id=flow_id)

    @mcp.tool(name="siprtc.delete_flow", description="Delete a flow, its container and its voice application.")
    def delete_flow(flow_id: str) -> Any:
        return api(client_factory, "DELETE", FLOW, flow_id=flow_id)
