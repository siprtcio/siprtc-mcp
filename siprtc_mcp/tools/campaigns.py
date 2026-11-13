"""Outbound campaigns (progressive/predictive/power dialing and broadcast messaging), their contact
lists (groups), contacts and message templates."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api, merge

CAMPAIGNS = ACCOUNT + "/Campaign"
CAMPAIGN = CAMPAIGNS + "/{campaign_id}"
CONTACTS = CAMPAIGNS + "/Contact"
GROUPS = CAMPAIGNS + "/Group"
TEMPLATES = CAMPAIGNS + "/Template"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_campaigns",
        description="List campaigns, filterable by name, status, channel or dial type.",
    )
    def list_campaigns(
        name: str | None = None,
        status: str | None = None,
        channel: str | None = None,
        dial_type: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {
            "name": name,
            "status": status,
            "channel": channel,
            "dial_type": dial_type,
            "page": page,
            "limit": limit,
        }
        return api(client_factory, "GET", CAMPAIGNS, params=params)

    @mcp.tool(
        name="siprtc.create_campaign",
        description=(
            "Create a campaign as a draft. group: contact-list ids to reach; channel_id: the number/"
            "channel it uses; queue_id: the task queue whose agents handle it; start_date/end_date "
            "ISO 8601. extra takes other fields (caller_id, concurrency, workspace_sid, template_id, "
            "voice_* for broadcast, time_zone, ...). Start it with siprtc.set_campaign_status."
        ),
    )
    def create_campaign(
        name: str,
        group: list[int],
        channel_id: str,
        queue_id: str,
        dial_type: Literal["progressive", "predictive", "power", "broadcast"],
        start_date: str,
        end_date: str,
        channel: str | None = None,
        caller_id: str | None = None,
        concurrency: int | None = None,
        workspace_sid: str | None = None,
        extra: dict | None = None,
    ) -> Any:
        body = merge(
            {
                "name": name,
                "group": group,
                "channel_id": channel_id,
                "queue_id": queue_id,
                "dial_type": dial_type,
                "start_date": start_date,
                "end_date": end_date,
                "channel": channel,
                "caller_id": caller_id,
                "concurrency": concurrency,
                "workspace_sid": workspace_sid,
            },
            extra,
        )
        return api(client_factory, "POST", CAMPAIGNS, json=body)

    @mcp.tool(
        name="siprtc.update_campaign",
        description="Change a campaign's settings. fields takes any create_campaign field; only those change.",
    )
    def update_campaign(campaign_id: int, fields: dict) -> Any:
        if not fields:
            raise ToolError("Pass at least one field to change.")
        return api(client_factory, "PUT", CAMPAIGN, json=fields, campaign_id=campaign_id)

    @mcp.tool(
        name="siprtc.set_campaign_status",
        description=(
            "Start (running), pause, resume (running), finish or cancel a campaign. Running starts "
            "dialing or sending at once. Allowed: draft->running/cancelled, running->paused/cancelled/"
            "finished, paused->running/cancelled."
        ),
    )
    def set_campaign_status(campaign_id: int, status: Literal["running", "paused", "cancelled", "finished"]) -> Any:
        return api(client_factory, "PUT", CAMPAIGN + "/Status", json={"status": status}, campaign_id=campaign_id)

    @mcp.tool(name="siprtc.delete_campaign", description="Delete a campaign.")
    def delete_campaign(campaign_id: int) -> Any:
        return api(client_factory, "DELETE", CAMPAIGN, campaign_id=campaign_id)

    @mcp.tool(
        name="siprtc.list_campaign_progress",
        description="Per-contact progress of one campaign (who was reached, pending or failed).",
    )
    def list_campaign_progress(
        campaign_id: int, status: str | None = None, page: int | None = None, limit: int | None = None
    ) -> Any:
        params = {"status": status, "page": page, "limit": limit}
        return api(client_factory, "GET", CAMPAIGN + "/Contact", params=params, campaign_id=campaign_id)

    # --- contact lists (groups) -------------------------------------------------------------
    @mcp.tool(name="siprtc.list_contact_groups", description="List campaign contact lists (groups).")
    def list_contact_groups(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", GROUPS, params={"page": page, "limit": limit})

    @mcp.tool(name="siprtc.create_contact_group", description="Create a campaign contact list (group).")
    def create_contact_group(name: str, description: str | None = None) -> Any:
        return api(client_factory, "POST", GROUPS, json={"name": name, "description": description})

    @mcp.tool(name="siprtc.delete_contact_group", description="Delete a campaign contact list (group).")
    def delete_contact_group(group_id: int) -> Any:
        return api(client_factory, "DELETE", GROUPS + "/{group_id}", group_id=group_id)

    # --- contacts ---------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_contacts",
        description="List campaign contacts, filterable by name, email, number or contact list (group_id).",
    )
    def list_contacts(
        name: str | None = None,
        email: str | None = None,
        number: str | None = None,
        group_id: int | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {"name": name, "email": email, "number": number, "groupId": group_id, "page": page, "limit": limit}
        return api(client_factory, "GET", CONTACTS, params=params)

    @mcp.tool(
        name="siprtc.create_contact",
        description="Add a campaign contact and put it in contact lists (group ids). is_dnc marks do-not-contact.",
    )
    def create_contact(
        number: str,
        group: list[int],
        firstname: str | None = None,
        lastname: str | None = None,
        email: str | None = None,
        company: str | None = None,
        is_dnc: bool | None = None,
        metadata: dict | None = None,
    ) -> Any:
        body = {
            "number": number,
            "group": group,
            "firstname": firstname,
            "lastname": lastname,
            "email": email,
            "company": company,
            "isDnc": is_dnc,
            "metadata": metadata,
        }
        return api(client_factory, "POST", CONTACTS, json=body)

    @mcp.tool(
        name="siprtc.update_contact",
        description=(
            "Change a campaign contact. The API replaces the contact, so pass its number or email "
            "(or both) every time; fields takes any other create_contact field."
        ),
    )
    def update_contact(
        contact_id: int, number: str | None = None, email: str | None = None, fields: dict | None = None
    ) -> Any:
        if not number and not email:
            raise ToolError("Pass the contact's number or email (the API needs one on every update).")
        body = merge({"number": number, "email": email}, fields)
        return api(client_factory, "PUT", CONTACTS + "/{contact_id}", json=body, contact_id=contact_id)

    @mcp.tool(name="siprtc.delete_contact", description="Delete a campaign contact.")
    def delete_contact(contact_id: int) -> Any:
        return api(client_factory, "DELETE", CONTACTS + "/{contact_id}", contact_id=contact_id)

    # --- templates --------------------------------------------------------------------------
    @mcp.tool(name="siprtc.list_campaign_templates", description="List message templates used by messaging campaigns.")
    def list_campaign_templates(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", TEMPLATES, params={"page": page, "limit": limit})

    @mcp.tool(
        name="siprtc.create_campaign_template",
        description="Create a campaign message template. type: sms, whatsapp or email (email also takes a subject).",
    )
    def create_campaign_template(type: str, name: str, body: str, subject: str | None = None) -> Any:
        return api(
            client_factory, "POST", TEMPLATES, json={"type": type, "name": name, "body": body, "subject": subject}
        )

    @mcp.tool(name="siprtc.delete_campaign_template", description="Delete a campaign message template.")
    def delete_campaign_template(template_id: int) -> Any:
        return api(client_factory, "DELETE", TEMPLATES + "/{template_id}", template_id=template_id)
