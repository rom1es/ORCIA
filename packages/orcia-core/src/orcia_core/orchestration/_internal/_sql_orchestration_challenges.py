"""PostgreSQL 18 Repository for `upstream_challenges` (`0016`, `REM-09`)."""

from __future__ import annotations

import json
from typing import Any, cast

import sqlalchemy as sa

from orcia_core.ontology.models import HumanProfileArchetype
from orcia_core.orchestration._internal._sql_orchestration_parents import (
    resolve_existing_user_id_sql,
)
from orcia_core.orchestration._internal.uow import DbosSqlAlchemyUnitOfWork
from orcia_core.orchestration.challenge_and_replay import ChallengeStatus, UpstreamChallengeEntity


async def upsert_upstream_challenge_sql(
    uow: DbosSqlAlchemyUnitOfWork,
    challenge: UpstreamChallengeEntity,
) -> None:
    """Persist or update an `upstream_challenges` row (`0016`)."""
    async with uow.session_scope() as session:
        resolved_uid = await resolve_existing_user_id_sql(
            session, challenge.created_by_user_id, fallback_to_any=True
        )
        if resolved_uid is None:
            return
        await session.execute(
            sa.text(
                """
                INSERT INTO upstream_challenges (
                    id, challenge_key, workspace_id, run_id, challenger_step_key,
                    target_upstream_step_key, challenged_section_key, challenge_reason,
                    target_profile_archetype, translated_summary, invalidated_steps_jsonb,
                    invalidated_sections_jsonb, invalidated_axioms_jsonb, status,
                    created_by_user_id, outbox_event_id, resolved_at
                ) VALUES (
                    CAST(:id AS uuid), :challenge_key, CAST(:workspace_id AS uuid),
                    CAST(:run_id AS uuid), :challenger_step_key,
                    :target_upstream_step_key, :challenged_section_key, :challenge_reason,
                    :target_profile_archetype, :translated_summary,
                    CAST(:invalidated_steps_jsonb AS jsonb),
                    CAST(:invalidated_sections_jsonb AS jsonb),
                    CAST(:invalidated_axioms_jsonb AS jsonb),
                    :status, CAST(:created_by_user_id AS uuid),
                    CAST(:outbox_event_id AS uuid),
                    CASE WHEN :is_resolved THEN NOW() ELSE NULL END
                )
                ON CONFLICT (challenge_key) DO UPDATE SET
                    status = EXCLUDED.status,
                    translated_summary = EXCLUDED.translated_summary,
                    resolved_at = EXCLUDED.resolved_at;
                """
            ),
            {
                "id": challenge.id,
                "challenge_key": challenge.challenge_key,
                "workspace_id": challenge.workspace_id,
                "run_id": challenge.run_id,
                "challenger_step_key": challenge.challenger_step_key,
                "target_upstream_step_key": challenge.target_upstream_step_key,
                "challenged_section_key": challenge.challenged_section_key,
                "challenge_reason": challenge.challenge_reason,
                "target_profile_archetype": str(challenge.target_profile_archetype)[:48],
                "translated_summary": challenge.translated_summary,
                "invalidated_steps_jsonb": json.dumps(
                    list(challenge.invalidated_downstream_step_keys)
                ),
                "invalidated_sections_jsonb": json.dumps(
                    list(challenge.invalidated_artifact_sections)
                ),
                "invalidated_axioms_jsonb": json.dumps(
                    list(challenge.invalidated_ontology_axiom_keys)
                ),
                "status": challenge.status,
                "created_by_user_id": resolved_uid,
                "outbox_event_id": challenge.outbox_event_id,
                "is_resolved": challenge.status != "OPEN",
            },
        )


async def mark_upstream_challenges_replayed_sql(
    uow: DbosSqlAlchemyUnitOfWork,
    *,
    run_id: str,
    target_upstream_step_key: str,
) -> None:
    """Mark matching `upstream_challenges` as `REPLAYED` on targeted replay."""
    async with uow.session_scope() as session:
        await session.execute(
            sa.text(
                """
                UPDATE upstream_challenges
                SET status = 'REPLAYED',
                    resolved_at = NOW()
                WHERE run_id = CAST(:run_id AS uuid)
                  AND target_upstream_step_key = :step_key;
                """
            ),
            {"run_id": run_id, "step_key": target_upstream_step_key},
        )


async def list_upstream_challenges_sql(
    uow: DbosSqlAlchemyUnitOfWork, *, run_id: str | None = None
) -> tuple[UpstreamChallengeEntity, ...]:
    """Read `upstream_challenges` rows from PostgreSQL 18."""
    where_clause = "WHERE run_id = CAST(:run_id AS uuid)" if run_id else ""
    params: dict[str, Any] = {"run_id": run_id} if run_id else {}
    async with uow.session_scope() as session:
        rows = (
            (
                await session.execute(
                    sa.text(
                        f"""
                        SELECT
                            id::text, challenge_key, workspace_id::text, run_id::text,
                            challenger_step_key, target_upstream_step_key,
                            challenged_section_key, challenge_reason,
                            target_profile_archetype, translated_summary,
                            invalidated_steps_jsonb, invalidated_sections_jsonb,
                            invalidated_axioms_jsonb, status, created_by_user_id::text,
                            outbox_event_id::text
                        FROM upstream_challenges
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
        out: list[UpstreamChallengeEntity] = []
        for r in rows:
            inv_steps = r["invalidated_steps_jsonb"]
            inv_secs = r["invalidated_sections_jsonb"]
            inv_axs = r["invalidated_axioms_jsonb"]
            steps_list = (
                json.loads(inv_steps) if isinstance(inv_steps, str) else list(inv_steps or [])
            )
            secs_list = json.loads(inv_secs) if isinstance(inv_secs, str) else list(inv_secs or [])
            axs_list = json.loads(inv_axs) if isinstance(inv_axs, str) else list(inv_axs or [])
            out.append(
                UpstreamChallengeEntity(
                    id=str(r["id"]),
                    challenge_key=str(r["challenge_key"]),
                    workspace_id=str(r["workspace_id"]),
                    run_id=str(r["run_id"]),
                    challenger_step_key=str(r["challenger_step_key"]),
                    target_upstream_step_key=str(r["target_upstream_step_key"]),
                    challenged_section_key=str(r["challenged_section_key"]),
                    challenge_reason=str(r["challenge_reason"]),
                    target_profile_archetype=cast(
                        HumanProfileArchetype, str(r["target_profile_archetype"])
                    ),
                    translated_summary=str(r["translated_summary"]),
                    invalidated_downstream_step_keys=tuple(str(x) for x in steps_list),
                    invalidated_artifact_sections=tuple(str(x) for x in secs_list),
                    invalidated_ontology_axiom_keys=tuple(str(x) for x in axs_list),
                    preserved_upstream_step_keys=(),
                    status=cast(ChallengeStatus, str(r["status"])),
                    created_by_user_id=str(r["created_by_user_id"]),
                    outbox_event_id=str(r["outbox_event_id"] or ""),
                )
            )
        return tuple(out)
