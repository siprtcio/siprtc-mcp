from __future__ import annotations

import base64

from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.dependencies import get_access_token

from .config import resolve_env_auth


def decode_bearer_token(token: str) -> tuple[str, str]:
    token = token.strip()
    if not token:
        raise ValueError("Missing bearer token.")

    try:
        decoded = base64.urlsafe_b64decode(token).decode()
        auth_id, auth_secret = decoded.split(":", 1)
    except Exception as exc:
        raise ValueError("Invalid bearer token.") from exc

    if not auth_id or not auth_secret:
        raise ValueError("Bearer token must decode to 'auth_id:auth_secret'.")
    return auth_id, auth_secret


class SiprtcCredentialTokenVerifier(TokenVerifier):
    """
    Accept bearer tokens that decode to ``auth_id:auth_secret``.
    NOTE: This verifier does not validate the credential pair against Siprtc.
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            auth_id, _ = decode_bearer_token(token)
        except ValueError:
            return None

        return AccessToken(
            token=token,
            client_id=auth_id,
            scopes=["siprtc"],
            claims={"siprtc_auth_id": auth_id},
        )


def resolve_request_auth() -> tuple[str, str]:
    access_token = get_access_token()
    if access_token is None:
        return resolve_env_auth()
    return decode_bearer_token(access_token.token)
