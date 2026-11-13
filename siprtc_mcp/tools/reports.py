"""Contact-centre reports: run one inline, or export it as a CSV job and fetch the download link."""

from __future__ import annotations

from typing import Any, Literal

from ._common import ACCOUNT, api

REPORTS = ACCOUNT + "/Reports"

InlineReport = Literal[
    "AgentPerformance",
    "AgentProductivity",
    "AgentOverview",
    "AgentActivity",
    "SkillProductivity",
    "AbandonedInteraction",
    "CampaignProductivity",
    "InteractionHistory",
    "Disposition",
    "DispositionLog",
    "DispositionSummary",
    "SLA",
    "VoicemailSla",
    "BreakReport",
    "Adherence",
    "ActivityLogs",
    "AgentPerformanceSummary",
    "AgentProductivitySummary",
    "QueuePerformanceSummary",
    "CampaignProductivitySummary",
    "ConversationLogSummary",
    "InteractionHistorySummary",
    "AIInteractionSummary",
    "LiveWallboardSummary",
    "QASummary",
    "Dashboard",
]
ExportReport = Literal[
    "AgentPerformance",
    "AgentProductivity",
    "AbandonedInteraction",
    "CampaignProductivity",
    "InteractionHistory",
    "Disposition",
    "SLA",
    "CDR",
    "Interactions",
    "QA",
    "Ticket",
    "ConversationLog",
    "CampaignContact",
]


def _params(from_date, to_date, workspace_sid, filters) -> dict:
    params = dict(filters or {})
    params.update({"fromDate": from_date, "toDate": to_date, "workspaceSid": workspace_sid})
    return params


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.run_report",
        description=(
            "Run a contact-centre report and return its rows. Dates are yyyy-mm-dd or ISO 8601; most "
            "reports need workspace_sid. filters takes extra query fields such as workerSid, "
            "taskQueueSid, taskChannelSid, campaignId, direction, page, limit."
        ),
    )
    def run_report(
        report: InlineReport,
        from_date: str,
        to_date: str,
        workspace_sid: str | None = None,
        filters: dict | None = None,
    ) -> Any:
        return api(
            client_factory, "GET", REPORTS + "/" + report, params=_params(from_date, to_date, workspace_sid, filters)
        )

    @mcp.tool(
        name="siprtc.export_report",
        description="Start a CSV export of a report. Returns a report id; fetch the download link with siprtc.get_report_export.",
    )
    def export_report(
        report: ExportReport,
        from_date: str,
        to_date: str,
        workspace_sid: str | None = None,
        filters: dict | None = None,
    ) -> Any:
        return api(
            client_factory, "POST", REPORTS + "/" + report, json=_params(from_date, to_date, workspace_sid, filters)
        )

    @mcp.tool(name="siprtc.list_report_exports", description="List generated report exports.")
    def list_report_exports(
        from_date: str | None = None, to_date: str | None = None, page: int | None = None, limit: int | None = None
    ) -> Any:
        params = {"fromDate": from_date, "toDate": to_date, "page": page, "limit": limit}
        return api(client_factory, "GET", REPORTS, params=params)

    @mcp.tool(
        name="siprtc.get_report_export",
        description="Get a finished report export's download link (a short-lived signed URL).",
    )
    def get_report_export(report_id: str) -> Any:
        return api(client_factory, "GET", REPORTS + "/{report_id}", report_id=report_id)

    @mcp.tool(name="siprtc.delete_report_export", description="Delete a generated report export.")
    def delete_report_export(report_id: str) -> Any:
        return api(client_factory, "DELETE", REPORTS + "/{report_id}", report_id=report_id)
