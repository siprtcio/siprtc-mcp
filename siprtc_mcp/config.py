from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.siprtc.io/v1"

ENV_AUTH_ID = "SIPRTC_AUTH_ID"
ENV_AUTH_SECRET = "SIPRTC_AUTH_SECRET"

# Optional configurable paths for modules not present in the provided Swagger.
ENV_PHONE_NUMBERS_LIST_PATH = "SIPRTC_PHONE_NUMBERS_LIST_PATH"
ENV_PHONE_NUMBERS_GET_PATH = "SIPRTC_PHONE_NUMBERS_GET_PATH"
ENV_PHONE_NUMBERS_BUY_PATH = "SIPRTC_PHONE_NUMBERS_BUY_PATH"
ENV_PHONE_NUMBERS_RELEASE_PATH = "SIPRTC_PHONE_NUMBERS_RELEASE_PATH"
ENV_PHONE_NUMBERS_AVAILABLE_PATH = "SIPRTC_PHONE_NUMBERS_AVAILABLE_PATH"
ENV_PHONE_NUMBERS_ASSOCIATE_PATH = "SIPRTC_PHONE_NUMBERS_ASSOCIATE_PATH"
ENV_SIP_USERS_PATH = "SIPRTC_SIP_USERS_PATH"
ENV_SIP_USER_PATH = "SIPRTC_SIP_USER_PATH"
ENV_DOMAINS_PATH = "SIPRTC_DOMAINS_PATH"
ENV_DOMAIN_PATH = "SIPRTC_DOMAIN_PATH"
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
DEFAULT_DOMAINS_PATH = "/Accounts/{auth_id}/Domains"
DEFAULT_DOMAIN_PATH = "/Accounts/{auth_id}/Domains/{domain_id}"
DEFAULT_APPLICATIONS_PATH = "/Accounts/{auth_id}/Applications"
DEFAULT_APPLICATION_PATH = "/Accounts/{auth_id}/Applications/{application_sid}"


@dataclass
class SessionConfig:
    auth_id: str | None = None
    auth_secret: str | None = None

    def set_credentials(self, auth_id: str, auth_secret: str) -> None:
        self.auth_id = auth_id
        self.auth_secret = auth_secret


SESSION = SessionConfig()


def env_or_default(env_name: str, default: str) -> str:
    value = os.getenv(env_name)
    return value.strip() if value else default


def get_base_url() -> str:
    return os.getenv("SIPRTC_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def resolve_auth(
    auth_id: str | None,
    auth_secret: str | None,
) -> tuple[str, str]:
    resolved_id = auth_id or SESSION.auth_id or os.getenv(ENV_AUTH_ID)
    resolved_secret = auth_secret or SESSION.auth_secret or os.getenv(ENV_AUTH_SECRET)
    if not resolved_id or not resolved_secret:
        raise ValueError(
            "Missing Siprtc credentials. Provide auth_id and auth_secret, "
            "call siprtc.set_credentials, or set SIPRTC_AUTH_ID and SIPRTC_AUTH_SECRET."
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


def domains_path() -> str:
    return env_or_default(ENV_DOMAINS_PATH, DEFAULT_DOMAINS_PATH)


def domain_path() -> str:
    return env_or_default(ENV_DOMAIN_PATH, DEFAULT_DOMAIN_PATH)


def applications_path() -> str:
    return env_or_default(ENV_APPLICATIONS_PATH, DEFAULT_APPLICATIONS_PATH)


def application_path() -> str:
    return env_or_default(ENV_APPLICATION_PATH, DEFAULT_APPLICATION_PATH)
