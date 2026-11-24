"""PostgreSQL 18 repository for `wizard_sessions` (`Story 22.5`, `REM-15`).

Pure asynchronous SQL repository implementing `WizardSessionRepositoryPort` (`AD-19`).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from uuid_utils import uuid7

from orcia_core.bootstrap.durable_wizards import (
    WIZARD_STEPS_BY_TYPE,
    WizardSessionRecord,
    WizardSessionStatus,
    WizardType,
)
from orcia_core.permissions.errors import ResourceNotFoundError, ValidationDomainError

_META_COMPLETED_KEY = "_completed_steps"
_META_RAG_KEY = "_rag_reciprocity_verified"
_DEFAULT_GLOBAL_SCOPE_UUID = "0195f000-0000-7000-8000-000000000301"
_SELECT_COLS = (
    "id::text, wizard_type, user_id::text, scope_id::text, current_step_index, "
    "state_jsonb, dbos_workflow_id, status, updated_at"
)


def _normalize_uuid(raw: str, *, field_name: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        raise ValidationDomainError(detail_override=f"Missing required UUID for {field_name}.")
    try:
        return str(uuid.UUID(cleaned))
    except ValueError as err:
        raise ValidationDomainError(
            detail_override=f"Invalid UUID format for {field_name}: {raw!r}."
        ) from err


def _normalize_scope_uuid(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned or cleaned.lower() in ("global", "scope-global"):
        return _DEFAULT_GLOBAL_SCOPE_UUID
    try:
        return str(uuid.UUID(cleaned))
    except ValueError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"orcia:scope:{cleaned}"))


def _parse_json_dict(raw: object) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            decoded = json.loads(raw)
            return dict(decoded) if isinstance(decoded, dict) else {}
        except ValueError:
            return {}
    return {}


def _serialize_state_json(
    state_jsonb: dict[str, Any], *, completed_steps: tuple[int, ...], rag_verified: bool
) -> str:
    payload = {
        k: v for k, v in state_jsonb.items() if k not in (_META_COMPLETED_KEY, _META_RAG_KEY)
    }
    payload[_META_COMPLETED_KEY] = list(completed_steps)
    payload[_META_RAG_KEY] = bool(rag_verified)
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _row_to_record(row: Any) -> WizardSessionRecord:
    wizard_type = cast(WizardType, str(row[1]))
    raw_state = _parse_json_dict(row[5])
    raw_completed = raw_state.pop(_META_COMPLETED_KEY, None)
    raw_rag = raw_state.pop(_META_RAG_KEY, None)
    if isinstance(raw_completed, list):
        completed = tuple(sorted({int(x) for x in raw_completed if isinstance(x, int)}))
    else:
        completed = tuple(
            sorted(
                int(k.removeprefix("step_"))
                for k in raw_state
                if k.startswith("step_") and k.removeprefix("step_").isdigit()
            )
        )
    status = cast(WizardSessionStatus, str(row[7]))
    ts = row[8]
    updated_iso = (
        ts.isoformat().replace("+00:00", "Z") if isinstance(ts, datetime) else str(ts or "")
    )
    return WizardSessionRecord(
        id=str(row[0]),
        wizard_type=wizard_type,
        user_id=str(row[2]),
        scope_id=str(row[3]),
        current_step_index=int(row[4]),
        total_steps=len(WIZARD_STEPS_BY_TYPE.get(wizard_type, ())) or 5,
        state_jsonb=raw_state,
        dbos_workflow_id=str(row[6]),
        status=status,
        completed_steps=completed,
        rag_reciprocity_verified=bool(raw_rag) or status == "COMPLETED",
        updated_at_iso=updated_iso,
    )


class SqlWizardSessionRepository:
    """Asynchronous PostgreSQL 18 repository for `wizard_sessions` (`REM-15`)."""

    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def start_or_resume_wizard_async(
        self,
        *,
        user_id: str,
        wizard_type: WizardType,
        scope_id: str,
        total_steps: int,
    ) -> WizardSessionRecord:
        del total_steps
        user_uuid = _normalize_uuid(user_id, field_name="user_id")
        scope_uuid = _normalize_scope_uuid(scope_id)

        async with self._engine.begin() as conn:
            user_exists = (
                await conn.execute(
                    sa.text("SELECT 1 FROM users WHERE id = CAST(:user_id AS uuid) LIMIT 1"),
                    {"user_id": user_uuid},
                )
            ).scalar()
            if user_exists is None:
                raise ResourceNotFoundError(
                    detail_code="ERR_WIZARD_USER_NOT_FOUND",
                    detail_params={"user_id": user_uuid},
                )

            existing = (
                await conn.execute(
                    sa.text(
                        f"SELECT {_SELECT_COLS} FROM wizard_sessions "
                        "WHERE wizard_type = :wizard_type AND user_id = CAST(:user_id AS uuid) "
                        "AND scope_id = CAST(:scope_id AS uuid) AND status = 'IN_PROGRESS' "
                        "ORDER BY updated_at DESC LIMIT 1"
                    ),
                    {"wizard_type": wizard_type, "user_id": user_uuid, "scope_id": scope_uuid},
                )
            ).fetchone()
            if existing is not None:
                return _row_to_record(existing)

            session_id = str(uuid7())
            base_wf_id = f"dbos:wizard:{wizard_type}:{user_uuid}:{scope_uuid}"
            wf_taken = (
                await conn.execute(
                    sa.text("SELECT 1 FROM wizard_sessions WHERE dbos_workflow_id = :wf LIMIT 1"),
                    {"wf": base_wf_id},
                )
            ).scalar()
            workflow_id = f"{base_wf_id}:{session_id}" if wf_taken is not None else base_wf_id

            inserted = (
                await conn.execute(
                    sa.text(
                        f"""
                        INSERT INTO wizard_sessions (
                            id, wizard_type, user_id, scope_id,
                            current_step_index, state_jsonb, dbos_workflow_id, status,
                            created_at, updated_at
                        )
                        VALUES (
                            CAST(:id AS uuid), :wizard_type, CAST(:user_id AS uuid),
                            CAST(:scope_id AS uuid), 1, CAST(:state_jsonb AS jsonb),
                            :dbos_workflow_id, 'IN_PROGRESS', NOW(), NOW()
                        )
                        RETURNING {_SELECT_COLS}
                        """
                    ),
                    {
                        "id": session_id,
                        "wizard_type": wizard_type,
                        "user_id": user_uuid,
                        "scope_id": scope_uuid,
                        "state_jsonb": _serialize_state_json(
                            {}, completed_steps=(), rag_verified=False
                        ),
                        "dbos_workflow_id": workflow_id,
                    },
                )
            ).fetchone()
            assert inserted is not None
            return _row_to_record(inserted)

    async def get_session_async(self, session_id: str) -> WizardSessionRecord | None:
        try:
            session_uuid = _normalize_uuid(session_id, field_name="session_id")
        except ValidationDomainError:
            return None
        async with self._engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"SELECT {_SELECT_COLS} FROM wizard_sessions "
                        "WHERE id = CAST(:id AS uuid) LIMIT 1"
                    ),
                    {"id": session_uuid},
                )
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    async def list_sessions_for_user_async(self, user_id: str) -> list[WizardSessionRecord]:
        try:
            user_uuid = _normalize_uuid(user_id, field_name="user_id")
        except ValidationDomainError:
            return []
        async with self._engine.connect() as conn:
            rows = (
                await conn.execute(
                    sa.text(
                        f"SELECT {_SELECT_COLS} FROM wizard_sessions "
                        "WHERE user_id = CAST(:user_id AS uuid) ORDER BY updated_at DESC"
                    ),
                    {"user_id": user_uuid},
                )
            ).fetchall()
        return [_row_to_record(row) for row in rows]

    async def save_step_and_advance_async(
        self,
        *,
        session_id: str,
        current_step_index: int,
        state_jsonb: dict[str, Any],
        status: WizardSessionStatus,
        completed_steps: tuple[int, ...],
        rag_reciprocity_verified: bool,
    ) -> WizardSessionRecord | None:
        session_uuid = _normalize_uuid(session_id, field_name="session_id")
        serialized_state = _serialize_state_json(
            state_jsonb, completed_steps=completed_steps, rag_verified=rag_reciprocity_verified
        )
        async with self._engine.begin() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        f"""
                        UPDATE wizard_sessions
                        SET current_step_index = :current_step_index,
                            state_jsonb = CAST(:state_jsonb AS jsonb),
                            status = :status,
                            updated_at = NOW()
                        WHERE id = CAST(:id AS uuid)
                        RETURNING {_SELECT_COLS}
                        """
                    ),
                    {
                        "id": session_uuid,
                        "current_step_index": current_step_index,
                        "state_jsonb": serialized_state,
                        "status": status,
                    },
                )
            ).fetchone()
        return _row_to_record(row) if row is not None else None

    async def update_session_state_async(
        self,
        *,
        session_id: str,
        state_jsonb: dict[str, Any],
        status: WizardSessionStatus,
    ) -> WizardSessionRecord | None:
        existing = await self.get_session_async(session_id)
        if existing is None:
            return None
        return await self.save_step_and_advance_async(
            session_id=session_id,
            current_step_index=existing.current_step_index,
            state_jsonb=state_jsonb,
            status=status,
            completed_steps=existing.completed_steps,
            rag_reciprocity_verified=existing.rag_reciprocity_verified,
        )


__all__ = ["SqlWizardSessionRepository"]
