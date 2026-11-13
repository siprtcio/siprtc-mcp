"""SIP trunking (BYOC): trunks to your own carrier or PBX, and the credential lists, IP access lists,
termination URIs, origination URIs and phone numbers attached to them (``/SipTrunk``)."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp.exceptions import ToolError

from ._common import ACCOUNT, api, digits

BASE = ACCOUNT + "/SipTrunk"
TRUNK = BASE + "/{trunk_id}"
TRUNK_GET = ACCOUNT + "/SipTrunks/{trunk_id}"  # the API reads one trunk at the plural path
CRED_LISTS = BASE + "/CredentialList"
CRED_LIST = CRED_LISTS + "/{credential_list_id}"
AUTH_CREDS = BASE + "/AuthCredentials"
AUTH_CRED = AUTH_CREDS + "/{auth_credential_id}"
ACLS = BASE + "/IPAcl"
ACL = ACLS + "/{ip_acl_id}"
ADDRS = BASE + "/IPAclIPAddrs"
ADDR = ADDRS + "/{ip_address_id}"
TERMINATIONS = TRUNK + "/TerminationUri"
TERMINATION = TERMINATIONS + "/{termination_uri_id}"
ORIGINATIONS = TRUNK + "/OriginationUri"
ORIGINATION = ORIGINATIONS + "/{origination_uri_id}"
NUMBERS = TRUNK + "/PhoneNumber"
NUMBER = NUMBERS + "/{trunk_number_id}"

Status = Literal["active", "inactive"]


def _paging(page: int | None, limit: int | None, **filters: Any) -> dict:
    return {"page": page, "limit": limit, **filters}


def _record(answer: Any) -> dict:
    """GET-by-id answers are the record itself, or wrapped in ``result`` or ``data``."""
    if isinstance(answer, dict):
        for key in ("result", "data"):
            if isinstance(answer.get(key), dict):
                return answer[key]
        return answer
    return {}


def _pick(value: Any, current: dict, key: str) -> Any:
    return value if value is not None else current.get(key)


def _priority(priority: int | None) -> str | None:
    return None if priority is None else str(priority)


def register(mcp, client_factory):
    # --- trunks -----------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunks",
        description=(
            "List SIP trunks (bring-your-own-carrier). With include_uris=true each trunk also lists its "
            "termination and origination URIs. Filter by name or status; paged with page and limit."
        ),
    )
    def list_sip_trunks(
        include_uris: bool = False,
        name: str | None = None,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        path = BASE + "/WithUris" if include_uris else BASE
        return api(client_factory, "GET", path, params=_paging(page, limit, name=name, status=status))

    @mcp.tool(name="siprtc.get_sip_trunk", description="Fetch one SIP trunk by trunk_id.")
    def get_sip_trunk(trunk_id: str) -> Any:
        return api(client_factory, "GET", TRUNK_GET, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk",
        description=(
            "Create a SIP trunk. name must be unique on the account. phone_numbers (optional) are numbers "
            "you own to route over this trunk; they must not already be on another trunk. Add termination "
            "and origination URIs afterwards."
        ),
    )
    def create_sip_trunk(name: str, phone_numbers: list[str] | None = None) -> Any:
        body = {"name": name, "phone_number": [digits(n) for n in phone_numbers] if phone_numbers else None}
        return api(client_factory, "POST", BASE, json=body)

    @mcp.tool(
        name="siprtc.update_sip_trunk",
        description="Rename a SIP trunk, set it active or inactive, or turn call recording on it on or off.",
    )
    def update_sip_trunk(
        trunk_id: str,
        name: str | None = None,
        status: Status | None = None,
        is_recording: bool | None = None,
    ) -> Any:
        if name is None and status is None and is_recording is None:
            raise ToolError("Pass at least one change: name, status or is_recording.")
        # The API overwrites name, status and is_recording together, so start from the current values.
        current = _record(api(client_factory, "GET", TRUNK_GET, trunk_id=trunk_id))
        body = {
            "name": _pick(name, current, "name"),
            "status": _pick(status, current, "status"),
            "is_recording": is_recording if is_recording is not None else bool(current.get("is_recording")),
        }
        return api(client_factory, "PUT", TRUNK, json=body, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.delete_sip_trunk",
        description="Delete a SIP trunk by trunk_id. Calls stop routing over it.",
    )
    def delete_sip_trunk(trunk_id: str) -> Any:
        return api(client_factory, "DELETE", TRUNK, trunk_id=trunk_id)

    # --- credential lists -----------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_credential_lists",
        description="List SIP trunk credential lists (groups of username/password credentials). Paged.",
    )
    def list_sip_trunk_credential_lists(
        name: str | None = None,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        return api(client_factory, "GET", CRED_LISTS, params=_paging(page, limit, name=name, status=status))

    @mcp.tool(name="siprtc.get_sip_trunk_credential_list", description="Fetch one credential list by its id.")
    def get_sip_trunk_credential_list(credential_list_id: str) -> Any:
        return api(client_factory, "GET", CRED_LIST, credential_list_id=credential_list_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk_credential_list",
        description=(
            "Create a credential list for SIP trunk authentication. usernames (optional) adds existing "
            "auth credentials, by username, to the new list."
        ),
    )
    def create_sip_trunk_credential_list(name: str, usernames: list[str] | None = None) -> Any:
        return api(client_factory, "POST", CRED_LISTS, json={"name": name, "username": usernames})

    @mcp.tool(
        name="siprtc.update_sip_trunk_credential_list",
        description=(
            "Rename a credential list or set it active/inactive. usernames (optional) replaces which auth "
            "credentials are in it; leave it out to keep the current ones."
        ),
    )
    def update_sip_trunk_credential_list(
        credential_list_id: str,
        name: str | None = None,
        status: Status | None = None,
        usernames: list[str] | None = None,
    ) -> Any:
        if name is None and status is None and usernames is None:
            raise ToolError("Pass at least one change: name, status or usernames.")
        # The API overwrites name and status and replaces the members with update_username, so start
        # from the current list.
        current = _record(api(client_factory, "GET", CRED_LIST, credential_list_id=credential_list_id))
        body = {
            "name": _pick(name, current, "name"),
            "status": _pick(status, current, "status"),
            "update_username": usernames if usernames is not None else list(current.get("auth_credential_names") or []),
        }
        return api(client_factory, "PUT", CRED_LIST, json=body, credential_list_id=credential_list_id)

    @mcp.tool(
        name="siprtc.delete_sip_trunk_credential_list",
        description=(
            "Delete a credential list by its id. Delete or move its auth credentials first; ones left in no "
            "list can no longer be read or deleted."
        ),
    )
    def delete_sip_trunk_credential_list(credential_list_id: str) -> Any:
        return api(client_factory, "DELETE", CRED_LIST, credential_list_id=credential_list_id)

    # --- auth credentials -------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_auth_credentials",
        description=(
            "List SIP trunk auth credentials (username/password pairs). Pass credential_list_id to list only "
            "the ones in that credential list. Passwords are never returned. Paged."
        ),
    )
    def list_sip_trunk_auth_credentials(
        credential_list_id: str | None = None,
        name: str | None = None,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = _paging(page, limit, name=name, status=status)
        if credential_list_id:
            return api(
                client_factory,
                "GET",
                CRED_LIST + "/AuthCredentials",
                params=params,
                credential_list_id=credential_list_id,
            )
        return api(client_factory, "GET", AUTH_CREDS, params=params)

    @mcp.tool(name="siprtc.get_sip_trunk_auth_credential", description="Fetch one auth credential by its id.")
    def get_sip_trunk_auth_credential(auth_credential_id: str) -> Any:
        return api(client_factory, "GET", AUTH_CRED, auth_credential_id=auth_credential_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk_auth_credential",
        description=(
            "Create a username/password credential that a carrier or PBX uses to authenticate on a SIP "
            "trunk. friendly_name must be unique. credential_list_ids puts it in those credential lists."
        ),
    )
    def create_sip_trunk_auth_credential(
        friendly_name: str,
        username: str,
        password: str,
        credential_list_ids: list[str] | None = None,
    ) -> Any:
        body = {
            "friendly_name": friendly_name,
            "username": username,
            "password": password,
            "list_id": credential_list_ids,
        }
        return api(client_factory, "POST", AUTH_CREDS, json=body)

    @mcp.tool(
        name="siprtc.update_sip_trunk_auth_credential",
        description=(
            "Update an auth credential. The API rewrites the password on every update and never returns it, "
            "so password is required (send the current one to keep it). friendly_name and username default "
            "to their current values; credential_list_ids (optional) replaces which credential lists it is in."
        ),
    )
    def update_sip_trunk_auth_credential(
        auth_credential_id: str,
        password: str,
        friendly_name: str | None = None,
        username: str | None = None,
        credential_list_ids: list[str] | None = None,
    ) -> Any:
        current = _record(api(client_factory, "GET", AUTH_CRED, auth_credential_id=auth_credential_id))
        body = {
            "friendly_name": _pick(friendly_name, current, "friendly_name"),
            "username": _pick(username, current, "username"),
            "password": password,
            "update_list_id": credential_list_ids,
        }
        return api(client_factory, "PUT", AUTH_CRED, json=body, auth_credential_id=auth_credential_id)

    @mcp.tool(
        name="siprtc.delete_sip_trunk_auth_credential",
        description=(
            "Delete an auth credential by its id. Delete it before the credential lists it is in: the "
            "platform fails (HTTP 500) on a credential that belongs to no list."
        ),
    )
    def delete_sip_trunk_auth_credential(auth_credential_id: str) -> Any:
        return api(client_factory, "DELETE", AUTH_CRED, auth_credential_id=auth_credential_id)

    # --- IP access control lists ------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_ip_acls",
        description="List SIP trunk IP access control lists (groups of allowed source IPs/CIDRs). Paged.",
    )
    def list_sip_trunk_ip_acls(
        name: str | None = None,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        return api(client_factory, "GET", ACLS, params=_paging(page, limit, name=name, status=status))

    @mcp.tool(name="siprtc.get_sip_trunk_ip_acl", description="Fetch one IP access control list by its id.")
    def get_sip_trunk_ip_acl(ip_acl_id: str) -> Any:
        return api(client_factory, "GET", ACL, ip_acl_id=ip_acl_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk_ip_acl",
        description=(
            "Create an IP access control list. name must be unique. cidrs (optional) adds existing IP "
            "addresses, by their CIDR, to the new list; create addresses with create_sip_trunk_ip_address."
        ),
    )
    def create_sip_trunk_ip_acl(name: str, cidrs: list[str] | None = None) -> Any:
        return api(client_factory, "POST", ACLS, json={"ip_acl_name": name, "cidr": cidrs})

    @mcp.tool(
        name="siprtc.update_sip_trunk_ip_acl",
        description=(
            "Rename an IP access control list. cidrs (optional) replaces which IP addresses are in it; leave "
            "it out to keep the current ones."
        ),
    )
    def update_sip_trunk_ip_acl(ip_acl_id: str, name: str | None = None, cidrs: list[str] | None = None) -> Any:
        if name is None and cidrs is None:
            raise ToolError("Pass at least one change: name or cidrs.")
        # The API drops every address not named in update_ipacl_list_id (which holds CIDRs, despite its
        # name), so start from the current members.
        current = _record(api(client_factory, "GET", ACL, ip_acl_id=ip_acl_id))
        if cidrs is None:
            cidrs = [a["cidr"] for a in current.get("ip_addresses") or [] if isinstance(a, dict) and a.get("cidr")]
        body = {"ip_acl_name": _pick(name, current, "ip_acl_name"), "update_ipacl_list_id": cidrs}
        return api(client_factory, "PUT", ACL, json=body, ip_acl_id=ip_acl_id)

    @mcp.tool(
        name="siprtc.delete_sip_trunk_ip_acl",
        description=(
            "Delete an IP access control list by its id. Delete or move its IP addresses first; ones left in "
            "no list can no longer be read or deleted."
        ),
    )
    def delete_sip_trunk_ip_acl(ip_acl_id: str) -> Any:
        return api(client_factory, "DELETE", ACL, ip_acl_id=ip_acl_id)

    # --- IP addresses -----------------------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_ip_addresses",
        description=(
            "List IP addresses (CIDRs) allowed on SIP trunks. Pass ip_acl_id to list only the ones in that "
            "IP access control list. Paged."
        ),
    )
    def list_sip_trunk_ip_addresses(
        ip_acl_id: str | None = None,
        cidr: str | None = None,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        # The per-list route (/IPAcl/{id}/IPAclIPAddrs) crashes on the platform; the flat list filters
        # by list with ``listid`` instead.
        params = _paging(page, limit, cidr=cidr, status=status, listid=ip_acl_id)
        return api(client_factory, "GET", ADDRS, params=params)

    @mcp.tool(name="siprtc.get_sip_trunk_ip_address", description="Fetch one allowed IP address by its id.")
    def get_sip_trunk_ip_address(ip_address_id: str) -> Any:
        return api(client_factory, "GET", ADDR, ip_address_id=ip_address_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk_ip_address",
        description=(
            "Allow a source IP address on SIP trunks and put it in the given IP access control lists "
            "(ip_acl_ids). cidr is a single IPv4 address such as 203.0.113.10; the API rejects /prefix ranges."
        ),
    )
    def create_sip_trunk_ip_address(cidr: str, ip_acl_ids: list[str] | None = None) -> Any:
        return api(client_factory, "POST", ADDRS, json={"cidr": cidr, "ip_acl_list_id": ip_acl_ids})

    @mcp.tool(
        name="siprtc.update_sip_trunk_ip_address",
        description=(
            "Change an allowed IP address (cidr, a single IPv4 address). ip_acl_ids (optional) replaces which "
            "IP access control lists it is in; leave it out to keep the current ones."
        ),
    )
    def update_sip_trunk_ip_address(
        ip_address_id: str,
        cidr: str | None = None,
        ip_acl_ids: list[str] | None = None,
    ) -> Any:
        if cidr is None and ip_acl_ids is None:
            raise ToolError("Pass at least one change: cidr or ip_acl_ids.")
        current = _record(api(client_factory, "GET", ADDR, ip_address_id=ip_address_id))
        body = {"cidr": _pick(cidr, current, "cidr"), "updated_ip_acl_list_id": ip_acl_ids}
        return api(client_factory, "PUT", ADDR, json=body, ip_address_id=ip_address_id)

    @mcp.tool(
        name="siprtc.delete_sip_trunk_ip_address",
        description=(
            "Delete an allowed IP address by its id. Delete it before the IP access lists it is in: the "
            "platform fails (HTTP 500) on an address that belongs to no list."
        ),
    )
    def delete_sip_trunk_ip_address(ip_address_id: str) -> Any:
        return api(client_factory, "DELETE", ADDR, ip_address_id=ip_address_id)

    # --- termination URIs (calls from your PBX/carrier into SIPRTC) -------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_termination_uris",
        description="List a trunk's termination URIs (the SIP domains your PBX sends calls to). Paged.",
    )
    def list_sip_trunk_termination_uris(
        trunk_id: str,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        return api(client_factory, "GET", TERMINATIONS, params=_paging(page, limit, status=status), trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.get_sip_trunk_termination_uri",
        description="Fetch one termination URI of a trunk.",
    )
    def get_sip_trunk_termination_uri(trunk_id: str, termination_uri_id: str) -> Any:
        return api(client_factory, "GET", TERMINATION, trunk_id=trunk_id, termination_uri_id=termination_uri_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk_termination_uri",
        description=(
            "Give a trunk a termination URI: sip_domain is the domain name your PBX or carrier sends calls "
            "to. Calls are accepted when they authenticate with a credential in credential_list_ids or come "
            "from an address in ip_acl_ids."
        ),
    )
    def create_sip_trunk_termination_uri(
        trunk_id: str,
        sip_domain: str,
        credential_list_ids: list[str] | None = None,
        ip_acl_ids: list[str] | None = None,
    ) -> Any:
        body = {
            "sip_domain": sip_domain,
            "authecredentiallist_ids": credential_list_ids,
            "ipaccesscontrollist_ids": ip_acl_ids,
        }
        return api(client_factory, "POST", TERMINATIONS, json=body, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.update_sip_trunk_termination_uri",
        description=(
            "Change a termination URI's sip_domain. credential_list_ids and ip_acl_ids (optional) replace which "
            "credential lists and IP access lists it accepts; leave them out to keep the current ones."
        ),
    )
    def update_sip_trunk_termination_uri(
        trunk_id: str,
        termination_uri_id: str,
        sip_domain: str | None = None,
        credential_list_ids: list[str] | None = None,
        ip_acl_ids: list[str] | None = None,
    ) -> Any:
        if sip_domain is None and credential_list_ids is None and ip_acl_ids is None:
            raise ToolError("Pass at least one change: sip_domain, credential_list_ids or ip_acl_ids.")
        if sip_domain is None:
            current = _record(
                api(client_factory, "GET", TERMINATION, trunk_id=trunk_id, termination_uri_id=termination_uri_id)
            )
            sip_domain = current.get("sip_domain")
        body = {
            "sip_domain": sip_domain,
            "update_authecredentiallist_ids": credential_list_ids,
            "update_ipaccesscontrollist_ids": ip_acl_ids,
        }
        return api(
            client_factory,
            "PUT",
            TERMINATION,
            json=body,
            trunk_id=trunk_id,
            termination_uri_id=termination_uri_id,
        )

    @mcp.tool(
        name="siprtc.delete_sip_trunk_termination_uri",
        description="Delete a termination URI from a trunk.",
    )
    def delete_sip_trunk_termination_uri(trunk_id: str, termination_uri_id: str) -> Any:
        return api(client_factory, "DELETE", TERMINATION, trunk_id=trunk_id, termination_uri_id=termination_uri_id)

    # --- origination URIs (where SIPRTC sends calls for the trunk's numbers) ----------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_origination_uris",
        description="List a trunk's origination URIs (where SIPRTC sends inbound calls for its numbers). Paged.",
    )
    def list_sip_trunk_origination_uris(trunk_id: str, page: int | None = None, limit: int | None = None) -> Any:
        return api(client_factory, "GET", ORIGINATIONS, params=_paging(page, limit), trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.get_sip_trunk_origination_uri",
        description="Fetch one origination URI of a trunk.",
    )
    def get_sip_trunk_origination_uri(trunk_id: str, origination_uri_id: str) -> Any:
        return api(client_factory, "GET", ORIGINATION, trunk_id=trunk_id, origination_uri_id=origination_uri_id)

    @mcp.tool(
        name="siprtc.create_sip_trunk_origination_uri",
        description=(
            "Add an origination URI to a trunk: sip_uri (e.g. sip:pbx.example.com:5060) receives calls for "
            "the trunk's numbers. Lower priority numbers are tried first."
        ),
    )
    def create_sip_trunk_origination_uri(
        trunk_id: str,
        sip_uri: str,
        priority: int | None = None,
        enabled: bool | None = None,
    ) -> Any:
        body = {"sip_uri": sip_uri, "priority": _priority(priority), "status": enabled}
        return api(client_factory, "POST", ORIGINATIONS, json=body, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.update_sip_trunk_origination_uri",
        description=(
            "Change an origination URI's sip_uri or priority, or turn it on or off (enabled). Anything left "
            "out keeps its current value."
        ),
    )
    def update_sip_trunk_origination_uri(
        trunk_id: str,
        origination_uri_id: str,
        sip_uri: str | None = None,
        priority: int | None = None,
        enabled: bool | None = None,
    ) -> Any:
        if sip_uri is None and priority is None and enabled is None:
            raise ToolError("Pass at least one change: sip_uri, priority or enabled.")
        # The API overwrites sip_uri, priority and status together, so start from the current values.
        current = _record(
            api(client_factory, "GET", ORIGINATION, trunk_id=trunk_id, origination_uri_id=origination_uri_id)
        )
        body = {
            "sip_uri": _pick(sip_uri, current, "sip_uri"),
            "priority": _priority(priority) if priority is not None else current.get("priority"),
            "status": _pick(enabled, current, "status"),
            "meta_data": current.get("meta_data"),
        }
        return api(
            client_factory,
            "PUT",
            ORIGINATION,
            json=body,
            trunk_id=trunk_id,
            origination_uri_id=origination_uri_id,
        )

    @mcp.tool(
        name="siprtc.delete_sip_trunk_origination_uri",
        description="Delete an origination URI from a trunk.",
    )
    def delete_sip_trunk_origination_uri(trunk_id: str, origination_uri_id: str) -> Any:
        return api(client_factory, "DELETE", ORIGINATION, trunk_id=trunk_id, origination_uri_id=origination_uri_id)

    # --- phone numbers on a trunk -----------------------------------------------------------------
    @mcp.tool(
        name="siprtc.list_sip_trunk_phone_numbers",
        description="List the phone numbers routed over a trunk. Paged.",
    )
    def list_sip_trunk_phone_numbers(
        trunk_id: str,
        phone_number: str | None = None,
        status: Status | None = None,
        page: int | None = None,
        limit: int | None = None,
    ) -> Any:
        params = _paging(page, limit, phonenumber=digits(phone_number) if phone_number else None, status=status)
        return api(client_factory, "GET", NUMBERS, params=params, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.get_sip_trunk_phone_number",
        description="Fetch one phone number on a trunk by its trunk_number_id (from list_sip_trunk_phone_numbers).",
    )
    def get_sip_trunk_phone_number(trunk_id: str, trunk_number_id: str) -> Any:
        return api(client_factory, "GET", NUMBER, trunk_id=trunk_id, trunk_number_id=trunk_number_id)

    @mcp.tool(
        name="siprtc.add_sip_trunk_phone_numbers",
        description=(
            "Route numbers you own over a trunk: their inbound calls go to the trunk's origination URIs. "
            "A number can be on one trunk only."
        ),
    )
    def add_sip_trunk_phone_numbers(trunk_id: str, phone_numbers: list[str]) -> Any:
        if not phone_numbers:
            raise ToolError("Pass at least one phone number.")
        body = {"phone_number": [digits(n) for n in phone_numbers]}
        return api(client_factory, "POST", NUMBERS, json=body, trunk_id=trunk_id)

    @mcp.tool(
        name="siprtc.update_sip_trunk_phone_number",
        description="Set a phone number on a trunk active or inactive.",
    )
    def update_sip_trunk_phone_number(trunk_id: str, trunk_number_id: str, status: Status) -> Any:
        # The API validates the whole record, so send the stored number details back with the new status.
        current = _record(api(client_factory, "GET", NUMBER, trunk_id=trunk_id, trunk_number_id=trunk_number_id))
        body = {
            "phone_number": current.get("phone_number"),
            "type": current.get("type"),
            "country_code": current.get("country_code"),
            "country_iso": current.get("country_iso"),
            "status": status,
        }
        return api(client_factory, "PUT", NUMBER, json=body, trunk_id=trunk_id, trunk_number_id=trunk_number_id)

    @mcp.tool(
        name="siprtc.remove_sip_trunk_phone_number",
        description="Take a phone number off a trunk by its trunk_number_id.",
    )
    def remove_sip_trunk_phone_number(trunk_id: str, trunk_number_id: str) -> Any:
        return api(client_factory, "DELETE", NUMBER, trunk_id=trunk_id, trunk_number_id=trunk_number_id)
