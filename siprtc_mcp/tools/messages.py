from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..models import MessageRequest


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.send_sms",
        description=(
            "Send an outbound SMS message. Provide MessageRequest payload. "
            "Supports status callbacks and other optional fields per Siprtc API."
        ),
    )
    def send_sms(sms: MessageRequest) -> Any:
        """
        Send an outbound SMS.

        Args:
          sms: SMS request payload.
        """
        client: SiprtcClient = client_factory()
        path = format_path("/Accounts/{auth_id}/Messages", auth_id=client.auth_id)
        return client.request("POST", path, json=sms.model_dump(by_alias=True, exclude_none=True))
