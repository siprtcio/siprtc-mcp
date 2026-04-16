from __future__ import annotations

import os

from fastmcp import FastMCP

from .auth import SiprtcCredentialTokenVerifier, resolve_request_auth
from .client import SiprtcClient
from .tools import applications, domains, messages, phone_numbers, sip_users, voice_calls


def create_server() -> FastMCP:
    mcp = FastMCP("siprtc", auth=SiprtcCredentialTokenVerifier())

    def client_factory() -> SiprtcClient:
        resolved_id, resolved_secret = resolve_request_auth()
        return SiprtcClient(auth_id=resolved_id, auth_secret=resolved_secret)

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
