"""Helpers for the live suite: call a tool through a real MCP client and read its JSON answer."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from fastmcp import Client

from siprtc_mcp.server import create_server

RUN = f"mcpe2e{int(time.time()) % 10_000_000}"


class ToolFailed(AssertionError):
    pass


def client() -> Client:
    return Client(create_server())


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"live tests need {name}")
    return value


def _parse(result) -> Any:
    if result.content:
        text = result.content[0].text
        try:
            return json.loads(text)
        except (TypeError, ValueError):
            return text
    return result.data


async def ok(c: Client, tool: str, /, **args: Any) -> Any:
    result = await c.call_tool(f"siprtc.{tool}", args, raise_on_error=False)
    body = _parse(result)
    if result.is_error:
        raise ToolFailed(f"{tool}({args}) failed: {body}")
    return body


async def refused(c: Client, tool: str, /, **args: Any) -> str:
    result = await c.call_tool(f"siprtc.{tool}", args, raise_on_error=False)
    body = _parse(result)
    if not result.is_error:
        raise ToolFailed(f"{tool}({args}) was expected to fail but returned {body}")
    return str(body)


async def quietly(c: Client, tool: str, /, **args: Any) -> None:
    """Cleanup: try, and never mask the test's own failure."""
    try:
        await c.call_tool(f"siprtc.{tool}", args, raise_on_error=False)
    except Exception:  # noqa: S110
        pass


def find(value: Any, *keys: str) -> Any:
    """The first of ``keys`` found anywhere in a nested answer."""
    if isinstance(value, dict):
        for key in keys:
            if value.get(key) not in (None, ""):
                return value[key]
        for item in value.values():
            found = find(item, *keys)
            if found not in (None, ""):
                return found
    if isinstance(value, list):
        for item in value:
            found = find(item, *keys)
            if found not in (None, ""):
                return found
    return None


def items(value: Any, key: str) -> list:
    """A list in an answer, wherever the API nested it."""
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        if isinstance(value.get(key), list):
            return value[key]
        for item in value.values():
            if isinstance(item, (dict, list)):
                found = items(item, key)
                if found:
                    return found
    return []
