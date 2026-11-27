"""SQL materialization for pack DNA mechanisms, broker policies & audit (`Story 31.2`)."""

from __future__ import annotations

import json
import re
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection
from uuid_utils import uuid7

from orcia_core.packs.models import LoadedPackBundleV2

_SCHEME_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,31}$")


async def materialize_pack_mechanisms_and_policies(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    bundle: LoadedPackBundleV2,
) -> None:
    """Materialize `pack_dna_mechanisms` and `permission_broker_policies` inside transaction."""
    slug = bundle.manifest.slug.strip()
    kept_mechs: list[str] = []
    for mech in bundle.dna_mechanisms:
        kept_mechs.append(mech.mechanism_slug)
        await conn.execute(
            sa.text(
                """
                INSERT INTO pack_dna_mechanisms (
                    id, pack_bundle_id, mechanism_slug, name, starlark_source,
                    source_sha256, input_schema_jsonb, output_schema_jsonb,
                    passing_test_payload_jsonb, failing_test_payload_jsonb
                )
                VALUES (
                    CAST(:id AS uuid), CAST(:bid AS uuid), :mslug, :name, :src,
                    :sha, CAST(:in_s AS jsonb), CAST(:out_s AS jsonb),
                    CAST(:pass_p AS jsonb), CAST(:fail_p AS jsonb)
                )
                ON CONFLICT (pack_bundle_id, mechanism_slug) DO UPDATE SET
                    name = EXCLUDED.name, starlark_source = EXCLUDED.starlark_source,
                    source_sha256 = EXCLUDED.source_sha256,
                    input_schema_jsonb = EXCLUDED.input_schema_jsonb,
                    output_schema_jsonb = EXCLUDED.output_schema_jsonb,
                    passing_test_payload_jsonb = EXCLUDED.passing_test_payload_jsonb,
                    failing_test_payload_jsonb = EXCLUDED.failing_test_payload_jsonb
                """
            ),
            {
                "id": str(uuid7()),
                "bid": bundle_id,
                "mslug": mech.mechanism_slug,
                "name": mech.name,
                "src": mech.starlark_source,
                "sha": mech.source_sha256,
                "in_s": json.dumps(mech.input_schema, sort_keys=True),
                "out_s": json.dumps(mech.output_schema, sort_keys=True),
                "pass_p": json.dumps(mech.passing_test_payload or {}, sort_keys=True),
                "fail_p": json.dumps(mech.failing_test_payload or {}, sort_keys=True),
            },
        )
    await conn.execute(
        sa.text(
            "DELETE FROM pack_dna_mechanisms WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (mechanism_slug = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_mechs},
    )

    active_schemes: set[str] = set()
    if bundle.policies:
        scheme_rows = (
            await conn.execute(
                sa.text("SELECT scheme FROM connector_schemes WHERE is_active = TRUE")
            )
        ).all()
        active_schemes = {str(r[0]).strip().lower() for r in scheme_rows if r and r[0]}

    kept_policies: list[str] = []
    for pol in bundle.policies:
        pkey = f"{slug}:{pol.policy_key}"[:128]
        kept_policies.append(pkey)
        scheme = pol.connector_scheme.strip().lower()
        if active_schemes:
            if scheme not in active_schemes:
                scheme = "mcp" if "mcp" in active_schemes else sorted(active_schemes)[0]
        elif not _SCHEME_SLUG_RE.match(scheme):
            scheme = "mcp"
        await conn.execute(
            sa.text(
                "DELETE FROM permission_broker_policies WHERE pack_bundle_id = CAST(:bid AS uuid) "
                "AND uri_pattern = :up AND policy_key <> :pk"
            ),
            {"bid": bundle_id, "up": pol.uri_pattern, "pk": pkey},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO permission_broker_policies (
                    id, policy_key, uri_pattern, connector_scheme, required_role,
                    approver_team, request_url_template, sla_hours, procedure_markdown,
                    pack_bundle_id
                )
                VALUES (
                    CAST(:id AS uuid), :pk, :up, :scheme, :role, :team,
                    :tpl, :sla, :proc, CAST(:bid AS uuid)
                )
                ON CONFLICT (pack_bundle_id, policy_key)
                WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
                    uri_pattern = EXCLUDED.uri_pattern,
                    connector_scheme = EXCLUDED.connector_scheme,
                    required_role = EXCLUDED.required_role,
                    approver_team = EXCLUDED.approver_team,
                    sla_hours = EXCLUDED.sla_hours,
                    procedure_markdown = EXCLUDED.procedure_markdown
                """
            ),
            {
                "id": str(uuid7()),
                "pk": pkey,
                "up": pol.uri_pattern,
                "scheme": scheme,
                "role": pol.required_role[:128],
                "team": (pol.approver_team or "platform-ops")[:128],
                "tpl": str(pol.frontmatter.get("request_url_template") or pol.uri_pattern),
                "sla": max(1, int(pol.sla_hours)),
                "proc": pol.procedure_markdown,
                "bid": bundle_id,
            },
        )
    await conn.execute(
        sa.text(
            "DELETE FROM permission_broker_policies WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (policy_key = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_policies},
    )


async def append_pack_audit_event(
    conn: AsyncConnection,
    *,
    event_type: str,
    summary: str,
    scope_path: str,
    actor_id: str,
    actor_email: str | None,
    metadata: dict[str, Any],
    cas_references: list[str] | None = None,
    trace_id: str | None = None,
) -> None:
    """Append an immutable row to `audit_ledger` when table exists."""
    reg = (await conn.execute(sa.text("SELECT to_regclass('public.audit_ledger')"))).scalar()
    if reg is None:
        return
    await conn.execute(
        sa.text(
            """
            INSERT INTO audit_ledger (
                id, source_event_id, scope_path, actor_type, actor_id, actor_email,
                event_type, summary, trace_id, cas_references_jsonb, metadata_jsonb
            )
            VALUES (
                CAST(:id AS uuid), CAST(:src_id AS uuid), :scope_path, 'HUMAN',
                :actor_id, :actor_email, :event_type, :summary, :trace_id,
                CAST(:cas_refs AS jsonb), CAST(:meta AS jsonb)
            )
            """
        ),
        {
            "id": str(uuid7()),
            "src_id": str(uuid7()),
            "scope_path": scope_path[:256] or "GLOBAL",
            "actor_id": actor_id[:128],
            "actor_email": actor_email,
            "event_type": event_type[:64],
            "summary": summary,
            "trace_id": (trace_id or str(uuid7()).replace("-", ""))[:64],
            "cas_refs": json.dumps(cas_references or []),
            "meta": json.dumps(metadata, ensure_ascii=False),
        },
    )


__all__ = ["append_pack_audit_event", "materialize_pack_mechanisms_and_policies"]
