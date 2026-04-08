from test_app.agent import build_agent, render_message_content, siprtc_tool


def main() -> None:
    # Direct tool tests to ensure each endpoint works.
    print("== Sip Users ==")
    print(siprtc_tool("siprtc.list_sip_users", {}))
    print("\n== Applications ==")
    print(siprtc_tool("siprtc.list_applications", {}))
    print("\n== Domains ==")
    print(siprtc_tool("siprtc.list_domains", {}))
    print("\n== Phone Numbers ==")
    print(siprtc_tool("siprtc.list_phone_numbers", {}))

    # Also keep the agent path for manual testing.
    agent = build_agent()
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "Summarize the current Siprtc resources.",
                }
            ]
        }
    )
    last = result["messages"][-1]
    print("\n== Agent Summary ==")
    print(render_message_content(last))


if __name__ == "__main__":
    main()
