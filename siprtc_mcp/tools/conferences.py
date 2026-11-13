from __future__ import annotations

from typing import Any, Literal

from ._common import ACCOUNT, api

CONFERENCES = ACCOUNT + "/Conferences"
CONFERENCE = CONFERENCES + "/{conference_sid}"
PARTICIPANTS = CONFERENCE + "/Participants"
PARTICIPANT = PARTICIPANTS + "/{call_sid}"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_conferences",
        description="List conferences, optionally by status (init, in-progress, completed) or friendly name.",
    )
    def list_conferences(
        status: Literal["init", "in-progress", "completed"] | None = None,
        friendly_name: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {"Status": status, "friendlyName": friendly_name, "Page": page, "PageSize": page_size}
        return api(client_factory, "GET", CONFERENCES, params=params)

    @mcp.tool(name="siprtc.get_conference", description="Fetch one conference by SID.")
    def get_conference(conference_sid: str) -> Any:
        return api(client_factory, "GET", CONFERENCE, conference_sid=conference_sid)

    @mcp.tool(
        name="siprtc.update_conference",
        description=(
            "Update a conference. status='complete' ends it and hangs up every participant; "
            "announce_url plays TinyML/audio to everyone in it."
        ),
    )
    def update_conference(
        conference_sid: str,
        status: Literal["complete"] | None = None,
        announce_url: str | None = None,
        announce_method: Literal["GET", "POST"] | None = None,
    ) -> Any:
        body = {"status": status, "announce_url": announce_url, "announce_method": announce_method}
        return api(client_factory, "POST", CONFERENCE, json=body, conference_sid=conference_sid)

    @mcp.tool(name="siprtc.list_conference_participants", description="List the participants of a conference.")
    def list_conference_participants(
        conference_sid: str,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {"Page": page, "PageSize": page_size}
        return api(client_factory, "GET", PARTICIPANTS, params=params, conference_sid=conference_sid)

    @mcp.tool(name="siprtc.get_conference_participant", description="Fetch one conference participant by call SID.")
    def get_conference_participant(conference_sid: str, call_sid: str) -> Any:
        return api(client_factory, "GET", PARTICIPANT, conference_sid=conference_sid, call_sid=call_sid)

    @mcp.tool(
        name="siprtc.update_conference_participant",
        description="Mute/unmute, hold/unhold a participant, or play an announcement to them.",
    )
    def update_conference_participant(
        conference_sid: str,
        call_sid: str,
        muted: bool | None = None,
        hold: bool | None = None,
        hold_url: str | None = None,
        announce_url: str | None = None,
    ) -> Any:
        body = {"muted": muted, "hold": hold, "hold_url": hold_url, "announce_url": announce_url}
        return api(client_factory, "POST", PARTICIPANT, json=body, conference_sid=conference_sid, call_sid=call_sid)

    @mcp.tool(
        name="siprtc.remove_conference_participant",
        description="Remove a participant from a conference, hanging up their leg.",
    )
    def remove_conference_participant(conference_sid: str, call_sid: str) -> Any:
        return api(client_factory, "DELETE", PARTICIPANT, conference_sid=conference_sid, call_sid=call_sid)
