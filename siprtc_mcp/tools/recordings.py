"""Recordings, transcripts and the privacy controls around them (settings, keys, legal holds, audit)."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api

RECORDINGS = ACCOUNT + "/Recordings"
RECORDING = RECORDINGS + "/{recording_sid}"
SETTINGS = ACCOUNT + "/RecordingSettings/Default"
TRANSCRIPTS = ACCOUNT + "/Transcripts"
TRANSCRIPT = TRANSCRIPTS + "/{transcript_sid}"
PUBLIC_KEYS = ACCOUNT + "/Credentials/PublicKeys"
PUBLIC_KEY = PUBLIC_KEYS + "/{key_sid}"
LEGAL_HOLDS = ACCOUNT + "/LegalHolds"
LEGAL_HOLD = LEGAL_HOLDS + "/{hold_sid}"
AUDIT_EVENTS = ACCOUNT + "/AuditEvents"


def _flag(value: bool | None) -> str | None:
    return None if value is None else ("true" if value else "false")


def register(mcp, client_factory):
    # --- recordings -------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_recordings",
        description=(
            "List call recordings, optionally for one call or conference. date_created filters by "
            "day (yyyy-mm-dd); date_created_before/after bound it. Paged with page (from 0) and page_size."
        ),
    )
    def list_recordings(
        call_sid: str | None = None,
        conference_sid: str | None = None,
        status: str | None = None,
        date_created: str | None = None,
        date_created_before: str | None = None,
        date_created_after: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {
            "CallSid": call_sid,
            "ConferenceSid": conference_sid,
            "Status": status,
            "DateCreated": date_created,
            "DateCreated<": date_created_before,
            "DateCreated>": date_created_after,
            "Page": page,
            "PageSize": page_size,
        }
        return api(client_factory, "GET", RECORDINGS, params=params)

    @mcp.tool(
        name="siprtc.get_recording",
        description=(
            "Fetch a recording's metadata. With include_media_url=true the response also carries a "
            "short-lived (15 min) download link in redirect_to; that access is audited and needs playback rights."
        ),
    )
    def get_recording(recording_sid: str, include_media_url: bool = False) -> Any:
        template = RECORDING + (".json" if include_media_url else "")
        return api(client_factory, "GET", template, recording_sid=recording_sid)

    @mcp.tool(
        name="siprtc.delete_recording",
        description="Permanently delete a recording's audio (a tombstone record stays). Refused while under a legal hold.",
    )
    def delete_recording(recording_sid: str) -> Any:
        return api(client_factory, "DELETE", RECORDING, recording_sid=recording_sid)

    # --- recording settings -----------------------------------------------------------------
    @mcp.tool(
        name="siprtc.get_recording_settings",
        description="Show the account's recording, transcript-storage, encryption, retention and playback-access settings.",
    )
    def get_recording_settings() -> Any:
        return api(client_factory, "GET", SETTINGS)

    @mcp.tool(
        name="siprtc.update_recording_settings",
        description=(
            "Change recording settings. Only the fields you pass change. retention_* are days "
            "(0 = keep forever); playback_roles is a comma list of tenant, admin, supervisor, agent, member, qa_agent."
        ),
    )
    def update_recording_settings(
        voice_mode: Literal["app_controlled", "always", "on_demand", "never"] | None = None,
        voice_channels: Literal["mono", "dual"] | None = None,
        voice_voicemail: bool | None = None,
        chat_storage: str | None = None,
        encryption_enabled: bool | None = None,
        encryption_type: Literal["none", "platform", "customer_key"] | None = None,
        encryption_key_sid: str | None = None,
        retention_recordings_days: int | None = None,
        retention_voicemail_days: int | None = None,
        retention_transcripts_days: int | None = None,
        retention_chat_messages_days: int | None = None,
        playback_roles: str | None = None,
        friendly_name: str | None = None,
    ) -> Any:
        form = {
            "FriendlyName": friendly_name,
            "Voice.Mode": voice_mode,
            "Voice.Channels": voice_channels,
            "Voice.Voicemail": _flag(voice_voicemail),
            "Chat.Storage": chat_storage,
            "EncryptionEnabled": _flag(encryption_enabled),
            "EncryptionType": encryption_type,
            "EncryptionKeySid": encryption_key_sid,
            "Retention.RecordingsDays": retention_recordings_days,
            "Retention.VoicemailDays": retention_voicemail_days,
            "Retention.TranscriptsDays": retention_transcripts_days,
            "Retention.ChatMessagesDays": retention_chat_messages_days,
            "Access.PlaybackRoles": playback_roles,
        }
        if all(value is None for value in form.values()):
            raise ToolError("Pass at least one setting to change.")
        return api(client_factory, "POST", SETTINGS, data=form)

    # --- transcripts ------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_transcripts",
        description="List stored conversation transcripts (voice, webchat, whatsapp, ...).",
    )
    def list_transcripts(
        conversation_sid: str | None = None,
        channel: str | None = None,
        date_created_after: str | None = None,
        date_created_before: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {
            "ConversationSid": conversation_sid,
            "Channel": channel,
            "DateCreated>": date_created_after,
            "DateCreated<": date_created_before,
            "Page": page,
            "PageSize": page_size,
        }
        return api(client_factory, "GET", TRANSCRIPTS, params=params)

    @mcp.tool(
        name="siprtc.get_transcript",
        description="Fetch a transcript's metadata, or with include_content=true its text (needs playback rights; audited).",
    )
    def get_transcript(transcript_sid: str, include_content: bool = False) -> Any:
        template = TRANSCRIPT + (".json" if include_content else "")
        return api(client_factory, "GET", template, transcript_sid=transcript_sid)

    @mcp.tool(
        name="siprtc.delete_transcript",
        description="Permanently delete a transcript. Refused while under a legal hold.",
    )
    def delete_transcript(transcript_sid: str) -> Any:
        return api(client_factory, "DELETE", TRANSCRIPT, transcript_sid=transcript_sid)

    # --- encryption public keys -------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_public_keys",
        description="List the RSA public keys registered for customer-key recording encryption.",
    )
    def list_public_keys() -> Any:
        return api(client_factory, "GET", PUBLIC_KEYS)

    @mcp.tool(
        name="siprtc.create_public_key",
        description="Register an RSA public key (PEM 'PUBLIC KEY', 2048-4096 bit) for customer-key recording encryption.",
    )
    def create_public_key(public_key: str, friendly_name: str | None = None) -> Any:
        return api(client_factory, "POST", PUBLIC_KEYS, data={"PublicKey": public_key, "FriendlyName": friendly_name})

    @mcp.tool(name="siprtc.get_public_key", description="Fetch one registered public key by SID (CR...).")
    def get_public_key(key_sid: str) -> Any:
        return api(client_factory, "GET", PUBLIC_KEY, key_sid=key_sid)

    @mcp.tool(
        name="siprtc.update_public_key", description="Rename a registered public key (the key itself cannot change)."
    )
    def update_public_key(key_sid: str, friendly_name: str) -> Any:
        return api(client_factory, "POST", PUBLIC_KEY, data={"FriendlyName": friendly_name}, key_sid=key_sid)

    @mcp.tool(
        name="siprtc.delete_public_key",
        description="Delete a registered public key. Refused while it is the active encryption key.",
    )
    def delete_public_key(key_sid: str) -> Any:
        return api(client_factory, "DELETE", PUBLIC_KEY, key_sid=key_sid)

    # --- legal holds ------------------------------------------------------------------------
    @mcp.tool(name="siprtc.list_legal_holds", description="List legal holds, optionally only active or released ones.")
    def list_legal_holds(status: Literal["active", "released"] | None = None) -> Any:
        return api(client_factory, "GET", LEGAL_HOLDS, params={"Status": status})

    @mcp.tool(
        name="siprtc.create_legal_hold",
        description=(
            "Put recordings/transcripts on legal hold so retention and deletes skip them. Scope fields are "
            "ANDed; pass all_records=true to hold everything. Holds are released, never deleted."
        ),
    )
    def create_legal_hold(
        reason: str,
        matter_id: str | None = None,
        recording_sid: str | None = None,
        call_sid: str | None = None,
        conversation_sid: str | None = None,
        phone_number: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        all_records: bool | None = None,
    ) -> Any:
        form = {
            "Reason": reason,
            "MatterId": matter_id,
            "RecordingSid": recording_sid,
            "CallSid": call_sid,
            "ConversationSid": conversation_sid,
            "PhoneNumber": phone_number,
            "DateFrom": date_from,
            "DateTo": date_to,
            "All": _flag(all_records),
        }
        return api(client_factory, "POST", LEGAL_HOLDS, data=form)

    @mcp.tool(name="siprtc.get_legal_hold", description="Fetch one legal hold by SID (LH...).")
    def get_legal_hold(hold_sid: str) -> Any:
        return api(client_factory, "GET", LEGAL_HOLD, hold_sid=hold_sid)

    @mcp.tool(
        name="siprtc.release_legal_hold",
        description="Release a legal hold (its scope cannot change). Optionally record why.",
    )
    def release_legal_hold(hold_sid: str, reason: str | None = None) -> Any:
        return api(client_factory, "POST", LEGAL_HOLD, data={"Status": "released", "Reason": reason}, hold_sid=hold_sid)

    # --- audit ------------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_audit_events",
        description="List privacy audit events (e.g. recording.accessed, recording.deleted), filterable by resource, type, actor and date.",
    )
    def list_audit_events(
        resource_sid: str | None = None,
        event_type: str | None = None,
        actor_sid: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {
            "ResourceSid": resource_sid,
            "EventType": event_type,
            "ActorSid": actor_sid,
            "StartDate": start_date,
            "EndDate": end_date,
            "Page": page,
            "PageSize": page_size,
        }
        return api(client_factory, "GET", AUDIT_EVENTS, params=params)
