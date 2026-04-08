from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from .config import get_base_url


class SiprtcApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


@dataclass
class SiprtcClient:
    auth_id: str
    auth_secret: str
    base_url: str | None = None
    timeout: float = 20.0

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url or get_base_url(),
            auth=(self.auth_id, self.auth_secret),
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )

    def request(self, method: str, path: str, *, json: dict | None = None, params: dict | None = None) -> Any:
        with self._client() as client:
            response = client.request(method, path, json=json, params=params)
        if response.status_code >= 400:
            payload = None
            try:
                payload = response.json()
            except Exception:
                payload = response.text
            raise SiprtcApiError(
                f"Siprtc API error ({response.status_code})",
                status_code=response.status_code,
                payload=payload,
            )
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            return response.json()
        return response.text


def format_path(path_template: str, **values: str) -> str:
    return path_template.format(**values)
