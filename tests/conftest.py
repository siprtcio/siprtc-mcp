from __future__ import annotations

import pytest

from siprtc_mcp import client as client_module
from siprtc_mcp.config import get_settings

BASE = "https://api.test.invalid/v1"


@pytest.fixture(autouse=True)
def _isolated_settings(monkeypatch, request):
    """Unit tests run against a fake base URL with known credentials; live tests keep the real env."""
    if request.node.get_closest_marker("live") is None:
        for name in ("SIPRTC_READ_ONLY", "SIPRTC_TOOLSETS", "SIPRTC_ALLOW_INSECURE_HTTP", "MCP_TRANSPORT"):
            monkeypatch.delenv(name, raising=False)
        monkeypatch.setenv("SIPRTC_BASE_URL", BASE)
        monkeypatch.setenv("SIPRTC_AUTH_ID", "AC0000000000000TEST0")
        monkeypatch.setenv("SIPRTC_AUTH_SECRET", "unit-test-secret")
        monkeypatch.setenv("SIPRTC_MAX_RETRIES", "2")
        monkeypatch.setattr(client_module.SiprtcClient, "_sleep", staticmethod(lambda attempt, retry_after: None))
    get_settings.cache_clear()
    client_module.close_shared_client()
    yield
    get_settings.cache_clear()
    client_module.close_shared_client()
