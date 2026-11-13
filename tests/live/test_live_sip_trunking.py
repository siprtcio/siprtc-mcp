"""Live checks for the SIP trunking (BYOC) tools: a trunk with every kind of resource attached, built,
changed, read back and torn down again. Uses RFC 5737 addresses and .invalid hostnames only."""

from __future__ import annotations

import os

import pytest

from .helpers import RUN, client, find, items, ok, quietly

pytestmark = [pytest.mark.live, pytest.mark.skipif(not os.getenv("SIPRTC_AUTH_ID"), reason="needs SIPRTC_* env")]

# A number that is not on the platform: adding it to a trunk must not attach anything. Real numbers are
# left alone because putting one on a trunk reroutes its inbound calls.
UNKNOWN_NUMBER = "+442079460999"


def _ids(rows: list, key: str = "id") -> set:
    return {row.get(key) for row in rows if isinstance(row, dict)}


async def test_sip_trunk_lifecycle():
    name = RUN + "trk"
    made: dict[str, str] = {}
    async with client() as c:
        try:
            # --- build ---------------------------------------------------------------------
            created = await ok(c, "create_sip_trunk", name=name)
            made["trunk"] = trunk = find(created, "id")
            assert trunk, created

            cred_list = await ok(c, "create_sip_trunk_credential_list", name=name + "cl")
            made["cred_list"] = cl_id = cred_list["id"]

            cred = await ok(
                c,
                "create_sip_trunk_auth_credential",
                friendly_name=name + "ac",
                username=name + "u",
                password="Mcp-e2e-Pass-1",
                credential_list_ids=[cl_id],
            )
            made["cred"] = cred_id = cred["id"]
            assert cred["password"] == "[redacted]"

            acl = await ok(c, "create_sip_trunk_ip_acl", name=name + "acl")
            made["acl"] = acl_id = acl["ip_acl_id"]

            addr = await ok(c, "create_sip_trunk_ip_address", cidr="203.0.113.10", ip_acl_ids=[acl_id])
            made["addr"] = addr_id = addr["id"]

            term = await ok(
                c,
                "create_sip_trunk_termination_uri",
                trunk_id=trunk,
                sip_domain=name + ".example.invalid",
                credential_list_ids=[cl_id],
                ip_acl_ids=[acl_id],
            )
            made["term"] = term_id = term["id"]

            orig = await ok(
                c,
                "create_sip_trunk_origination_uri",
                trunk_id=trunk,
                sip_uri="sip:pbx.example.invalid:5060",
                priority=10,
                enabled=True,
            )
            made["orig"] = orig_id = orig["id"]

            # --- read back -----------------------------------------------------------------
            listed = await ok(c, "list_sip_trunks", name=name)
            assert trunk in _ids(items(listed, "trunks"))
            with_uris = await ok(c, "list_sip_trunks", include_uris=True, name=name)
            row = next(t for t in items(with_uris, "trunks") if t["id"] == trunk)
            assert row["termination_uris"] == name + ".example.invalid"

            got = await ok(c, "get_sip_trunk", trunk_id=trunk)
            assert got["name"] == name and got["status"] == "active"
            assert got["origination_uris"][0]["uri"] == "sip:pbx.example.invalid:5060"

            assert cl_id in _ids(items(await ok(c, "list_sip_trunk_credential_lists", name=name), "credentiallist"))
            got_cl = await ok(c, "get_sip_trunk_credential_list", credential_list_id=cl_id)
            assert got_cl["auth_credential_names"] == [name + "u"]

            in_list = await ok(c, "list_sip_trunk_auth_credentials", credential_list_id=cl_id)
            assert cred_id in _ids(items(in_list, "trunkAuthCredential"))
            got_cred = await ok(c, "get_sip_trunk_auth_credential", auth_credential_id=cred_id)
            assert find(got_cred, "username") == name + "u" and find(got_cred, "password") == "[redacted]"

            assert acl_id in _ids(items(await ok(c, "list_sip_trunk_ip_acls", name=name), "ipacllist"))
            got_acl = await ok(c, "get_sip_trunk_ip_acl", ip_acl_id=acl_id)
            assert [a["cidr"] for a in got_acl["ip_addresses"]] == ["203.0.113.10"]

            in_acl = await ok(c, "list_sip_trunk_ip_addresses", ip_acl_id=acl_id)
            assert addr_id in _ids(items(in_acl, "ipacllist"))
            assert find(await ok(c, "get_sip_trunk_ip_address", ip_address_id=addr_id), "cidr") == "203.0.113.10"

            terms = await ok(c, "list_sip_trunk_termination_uris", trunk_id=trunk)
            assert term_id in _ids(items(terms, "termination"))
            got_term = await ok(c, "get_sip_trunk_termination_uri", trunk_id=trunk, termination_uri_id=term_id)
            assert find(got_term, "sip_domain") == name + ".example.invalid"

            origs = await ok(c, "list_sip_trunk_origination_uris", trunk_id=trunk)
            assert orig_id in _ids(items(origs, "originationUris"))
            got_orig = await ok(c, "get_sip_trunk_origination_uri", trunk_id=trunk, origination_uri_id=orig_id)
            assert find(got_orig, "priority") == "10"

            # --- change --------------------------------------------------------------------
            await ok(c, "update_sip_trunk", trunk_id=trunk, status="inactive")
            got = await ok(c, "get_sip_trunk", trunk_id=trunk)
            assert got["status"] == "inactive" and got["name"] == name  # name kept

            await ok(c, "update_sip_trunk_credential_list", credential_list_id=cl_id, name=name + "cl2")
            got_cl = await ok(c, "get_sip_trunk_credential_list", credential_list_id=cl_id)
            assert got_cl["name"] == name + "cl2" and got_cl["auth_credential_names"] == [name + "u"]  # members kept

            await ok(c, "update_sip_trunk_auth_credential", auth_credential_id=cred_id, password="Mcp-e2e-Pass-2")
            got_cred = await ok(c, "get_sip_trunk_auth_credential", auth_credential_id=cred_id)
            assert find(got_cred, "friendly_name") == name + "ac" and find(got_cred, "username") == name + "u"

            await ok(c, "update_sip_trunk_ip_acl", ip_acl_id=acl_id, name=name + "acl2")
            got_acl = await ok(c, "get_sip_trunk_ip_acl", ip_acl_id=acl_id)
            assert got_acl["ip_acl_name"] == name + "acl2"
            assert [a["cidr"] for a in got_acl["ip_addresses"]] == ["203.0.113.10"]  # members kept

            await ok(c, "update_sip_trunk_ip_address", ip_address_id=addr_id, cidr="203.0.113.11")
            assert find(await ok(c, "get_sip_trunk_ip_address", ip_address_id=addr_id), "cidr") == "203.0.113.11"
            assert addr_id in _ids(items(await ok(c, "list_sip_trunk_ip_addresses", ip_acl_id=acl_id), "ipacllist"))

            await ok(
                c,
                "update_sip_trunk_termination_uri",
                trunk_id=trunk,
                termination_uri_id=term_id,
                sip_domain=name + "2.example.invalid",
            )
            got_term = await ok(c, "get_sip_trunk_termination_uri", trunk_id=trunk, termination_uri_id=term_id)
            assert find(got_term, "sip_domain") == name + "2.example.invalid"
            assert acl_id in find(got_term, "ipaccesscontrollist_ids")  # lists kept

            await ok(c, "update_sip_trunk_origination_uri", trunk_id=trunk, origination_uri_id=orig_id, enabled=False)
            got_orig = await ok(c, "get_sip_trunk_origination_uri", trunk_id=trunk, origination_uri_id=orig_id)
            got_orig = got_orig.get("result", got_orig)
            assert got_orig["status"] is False
            assert got_orig["sip_uri"] == "sip:pbx.example.invalid:5060" and got_orig["priority"] == "10"  # kept

            # --- numbers: read only, plus a number nobody owns ----------------------------
            numbers = await ok(c, "list_sip_trunk_phone_numbers", trunk_id=trunk)
            assert not items(numbers, "trunkphonenumber")
            await quietly(c, "add_sip_trunk_phone_numbers", trunk_id=trunk, phone_numbers=[UNKNOWN_NUMBER])
            numbers = await ok(c, "list_sip_trunk_phone_numbers", trunk_id=trunk)
            assert not items(numbers, "trunkphonenumber"), "a number that is not on the platform was attached"

            # --- tear down ----------------------------------------------------------------
            await ok(c, "delete_sip_trunk_origination_uri", trunk_id=trunk, origination_uri_id=made.pop("orig"))
            await ok(c, "delete_sip_trunk_termination_uri", trunk_id=trunk, termination_uri_id=made.pop("term"))
            await ok(c, "delete_sip_trunk_ip_address", ip_address_id=made.pop("addr"))
            await ok(c, "delete_sip_trunk_ip_acl", ip_acl_id=made.pop("acl"))
            await ok(c, "delete_sip_trunk_auth_credential", auth_credential_id=made.pop("cred"))
            await ok(c, "delete_sip_trunk_credential_list", credential_list_id=made.pop("cred_list"))
            await ok(c, "delete_sip_trunk", trunk_id=made.pop("trunk"))
            assert trunk not in _ids(items(await ok(c, "list_sip_trunks", name=name), "trunks"))
        finally:
            trunk = made.get("trunk")
            if "orig" in made:
                await quietly(c, "delete_sip_trunk_origination_uri", trunk_id=trunk, origination_uri_id=made["orig"])
            if "term" in made:
                await quietly(c, "delete_sip_trunk_termination_uri", trunk_id=trunk, termination_uri_id=made["term"])
            if "addr" in made:
                await quietly(c, "delete_sip_trunk_ip_address", ip_address_id=made["addr"])
            if "acl" in made:
                await quietly(c, "delete_sip_trunk_ip_acl", ip_acl_id=made["acl"])
            if "cred" in made:
                await quietly(c, "delete_sip_trunk_auth_credential", auth_credential_id=made["cred"])
            if "cred_list" in made:
                await quietly(c, "delete_sip_trunk_credential_list", credential_list_id=made["cred_list"])
            if trunk:
                await quietly(c, "delete_sip_trunk", trunk_id=trunk)
