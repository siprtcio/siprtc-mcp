"""AI agents (LLM voice/chat agents), their chat sessions, and the TTS voice catalogue."""

from __future__ import annotations

from typing import Any

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api, merge

AGENTS = ACCOUNT + "/agents"
AGENT = AGENTS + "/{agent_id}"
SESSIONS = ACCOUNT + "/sessions"
SESSION = SESSIONS + "/{session_id}"
VOICES = ACCOUNT + "/voices"


def register(mcp, client_factory):
    @mcp.tool(name="siprtc.list_ai_agents", description="List AI agents.")
    def list_ai_agents(limit: int | None = None, offset: int | None = None) -> Any:
        return api(client_factory, "GET", AGENTS, params={"limit": limit, "offset": offset})

    @mcp.tool(
        name="siprtc.get_ai_agent", description="Fetch one AI agent, including its prompt, tools and runtime settings."
    )
    def get_ai_agent(agent_id: str) -> Any:
        return api(client_factory, "GET", AGENT, agent_id=agent_id)

    @mcp.tool(
        name="siprtc.create_ai_agent",
        description=(
            'Create an AI agent. channels e.g. ["voice", "webchat"]; category from '
            "siprtc.list_ai_agent_categories. extra takes other fields: tools, mcp_servers, "
            "builtin_tools, runtime_config {llm_model, temperature, max_tokens, kb_enabled, ...}, "
            "vendor/language/voice for speech."
        ),
    )
    def create_ai_agent(
        name: str,
        system_prompt: str,
        description: str | None = None,
        category: str | None = None,
        channels: list[str] | None = None,
        welcome_message: str | None = None,
        extra: dict | None = None,
    ) -> Any:
        body = merge(
            {
                "name": name,
                "system_prompt": system_prompt,
                "description": description,
                "category": category,
                "channels": channels,
                "welcome_message": welcome_message,
            },
            extra,
        )
        return api(client_factory, "POST", AGENTS, json=body)

    @mcp.tool(
        name="siprtc.update_ai_agent",
        description="Change an AI agent. fields takes any create_ai_agent field; only those change.",
    )
    def update_ai_agent(agent_id: str, fields: dict) -> Any:
        if not fields:
            raise ToolError("Pass at least one field to change.")
        return api(client_factory, "PUT", AGENT, json=fields, agent_id=agent_id)

    @mcp.tool(name="siprtc.delete_ai_agent", description="Delete an AI agent.")
    def delete_ai_agent(agent_id: str) -> Any:
        return api(client_factory, "DELETE", AGENT, agent_id=agent_id)

    @mcp.tool(name="siprtc.list_ai_agent_categories", description="List the categories an AI agent can have.")
    def list_ai_agent_categories() -> Any:
        return api(client_factory, "GET", AGENTS + "/categories")

    # --- sessions ---------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_ai_agent_sessions",
        description="List AI agent conversations (sessions), optionally for one agent.",
    )
    def list_ai_agent_sessions(agent_id: str | None = None, limit: int | None = None, offset: int | None = None) -> Any:
        return api(client_factory, "GET", SESSIONS, params={"agent_id": agent_id, "limit": limit, "offset": offset})

    @mcp.tool(
        name="siprtc.create_ai_agent_session",
        description="Open a chat session with an AI agent; then talk to it with siprtc.send_agent_message.",
    )
    def create_ai_agent_session(
        agent_id: str, title: str | None = None, metadata: dict | None = None, ttl_seconds: int | None = None
    ) -> Any:
        body = {
            "agent_id": agent_id,
            "session_type": "chat",
            "title": title,
            "metadata": metadata,
            "ttl_seconds": ttl_seconds,
        }
        return api(client_factory, "POST", SESSIONS, json=body)

    @mcp.tool(name="siprtc.get_ai_agent_session", description="Fetch one AI agent session.")
    def get_ai_agent_session(session_id: str) -> Any:
        return api(client_factory, "GET", SESSION, session_id=session_id)

    @mcp.tool(
        name="siprtc.send_agent_message",
        description="Send a user message into an AI agent session and get the agent's reply (and any tool calls it made).",
    )
    def send_agent_message(session_id: str, content: str, metadata: dict | None = None) -> Any:
        return api(
            client_factory,
            "POST",
            SESSION + "/messages",
            json={"content": content, "metadata": metadata},
            session_id=session_id,
        )

    @mcp.tool(
        name="siprtc.list_ai_agent_session_messages", description="List the messages exchanged in an AI agent session."
    )
    def list_ai_agent_session_messages(session_id: str) -> Any:
        return api(client_factory, "GET", SESSION + "/messages", session_id=session_id)

    @mcp.tool(name="siprtc.delete_ai_agent_session", description="Delete an AI agent session and its messages.")
    def delete_ai_agent_session(session_id: str) -> Any:
        return api(client_factory, "DELETE", SESSION, session_id=session_id)

    # --- voices -----------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_voices",
        description="List text-to-speech voices: the account's saved voices, or the full catalogue with catalog=true.",
    )
    def list_voices(catalog: bool = False) -> Any:
        return api(client_factory, "GET", VOICES + ("/catalog" if catalog else ""))
