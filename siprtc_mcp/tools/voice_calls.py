from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ..models import CallRequest
from ._common import ACCOUNT, api

CALLS = ACCOUNT + "/Calls"
CALL = CALLS + "/{call_sid}"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.make_call",
        description=(
            "Place an outbound voice call (billed). Needs To, From (a number you own or have "
            "verified) and one of Url, TinyML, play or speak. Returns the call resource with its sid."
        ),
    )
    def make_call(call: CallRequest) -> Any:
        return api(client_factory, "POST", CALLS, json=call.model_dump(by_alias=True, exclude_none=True))

    @mcp.tool(
        name="siprtc.list_calls",
        description=(
            "List call detail records (CDRs). Dates are yyyy-mm-dd; without them the API returns "
            "roughly today and yesterday. Paged with page (from 1) and limit (max 100)."
        ),
    )
    def list_calls(
        from_date: str | None = None,
        to_date: str | None = None,
        status: str | None = None,
        direction: str | None = None,
        from_number: str | None = None,
        to_number: str | None = None,
        parent_call_sid: str | None = None,
        min_duration: int | None = None,
        max_duration: int | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {
            "from_date": from_date,
            "to_date": to_date,
            "status": status,
            "direction": direction,
            "from": from_number,
            "to": to_number,
            "ParentCallSid": parent_call_sid,
            "minduration": min_duration,
            "maxduration": max_duration,
            "page": page,
            "limit": limit,
        }
        return api(client_factory, "GET", CALLS, params=params)

    @mcp.tool(
        name="siprtc.get_call",
        description="Fetch one call detail record (CDR) by call SID.",
    )
    def get_call(call_id: str) -> Any:
        return api(client_factory, "GET", CALL, call_sid=call_id)

    @mcp.tool(
        name="siprtc.update_call",
        description=(
            "Change a live call: redirect it to new TinyML (url or tinyml), end it with "
            "status='completed', or put it on hold / take it off hold. Only works while the call is live."
        ),
    )
    def update_call(
        call_id: str,
        url: str | None = None,
        method: Literal["GET", "POST"] | None = None,
        tinyml: str | None = None,
        status: Literal["completed", "canceled"] | None = None,
        hold: bool | None = None,
        wait_url: str | None = None,
        fallback_url: str | None = None,
        status_callback: str | None = None,
    ) -> Any:
        body = {
            "Url": url,
            "Method": method,
            "TinyML": tinyml,
            "Status": status,
            "hold": hold,
            "wait_url": wait_url,
            "FallbackUrl": fallback_url,
            "StatusCallback": status_callback,
        }
        if all(value is None for value in body.values()):
            raise ToolError("Pass at least one change: url, tinyml, status, hold or wait_url.")
        return api(client_factory, "POST", CALL, json=body, call_sid=call_id)

    @mcp.tool(
        name="siprtc.hangup_call",
        description=(
            "Hang up a ringing or in-progress call by call SID. Returns the call; on a call that "
            "already ended it returns that call's record unchanged."
        ),
    )
    def hangup_call(call_id: str) -> Any:
        # Twilio semantics: a call is ended by updating it with Status=completed.
        # DELETE /Calls/{sid} is for deleting a finished call's record, not for hanging up.
        return api(client_factory, "POST", CALL, json={"Status": "completed"}, call_sid=call_id)

    @mcp.tool(
        name="siprtc.start_call_recording",
        description="Start recording a live call. Returns the recording resource; keep its sid to pause or stop it.",
    )
    def start_call_recording(
        call_id: str,
        recording_channels: Literal["mono", "dual"] | None = None,
        recording_track: Literal["inbound", "outbound", "both"] | None = None,
        trim: Literal["trim-silence", "do-not-trim"] | None = None,
        recording_status_callback: str | None = None,
        recording_status_callback_method: Literal["GET", "POST"] | None = None,
    ) -> Any:
        body = {
            "RecordingChannels": recording_channels,
            "RecordingTrack": recording_track,
            "Trim": trim,
            "RecordingStatusCallback": recording_status_callback,
            "RecordingStatusCallbackMethod": recording_status_callback_method,
        }
        return api(client_factory, "POST", CALL + "/Recordings", json=body, call_sid=call_id)

    @mcp.tool(
        name="siprtc.update_call_recording",
        description="Pause, resume (status in-progress) or stop a recording on a live call.",
    )
    def update_call_recording(
        call_id: str,
        recording_sid: str,
        status: Literal["paused", "in-progress", "stopped"],
        pause_behavior: Literal["skip", "silence"] | None = None,
    ) -> Any:
        return api(
            client_factory,
            "POST",
            CALL + "/Recordings/{recording_sid}",
            json={"Status": status, "PauseBehavior": pause_behavior},
            call_sid=call_id,
            recording_sid=recording_sid,
        )
