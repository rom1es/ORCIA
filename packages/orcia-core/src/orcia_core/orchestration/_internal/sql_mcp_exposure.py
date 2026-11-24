"""PG18 SQLAlchemy Async repository for `mcp_exposed_agents` & PAT hashes (`Story 24.3`)."""

from __future__ import annotations

import hashlib
import json
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration._internal._sql_mcp_exposure_helpers import (
    _SELECT_AGENT_COLS,
    _ensure_root_org_unit_id,
    _parse_str_tuple,
    _row_to_spec,
)
from orcia_core.orchestration._orchestration_runtime_locales import (
    MCP_BENCH_LOCALES,
    get_runtime_copy,
)
from orcia_core.orchestration.remote_test_bench_models import ExposedMcpAgentSpec


class SqlMcpExposureRepository:
    """Async SQLAlchemy repository for `mcp_exposed_agents` & `mcp_governed_pat_tokens`."""

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
            raise RuntimeError("SqlMcpExposureRepository requires a PG18 engine/session.")
        return self._session_maker

    async def upsert_exposed_agent(
        self,
        spec: ExposedMcpAgentSpec,
        *,
        updated_by: str | None = None,
    ) -> ExposedMcpAgentSpec:
        """Upsert an MCP exposure config into `mcp_exposed_agents` and mirror in `catalog_items`."""
        sm = self._require_session_maker()
        async with sm() as session, session.begin():
            row = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            INSERT INTO mcp_exposed_agents (
                                id, workspace_slug, agent_slug, display_name, mcp_exposed,
                                regime, system_prompt_layers_1_to_4, secret_refs_jsonb,
                                human_authored_required, updated_by
                            ) VALUES (
                                CAST(:id AS uuid), :workspace_slug, :agent_slug, :display_name,
                                :mcp_exposed, :regime, :system_prompt,
                                CAST(:secret_refs AS jsonb), :human_authored_required, :updated_by
                            )
                            ON CONFLICT (workspace_slug, agent_slug) DO UPDATE SET
                                display_name = EXCLUDED.display_name,
                                mcp_exposed = EXCLUDED.mcp_exposed,
                                regime = EXCLUDED.regime,
                                system_prompt_layers_1_to_4 = EXCLUDED.system_prompt_layers_1_to_4,
                                secret_refs_jsonb = EXCLUDED.secret_refs_jsonb,
                                human_authored_required = EXCLUDED.human_authored_required,
                                updated_by = COALESCE(
                                    EXCLUDED.updated_by, mcp_exposed_agents.updated_by
                                ),
                                updated_at = NOW()
                            RETURNING {_SELECT_AGENT_COLS}
                            """
                        ),
                        {
                            "id": new_uuid7_str(),
                            "workspace_slug": spec.workspace_slug,
                            "agent_slug": spec.agent_slug,
                            "display_name": spec.display_name,
                            "mcp_exposed": spec.mcp_exposed,
                            "regime": spec.regime,
                            "system_prompt": spec.system_prompt_layers_1_to_4,
                            "secret_refs": json.dumps(list(spec.secret_refs)),
                            "human_authored_required": spec.human_authored_required,
                            "updated_by": updated_by,
                        },
                    )
                )
                .mappings()
                .one()
            )
            org_id = await _ensure_root_org_unit_id(session)
            resource_id = f"mcp-exposed:{spec.workspace_slug}:{spec.agent_slug}"[:128]
            uri = f"mcp://{spec.workspace_slug}/{spec.agent_slug}"
            sha = hashlib.sha256(f"{uri}:{spec.regime}:{spec.mcp_exposed}".encode()).hexdigest()
            meta = {
                "workspace_slug": spec.workspace_slug,
                "agent_slug": spec.agent_slug,
                "mcp_exposed": spec.mcp_exposed,
                "regime": spec.regime,
                "human_authored_required": spec.human_authored_required,
            }
            await session.execute(
                sa.text(
                    """
                    INSERT INTO catalog_items (
                        id, resource_id, uri, title, description, resource_type,
                        source_format, version, sha256, cas_key, visibility_scope,
                        owner_org_unit_id, item_type, metadata_jsonb
                    ) VALUES (
                        :id, :resource_id, :uri, :title, :description, 'agent',
                        'ORCIA', '1.0.0', :sha256, :cas_key, :visibility_scope,
                        :owner_org_unit_id, 'MCP_EXPOSED_AGENT', CAST(:metadata_jsonb AS jsonb)
                    )
                    ON CONFLICT (resource_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        sha256 = EXCLUDED.sha256,
                        cas_key = EXCLUDED.cas_key,
                        visibility_scope = EXCLUDED.visibility_scope,
                        metadata_jsonb = EXCLUDED.metadata_jsonb
                    """
                ),
                {
                    "id": UUID(new_uuid7_str()),
                    "resource_id": resource_id,
                    "uri": uri,
                    "title": spec.display_name[:255],
                    "description": get_runtime_copy(MCP_BENCH_LOCALES)["exposure_desc"].format(
                        regime=spec.regime
                    ),
                    "sha256": sha,
                    "cas_key": f"cas/{sha}",
                    "visibility_scope": "SHARED_WORKSPACE" if spec.mcp_exposed else "DRAFT",
                    "owner_org_unit_id": org_id,
                    "metadata_jsonb": json.dumps(meta, ensure_ascii=False),
                },
            )
            return _row_to_spec(row)

    async def list_exposed_agents(self, workspace_slug: str) -> list[ExposedMcpAgentSpec]:
        """List all persisted MCP exposure specs for `workspace_slug`."""
        sm = self._require_session_maker()
        async with sm() as session:
            rows = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            SELECT {_SELECT_AGENT_COLS}
                            FROM mcp_exposed_agents
                            WHERE workspace_slug = :workspace_slug
                            ORDER BY updated_at DESC, id DESC
                            """
                        ),
                        {"workspace_slug": workspace_slug},
                    )
                )
                .mappings()
                .all()
            )
            return [_row_to_spec(row) for row in rows]

    async def get_exposed_agent(
        self, workspace_slug: str, agent_slug: str
    ) -> ExposedMcpAgentSpec | None:
        """Load a single persisted MCP exposure spec from PG18."""
        sm = self._require_session_maker()
        async with sm() as session:
            row = (
                (
                    await session.execute(
                        sa.text(
                            f"""
                            SELECT {_SELECT_AGENT_COLS}
                            FROM mcp_exposed_agents
                            WHERE workspace_slug = :workspace_slug
                              AND agent_slug = :agent_slug
                            LIMIT 1
                            """
                        ),
                        {"workspace_slug": workspace_slug, "agent_slug": agent_slug},
                    )
                )
                .mappings()
                .first()
            )
            return _row_to_spec(row) if row is not None else None

    async def upsert_pat_token_hash(
        self,
        *,
        token_sha256: str,
        allowed_workspace_slugs: set[str],
    ) -> None:
        """Persist SHA-256 hash and allowed workspaces in `mcp_governed_pat_tokens`."""
        sm = self._require_session_maker()
        payload_json = json.dumps(sorted(allowed_workspace_slugs))
        async with sm() as session, session.begin():
            await session.execute(
                sa.text(
                    """
                    INSERT INTO mcp_governed_pat_tokens (
                        id, token_sha256, allowed_workspace_slugs_jsonb
                    ) VALUES (
                        CAST(:id AS uuid), :token_sha256, CAST(:allowed AS jsonb)
                    )
                    ON CONFLICT (token_sha256) DO UPDATE SET
                        allowed_workspace_slugs_jsonb = EXCLUDED.allowed_workspace_slugs_jsonb,
                        revoked_at = NULL,
                        updated_at = NOW()
                    """
                ),
                {
                    "id": new_uuid7_str(),
                    "token_sha256": token_sha256,
                    "allowed": payload_json,
                },
            )

    async def get_pat_allowed_workspaces(self, token_sha256: str) -> set[str] | None:
        """Return allowed workspace slugs for an active SHA-256 PAT hash, or None."""
        sm = self._require_session_maker()
        async with sm() as session:
            raw = (
                await session.execute(
                    sa.text(
                        """
                        SELECT allowed_workspace_slugs_jsonb
                        FROM mcp_governed_pat_tokens
                        WHERE token_sha256 = :token_sha256
                          AND revoked_at IS NULL
                        LIMIT 1
                        """
                    ),
                    {"token_sha256": token_sha256},
                )
            ).scalar_one_or_none()
            if raw is None:
                return None
            return set(_parse_str_tuple(raw))


__all__ = ["SqlMcpExposureRepository"]
