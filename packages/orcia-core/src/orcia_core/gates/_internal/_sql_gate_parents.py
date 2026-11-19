"""Parent FK resolution helpers for `SqlGateEvaluationRepository` (`0017`, `0018`, `REM-11`)."""

from __future__ import annotations

import hashlib
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from orcia_kernel.ids import new_uuid7_str

_GATE_NS = UUID("0195f000-0000-7000-8000-00000000e000")
_DEFAULT_ORG_UNIT_ID = UUID("0192c4e0-0000-7000-8000-000000000101")
_DEFAULT_WF_DEF_ID = UUID("0195f000-0000-7000-8000-000000000602")


def coerce_gate_uuid(raw_id: str | None) -> UUID:
    """Convert any identifier string into a valid UUID (deterministic UUIDv5 fallback)."""
    if raw_id is None or not raw_id.strip():
        return UUID(new_uuid7_str())
    cleaned = raw_id.strip()
    try:
        return UUID(cleaned)
    except ValueError:
        return uuid5(_GATE_NS, cleaned)


async def resolve_gate_user_id(conn: AsyncConnection, user_id: str | None) -> str | None:
    """Resolve `users.id` in PG18 if present; else return `None`."""
    if not user_id or not user_id.strip():
        return None
    row = (
        await conn.execute(
            sa.text(
                "SELECT id::text FROM users "
                "WHERE id::text = :uid OR lower(email) = lower(:uid) LIMIT 1"
            ),
            {"uid": user_id.strip()},
        )
    ).first()
    return str(row[0]) if row is not None else None


async def _resolve_or_ensure_org_unit(conn: AsyncConnection) -> UUID:
    any_org = (
        await conn.execute(sa.text("SELECT id FROM org_units ORDER BY created_at ASC LIMIT 1"))
    ).scalar_one_or_none()
    if any_org is not None:
        return UUID(str(any_org))
    await conn.execute(
        sa.text(
            "INSERT INTO org_units (id, slug, name, unit_type, parent_id) VALUES ("
            "CAST(:id AS uuid), 'orcia-enterprise', 'Entreprise ORCIA', 'ENTERPRISE', NULL"
            ") ON CONFLICT (slug) DO NOTHING"
        ),
        {"id": str(_DEFAULT_ORG_UNIT_ID)},
    )
    resolved = (
        await conn.execute(sa.text("SELECT id FROM org_units ORDER BY created_at ASC LIMIT 1"))
    ).scalar_one()
    return UUID(str(resolved))


async def ensure_gate_parents(
    conn: AsyncConnection,
    *,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
) -> tuple[str, str, str]:
    """Ensure parent `workspaces`, `workflow_runs`, and `step_executions` rows exist in PG18."""
    ws_uuid = coerce_gate_uuid(workspace_id)
    run_uuid = coerce_gate_uuid(run_id)
    step_uuid = coerce_gate_uuid(step_execution_id)

    ws_row = (
        await conn.execute(
            sa.text(
                "SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) OR slug = :raw LIMIT 1"
            ),
            {"ws": str(ws_uuid), "raw": workspace_id.strip()},
        )
    ).first()
    if ws_row is not None:
        ws_uuid = UUID(str(ws_row[0]))
    else:
        org_uuid = await _resolve_or_ensure_org_unit(conn)
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (CAST(:id AS uuid), :slug, :name, CAST(:org_id AS uuid), 'STANDARD') "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {
                "id": str(ws_uuid),
                "slug": f"ws-gate-{str(ws_uuid)[-12:]}",
                "name": "Espace Validation Gates",
                "org_id": str(org_uuid),
            },
        )
        ws_check = (
            await conn.execute(
                sa.text("SELECT id FROM workspaces WHERE id = CAST(:ws AS uuid) LIMIT 1"),
                {"ws": str(ws_uuid)},
            )
        ).first()
        if ws_check is None:
            fallback_ws = (
                await conn.execute(
                    sa.text("SELECT id FROM workspaces ORDER BY created_at ASC LIMIT 1")
                )
            ).first()
            if fallback_ws is not None:
                ws_uuid = UUID(str(fallback_ws[0]))

    wf_def_row = (
        await conn.execute(
            sa.text("SELECT id FROM workflow_definitions ORDER BY created_at ASC LIMIT 1")
        )
    ).first()
    if wf_def_row is not None:
        wf_def_uuid = UUID(str(wf_def_row[0]))
    else:
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions ("
                "id, workspace_id, uri, version, source_format, steps_schema_jsonb, sha256"
                ") VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), "
                "'orcia://system/workflows/gate-evaluation-parent', '1.0.0', 'ORCIA', "
                "'{}'::jsonb, :sha256) ON CONFLICT (uri) DO NOTHING"
            ),
            {"id": str(_DEFAULT_WF_DEF_ID), "ws": str(ws_uuid), "sha256": "0" * 64},
        )
        wf_def_uuid = UUID(
            str(
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id FROM workflow_definitions ORDER BY created_at ASC LIMIT 1"
                        )
                    )
                ).scalar_one()
            )
        )

    await conn.execute(
        sa.text(
            "INSERT INTO workflow_runs ("
            "id, run_key, workspace_id, workflow_def_id, root_run_id, status"
            ") VALUES (CAST(:id AS uuid), :run_key, CAST(:ws AS uuid), "
            "CAST(:wf_def_id AS uuid), CAST(:id AS uuid), 'WAITING_FOR_HUMAN_GATE') "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {
            "id": str(run_uuid),
            "run_key": f"run-gate-{str(run_uuid)}",
            "ws": str(ws_uuid),
            "wf_def_id": str(wf_def_uuid),
        },
    )
    await conn.execute(
        sa.text(
            "INSERT INTO step_executions ("
            "id, step_execution_key, run_id, step_key, step_index, status"
            ") VALUES (CAST(:id AS uuid), :step_exec_key, CAST(:run_id AS uuid), "
            ":step_key, 0, 'WAITING_FOR_HUMAN_GATE') ON CONFLICT DO NOTHING"
        ),
        {
            "id": str(step_uuid),
            "step_exec_key": f"step-gate-{str(step_uuid)}",
            "run_id": str(run_uuid),
            "step_key": (step_key or "step-gate")[:128],
        },
    )
    existing_step = (
        await conn.execute(
            sa.text("SELECT id::text FROM step_executions WHERE id = CAST(:id AS uuid) LIMIT 1"),
            {"id": str(step_uuid)},
        )
    ).scalar_one_or_none()
    if existing_step is None:
        fallback_step = (
            await conn.execute(
                sa.text(
                    "SELECT id::text FROM step_executions "
                    "WHERE run_id = CAST(:run_id AS uuid) LIMIT 1"
                ),
                {"run_id": str(run_uuid)},
            )
        ).scalar_one_or_none()
        if fallback_step is not None:
            step_uuid = UUID(str(fallback_step))
    return str(ws_uuid), str(run_uuid), str(step_uuid)


async def ensure_chunk_anchor_signature(
    conn: AsyncConnection,
    *,
    signature_id: str | None,
    workspace_id: str,
    run_id: str,
    step_execution_id: str,
    step_key: str,
    chunk_key: str,
    content_markdown: str,
    content_sha256: str | None,
    reviewer_user_id: str | None,
) -> str | None:
    """Resolve or persist a `human_anchor_signatures` row when co-editing a >=30-char chunk."""
    if not signature_id:
        return None
    sig_uuid = coerce_gate_uuid(signature_id)
    existing = (
        await conn.execute(
            sa.text(
                "SELECT id::text FROM human_anchor_signatures WHERE id = CAST(:id AS uuid) LIMIT 1"
            ),
            {"id": str(sig_uuid)},
        )
    ).scalar_one_or_none()
    if existing is not None:
        return str(existing)

    cleaned = content_markdown.strip()
    if len(cleaned) < 30:
        return None
    resolved_uid = await resolve_gate_user_id(conn, reviewer_user_id)
    if resolved_uid is None:
        resolved_uid = (
            await conn.execute(
                sa.text("SELECT id::text FROM users ORDER BY created_at ASC LIMIT 1")
            )
        ).scalar_one_or_none()
    if resolved_uid is None:
        return None

    sha = (content_sha256 or hashlib.sha256(cleaned.encode("utf-8")).hexdigest())[:64]
    sig_hash = hashlib.sha256(f"{resolved_uid}:{sha}".encode()).hexdigest()
    sig_key = f"chunk-{run_id[-6:]}-{chunk_key}-{str(sig_uuid)[-6:]}"[:160]
    await conn.execute(
        sa.text(
            """
            INSERT INTO human_anchor_signatures (
                id, signature_key, workspace_id, run_id, step_execution_id,
                step_key, section_key, content_text, content_sha256,
                char_length, authored_by_user_id, author_display_name, signature_hash
            ) VALUES (
                CAST(:id AS uuid), :signature_key, CAST(:workspace_id AS uuid),
                CAST(:run_id AS uuid), CAST(:step_execution_id AS uuid),
                :step_key, :section_key, :content_text, :content_sha256,
                :char_length, CAST(:authored_by_user_id AS uuid),
                'Reviewer', :signature_hash
            )
            ON CONFLICT (signature_key) DO NOTHING;
            """
        ),
        {
            "id": str(sig_uuid),
            "signature_key": sig_key,
            "workspace_id": workspace_id,
            "run_id": run_id,
            "step_execution_id": step_execution_id,
            "step_key": step_key[:128],
            "section_key": chunk_key[:128],
            "content_text": cleaned,
            "content_sha256": sha,
            "char_length": len(cleaned),
            "authored_by_user_id": resolved_uid,
            "signature_hash": sig_hash,
        },
    )
    verified = (
        await conn.execute(
            sa.text(
                "SELECT id::text FROM human_anchor_signatures WHERE id = CAST(:id AS uuid) LIMIT 1"
            ),
            {"id": str(sig_uuid)},
        )
    ).scalar_one_or_none()
    return str(verified) if verified is not None else None
