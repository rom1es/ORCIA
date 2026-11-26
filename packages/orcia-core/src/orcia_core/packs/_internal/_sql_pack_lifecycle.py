"""Pack lifecycle, DNA mechanisms & guarded deletion SQL helpers (`Story 31.1`)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.packs.errors import (
    EntityReferencedByPackDraftError,
    ResourcePinnedByActiveRunsError,
)
from orcia_core.packs.models import PackDnaMechanismSpec

_OWNED_CHILD_TABLES: tuple[tuple[str, str], ...] = (
    ("catalog_items", "catalog_item_id"),
    ("workflow_definitions_v2", "workflow_v2_id"),
    ("vsm_definitions_v2", "vsm_v2_id"),
    ("ontology_concepts", "ontology_concept_id"),
    ("ontology_relations", "ontology_relation_id"),
    ("ontology_axioms", "ontology_axiom_id"),
    ("permission_broker_policies", "policy_id"),
)


def _parse_json_dict_or_none(raw: object) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return dict(raw) if raw else None
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            return dict(decoded) if isinstance(decoded, dict) and decoded else None
        except ValueError:
            return None
    return None


async def upsert_pack_dna_mechanisms_sql(
    engine: AsyncEngine,
    *,
    pack_bundle_id: str,
    mechanisms: Sequence[PackDnaMechanismSpec],
) -> None:
    """Idempotently upsert `pack_dna_mechanisms` including passing/failing test payloads."""
    if not mechanisms:
        return
    async with engine.begin() as conn:
        for mech in mechanisms:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO pack_dna_mechanisms (
                        id, pack_bundle_id, mechanism_slug, name, starlark_source,
                        source_sha256, input_schema_jsonb, output_schema_jsonb,
                        passing_test_payload_jsonb, failing_test_payload_jsonb
                    )
                    VALUES (
                        CAST(:id AS uuid), CAST(:pack_bundle_id AS uuid), :mechanism_slug, :name,
                        :starlark_source, :source_sha256, CAST(:input_schema AS jsonb),
                        CAST(:output_schema AS jsonb), CAST(:passing_payload AS jsonb),
                        CAST(:failing_payload AS jsonb)
                    )
                    ON CONFLICT (pack_bundle_id, mechanism_slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        starlark_source = EXCLUDED.starlark_source,
                        source_sha256 = EXCLUDED.source_sha256,
                        input_schema_jsonb = EXCLUDED.input_schema_jsonb,
                        output_schema_jsonb = EXCLUDED.output_schema_jsonb,
                        passing_test_payload_jsonb = EXCLUDED.passing_test_payload_jsonb,
                        failing_test_payload_jsonb = EXCLUDED.failing_test_payload_jsonb
                    """
                ),
                {
                    "id": str(uuid7()),
                    "pack_bundle_id": pack_bundle_id,
                    "mechanism_slug": mech.mechanism_slug,
                    "name": mech.name,
                    "starlark_source": mech.starlark_source,
                    "source_sha256": mech.source_sha256,
                    "input_schema": json.dumps(mech.input_schema, sort_keys=True),
                    "output_schema": json.dumps(mech.output_schema, sort_keys=True),
                    "passing_payload": json.dumps(mech.passing_test_payload or {}, sort_keys=True),
                    "failing_payload": json.dumps(mech.failing_test_payload or {}, sort_keys=True),
                },
            )


async def list_pack_dna_mechanisms_sql(
    engine: AsyncEngine,
    *,
    pack_bundle_id: str,
) -> list[PackDnaMechanismSpec]:
    """Load persisted `PackDnaMechanismSpec` rows for `pack_bundle_id`."""
    async with engine.connect() as conn:
        rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT mechanism_slug, name, starlark_source, source_sha256,
                           input_schema_jsonb, output_schema_jsonb,
                           passing_test_payload_jsonb, failing_test_payload_jsonb
                    FROM pack_dna_mechanisms
                    WHERE pack_bundle_id = CAST(:pack_bundle_id AS uuid)
                    ORDER BY mechanism_slug ASC
                    """
                ),
                {"pack_bundle_id": pack_bundle_id},
            )
        ).fetchall()
    return [
        PackDnaMechanismSpec(
            mechanism_slug=str(r[0]),
            name=str(r[1]),
            starlark_source=str(r[2]),
            source_sha256=str(r[3]).strip(),
            input_schema=_parse_json_dict_or_none(r[4]) or {},
            output_schema=_parse_json_dict_or_none(r[5]) or {},
            passing_test_payload=_parse_json_dict_or_none(r[6]),
            failing_test_payload=_parse_json_dict_or_none(r[7]),
        )
        for r in rows
    ]


async def delete_pack_bundle_sql(engine: AsyncEngine, *, bundle_id: str) -> None:
    """Safely delete a pack bundle after checking active run pins and cross-draft references."""
    async with engine.begin() as conn:
        active_activation = (
            await conn.execute(
                sa.text(
                    "SELECT 1 FROM workspace_pack_activations "
                    "WHERE pack_bundle_id = CAST(:bundle_id AS uuid) AND is_active = TRUE LIMIT 1"
                ),
                {"bundle_id": bundle_id},
            )
        ).scalar()
        if active_activation is not None:
            raise ResourcePinnedByActiveRunsError(
                detail_override=f"Pack bundle {bundle_id!r} has active workspace activations."
            )
        pinned_run = (
            await conn.execute(
                sa.text(
                    "SELECT 1 FROM run_lock_manifests rlm "
                    "JOIN workflow_runs wr ON wr.id = rlm.run_id "
                    "WHERE wr.status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED') "
                    "AND rlm.manifest_jsonb::text LIKE :pattern LIMIT 1"
                ),
                {"pattern": f"%{bundle_id}%"},
            )
        ).scalar()
        if pinned_run is not None:
            raise ResourcePinnedByActiveRunsError(
                detail_override=f"Pack bundle {bundle_id!r} is pinned by active workflow runs."
            )

        for tbl, fk_col in _OWNED_CHILD_TABLES:
            ref_draft = (
                await conn.execute(
                    sa.text(
                        f"SELECT 1 FROM pack_draft_memberships m "
                        f"JOIN {tbl} c ON c.id = m.{fk_col} "
                        f"WHERE c.pack_bundle_id = CAST(:bundle_id AS uuid) "
                        f"AND m.draft_bundle_id <> CAST(:bundle_id AS uuid) LIMIT 1"
                    ),
                    {"bundle_id": bundle_id},
                )
            ).scalar()
            if ref_draft is not None:
                raise EntityReferencedByPackDraftError(
                    detail_override=(
                        f"Entities in bundle {bundle_id!r} are referenced by another pack draft."
                    )
                )

        mech_ref = (
            await conn.execute(
                sa.text(
                    "SELECT 1 FROM pack_draft_memberships m "
                    "JOIN pack_dna_mechanisms d ON d.id = m.dna_mechanism_id "
                    "WHERE d.pack_bundle_id = CAST(:bundle_id AS uuid) "
                    "AND m.draft_bundle_id <> CAST(:bundle_id AS uuid) LIMIT 1"
                ),
                {"bundle_id": bundle_id},
            )
        ).scalar()
        if mech_ref is not None:
            raise EntityReferencedByPackDraftError(
                detail_override=(
                    f"DNA mechanisms in bundle {bundle_id!r} are referenced by another pack draft."
                )
            )

        await conn.execute(
            sa.text(
                "DELETE FROM pack_draft_memberships "
                "WHERE draft_bundle_id = CAST(:bundle_id AS uuid)"
            ),
            {"bundle_id": bundle_id},
        )
        await conn.execute(
            sa.text(
                "DELETE FROM workspace_pack_activations "
                "WHERE pack_bundle_id = CAST(:bundle_id AS uuid) AND is_active = FALSE"
            ),
            {"bundle_id": bundle_id},
        )
        await conn.execute(
            sa.text("DELETE FROM declarative_pack_bundles WHERE id = CAST(:bundle_id AS uuid)"),
            {"bundle_id": bundle_id},
        )


__all__ = [
    "delete_pack_bundle_sql",
    "list_pack_dna_mechanisms_sql",
    "upsert_pack_dna_mechanisms_sql",
]
