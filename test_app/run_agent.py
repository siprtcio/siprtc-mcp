import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


def _require_env(name: str) -> None:
    if not os.getenv(name):
        raise RuntimeError(f"Missing required env var: {name}")


def _format_tools(tools: list[Any]) -> str:
    lines = []
    for tool in tools:
        schema = json.dumps(tool.inputSchema, indent=2)
        lines.append(f"- {tool.name}: {tool.description}\n  input_schema: {schema}")
    return "\n".join(lines)


async def main() -> None:
    load_dotenv()

    # The MCP server uses these credentials to authenticate to Siprtc.
    _require_env("SIPRTC_AUTH_ID")
    _require_env("SIPRTC_AUTH_SECRET")

    # LangChain model credentials.
    _require_env("OPENAI_API_KEY")

    server_url = os.getenv("MCP_SERVER_URL", "http://siprtc-mcp:8000/mcp")

    async with streamable_http_client(server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools_result = await session.list_tools()
            tool_list = tools_result.tools

            class McpToolArgs(BaseModel):
                tool_name: str = Field(description="Exact MCP tool name to call.")
                arguments: dict = Field(default_factory=dict, description="JSON arguments for the tool.")

            async def call_mcp_tool(tool_name: str, arguments: dict) -> str:
                result = await session.call_tool(tool_name, arguments)
                if not result.content:
                    return ""
                parts = []
                for item in result.content:
                    if item.type == "text":
                        parts.append(item.text)
                    elif item.type == "json":
                        parts.append(json.dumps(item.json, indent=2))
                return "\n".join(parts)

            mcp_tool = StructuredTool.from_function(
                func=None,
                args_schema=McpToolArgs,
                coroutine=call_mcp_tool,
                name="siprtc_mcp_call",
                description=(
                    "Call a tool on the Siprtc MCP server using tool_name and arguments."
                ),
            )

            llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
            system_prompt = (
                "Respond to the human as helpfully and accurately as possible. "
                "You have access to the following tools:\n\n"
                "{tools}\n\n"
                "Use a json blob to specify a tool by providing an action key (tool name) "
                "and an action_input key (tool input).\n\n"
                "Valid \"action\" values: \"Final Answer\" or {tool_names}\n\n"
                "Provide only ONE action per $JSON_BLOB, as shown:\n\n"
                "```\n"
                "{{\n"
                "  \"action\": $TOOL_NAME,\n"
                "  \"action_input\": $INPUT\n"
                "}}\n"
                "```\n\n"
                "Follow this format:\n\n"
                "Question: input question to answer\n"
                "Thought: consider previous and subsequent steps\n"
                "Action:\n"
                "```\n"
                "$JSON_BLOB\n"
                "```\n"
                "Observation: action result\n"
                "... (repeat Thought/Action/Observation N times)\n"
                "Thought: I know what to respond\n"
                "Action:\n"
                "```\n"
                "{{\n"
                "  \"action\": \"Final Answer\",\n"
                "  \"action_input\": \"Final response to human\"\n"
                "}}\n"
                "```\n\n"
                "Begin! Reminder to ALWAYS respond with a valid json blob of a single action. "
                "Use tools if necessary. Respond directly if appropriate. Format is Action:```$JSON_BLOB```then Observation."
            )

            human_prompt = "{input}\n\n{agent_scratchpad}\n\n(reminder to respond in a JSON blob no matter what)"

            prompt_template = ChatPromptTemplate.from_messages(
                [
                    ("system", system_prompt),
                    MessagesPlaceholder("chat_history", optional=True),
                    ("human", human_prompt),
                ]
            )

            agent = create_structured_chat_agent(
                llm=llm,
                tools=[mcp_tool],
                prompt=prompt_template,
            )
            executor = AgentExecutor(agent=agent, tools=[mcp_tool], verbose=False)

            tool_catalog = _format_tools(tool_list)
            prompt = (
                "Use the MCP tool to list purchased phone numbers.\n"
                "Available MCP tools:\n"
                f"{tool_catalog}\n\n"
                "Call siprtc_mcp_call with tool_name and arguments, for example:\n"
                "tool_name: siprtc.list_phone_numbers\n"
                "arguments: {}\n"
                "Return the tool result."
            )

            result = await executor.ainvoke({"input": prompt})
            print(result.get("output") or result)


if __name__ == "__main__":
    asyncio.run(main())
