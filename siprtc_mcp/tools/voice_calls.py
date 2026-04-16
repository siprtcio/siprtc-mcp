from __future__ import annotations

from typing import Any

from ..client import SiprtcClient, format_path
from ..models import CallRequest


def register(mcp, client_factory):
    @mcp.tool(
        name="siprtc.make_call",
        description=(
            "Create an outbound voice call. Provide a CallRequest payload. "
            "Returns the Siprtc call response with request_id and status."
        ),
    )
    def make_call(call: CallRequest) -> Any:
        """
        Create an outbound call.

        Args:
          call: Call request payload.
        """
        client: SiprtcClient = client_factory()
        path = format_path("/Accounts/{auth_id}/Calls", auth_id=client.auth_id)
        return client.request("POST", path, json=call.model_dump(by_alias=True, exclude_none=True))

    @mcp.tool(
        name="siprtc.get_call",
        description=(
            "Fetch a call detail record (CDR) by call_sid. "
            "Returns the CDR payload or plain text if the API returns non-JSON."
        ),
    )
    def get_call(call_id: str) -> Any:
        """
        Get call detail record by call ID.

        Args:
          call_id: Call SID returned from siprtc.make_call.
        """
        client: SiprtcClient = client_factory()
        path = format_path("/Accounts/{auth_id}/Calls/{call_id}", auth_id=client.auth_id, call_id=call_id)
        return client.request("GET", path)

    @mcp.tool(
        name="siprtc.hangup_call",
        description=(
            "Hang up (delete) an in-progress call by call_sid. "
            "Returns the API response or plain text if the API returns non-JSON."
        ),
    )
    def hangup_call(call_id: str) -> Any:
        """
        Hang up an in-progress call.

        Args:
          call_id: Call SID returned from siprtc.make_call.
        """
        client: SiprtcClient = client_factory()
        path = format_path("/Accounts/{auth_id}/Calls/{call_id}", auth_id=client.auth_id, call_id=call_id)
        return client.request("DELETE", path)
