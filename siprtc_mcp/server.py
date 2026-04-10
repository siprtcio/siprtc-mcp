from __future__ import annotations

import os

from fastmcp import FastMCP

from .client import SiprtcClient
from .config import SESSION, resolve_auth
from .tools import applications, domains, messages, phone_numbers, sip_users, voice_calls


def create_server() -> FastMCP:
    mcp = FastMCP("siprtc")

    def client_factory(auth_id: str | None, auth_secret: str | None) -> SiprtcClient:
        resolved_id, resolved_secret = resolve_auth(auth_id, auth_secret)
        return SiprtcClient(auth_id=resolved_id, auth_secret=resolved_secret)

    @mcp.tool(
        name="siprtc.set_credentials",
        description=(
            "Set Siprtc credentials for the current server session. "
            "Use this if you don't want to pass auth_id/auth_secret to every call."
        ),
    )
    def set_credentials(auth_id: str, auth_secret: str) -> dict:
        """
        Store Siprtc credentials in memory for this MCP server session.

        Args:
          auth_id: Siprtc auth ID.
          auth_secret: Siprtc auth secret.
        """
        SESSION.set_credentials(auth_id=auth_id, auth_secret=auth_secret)
        return {"status": "ok"}

    voice_calls.register(mcp, client_factory)
    messages.register(mcp, client_factory)
    phone_numbers.register(mcp, client_factory)
    sip_users.register(mcp, client_factory)
    domains.register(mcp, client_factory)
    applications.register(mcp, client_factory)

    return mcp


def main() -> None:
    mcp = create_server()
    transport = os.getenv("MCP_TRANSPORT", "stdio")
    if transport == "http":
        host = os.getenv("MCP_HOST", "127.0.0.1")
        port = int(os.getenv("MCP_PORT", "8000"))
        path = os.getenv("MCP_PATH", "/mcp")
        mcp.run(transport="http", host=host, port=port, path=path)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
