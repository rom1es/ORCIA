"""PostgreSQL 18 Governance Repository for Orchestration (`REM-09`).

Persists & rehydrates `human_anchor_signatures` (`0015`) and `human_arbitration_requests` (`0015`)
and re-exports challenge/parent helpers via `DbosSqlAlchemyUnitOfWork`.
"""

from __future__ import annotations

import json
from typing import Any, cast

import sqlalchemy as sa

from orcia_core.orchestration._internal._sql_orchestration_challenges import (
    list_upstream_challenges_sql,
    mark_upstream_challenges_replayed_sql,
    upsert_upstream_challenge_sql,
)
from orcia_core.orchestration._internal._sql_orchestration_parents import (
    ensure_run_row_exists_in_session,
    ensure_workflow_definition_sql,
    list_workflow_runs_with_locks_sql,
    resolve_existing_user_id_sql,
    upsert_run_lock_manifest_sql,
)
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_core.orchestration.human_anchors_and_arbitration import (
    ArbitrationOptionItem,
    HumanAnchorSignatureEntity,
    HumanArbitrationRequestEntity,
    HumanArbitrationStatus,
)
from orcia_core.orchestration.models import TieBreakPolicy


async def upsert_human_anchor_signature_sql(
    uow: DbosSqlAlchemyUnitOfWork,
    sig: HumanAnchorSignatureEntity,
) -> None:
    """Persist or update a `human_anchor_signatures` row (`0015`)."""
    async with uow.session_scope() as session:
        resolved_uid = await resolve_existing_user_id_sql(
            session, sig.authored_by_user_id, fallback_to_any=True
        )
        if resolved_uid is None:
            return
        await session.execute(
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
                    :author_display_name, :signature_hash
                )
                ON CONFLICT (signature_key) DO UPDATE SET
                    content_text = EXCLUDED.content_text,
                    content_sha256 = EXCLUDED.content_sha256,
                    char_length = EXCLUDED.char_length,
                    authored_by_user_id = EXCLUDED.authored_by_user_id,
                    author_display_name = EXCLUDED.author_display_name,
                    signature_hash = EXCLUDED.signature_hash,
                    signed_at = NOW();
                """
            ),
            {
                "id": sig.id,
                "signature_key": sig.signature_key,
                "workspace_id": sig.workspace_id,
                "run_id": sig.run_id,
                "step_execution_id": sig.step_execution_id,
                "step_key": sig.step_key,
                "section_key": sig.section_key,
                "content_text": sig.content_text,
                "content_sha256": sig.content_sha256[:64],
                "char_length": sig.char_length,
                "authored_by_user_id": resolved_uid,
                "author_display_name": sig.author_display_name[:160],
                "signature_hash": sig.signature_hash[:255],
            },
        )


async def list_human_anchor_signatures_sql(
    uow: DbosSqlAlchemyUnitOfWork, *, run_id: str | None = None
) -> tuple[HumanAnchorSignatureEntity, ...]:
    """Read `human_anchor_signatures` rows from PostgreSQL 18."""
    where_clause = "WHERE run_id = CAST(:run_id AS uuid)" if run_id else ""
    params: dict[str, Any] = {"run_id": run_id} if run_id else {}
    async with uow.session_scope() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            id::text, signature_key, workspace_id::text, run_id::text,
                            step_execution_id::text, step_key, section_key, content_text,
                            TRIM(content_sha256) AS content_sha256, char_length,
                            authored_by_user_id::text, author_display_name, signature_hash
                        FROM human_anchor_signatures
                        {where_clause}
                        ORDER BY signed_at ASC, id ASC;
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        return tuple(
            HumanAnchorSignatureEntity(
                id=str(r["id"]),
                signature_key=str(r["signature_key"]),
                workspace_id=str(r["workspace_id"]),
                run_id=str(r["run_id"]),
                step_execution_id=str(r["step_execution_id"]),
                step_key=str(r["step_key"]),
                section_key=str(r["section_key"]),
                content_text=str(r["content_text"]),
                content_sha256=str(r["content_sha256"]).strip(),
                char_length=int(r["char_length"]),
                authored_by_user_id=str(r["authored_by_user_id"]),
                author_display_name=str(r["author_display_name"]),
                signature_hash=str(r["signature_hash"]),
            )
            for r in rows
        )


async def upsert_human_arbitration_sql(
    uow: DbosSqlAlchemyUnitOfWork,
    arb: HumanArbitrationRequestEntity,
) -> None:
    """Persist or update a `human_arbitration_requests` row (`0015`)."""
    async with uow.session_scope() as session:
        resolved_uid = await resolve_existing_user_id_sql(
            session, arb.resolved_by_user_id, fallback_to_any=False
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO human_arbitration_requests (
                    id, arbitration_key, workspace_id, run_id, step_execution_id,
                    step_key, tie_break_policy, status, question_title, context_summary,
                    options_matrix_jsonb, selected_option_key, human_justification,
                    resolved_by_user_id, resolved_by_axiom_key, resolved_at
                ) VALUES (
                    CAST(:id AS uuid), :arbitration_key, CAST(:workspace_id AS uuid),
                    CAST(:run_id AS uuid), CAST(:step_execution_id AS uuid),
                    :step_key, :tie_break_policy, :status, :question_title, :context_summary,
                    CAST(:options_matrix_jsonb AS jsonb), :selected_option_key,
                    :human_justification, CAST(:resolved_by_user_id AS uuid),
                    :resolved_by_axiom_key, CASE WHEN :is_resolved THEN NOW() ELSE NULL END
                )
                ON CONFLICT (arbitration_key) DO UPDATE SET
                    status = EXCLUDED.status,
                    selected_option_key = EXCLUDED.selected_option_key,
                    human_justification = EXCLUDED.human_justification,
                    resolved_by_user_id = EXCLUDED.resolved_by_user_id,
                    resolved_by_axiom_key = EXCLUDED.resolved_by_axiom_key,
                    resolved_at = EXCLUDED.resolved_at;
                """
            ),
            {
                "id": arb.id,
                "arbitration_key": arb.arbitration_key,
                "workspace_id": arb.workspace_id,
                "run_id": arb.run_id,
                "step_execution_id": arb.step_execution_id,
                "step_key": arb.step_key,
                "tie_break_policy": arb.tie_break_policy,
                "status": arb.status,
                "question_title": arb.question_title[:255],
                "context_summary": arb.context_summary,
                "options_matrix_jsonb": json.dumps([o.to_dict() for o in arb.options_matrix]),
                "selected_option_key": arb.selected_option_key,
                "human_justification": arb.human_justification,
                "resolved_by_user_id": resolved_uid,
                "resolved_by_axiom_key": arb.resolved_by_axiom_key,
                "is_resolved": arb.status != "PENDING",
            },
        )


async def list_human_arbitrations_sql(
    uow: DbosSqlAlchemyUnitOfWork, *, run_id: str | None = None
) -> tuple[HumanArbitrationRequestEntity, ...]:
    """Read `human_arbitration_requests` rows from PostgreSQL 18."""
    where_clause = "WHERE run_id = CAST(:run_id AS uuid)" if run_id else ""
    params: dict[str, Any] = {"run_id": run_id} if run_id else {}
    async with uow.session_scope() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            id::text, arbitration_key, workspace_id::text, run_id::text,
                            step_execution_id::text, step_key, tie_break_policy, status,
                            question_title, context_summary, options_matrix_jsonb,
                            selected_option_key, human_justification,
                            resolved_by_user_id::text, resolved_by_axiom_key
                        FROM human_arbitration_requests
                        {where_clause}
                        ORDER BY created_at ASC, id ASC;
                        """
                    ),
                    params,
                )
            )
            .mappings()
            .all()
        )
        out: list[HumanArbitrationRequestEntity] = []
        for r in rows:
            raw_opts = r["options_matrix_jsonb"]
            opt_list = json.loads(raw_opts) if isinstance(raw_opts, str) else list(raw_opts or [])
            out.append(
                HumanArbitrationRequestEntity(
                    id=str(r["id"]),
                    arbitration_key=str(r["arbitration_key"]),
                    workspace_id=str(r["workspace_id"]),
                    run_id=str(r["run_id"]),
                    step_execution_id=str(r["step_execution_id"]),
                    step_key=str(r["step_key"]),
                    tie_break_policy=cast(TieBreakPolicy, str(r["tie_break_policy"])),
                    status=cast(HumanArbitrationStatus, str(r["status"])),
                    question_title=str(r["question_title"]),
                    context_summary=str(r["context_summary"]),
                    options_matrix=tuple(
                        ArbitrationOptionItem(
                            option_key=str(o["option_key"]),
                            title=str(o["title"]),
                            pros=tuple(str(p) for p in o.get("pros", [])),
                            cons=tuple(str(c) for c in o.get("cons", [])),
                            si_impact=str(o.get("si_impact", "")),
                            finops_impact=str(o.get("finops_impact", "")),
                            recommended=bool(o.get("recommended", False)),
                            ontology_concept_key=(
                                str(o["ontology_concept_key"])
                                if o.get("ontology_concept_key")
                                else None
                            ),
                        )
                        for o in opt_list
                    ),
                    selected_option_key=(
                        str(r["selected_option_key"]) if r["selected_option_key"] else None
                    ),
                    human_justification=(
                        str(r["human_justification"]) if r["human_justification"] else None
                    ),
                    resolved_by_user_id=(
                        str(r["resolved_by_user_id"]) if r["resolved_by_user_id"] else None
                    ),
                    resolved_by_axiom_key=(
                        str(r["resolved_by_axiom_key"]) if r["resolved_by_axiom_key"] else None
                    ),
                )
            )
        return tuple(out)


__all__ = [
    "ensure_run_row_exists_in_session",
    "ensure_workflow_definition_sql",
    "list_human_anchor_signatures_sql",
    "list_human_arbitrations_sql",
    "list_upstream_challenges_sql",
    "list_workflow_runs_with_locks_sql",
    "mark_upstream_challenges_replayed_sql",
    "resolve_existing_user_id_sql",
    "upsert_human_anchor_signature_sql",
    "upsert_human_arbitration_sql",
    "upsert_run_lock_manifest_sql",
    "upsert_upstream_challenge_sql",
]
