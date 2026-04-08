from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..models import MessageRequest


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.send_sms",
        description=(
            "Send an outbound SMS message. Provide MessageRequest payload and optional auth credentials. "
            "Supports status callbacks and other optional fields per Siprtc API."
        ),
    )
    def send_sms(
        sms: MessageRequest,
        auth_id: str | None = None,
        auth_secret: str | None = None,
    ) -> Any:
        """
        Send an outbound SMS.

        Args:
          sms: SMS request payload.
          auth_id: Optional Siprtc auth ID (overrides env/session).
          auth_secret: Optional Siprtc auth secret (overrides env/session).
        """
        client: SiprtcClient = client_factory(auth_id, auth_secret)
        path = format_path("/Accounts/{auth_id}/Messages", auth_id=client.auth_id)
        return client.request("POST", path, json=sms.model_dump(by_alias=True, exclude_none=True))
