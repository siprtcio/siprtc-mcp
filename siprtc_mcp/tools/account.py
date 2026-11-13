"""The account itself: balance, profile, settings, client tokens, API-credential status, sub-accounts."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api

TENANTS = ACCOUNT + "/Tenants"
TENANT = TENANTS + "/{tenant_auth_id}"


_SETTING_KEYS = {
    "theme",
    "language",
    "incoming_domain",
    "incoming_email",
    "outgoing_domain",
    "outgoing_email",
    "default_fax_did",
}


def register(mcp, client_factory):
    @mcp.tool(name="siprtc.get_balance", description="Show the account's prepaid balance (USD).")
    def get_balance() -> Any:
        return api(client_factory, "GET", ACCOUNT + "/Balance")

    @mcp.tool(name="siprtc.get_profile", description="Show the account owner's profile (name, email, phone, address).")
    def get_profile() -> Any:
        return api(client_factory, "GET", ACCOUNT + "/Profile")

    @mcp.tool(
        name="siprtc.update_profile",
        description="Update the account owner's profile details. Only the fields you pass change.",
    )
    def update_profile(
        first: str | None = None,
        last: str | None = None,
        phone1: str | None = None,
        address: str | None = None,
        city: str | None = None,
        country: str | None = None,
        postal_code: str | None = None,
        bio: str | None = None,
    ) -> Any:
        changes = {
            "first": first,
            "last": last,
            "phone1": phone1,
            "address": address,
            "city": city,
            "country": country,
            "postal_code": postal_code,
            "bio": bio,
        }
        changes = {key: value for key, value in changes.items() if value is not None}
        if not changes:
            raise ToolError("Pass at least one field to change.")
        current = api(client_factory, "GET", ACCOUNT + "/Profile")
        body = {
            key: value
            for key, value in (current if isinstance(current, dict) else {}).items()
            if key
            in {"first", "last", "email", "phone1", "address", "bio", "city", "country", "postal_code", "username"}
        }
        body.update(changes)
        return api(client_factory, "PUT", ACCOUNT + "/Profile", json=body)

    @mcp.tool(
        name="siprtc.get_account_settings",
        description="Show account settings: theme, language, email domains for fax-to-email, default fax number.",
    )
    def get_account_settings() -> Any:
        return api(client_factory, "GET", ACCOUNT + "/ProfileSetting")

    @mcp.tool(
        name="siprtc.update_account_settings",
        description=(
            "Change account settings: theme, language, the email domains and addresses used for "
            "fax-to-email and email-to-fax, and the default fax number. Only the fields you pass change."
        ),
    )
    def update_account_settings(
        theme: str | None = None,
        language: str | None = None,
        incoming_domain: str | None = None,
        incoming_email: str | None = None,
        outgoing_domain: str | None = None,
        outgoing_email: str | None = None,
        default_fax_number: str | None = None,
    ) -> Any:
        changes = {
            "theme": theme,
            "language": language,
            "incoming_domain": incoming_domain,
            "incoming_email": incoming_email,
            "outgoing_domain": outgoing_domain,
            "outgoing_email": outgoing_email,
            "default_fax_did": default_fax_number,
        }
        changes = {key: value for key, value in changes.items() if value is not None}
        if not changes:
            raise ToolError("Pass at least one setting to change.")
        current = api(client_factory, "GET", ACCOUNT + "/ProfileSetting")
        settings = current.get("settings") if isinstance(current, dict) else None
        body = {key: value for key, value in (settings or {}).items() if key in _SETTING_KEYS}
        body.update(changes)
        return api(client_factory, "PUT", ACCOUNT + "/ProfileSetting", json=body)

    @mcp.tool(
        name="siprtc.get_api_credentials",
        description=(
            "Show the account's API credentials status: the Auth ID and only a hint of each secret, "
            "with when it was last rotated. Secrets are never returned by this server."
        ),
    )
    def get_api_credentials() -> Any:
        return api(client_factory, "GET", ACCOUNT + "/ApiCredentials")

    @mcp.tool(name="siprtc.list_client_tokens", description="List client tokens issued for SDK / WebRTC clients.")
    def list_client_tokens(page: int | None = None, limit: int | None = None) -> Any:
        return api(
            client_factory,
            "GET",
            ACCOUNT + "/ClientToken",
            params={"page": page, "limit": limit},
            empty_as="client_tokens",
        )

    @mcp.tool(
        name="siprtc.create_client_token",
        description="Issue a client token (valid 7 days) for an SDK or WebRTC client. The response holds the token itself.",
    )
    def create_client_token(name: str) -> Any:
        return api(client_factory, "POST", ACCOUNT + "/ClientToken", json={"name": name})

    @mcp.tool(name="siprtc.delete_client_token", description="Revoke a client token by id.")
    def delete_client_token(client_id: str) -> Any:
        return api(client_factory, "DELETE", ACCOUNT + "/ClientToken/{client_id}", client_id=client_id)

    # --- sub-accounts (users under this account: agents, supervisors, members) ---------------
    @mcp.tool(
        name="siprtc.list_sub_accounts",
        description="List the users under this account (agents, supervisors, members), filterable by name, email, type or status.",
    )
    def list_sub_accounts(
        name: str | None = None,
        email: str | None = None,
        type: str | None = None,
        status: str | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = {"name": name, "email": email, "type": type, "status": status, "page": page, "limit": limit}
        return api(client_factory, "GET", TENANTS, params=params)

    @mcp.tool(name="siprtc.get_sub_account", description="Fetch one user under this account by Auth ID.")
    def get_sub_account(tenant_auth_id: str) -> Any:
        # GET /Tenants/{id} is for vendor accounts; the list's auth_id filter works for everyone.
        found = api(client_factory, "GET", TENANTS, params={"auth_id": tenant_auth_id, "limit": 5})
        users = found.get("data") if isinstance(found, dict) else None
        match = [user for user in users or [] if user.get("auth_id") == tenant_auth_id]
        if not match:
            raise ToolError(f"No user {tenant_auth_id} under this account.")
        return match[0]

    @mcp.tool(
        name="siprtc.create_sub_account",
        description=(
            "Create a user under this account (e.g. type agent or supervisor) with a sign-in. Agent "
            "and supervisor seats are limited by the account's plan. time_zone is IANA, e.g. Asia/Kolkata."
        ),
    )
    def create_sub_account(
        first: str,
        last: str,
        email: str,
        phone1: str,
        username: str,
        password: str,
        type: Literal["agent", "supervisor", "member"],
        role: list[str],
        time_zone: str,
    ) -> Any:
        body = {
            "first": first,
            "last": last,
            "email": email,
            "phone1": phone1,
            "username": username,
            "password": password,
            "type": type,
            "role": role,
            "time_zone": time_zone,
        }
        return api(client_factory, "POST", TENANTS, json=body)

    @mcp.tool(
        name="siprtc.set_sub_account_status",
        description="Disable (disabled=true) or re-enable a user under this account. A disabled user cannot sign in.",
    )
    def set_sub_account_status(tenant_auth_id: str, disabled: bool) -> Any:
        return api(
            client_factory, "PATCH", TENANT + "/Status", json={"is_disabled": disabled}, tenant_auth_id=tenant_auth_id
        )

    @mcp.tool(
        name="siprtc.delete_sub_account",
        description="Schedule a user under this account for deletion (removes their sign-in and data).",
    )
    def delete_sub_account(tenant_auth_id: str) -> Any:
        return api(client_factory, "POST", TENANTS + "/Delete", json={"tenant_id": tenant_auth_id, "is_deleted": True})

    # --- vendor (reseller) accounts ---------------------------------------------------------
    @mcp.tool(
        name="siprtc.get_customer_balance",
        description="Vendor accounts only: show a customer account's balance.",
    )
    def get_customer_balance(customer_auth_id: str) -> Any:
        return api(client_factory, "GET", ACCOUNT + "/Balances/{customer}", customer=customer_auth_id)

    @mcp.tool(
        name="siprtc.recharge_customer_balance",
        description="Vendor accounts only: add credit to (or, with a negative amount, debit) a customer account's balance.",
    )
    def recharge_customer_balance(customer_auth_id: str, amount: float) -> Any:
        return api(
            client_factory,
            "PATCH",
            ACCOUNT + "/Balances/{customer}",
            json={"balance": amount},
            customer=customer_auth_id,
        )

    @mcp.tool(
        name="siprtc.list_inventory_numbers",
        description="Vendor accounts only: list the vendor's phone number inventory.",
    )
    def list_inventory_numbers(page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", ACCOUNT + "/Vendors/PhoneNumbers", params={"page": page, "limit": limit})

    @mcp.tool(
        name="siprtc.add_inventory_number",
        description=(
            "Vendor accounts only: add a number to the inventory customers can buy from. type: "
            "Local/Mobile/TollFree; pulses in seconds; mrc/nrc are monthly/setup charges, rps the per-second rate."
        ),
    )
    def add_inventory_number(
        phone_number: str,
        country_code: str,
        country_iso: str,
        type: str,
        initial_pulse: int,
        sub_pulse: int,
        capability: str | None = None,
        mrc: float | None = None,
        nrc: float | None = None,
        rps: float | None = None,
    ) -> Any:
        body = {
            "phone_number": phone_number,
            "country_code": country_code,
            "country_iso": country_iso,
            "type": type,
            "initial_pulse": initial_pulse,
            "sub_pulse": sub_pulse,
            "capability": capability,
            "mrc": mrc,
            "nrc": nrc,
            "rps": rps,
        }
        return api(client_factory, "POST", ACCOUNT + "/Vendors/PhoneNumbers", json=body)
