import os
from base64 import urlsafe_b64encode

import anyio
from deepagents import create_deep_agent
from dotenv import load_dotenv
from fastmcp import Client


def _require_env(name: str) -> None:
    if not os.getenv(name):
        raise RuntimeError(f"Missing required env var: {name}")


def _format_result(result) -> str:
    if not result.content:
        return ""
    parts = []
    for item in result.content:
        if item.type == "text":
            parts.append(item.text)
        elif item.type == "json":
            parts.append(str(item.json))
    return "\n".join(parts)


def _build_auth_token() -> str:
    auth_id = os.getenv("SIPRTC_AUTH_ID")
    auth_secret = os.getenv("SIPRTC_AUTH_SECRET")
    if not auth_id or not auth_secret:
        raise RuntimeError("Missing SIPRTC_AUTH_ID or SIPRTC_AUTH_SECRET for MCP HTTP authentication.")

    return urlsafe_b64encode(f"{auth_id}:{auth_secret}".encode("utf-8")).decode("ascii")


def siprtc_tool(tool_name: str, arguments: dict) -> str:
    """Call a Siprtc MCP tool by name with JSON arguments."""
    server_url = os.getenv("MCP_SERVER_URL", "http://siprtc-mcp:8000/mcp")
    auth_token = _build_auth_token()

    async def _run() -> str:
        async with Client(server_url, auth=auth_token) as client:
            result = await client.call_tool(tool_name, arguments or {}, raise_on_error=False)
            return _format_result(result)

    return anyio.run(_run)


def build_agent():
    load_dotenv()

    # Credentials are provided via backend environment variables.
    # Do not prompt users for these in the UI.

    system_prompt = (
        "You are a helpful assistant for Siprtc CPaaS. You have a tool "
        "siprtc_tool(tool_name, arguments). Use it for Siprtc operations. "
        "Authentication is already provided via env vars, so do not ask for credentials. "
        "When asked to list resources, use these tools:\n"
        "- Sip users: tool_name='siprtc.list_sip_users'\n"
        "- Applications: tool_name='siprtc.list_applications'\n"
        "- Domains: tool_name='siprtc.list_domains'\n"
        "- Phone numbers: tool_name='siprtc.list_phone_numbers'\n"
        "Use arguments={} unless the user specifies filters."
    )

    model = os.getenv("DEEP_AGENT_MODEL", "openai:gpt-4.1-mini")
    return create_deep_agent(
        model=model,
        tools=[siprtc_tool],
        system_prompt=system_prompt,
    )


def render_message_content(message) -> str:
    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            else:
                parts.append(str(item))
        content = "\n".join(parts)
    return content if content is not None else str(message)
