from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError
from pydantic import BaseModel, Field

from ..models import MessageRequest
from ._common import ACCOUNT, api

MESSAGES = ACCOUNT + "/Messages"
CONVERSATIONS = ACCOUNT + "/Conversation"


class Attachment(BaseModel):
    file_url: str = Field(alias="fileUrl", description="Public URL of the file.")
    mime_type: str = Field(alias="mimeType", description="MIME type, e.g. image/png or application/pdf.")
    file_name: str | None = Field(default=None, alias="fileName", description="File name shown to the recipient.")
    text: str | None = Field(default=None, description="Caption.")


def _empty_list(result: Any, key: str) -> Any:
    # The conversation API answers 204 with no body when nothing matches.
    if isinstance(result, dict) and result.get("http_status") == 204:
        return {key: [], "pagination": None}
    return result


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.send_sms",
        description=(
            "Send an outbound SMS (billed). From must be a number on the account or a registered "
            "sender ID. Returns the message resource with its sid and status (queued)."
        ),
    )
    def send_sms(sms: MessageRequest) -> Any:
        body = sms.model_dump(by_alias=True, exclude_none=True)
        body["channel"] = "sms"
        return api(client_factory, "POST", MESSAGES, json=body)

    @mcp.tool(
        name="siprtc.send_message",
        description=(
            "Send an outbound message on sms, whatsapp, facebook or viber (billed). WhatsApp needs a "
            "connected WhatsApp channel and an open 24-hour window (no templates). Attachments are "
            "refused on sms."
        ),
    )
    def send_message(
        to: str,
        channel: Literal["sms", "whatsapp", "facebook", "viber"],
        body: str | None = None,
        from_number: str | None = None,
        attachments: list[Attachment] | None = None,
        status_callback: str | None = None,
        status_callback_method: Literal["GET", "POST"] | None = None,
    ) -> Any:
        if not body and not attachments:
            raise ToolError("Pass a body, attachments, or both.")
        payload = {
            "to": to,
            "from": from_number,
            "channel": channel,
            "body": body,
            "statusCallback": status_callback,
            "statusCallbackMethod": status_callback_method,
        }
        if attachments:
            payload["hasAttachment"] = True
            payload["mediaFileContents"] = [a.model_dump(by_alias=True, exclude_none=True) for a in attachments]
        return api(client_factory, "POST", MESSAGES, json=payload)

    @mcp.tool(
        name="siprtc.list_messages",
        description="List message detail records (SMS, WhatsApp, ...), newest first. Paged with page (from 0) and page_size.",
    )
    def list_messages(page: int | None = None, page_size: int | None = None) -> Any:
        return api(client_factory, "GET", MESSAGES, params={"Page": page, "PageSize": page_size})

    @mcp.tool(
        name="siprtc.get_message", description="Fetch one message record by its sid, including status and error code."
    )
    def get_message(message_sid: str) -> Any:
        return api(client_factory, "GET", MESSAGES + "/{sid}", sid=message_sid)

    @mcp.tool(
        name="siprtc.list_conversations",
        description=(
            "Search the conversation history across channels (sms, whatsapp, webchat, email, ...): "
            "filter by conversation_id, contact, to/from, channel, direction or dates (yyyy-mm-dd)."
        ),
    )
    def list_conversations(
        conversation_id: str | None = None,
        contact: str | None = None,
        to: str | None = None,
        from_number: str | None = None,
        channel: str | None = None,
        direction: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        task_sid: str | None = None,
        campaign_id: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {
            "conversationId": conversation_id,
            "contact": contact,
            "to": to,
            "from": from_number,
            "channel": channel,
            "direction": direction,
            "fromDate": from_date,
            "toDate": to_date,
            "taskSid": task_sid,
            "campaignId": campaign_id,
            "page": page,
            "limit": limit,
        }
        return _empty_list(api(client_factory, "GET", CONVERSATIONS, params=params), "conversationResponse")

    @mcp.tool(
        name="siprtc.get_conversation_transcript",
        description="Return one conversation as a plain-text transcript.",
    )
    def get_conversation_transcript(conversation_id: str) -> Any:
        return api(client_factory, "GET", CONVERSATIONS + "/Transcription/{cid}", cid=conversation_id)
