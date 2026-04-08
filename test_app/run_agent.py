import os

import anyio
from deepagents import create_deep_agent
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


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


def siprtc_tool(tool_name: str, arguments: dict) -> str:
    """Call a Siprtc MCP tool by name with JSON arguments."""
    server_url = os.getenv("MCP_SERVER_URL", "http://siprtc-mcp:8000/mcp")

    async def _run() -> str:
        async with streamable_http_client(server_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments or {})
                return _format_result(result)

    return anyio.run(_run)


def main() -> None:
    load_dotenv()

    _require_env("SIPRTC_AUTH_ID")
    _require_env("SIPRTC_AUTH_SECRET")
    _require_env("OPENAI_API_KEY")

    system_prompt = (
        "You are a helpful assistant. You have a tool siprtc_tool(tool_name, arguments). "
        "Use it for Siprtc operations. Authentication is already provided via env vars, "
        "so do not ask for credentials. For listing purchased numbers, call "
        "tool_name='siprtc.list_phone_numbers' with arguments={}."
    )

    model = os.getenv("DEEP_AGENT_MODEL", "openai:gpt-4.1-mini")
    agent = create_deep_agent(
        model=model,
        tools=[siprtc_tool],
        system_prompt=system_prompt,
    )

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Use siprtc_tool to list my purchased phone numbers and return the result.",
                }
            ]
        }
    )
    last = result["messages"][-1]
    content = getattr(last, "content", None)
    if content is None and isinstance(last, dict):
        content = last.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                parts.append(item["text"])
            else:
                parts.append(str(item))
        content = "\n".join(parts)
    print(content if content is not None else str(last))


if __name__ == "__main__":
    main()
