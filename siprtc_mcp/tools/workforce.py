"""Workforce management: shift templates, assigning agents to them, and the generated schedule."""

from __future__ import annotations

from typing import Any, Literal

from ._common import ACCOUNT, api

WFM = ACCOUNT + "/WorkForce"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_shift_templates", description="List shift templates (named working hours on given weekdays)."
    )
    def list_shift_templates(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", WFM + "/ShiftTemplates", params={"page": page, "limit": limit})

    @mcp.tool(
        name="siprtc.create_shift_template",
        description=(
            "Create a shift template. tz: IANA time zone; start_time/end_time HH:MM; days_of_week: "
            "0=Sunday ... 6=Saturday; break_mins: unpaid break length."
        ),
    )
    def create_shift_template(
        name: str,
        tz: str,
        start_time: str,
        end_time: str,
        days_of_week: list[int],
        break_mins: int | None = None,
        status: Literal["active", "inactive"] = "active",
    ) -> Any:
        body = {
            "name": name,
            "tz": tz,
            "startTime": start_time,
            "endTime": end_time,
            "daysOfWeek": days_of_week,
            "breakMins": break_mins,
            "status": status,
        }
        return api(client_factory, "POST", WFM + "/ShiftTemplates", json=body)

    @mcp.tool(name="siprtc.delete_shift_template", description="Delete a shift template.")
    def delete_shift_template(template_id: str) -> Any:
        return api(client_factory, "DELETE", WFM + "/ShiftTemplates/{template_id}", template_id=template_id)

    @mcp.tool(
        name="siprtc.list_shift_assignments", description="List which agents are assigned to which shift templates."
    )
    def list_shift_assignments(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", WFM + "/ShiftAssignments", params={"page": page, "limit": limit})

    @mcp.tool(
        name="siprtc.create_shift_assignment",
        description="Assign agents (Auth IDs) to a shift template from start_date (YYYY-MM-DD), optionally until end_date.",
    )
    def create_shift_assignment(
        agent_ids: list[str],
        shift_template_id: str,
        start_date: str,
        end_date: str | None = None,
        status: Literal["active", "inactive"] = "active",
    ) -> Any:
        body = {
            "agentId": agent_ids,
            "shiftTemplateId": shift_template_id,
            "startDate": start_date,
            "endDate": end_date,
            "status": status,
        }
        return api(client_factory, "POST", WFM + "/ShiftAssignments", json=body)

    @mcp.tool(name="siprtc.delete_shift_assignment", description="Remove a shift assignment.")
    def delete_shift_assignment(assignment_id: str) -> Any:
        return api(client_factory, "DELETE", WFM + "/ShiftAssignments/{assignment_id}", assignment_id=assignment_id)

    @mcp.tool(
        name="siprtc.list_scheduled_shifts",
        description="List concrete scheduled shifts, filterable by agent, template, status and date range (YYYY-MM-DD).",
    )
    def list_scheduled_shifts(
        agent_id: str | None = None,
        template_id: str | None = None,
        status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {
            "agentId": agent_id,
            "templateId": template_id,
            "status": status,
            "startDate": start_date,
            "endDate": end_date,
            "page": page,
            "limit": limit,
        }
        return api(client_factory, "GET", WFM + "/ScheduledShifts", params=params)
