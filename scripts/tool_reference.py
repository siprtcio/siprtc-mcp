"""Write (or with --check, verify) the README's tool reference from the server's real tool list."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

os.environ.setdefault("SIPRTC_BASE_URL", "https://api.siprtc.io/v1")
os.environ.pop("SIPRTC_READ_ONLY", None)
os.environ.pop("SIPRTC_TOOLSETS", None)

from fastmcp import Client  # noqa: E402

from siprtc_mcp.config import TOOLSETS  # noqa: E402
from siprtc_mcp.server import create_server  # noqa: E402

README = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- tools:start -->", "<!-- tools:end -->"
TITLES = {
    "voice": "Voice calls",
    "conferences": "Conferences",
    "recordings": "Recordings, transcripts and privacy",
    "messaging": "Messaging",
    "channels": "Messaging channels and Meta",
    "fax_email": "Fax and email",
    "phone_numbers": "Phone numbers",
    "sip": "SIP users and SIP domains",
    "trunks": "Carrier trunks and rates",
    "applications": "Applications",
    "account": "Account",
    "taskrouter": "TaskRouter (contact centre routing)",
    "campaigns": "Campaigns",
    "reports": "Reports",
    "flows": "Flows",
    "ai_agents": "AI agents",
    "workforce": "Workforce management",
}
MARK = {"read": "", "write": "✏️", "destructive": "⚠️"}


async def render() -> str:
    async with Client(create_server()) as client:
        tools = await client.list_tools()
    groups: dict[str, list] = {group: [] for group in TOOLSETS}
    for tool in tools:
        tags = set((tool.meta or {}).get("fastmcp", {}).get("tags", []))
        group = next(g for g in TOOLSETS if g in tags)
        kind = next(k for k in ("read", "write", "destructive") if k in tags)
        groups[group].append((tool.name, kind, tool.description.split(" This is billed")[0]))
    lines = [
        START,
        "",
        f"{len(tools)} tools in {len(TOOLSETS)} toolsets. ✏️ changes something, ⚠️ deletes or ends something, 💲 is billed or reaches people.",
        "",
    ]
    for group, rows in groups.items():
        lines += [f"### {TITLES[group]} — `{group}`", "", "| Tool | Does |", "| --- | --- |"]
        for name, kind, text in rows:
            billed = " 💲" if "billed to the account" in next(t.description for t in tools if t.name == name) else ""
            first = text.split(". ")[0].rstrip(".") + "."
            lines.append(f"| `{name}` {MARK[kind]}{billed} | {first.replace('|', '/')} |")
        lines.append("")
    lines.append(END)
    return "\n".join(lines)


def main() -> int:
    block = asyncio.run(render())
    text = README.read_text()
    current = text[text.index(START) : text.index(END) + len(END)]
    if "--check" in sys.argv:
        if current != block:
            print("README tool reference is out of date: run python scripts/tool_reference.py", file=sys.stderr)
            return 1
        return 0
    README.write_text(text.replace(current, block))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
