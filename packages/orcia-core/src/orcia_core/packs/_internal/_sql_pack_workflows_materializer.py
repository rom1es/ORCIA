"""SQL materialization of pack workflows v2 and VSMs (`Story 31.2`, `<= 300 L`)."""

from __future__ import annotations

import json

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection
from uuid_utils import uuid7

from orcia_core.packs.models import LoadedPackBundleV2


async def materialize_pack_workflows_and_vsms(
    conn: AsyncConnection,
    *,
    bundle_id: str,
    bundle: LoadedPackBundleV2,
) -> None:
    """Materialize `workflow_definitions_v2` and `vsm_definitions_v2` for `pack_bundle_id`."""
    pack_id = (bundle.manifest.id or f"orcia-pack-{bundle.manifest.slug}")[:128]
    kept_wf_keys: list[str] = []
    for wf in bundle.workflows:
        wf_key = f"{wf.id[:128]}::{wf.version[:64]}"
        kept_wf_keys.append(wf_key)
        await conn.execute(
            sa.text(
                """
                INSERT INTO workflow_definitions_v2 (
                    id, workflow_id, slug, version, status, pack_id,
                    execution_mode, spec_jsonb, pack_bundle_id, updated_at
                )
                VALUES (
                    CAST(:id AS uuid), :workflow_id, :slug, :version, :status, :pack_id,
                    :execution_mode, CAST(:spec_jsonb AS jsonb), CAST(:bid AS uuid), NOW()
                )
                ON CONFLICT (pack_bundle_id, workflow_id, version)
                WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
                    slug = EXCLUDED.slug, status = EXCLUDED.status, pack_id = EXCLUDED.pack_id,
                    execution_mode = EXCLUDED.execution_mode, spec_jsonb = EXCLUDED.spec_jsonb,
                    updated_at = NOW()
                """
            ),
            {
                "id": str(uuid7()),
                "workflow_id": wf.id[:128],
                "slug": wf.slug[:128],
                "version": wf.version[:64],
                "status": str(wf.status),
                "pack_id": pack_id,
                "execution_mode": str(wf.execution_mode),
                "spec_jsonb": json.dumps(wf.model_dump(mode="json"), ensure_ascii=False),
                "bid": bundle_id,
            },
        )
    await conn.execute(
        sa.text(
            "DELETE FROM workflow_definitions_v2 WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT ((workflow_id || '::' || version) = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_wf_keys},
    )

    kept_vsm_ids: list[str] = []
    for vsm in bundle.vsm_specs:
        vsm_id = vsm.id[:128]
        vsm_slug = vsm.slug[:128]
        kept_vsm_ids.append(vsm_id)
        await conn.execute(
            sa.text(
                "DELETE FROM vsm_definitions_v2 WHERE pack_bundle_id = CAST(:bid AS uuid) "
                "AND slug = :slug AND vsm_id <> :vsm_id"
            ),
            {"bid": bundle_id, "slug": vsm_slug, "vsm_id": vsm_id},
        )
        await conn.execute(
            sa.text(
                """
                INSERT INTO vsm_definitions_v2 (
                    id, vsm_id, slug, pack_id, title, spec_jsonb, pack_bundle_id, updated_at
                )
                VALUES (
                    CAST(:id AS uuid), :vsm_id, :slug, :pack_id, :title,
                    CAST(:spec_jsonb AS jsonb), CAST(:bid AS uuid), NOW()
                )
                ON CONFLICT (pack_bundle_id, vsm_id)
                WHERE pack_bundle_id IS NOT NULL DO UPDATE SET
                    slug = EXCLUDED.slug, pack_id = EXCLUDED.pack_id, title = EXCLUDED.title,
                    spec_jsonb = EXCLUDED.spec_jsonb, updated_at = NOW()
                """
            ),
            {
                "id": str(uuid7()),
                "vsm_id": vsm_id,
                "slug": vsm_slug,
                "pack_id": pack_id,
                "title": vsm.title[:255],
                "spec_jsonb": json.dumps(
                    vsm.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
                ),
                "bid": bundle_id,
            },
        )
    await conn.execute(
        sa.text(
            "DELETE FROM vsm_definitions_v2 WHERE pack_bundle_id = CAST(:bid AS uuid) "
            "AND NOT (vsm_id = ANY(:kept))"
        ),
        {"bid": bundle_id, "kept": kept_vsm_ids},
    )


__all__ = ["materialize_pack_workflows_and_vsms"]
