"""Applications: the voice/SMS/fax webhook configuration a number, SIP user or domain points at."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ..config import application_path, applications_path
from ._common import api

Method = Literal["GET", "POST"]


def _fields(
    friendly_name: str | None,
    voice_url: str | None,
    voice_method: Method | None,
    voice_fallback_url: str | None,
    status_callback: str | None,
    sms_url: str | None,
    sms_method: Method | None,
    sms_fallback_url: str | None,
    sms_status_callback: str | None,
    extra: dict | None,
) -> dict:
    body = dict(extra or {})
    body.update(
        {
            key: value
            for key, value in {
                "FriendlyName": friendly_name,
                "VoiceUrl": voice_url,
                "VoiceMethod": voice_method,
                "VoiceFallbackUrl": voice_fallback_url,
                "StatusCallback": status_callback,
                "SmsUrl": sms_url,
                "SmsMethod": sms_method,
                "SmsFallbackUrl": sms_fallback_url,
                "SmsStatusCallback": sms_status_callback,
            }.items()
            if value is not None
        }
    )
    return body


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_applications",
        description="List applications, optionally filtered by friendly name or status.",
    )
    def list_applications(
        friendly_name: str | None = None,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {"friendly_name": friendly_name, "status": status, "page": page, "limit": limit}
        return api(client_factory, "GET", applications_path(), params=params)

    @mcp.tool(name="siprtc.get_application", description="Fetch one application by SID.")
    def get_application(application_id: str) -> Any:
        return api(client_factory, "GET", application_path(), application_sid=application_id)

    @mcp.tool(
        name="siprtc.create_application",
        description=(
            "Create an application: the webhooks SIPRTC calls for inbound voice (voice_url returns "
            "TinyML) and messages (sms_url). extra takes any other API field, e.g. VoiceStatusEvent or Fax* fields."
        ),
    )
    def create_application(
        friendly_name: str,
        voice_url: str | None = None,
        voice_method: Method | None = None,
        voice_fallback_url: str | None = None,
        status_callback: str | None = None,
        sms_url: str | None = None,
        sms_method: Method | None = None,
        sms_fallback_url: str | None = None,
        sms_status_callback: str | None = None,
        extra: dict | None = None,
    ) -> Any:
        body = _fields(
            friendly_name,
            voice_url,
            voice_method,
            voice_fallback_url,
            status_callback,
            sms_url,
            sms_method,
            sms_fallback_url,
            sms_status_callback,
            extra,
        )
        return api(client_factory, "POST", applications_path(), json=body)

    @mcp.tool(
        name="siprtc.update_application",
        description=(
            "Update an application. Only the fields you pass change: the current values are read "
            "first, because the API replaces the whole application."
        ),
    )
    def update_application(
        application_id: str,
        friendly_name: str | None = None,
        status: Literal["active", "inactive"] | None = None,
        voice_url: str | None = None,
        voice_method: Method | None = None,
        voice_fallback_url: str | None = None,
        status_callback: str | None = None,
        sms_url: str | None = None,
        sms_method: Method | None = None,
        sms_fallback_url: str | None = None,
        sms_status_callback: str | None = None,
        extra: dict | None = None,
    ) -> Any:
        changes = _fields(
            friendly_name,
            voice_url,
            voice_method,
            voice_fallback_url,
            status_callback,
            sms_url,
            sms_method,
            sms_fallback_url,
            sms_status_callback,
            extra,
        )
        if status is not None:
            changes["Status"] = status
        if not changes:
            raise ToolError("Pass at least one field to change.")
        current = api(client_factory, "GET", application_path(), application_sid=application_id)
        body = _current_fields(current if isinstance(current, dict) else {})
        body.update(changes)
        return api(client_factory, "PUT", application_path(), json=body, application_sid=application_id)

    @mcp.tool(
        name="siprtc.delete_application",
        description="Delete an application. Numbers and SIP users pointing at it lose their webhooks.",
    )
    def delete_application(application_id: str) -> Any:
        return api(client_factory, "DELETE", application_path(), application_sid=application_id)


# GET returns snake_case; PUT expects PascalCase.
_GET_TO_PUT = {
    "friendly_name": "FriendlyName",
    "status": "Status",
    "voice_url": "VoiceUrl",
    "voice_url_method": "VoiceMethod",
    "voice_fallback_url": "VoiceFallbackUrl",
    "voice_fallback_url_method": "VoiceFallbackMethod",
    "voice_status_url": "StatusCallback",
    "voice_status_url_method": "StatusCallbackMethod",
    "voice_status_event": "VoiceStatusEvent",
    "sms_url": "SmsUrl",
    "sms_url_method": "SmsMethod",
    "sms_fallback_url": "SmsFallbackUrl",
    "sms_fallback_url_method": "SmsFallbackMethod",
    "sms_status_url": "SmsStatusCallback",
    "sms_status_url_method": "SmsStatusCallbackMethod",
    "fax_fallback_url": "FaxFallbackUrl",
    "fax_fallback_url_method": "FaxFallbackMethod",
    "fax_status_url": "FaxStatusCallback",
    "fax_status_url_method": "FaxStatusCallbackMethod",
    "scope": "Scope",
}


def _current_fields(current: dict) -> dict:
    return {put: current[get] for get, put in _GET_TO_PUT.items() if current.get(get) not in (None, "")}
