"""Fax (send/receive, fax documents) and outbound email."""

from __future__ import annotations

import base64
from typing import Any

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api

FAXES = ACCOUNT + "/Faxes"
MEDIA = ACCOUNT + "/Media"


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.list_faxes",
        description="List sent faxes, optionally filtered by to, from, status or title.",
    )
    def list_faxes(
        to: str | None = None,
        from_number: str | None = None,
        status: str | None = None,
        title: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {"to": to, "from": from_number, "status": status, "title": title, "page": page, "page_size": page_size}
        return api(client_factory, "GET", FAXES, params=params)

    @mcp.tool(name="siprtc.list_received_faxes", description="List received (inbound) faxes.")
    def list_received_faxes(
        from_number: str | None = None,
        to: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> Any:
        params = {"from": from_number, "to": to, "page": page, "page_size": page_size}
        return api(client_factory, "GET", FAXES + "/recive", params=params)

    @mcp.tool(
        name="siprtc.send_fax",
        description=(
            "Send a fax (billed). media_sid is a document uploaded with siprtc.upload_fax_document; "
            "from_number is a fax-capable number on the account."
        ),
    )
    def send_fax(
        to: str,
        from_number: str,
        media_sid: str,
        title: str | None = None,
        max_retry: int | None = None,
        quality: str | None = None,
    ) -> Any:
        body = {
            "to": to,
            "from": from_number,
            "media_sid": media_sid,
            "title": title,
            "max_retry": max_retry,
            "quality": quality,
        }
        return api(client_factory, "POST", FAXES, json=body)

    @mcp.tool(name="siprtc.delete_fax", description="Delete a fax record.")
    def delete_fax(fax_id: str) -> Any:
        return api(client_factory, "DELETE", FAXES + "/{fax_id}", fax_id=fax_id)

    @mcp.tool(name="siprtc.list_fax_documents", description="List documents uploaded for faxing.")
    def list_fax_documents(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", MEDIA, params={"page": page, "limit": limit})

    @mcp.tool(
        name="siprtc.upload_fax_document",
        description="Upload a document (PDF, TIFF, ...) to fax later. content_base64 is the file's bytes, base64-encoded. Returns its media sid.",
    )
    def upload_fax_document(
        filename: str,
        content_base64: str,
        content_type: str = "application/pdf",
        docname: str | None = None,
        description: str | None = None,
    ) -> Any:
        try:
            content = base64.b64decode(content_base64, validate=True)
        except Exception as exc:
            raise ToolError("content_base64 is not valid base64.") from exc
        form = {
            "filename": filename,
            "docname": docname or filename,
            "docdescription": description,
            "content_type": content_type,
        }
        files = {"file": (filename, content, content_type)}
        return api(client_factory, "POST", MEDIA, data=form, files=files)

    @mcp.tool(name="siprtc.delete_fax_document", description="Delete an uploaded fax document.")
    def delete_fax_document(media_id: str) -> Any:
        return api(client_factory, "DELETE", MEDIA + "/{media_id}", media_id=media_id)

    @mcp.tool(
        name="siprtc.send_email",
        description=(
            "Send an email (HTML body) through the account's configured SMTP sender. from_email must "
            "match a sender configured on the account."
        ),
    )
    def send_email(to: str, from_email: str, subject: str, html_body: str) -> Any:
        body = {
            "email": to,
            "from": from_email,
            "subject": subject,
            "emailBody": html_body,
            "emailType": "send",
            "hasAttachment": False,
        }
        return api(client_factory, "POST", ACCOUNT + "/SendEmail", json=body)
