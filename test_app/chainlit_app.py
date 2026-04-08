import sys

import anyio
import chainlit as cl

sys.path.append("/app")

from test_app.agent import build_agent, render_message_content


@cl.on_chat_start
async def on_chat_start() -> None:
    cl.user_session.set("agent", build_agent())
    await cl.Message(
        content=(
            "Welcome to the **Siprtc Assistant**. Ask me about your Siprtc account, "
            "phone numbers, calls, or messages. Powered by siprtc.io."
        )
    ).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    agent = cl.user_session.get("agent")
    result = await anyio.to_thread.run_sync(
        agent.invoke,
        {"messages": [{"role": "user", "content": message.content}]},
    )
    last = result["messages"][-1]
    await cl.Message(content=render_message_content(last)).send()
