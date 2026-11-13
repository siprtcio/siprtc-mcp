from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

DEFAULT_BASE_URL = "https://api.siprtc.io/v1"

ENV_AUTH_ID = "SIPRTC_AUTH_ID"
ENV_AUTH_SECRET = "SIPRTC_AUTH_SECRET"  # noqa: S105 - the variable name, not a secret

TOOLSETS = (
    "voice",
    "conferences",
    "recordings",
    "messaging",
    "channels",
    "fax_email",
    "phone_numbers",
    "sip",
    "trunks",
    "applications",
    "account",
    "taskrouter",
    "campaigns",
    "reports",
    "flows",
    "ai_agents",
    "workforce",
)

# Deployments with different routes can override these paths. Paths are relative to
# SIPRTC_BASE_URL and may contain {auth_id} and the resource's own placeholders.
ENV_PHONE_NUMBERS_LIST_PATH = "SIPRTC_PHONE_NUMBERS_LIST_PATH"
ENV_PHONE_NUMBERS_GET_PATH = "SIPRTC_PHONE_NUMBERS_GET_PATH"
ENV_PHONE_NUMBERS_BUY_PATH = "SIPRTC_PHONE_NUMBERS_BUY_PATH"
ENV_PHONE_NUMBERS_RELEASE_PATH = "SIPRTC_PHONE_NUMBERS_RELEASE_PATH"
ENV_PHONE_NUMBERS_AVAILABLE_PATH = "SIPRTC_PHONE_NUMBERS_AVAILABLE_PATH"
ENV_PHONE_NUMBERS_ASSOCIATE_PATH = "SIPRTC_PHONE_NUMBERS_ASSOCIATE_PATH"
ENV_SIP_USERS_PATH = "SIPRTC_SIP_USERS_PATH"
ENV_SIP_USER_PATH = "SIPRTC_SIP_USER_PATH"
ENV_APPLICATIONS_PATH = "SIPRTC_APPLICATIONS_PATH"
ENV_APPLICATION_PATH = "SIPRTC_APPLICATION_PATH"

DEFAULT_PHONE_NUMBERS_LIST_PATH = "/Accounts/{auth_id}/PhoneNumbers"
DEFAULT_PHONE_NUMBERS_GET_PATH = "/Accounts/{auth_id}/PhoneNumbers/{phone_number}"
DEFAULT_PHONE_NUMBERS_BUY_PATH = "/Accounts/{auth_id}/PhoneNumbers/{phone_number}"
DEFAULT_PHONE_NUMBERS_RELEASE_PATH = "/Accounts/{auth_id}/PhoneNumbers/{phone_number}"
DEFAULT_PHONE_NUMBERS_AVAILABLE_PATH = "/Accounts/{auth_id}/AvailablePhoneNumbers/{country_code}/{phone_type}"
DEFAULT_PHONE_NUMBERS_ASSOCIATE_PATH = "/Accounts/{auth_id}/PhoneNumbers/{phone_number}"
DEFAULT_SIP_USERS_PATH = "/Accounts/{auth_id}/Sip/endpoint"
DEFAULT_SIP_USER_PATH = "/Accounts/{auth_id}/Sip/endpoint/{endpoint_id}"
DEFAULT_APPLICATIONS_PATH = "/Accounts/{auth_id}/Applications"
DEFAULT_APPLICATION_PATH = "/Accounts/{auth_id}/Applications/{application_sid}"


class ConfigError(ValueError):
    """Raised at start-up when the environment describes an unusable configuration."""


def _flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise ConfigError(f"{name} must be true or false, not {value!r}.")


def _number(name: str, default: float, *, minimum: float, maximum: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        number = float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, not {value!r}.") from exc
    if not minimum <= number <= maximum:
        raise ConfigError(f"{name} must be between {minimum:g} and {maximum:g}.")
    return number


@dataclass(frozen=True)
class Settings:
    base_url: str
    timeout: float
    max_retries: int
    read_only: bool
    toolsets: frozenset[str] | None
    verify_bearer: bool
    transport: str
    host: str
    port: int
    path: str
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        base_url = os.getenv("SIPRTC_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ConfigError(f"SIPRTC_BASE_URL must be an http(s) URL, not {base_url!r}.")
        local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme == "http" and not local and not _flag("SIPRTC_ALLOW_INSECURE_HTTP"):
            raise ConfigError(
                "SIPRTC_BASE_URL uses plain http, which sends credentials in the clear. Use https, "
                "or set SIPRTC_ALLOW_INSECURE_HTTP=true for a private network."
            )

        raw_toolsets = os.getenv("SIPRTC_TOOLSETS", "").strip()
        toolsets: frozenset[str] | None = None
        if raw_toolsets and raw_toolsets.lower() != "all":
            toolsets = frozenset(part.strip() for part in raw_toolsets.split(",") if part.strip())
            unknown = toolsets - set(TOOLSETS)
            if unknown:
                raise ConfigError(
                    f"SIPRTC_TOOLSETS has unknown toolsets {sorted(unknown)}; choose from {', '.join(TOOLSETS)}."
                )

        transport = os.getenv("MCP_TRANSPORT", "stdio").strip().lower()
        if transport not in {"stdio", "http"}:
            raise ConfigError(f"MCP_TRANSPORT must be stdio or http, not {transport!r}.")

        path = os.getenv("MCP_PATH", "/mcp").strip() or "/mcp"
        if not path.startswith("/"):
            path = "/" + path

        return cls(
            base_url=base_url,
            timeout=_number("SIPRTC_TIMEOUT", 30.0, minimum=1, maximum=300),
            max_retries=int(_number("SIPRTC_MAX_RETRIES", 2, minimum=0, maximum=5)),
            read_only=_flag("SIPRTC_READ_ONLY"),
            toolsets=toolsets,
            verify_bearer=_flag("SIPRTC_VERIFY_BEARER", True),
            transport=transport,
            host=os.getenv("MCP_HOST", "127.0.0.1").strip(),
            port=int(_number("MCP_PORT", 8000, minimum=1, maximum=65535)),
            path=path,
            log_level=os.getenv("SIPRTC_LOG_LEVEL", "INFO").strip().upper(),
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_env()


def env_or_default(env_name: str, default: str) -> str:
    value = os.getenv(env_name)
    return value.strip() if value else default


def get_base_url() -> str:
    return get_settings().base_url


def resolve_env_auth() -> tuple[str, str]:
    resolved_id = os.getenv(ENV_AUTH_ID, "").strip()
    resolved_secret = os.getenv(ENV_AUTH_SECRET, "").strip()
    if not resolved_id or not resolved_secret:
        raise ValueError(
            "Missing SIPRTC credentials. Send an Authorization bearer token with each HTTP request, "
            "or set SIPRTC_AUTH_ID and SIPRTC_AUTH_SECRET."
        )
    return resolved_id, resolved_secret


def phone_numbers_list_path() -> str:
    return env_or_default(ENV_PHONE_NUMBERS_LIST_PATH, DEFAULT_PHONE_NUMBERS_LIST_PATH)


def phone_numbers_get_path() -> str:
    return env_or_default(ENV_PHONE_NUMBERS_GET_PATH, DEFAULT_PHONE_NUMBERS_GET_PATH)


def phone_numbers_buy_path() -> str:
    return env_or_default(ENV_PHONE_NUMBERS_BUY_PATH, DEFAULT_PHONE_NUMBERS_BUY_PATH)


def phone_numbers_release_path() -> str:
    return env_or_default(ENV_PHONE_NUMBERS_RELEASE_PATH, DEFAULT_PHONE_NUMBERS_RELEASE_PATH)


def phone_numbers_available_path() -> str:
    return env_or_default(ENV_PHONE_NUMBERS_AVAILABLE_PATH, DEFAULT_PHONE_NUMBERS_AVAILABLE_PATH)


def phone_numbers_associate_path() -> str:
    return env_or_default(ENV_PHONE_NUMBERS_ASSOCIATE_PATH, DEFAULT_PHONE_NUMBERS_ASSOCIATE_PATH)


def sip_users_path() -> str:
    return env_or_default(ENV_SIP_USERS_PATH, DEFAULT_SIP_USERS_PATH)


def sip_user_path() -> str:
    return env_or_default(ENV_SIP_USER_PATH, DEFAULT_SIP_USER_PATH)


def applications_path() -> str:
    return env_or_default(ENV_APPLICATIONS_PATH, DEFAULT_APPLICATIONS_PATH)


def application_path() -> str:
    return env_or_default(ENV_APPLICATION_PATH, DEFAULT_APPLICATION_PATH)
