"""Tenant PG18 infrastructure identifier loader for export scrubbing (`Story 31.5`)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from urllib.parse import urlsplit

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection


@dataclass(frozen=True, slots=True)
class TenantInfraIdentifiers:
    """Pre-loaded `frozenset` tenant identifiers for `O(1)` export leak detection."""

    tenant_uuids: frozenset[str] = field(default_factory=frozenset)
    tenant_emails: frozenset[str] = field(default_factory=frozenset)
    tenant_hosts: frozenset[str] = field(default_factory=frozenset)
    datasource_slots_by_ref: dict[str, dict[str, str]] = field(default_factory=dict)


def extract_host(raw_url: str) -> str:
    """Extract normalized lowercase hostname from a URI."""
    try:
        parsed = urlsplit(raw_url.strip())
        return (parsed.hostname or "").strip().lower()
    except ValueError:
        return ""


async def load_tenant_infra_identifiers_conn(conn: AsyncConnection) -> TenantInfraIdentifiers:
    """Load tenant UUIDs, emails, private URLs, and datasource slot hints in one pass."""
    uuids: set[str] = set()
    emails: set[str] = set()
    hosts: set[str] = set()
    ds_refs: dict[str, dict[str, str]] = {}

    allowed_priv = os.environ.get("ORCIA_LLM_ALLOWED_PRIVATE_HOSTS", "")
    for tok in allowed_priv.split(","):
        if tok.strip():
            hosts.add(tok.strip().lower())

    for tbl in (
        "workspaces",
        "org_units",
        "users",
        "enterprise_connectors",
        "workspace_datasources",
        "llm_model_endpoints",
    ):
        reg = (await conn.execute(sa.text(f"SELECT to_regclass('public.{tbl}')"))).scalar()
        if reg is None:
            continue
        if tbl in ("workspaces", "org_units"):
            for uid in (await conn.execute(sa.text(f"SELECT id::text FROM {tbl}"))).scalars():
                uuids.add(str(uid).lower())
        elif tbl == "users":
            for r in (await conn.execute(sa.text("SELECT id::text, email FROM users"))).fetchall():
                uuids.add(str(r[0]).lower())
                if r[1]:
                    emails.add(str(r[1]).strip().lower())
        elif tbl == "enterprise_connectors":
            for r in (
                await conn.execute(
                    sa.text("SELECT id::text, connector_kind, base_url FROM enterprise_connectors")
                )
            ).fetchall():
                uid = str(r[0]).lower()
                uuids.add(uid)
                ckind = str(r[1] or "connector").lower()
                slot_meta = {
                    "slot_key": f"connector_{ckind}",
                    "scheme": ckind,
                    "connector_kind": ckind,
                }
                ds_refs[uid] = slot_meta
                if r[2]:
                    h = extract_host(str(r[2]))
                    if h:
                        hosts.add(h)
                    ds_refs[str(r[2]).strip()] = slot_meta
        elif tbl == "workspace_datasources":
            for r in (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, alias, scheme, source_nature, uri "
                        "FROM workspace_datasources"
                    )
                )
            ).fetchall():
                uid = str(r[0]).lower()
                uuids.add(uid)
                alias = (
                    re.sub(r"[^a-z0-9_]+", "_", str(r[1] or "source").lower()).strip("_")
                    or "source"
                )
                slot_meta = {
                    "slot_key": alias,
                    "scheme": str(r[2] or "git").lower(),
                    "connector_kind": str(r[2] or "git").lower(),
                    "source_nature": str(r[3] or ""),
                }
                ds_refs[uid] = slot_meta
                if r[4]:
                    ds_refs[str(r[4]).strip()] = slot_meta
                    h = extract_host(str(r[4]))
                    if h:
                        hosts.add(h)
        elif tbl == "llm_model_endpoints":
            for r in (
                await conn.execute(
                    sa.text("SELECT id::text, endpoint_uri FROM llm_model_endpoints")
                )
            ).fetchall():
                uuids.add(str(r[0]).lower())
                if r[1]:
                    h = extract_host(str(r[1]))
                    if h:
                        hosts.add(h)

    return TenantInfraIdentifiers(
        tenant_uuids=frozenset(uuids),
        tenant_emails=frozenset(emails),
        tenant_hosts=frozenset(hosts),
        datasource_slots_by_ref=ds_refs,
    )


__all__ = [
    "TenantInfraIdentifiers",
    "extract_host",
    "load_tenant_infra_identifiers_conn",
]
