"""PostgreSQL 18 SQLAlchemy Async repository for `workspace_dna_mechanisms` (`Story 24.2`)."""

from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from orcia_core.orchestration._dna_starlark_models import GeneratedStarlarkMechanism

_SELECT_COLS = (
    "id, workspace_id, rule_id, directive_title, norm_title, script_name, "
    "starlark_code, sha256, passing_test_payload_jsonb, failing_test_payload_jsonb, "
    "explanation_fr, self_corrected, compile_elapsed_ms, verified_badge_fr, "
    "causal_breadcrumb, signed_and_active"
)


def _parse_json_dict(raw: Any) -> dict[str, Any]:
    if isinstance(raw, str):
        parsed = json.loads(raw) if raw else {}
        return dict(parsed) if isinstance(parsed, dict) else {}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def _row_to_mechanism(row: RowMapping) -> GeneratedStarlarkMechanism:
    return GeneratedStarlarkMechanism(
        mechanism_id=UUID(str(row["id"])),
        workspace_id=UUID(str(row["workspace_id"])),
        rule_id=str(row["rule_id"]),
        directive_title=str(row["directive_title"]),
        norm_title=str(row["norm_title"]),
        script_name=str(row["script_name"]),
        starlark_code=str(row["starlark_code"]),
        sha256=str(row["sha256"]),
        passing_test_payload=_parse_json_dict(row["passing_test_payload_jsonb"]),
        failing_test_payload=_parse_json_dict(row["failing_test_payload_jsonb"]),
        explanation_fr=str(row["explanation_fr"]),
        self_corrected=bool(row["self_corrected"]),
        compile_elapsed_ms=float(cast(float, row["compile_elapsed_ms"])),
        verified_badge_fr=str(row["verified_badge_fr"]),
        causal_breadcrumb=str(row["causal_breadcrumb"]),
        signed_and_active=bool(row["signed_and_active"]),
    )


async def _resolve_existing_user(session: AsyncSession, user_id: UUID | None) -> str | None:
    if user_id is None:
        return None
    found = (
        await session.execute(
            sa.text("SELECT id::text FROM users WHERE id = CAST(:uid AS uuid) LIMIT 1"),
            {"uid": str(user_id)},
        )
    ).scalar_one_or_none()
    return str(found) if found is not None else None


class SqlStarlarkMechanismRepository:
    """Async SQLAlchemy repository for `workspace_dna_mechanisms` in PostgreSQL 18."""

    def __init__(
        self,
        *,
        session_maker: async_sessionmaker[AsyncSession] | None = None,
        engine: AsyncEngine | None = None,
    ) -> None:
        if session_maker is not None:
            self._session_maker: async_sessionmaker[AsyncSession] | None = session_maker
        elif engine is not None:
            self._session_maker = async_sessionmaker(engine, expire_on_commit=False)
        else:
            self._session_maker = None

    def _require_session_maker(self) -> async_sessionmaker[AsyncSession]:
        if self._session_maker is None:
            raise RuntimeError("SqlStarlarkMechanismRepository requires a PG18 engine/session.")
        return self._session_maker

    async def save_mechanism(
        self,
        *,
        workspace_id: UUID,
        mechanism: GeneratedStarlarkMechanism,
        signed_by_user_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism:
        """Upsert a compiled Starlark mechanism into `workspace_dna_mechanisms`."""
        sm = self._require_session_maker()
        async with sm() as session, session.begin():
            signer_id = await _resolve_existing_user(session, signed_by_user_id)
            row = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            INSERT INTO workspace_dna_mechanisms (
                                id, workspace_id, rule_id, directive_title, norm_title,
                                script_name, starlark_code, sha256,
                                passing_test_payload_jsonb, failing_test_payload_jsonb,
                                explanation_fr, self_corrected, compile_elapsed_ms,
                                verified_badge_fr, causal_breadcrumb, signed_and_active,
                                signed_by_user_id, signed_at
                            ) VALUES (
                                CAST(:id AS uuid), CAST(:workspace_id AS uuid), :rule_id,
                                :directive_title, :norm_title, :script_name,
                                :starlark_code, :sha256,
                                CAST(:passing_payload AS jsonb), CAST(:failing_payload AS jsonb),
                                :explanation_fr, :self_corrected, :compile_elapsed_ms,
                                :verified_badge_fr, :causal_breadcrumb, :signed_and_active,
                                CAST(:signed_by_user_id AS uuid),
                                CASE WHEN :signed_and_active THEN NOW() ELSE NULL END
                            )
                            ON CONFLICT (workspace_id, rule_id) DO UPDATE SET
                                directive_title = EXCLUDED.directive_title,
                                norm_title = EXCLUDED.norm_title,
                                script_name = EXCLUDED.script_name,
                                starlark_code = EXCLUDED.starlark_code,
                                sha256 = EXCLUDED.sha256,
                                passing_test_payload_jsonb = EXCLUDED.passing_test_payload_jsonb,
                                failing_test_payload_jsonb = EXCLUDED.failing_test_payload_jsonb,
                                explanation_fr = EXCLUDED.explanation_fr,
                                self_corrected = EXCLUDED.self_corrected,
                                compile_elapsed_ms = EXCLUDED.compile_elapsed_ms,
                                verified_badge_fr = EXCLUDED.verified_badge_fr,
                                causal_breadcrumb = EXCLUDED.causal_breadcrumb,
                                signed_and_active = EXCLUDED.signed_and_active,
                                signed_by_user_id = COALESCE(
                                    EXCLUDED.signed_by_user_id,
                                    workspace_dna_mechanisms.signed_by_user_id
                                ),
                                signed_at = CASE
                                    WHEN EXCLUDED.signed_and_active THEN NOW()
                                    ELSE workspace_dna_mechanisms.signed_at
                                END,
                                updated_at = NOW()
                            RETURNING {_SELECT_COLS}
                            """
                        ),
                        {
                            "id": str(mechanism.mechanism_id),
                            "workspace_id": str(workspace_id),
                            "rule_id": mechanism.rule_id,
                            "directive_title": mechanism.directive_title,
                            "norm_title": mechanism.norm_title,
                            "script_name": mechanism.script_name,
                            "starlark_code": mechanism.starlark_code,
                            "sha256": mechanism.sha256,
                            "passing_payload": json.dumps(mechanism.passing_test_payload),
                            "failing_payload": json.dumps(mechanism.failing_test_payload),
                            "explanation_fr": mechanism.explanation_fr,
                            "self_corrected": mechanism.self_corrected,
                            "compile_elapsed_ms": mechanism.compile_elapsed_ms,
                            "verified_badge_fr": mechanism.verified_badge_fr,
                            "causal_breadcrumb": mechanism.causal_breadcrumb,
                            "signed_and_active": mechanism.signed_and_active,
                            "signed_by_user_id": signer_id,
                        },
                    )
                )
                .mappings()
                .one()
            )
            return _row_to_mechanism(row)

    async def get_mechanism(
        self,
        *,
        workspace_id: UUID,
        mechanism_id: UUID,
    ) -> GeneratedStarlarkMechanism | None:
        """Load a compiled Starlark mechanism from PG18."""
        sm = self._require_session_maker()
        async with sm() as session:
            row = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            SELECT {_SELECT_COLS}
                            FROM workspace_dna_mechanisms
                            WHERE workspace_id = CAST(:workspace_id AS uuid)
                              AND id = CAST(:mechanism_id AS uuid)
                            LIMIT 1
                            """
                        ),
                        {"workspace_id": str(workspace_id), "mechanism_id": str(mechanism_id)},
                    )
                )
                .mappings()
                .first()
            )
            return _row_to_mechanism(row) if row is not None else None

    async def list_mechanisms(
        self,
        *,
        workspace_id: UUID,
    ) -> list[GeneratedStarlarkMechanism]:
        """List all compiled Starlark mechanisms for a workspace from PG18."""
        sm = self._require_session_maker()
        async with sm() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            SELECT {_SELECT_COLS}
                            FROM workspace_dna_mechanisms
                            WHERE workspace_id = CAST(:workspace_id AS uuid)
                            ORDER BY updated_at DESC, id DESC
                            """
                        ),
                        {"workspace_id": str(workspace_id)},
                    )
                )
                .mappings()
                .all()
            )
            return [_row_to_mechanism(row) for row in rows]

    async def activate_mechanism(
        self,
        *,
        workspace_id: UUID,
        mechanism_id: UUID,
        signed_by_user_id: UUID | None = None,
    ) -> GeneratedStarlarkMechanism | None:
        """Sign and activate a persisted Starlark mechanism in PG18."""
        sm = self._require_session_maker()
        async with sm() as session, session.begin():
            signer_id = await _resolve_existing_user(session, signed_by_user_id)
            row = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            UPDATE workspace_dna_mechanisms
                            SET signed_and_active = TRUE,
                                signed_by_user_id = COALESCE(
                                    CAST(:signed_by_user_id AS uuid),
                                    signed_by_user_id
                                ),
                                signed_at = NOW(),
                                updated_at = NOW()
                            WHERE workspace_id = CAST(:workspace_id AS uuid)
                              AND id = CAST(:mechanism_id AS uuid)
                            RETURNING {_SELECT_COLS}
                            """
                        ),
                        {
                            "workspace_id": str(workspace_id),
                            "mechanism_id": str(mechanism_id),
                            "signed_by_user_id": signer_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            return _row_to_mechanism(row) if row is not None else None
