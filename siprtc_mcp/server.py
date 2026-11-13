from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .auth import SiprtcCredentialTokenVerifier, resolve_request_auth
from .client import SiprtcClient, close_shared_client
from .config import TOOLSETS, ConfigError, Settings, get_settings
from .tools import (
    account,
    applications,
    channels,
    conferences,
    fax_email,
    messages,
    phone_numbers,
    recordings,
    sip,
    sip_trunking,
    trunks,
    voice_calls,
)
from .toolset import Toolset

log = logging.getLogger("siprtc_mcp")

MODULES = {
    "voice": voice_calls,
    "conferences": conferences,
    "recordings": recordings,
    "messaging": messages,
    "channels": channels,
    "fax_email": fax_email,
    "phone_numbers": phone_numbers,
    "sip": sip,
    "sip_trunking": sip_trunking,
    "trunks": trunks,
    "applications": applications,
    "account": account,
}
if tuple(MODULES) != TOOLSETS:  # pragma: no cover - a packaging mistake, caught by the tests
    raise RuntimeError("server.MODULES and config.TOOLSETS disagree")

INSTRUCTIONS = """\
Tools for the SIPRTC CPaaS API, acting on the account whose Auth ID and secret this server holds.
Phone numbers are E.164 (+14155550100). List tools are paged; ask for the next page rather than
assuming a list is complete. Tools that place calls, send messages, buy numbers or
delete things act on the real account and may cost money: confirm with the user before calling them.
"""


def create_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or get_settings()
    mcp = FastMCP(
        "siprtc",
        instructions=INSTRUCTIONS,
        version=__version__,
        auth=SiprtcCredentialTokenVerifier() if settings.transport == "http" else None,
        mask_error_details=True,
        on_duplicate="error",
    )

    def client_factory() -> SiprtcClient:
        auth_id, auth_secret = resolve_request_auth()
        return SiprtcClient(auth_id=auth_id, auth_secret=auth_secret)

    registered: list[str] = []
    for group, module in MODULES.items():
        toolset = Toolset(
            mcp,
            group,
            read_only=settings.read_only,
            enabled_groups=set(settings.toolsets) if settings.toolsets is not None else None,
            tool_timeout=settings.timeout * (settings.max_retries + 1) + 15,
        )
        module.register(toolset, client_factory)
        registered.extend(toolset.registered)
    log.info(
        "siprtc-mcp %s: %d tools (read_only=%s, toolsets=%s, base_url=%s)",
        __version__,
        len(registered),
        settings.read_only,
        ",".join(sorted(settings.toolsets)) if settings.toolsets else "all",
        settings.base_url,
    )

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(_: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "version": __version__, "tools": len(registered)})

    return mcp


def main() -> None:
    try:
        settings = get_settings()
    except ConfigError as exc:
        print(f"siprtc-mcp: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    # stdio carries the protocol on stdout, so logs always go to stderr.
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    mcp = create_server(settings)
    try:
        if settings.transport == "http":
            mcp.run(transport="http", host=settings.host, port=settings.port, path=settings.path)
        else:
            mcp.run()
    finally:
        close_shared_client()


if __name__ == "__main__":
    main()
