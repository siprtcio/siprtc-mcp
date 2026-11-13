"""Registers tools under one policy: MCP safety annotations, read-only mode and toolset selection.

Tool modules call ``mcp.tool(name=..., description=...)`` on a :class:`Toolset` exactly as they
would on FastMCP. The toolset classifies each tool by its name (``list_``/``get_`` read,
``delete_``/``release_``/... destroy, the rest write), sets the MCP hints clients use to ask for
confirmation, and leaves out tools the deployment has not enabled.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from mcp.types import ToolAnnotations

log = logging.getLogger("siprtc_mcp")

Kind = Literal["read", "write", "destructive"]

READ_PREFIXES = ("list_", "get_", "check_", "search_")
DESTRUCTIVE_PREFIXES = (
    "delete_",
    "release_",
    "disconnect_",
    "remove_",
    "hangup_",
    "cancel_",
    "stop_",
)
# Writes that are safe to repeat with the same arguments (a PUT of the same state).
IDEMPOTENT_PREFIXES = ("update_", "set_", "associate_")
# Tools that spend money or reach people outside the account.
COST_TOOLS = {
    "make_call",
    "send_sms",
    "send_message",
    "send_fax",
    "send_email",
    "send_messenger_message",
    "buy_phone_number",
}


def classify(short_name: str) -> Kind:
    if short_name.startswith(READ_PREFIXES):
        return "read"
    if short_name.startswith(DESTRUCTIVE_PREFIXES):
        return "destructive"
    return "write"


@dataclass
class Toolset:
    """A FastMCP stand-in that applies the server's tool policy while modules register."""

    mcp: Any
    group: str
    read_only: bool = False
    enabled_groups: set[str] | None = None
    tool_timeout: float | None = None
    registered: list[str] = field(default_factory=list)

    def tool(self, *, name: str, description: str, **kwargs: Any) -> Callable[[Callable], Callable]:
        short = name.split(".", 1)[-1]
        kind = classify(short)

        def decorator(fn: Callable) -> Callable:
            if self.enabled_groups is not None and self.group not in self.enabled_groups:
                return fn
            if self.read_only and kind != "read":
                return fn
            text = description
            if short in COST_TOOLS:
                text += " This is billed to the account or contacts people outside it."
            annotations = ToolAnnotations(
                title=short.replace("_", " ").capitalize(),
                read_only_hint=kind == "read",
                destructive_hint=kind == "destructive",
                idempotent_hint=kind == "read" or short.startswith(IDEMPOTENT_PREFIXES),
                open_world_hint=True,
            )
            self.mcp.tool(
                name=name,
                description=text,
                annotations=annotations,
                tags={self.group, kind},
                timeout=self.tool_timeout,
                **kwargs,
            )(fn)
            self.registered.append(name)
            return fn

        return decorator
