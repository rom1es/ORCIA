"""PostgreSQL 18 write operations for `kb_documents`, `kb_chunks`, and `code_graph_edges`.

Enforces `AD-24.7` (zero fake SHA-256 vectors: `embedding` remains `NULL` unless a real active
`embedding_model_id` is resolved in `workspace_llm_tier_mappings`).
"""

from __future__ import annotations

from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.rag.models import (
    CodeGraphEdgeEntity,
    KbChunkEntity,
    KbDocumentEntity,
)

_ALLOWED_DS_SCHEMES = frozenset({"git", "jira", "confluence", "db", "nexus"})
_ALLOWED_DOC_SCHEMES = frozenset({"confluence", "jira", "git", "db"})


def parse_uuid_or_none(raw: str | None) -> str | None:
    """Return canonical UUID string when valid, else `None`."""
    if not raw:
        return None
    try:
        return str(UUID(raw.strip()))
    except (ValueError, AttributeError):
        return None


_parse_uuid_or_none = parse_uuid_or_none


def _format_halfvec_literal(embedding: tuple[float, ...], dim: int = 1024) -> str:
    padded = list(embedding[:dim]) + [0.0] * max(0, dim - len(embedding))
    return "[" + ",".join(f"{v:.6f}" for v in padded) + "]"


async def workspace_exists(session: AsyncSession, wid: str) -> bool:
    """Return True if the workspace UUID exists in PostgreSQL 18."""
    found = (
        await session.execute(
            sa.text("SELECT 1 FROM workspaces WHERE id = CAST(:wid AS uuid) LIMIT 1"),
            {"wid": wid},
        )
    ).scalar_one_or_none()
    return found is not None


_workspace_exists = workspace_exists


async def _ensure_datasource_id(
    session: AsyncSession,
    *,
    workspace_id: str,
    candidate_ds_id: str | None,
    alias: str,
    scheme: str,
    uri: str,
) -> str:
    parsed_ds = _parse_uuid_or_none(candidate_ds_id)
    if parsed_ds is not None:
        exists = (
            await session.execute(
                sa.text(
                    "SELECT id::text FROM workspace_datasources "
                    "WHERE id = CAST(:ds_id AS uuid) AND workspace_id = CAST(:wid AS uuid) LIMIT 1"
                ),
                {"ds_id": parsed_ds, "wid": workspace_id},
            )
        ).scalar_one_or_none()
        if exists is not None:
            return str(exists)

    clean_alias = (alias or "").strip()[:120] or "default-source"
    by_alias = (
        await session.execute(
            sa.text(
                "SELECT id::text FROM workspace_datasources "
                "WHERE workspace_id = CAST(:wid AS uuid) AND alias = :alias LIMIT 1"
            ),
            {"wid": workspace_id, "alias": clean_alias},
        )
    ).scalar_one_or_none()
    if by_alias is not None:
        return str(by_alias)

    ds_id = parsed_ds or new_uuid7_str()
    ds_scheme = scheme if scheme in _ALLOWED_DS_SCHEMES else "confluence"
    await session.execute(
        sa.text(
            """
            INSERT INTO workspace_datasources (
                id, workspace_id, alias, scheme, uri, role
            ) VALUES (
                CAST(:id AS uuid), CAST(:wid AS uuid), :alias, :scheme, :uri, 'REFERENCE'
            )
            ON CONFLICT (workspace_id, alias) DO UPDATE SET
                uri = EXCLUDED.uri
            """
        ),
        {
            "id": ds_id,
            "wid": workspace_id,
            "alias": clean_alias,
            "scheme": ds_scheme,
            "uri": uri,
        },
    )
    resolved = (
        await session.execute(
            sa.text(
                "SELECT id::text FROM workspace_datasources "
                "WHERE workspace_id = CAST(:wid AS uuid) AND alias = :alias LIMIT 1"
            ),
            {"wid": workspace_id, "alias": clean_alias},
        )
    ).scalar_one()
    return str(resolved)


async def _resolve_active_embedding_model_id(
    session: AsyncSession,
    explicit_model_id: str | None,
) -> str | None:
    parsed = _parse_uuid_or_none(explicit_model_id)
    if parsed is not None:
        return parsed
    found = (
        await session.execute(
            sa.text(
                """
                SELECT id::text
                FROM workspace_llm_tier_mappings
                WHERE usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL'
                ORDER BY updated_at DESC
                LIMIT 1
                """
            )
        )
    ).scalar_one_or_none()
    return str(found) if found is not None else None


async def upsert_kb_document_bundle_pg(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    document: KbDocumentEntity,
    chunks: tuple[KbChunkEntity, ...] = (),
    code_edges: tuple[CodeGraphEdgeEntity, ...] = (),
    embedding_model_id: str | None = None,
) -> KbDocumentEntity | None:
    """Persist `kb_documents`, `kb_chunks` (AD-24.7), and `code_graph_edges` in PG18."""
    wid = _parse_uuid_or_none(document.workspace_id)
    if wid is None:
        return None
    async with session_factory() as session, session.begin():
        if not await _workspace_exists(session, wid):
            return None

        ds_id = await _ensure_datasource_id(
            session,
            workspace_id=wid,
            candidate_ds_id=document.datasource_id,
            alias=document.datasource_alias,
            scheme=document.source_scheme,
            uri=document.source_uri,
        )
        doc_scheme = (
            document.source_scheme
            if document.source_scheme in _ALLOWED_DOC_SCHEMES
            else "confluence"
        )
        doc_uuid = _parse_uuid_or_none(document.id) or new_uuid7_str()
        persisted_doc_id = str(
            (
                await session.execute(
                    sa.text(
                        """
                        INSERT INTO kb_documents (
                            id, doc_key, workspace_id, datasource_id, source_uri,
                            source_scheme, indexing_regime, title, revision_tag,
                            content_sha256, freshness_ttl_days, is_stale
                        ) VALUES (
                            CAST(:id AS uuid), :doc_key, CAST(:wid AS uuid),
                            CAST(:ds_id AS uuid), :source_uri, :source_scheme,
                            :indexing_regime, :title, :revision_tag,
                            :content_sha256, :ttl_days, :is_stale
                        )
                        ON CONFLICT (doc_key) DO UPDATE SET
                            source_uri = EXCLUDED.source_uri,
                            revision_tag = EXCLUDED.revision_tag,
                            content_sha256 = EXCLUDED.content_sha256,
                            is_stale = EXCLUDED.is_stale,
                            last_verified_at = NOW()
                        RETURNING id::text
                        """
                    ),
                    {
                        "id": doc_uuid,
                        "doc_key": document.doc_key[:128],
                        "wid": wid,
                        "ds_id": ds_id,
                        "source_uri": document.source_uri,
                        "source_scheme": doc_scheme,
                        "indexing_regime": document.indexing_regime,
                        "title": document.title[:255],
                        "revision_tag": document.revision_tag[:128],
                        "content_sha256": document.content_sha256[:64],
                        "ttl_days": max(1, int(document.freshness_ttl_days)),
                        "is_stale": bool(document.is_stale),
                    },
                )
            ).scalar_one()
        )

        active_model_id = await _resolve_active_embedding_model_id(session, embedding_model_id)
        chunk_id_map: dict[str, str] = {}
        for chunk in chunks:
            c_uuid = _parse_uuid_or_none(chunk.id) or new_uuid7_str()
            parent_uuid = (
                chunk_id_map.get(chunk.parent_chunk_id)
                if chunk.parent_chunk_id is not None
                else None
            )
            c_model_id = (
                _parse_uuid_or_none(chunk.embedding_model_id) or active_model_id
                if chunk.embedding is not None
                else None
            )
            vec_literal = (
                _format_halfvec_literal(chunk.embedding)
                if (chunk.embedding is not None and c_model_id is not None)
                else None
            )
            persisted_chunk_id = str(
                (
                    await session.execute(
                        sa.text(
                            """
                            INSERT INTO kb_chunks (
                                id, chunk_key, document_id, workspace_id, datasource_alias,
                                parent_chunk_id, chunk_role, contextual_header, content_text,
                                token_count, embedding, embedding_model_id, embedding_generated_at
                            ) VALUES (
                                CAST(:id AS uuid), :chunk_key, CAST(:doc_id AS uuid),
                                CAST(:wid AS uuid), :ds_alias,
                                CAST(:parent_id AS uuid), :chunk_role, :header, :content_text,
                                :token_count, CAST(:vec_lit AS halfvec(1024)),
                                CAST(:model_id AS uuid),
                                CASE
                                    WHEN CAST(:model_id AS uuid) IS NOT NULL THEN NOW()
                                    ELSE NULL
                                END
                            )
                            ON CONFLICT (chunk_key) DO UPDATE SET
                                content_text = EXCLUDED.content_text,
                                contextual_header = EXCLUDED.contextual_header,
                                token_count = EXCLUDED.token_count,
                                embedding = EXCLUDED.embedding,
                                embedding_model_id = EXCLUDED.embedding_model_id,
                                embedding_generated_at = EXCLUDED.embedding_generated_at
                            RETURNING id::text
                            """
                        ),
                        {
                            "id": c_uuid,
                            "chunk_key": chunk.chunk_key[:128],
                            "doc_id": persisted_doc_id,
                            "wid": wid,
                            "ds_alias": chunk.datasource_alias[:128],
                            "parent_id": parent_uuid,
                            "chunk_role": chunk.chunk_role,
                            "header": chunk.contextual_header,
                            "content_text": chunk.content_text,
                            "token_count": max(1, int(chunk.token_count)),
                            "vec_lit": vec_literal,
                            "model_id": c_model_id,
                        },
                    )
                ).scalar_one()
            )
            chunk_id_map[chunk.id] = persisted_chunk_id

        for edge in code_edges:
            e_uuid = _parse_uuid_or_none(edge.id) or new_uuid7_str()
            await session.execute(
                sa.text(
                    """
                    INSERT INTO code_graph_edges (
                        id, edge_key, workspace_id, source_repo_uri, source_symbol,
                        target_repo_uri, target_symbol, edge_type
                    ) VALUES (
                        CAST(:id AS uuid), :edge_key, CAST(:wid AS uuid),
                        :src_repo, :src_sym, :tgt_repo, :tgt_sym, :edge_type
                    )
                    ON CONFLICT (edge_key) DO NOTHING
                    """
                ),
                {
                    "id": e_uuid,
                    "edge_key": edge.edge_key[:128],
                    "wid": wid,
                    "src_repo": edge.source_repo_uri,
                    "src_sym": edge.source_symbol[:255],
                    "tgt_repo": edge.target_repo_uri,
                    "tgt_sym": edge.target_symbol[:255],
                    "edge_type": edge.edge_type,
                },
            )

        return KbDocumentEntity(
            id=persisted_doc_id,
            doc_key=document.doc_key,
            workspace_id=wid,
            datasource_id=ds_id,
            datasource_alias=document.datasource_alias,
            source_uri=document.source_uri,
            source_scheme=doc_scheme,
            indexing_regime=document.indexing_regime,
            title=document.title,
            revision_tag=document.revision_tag,
            content_sha256=document.content_sha256,
            freshness_ttl_days=document.freshness_ttl_days,
            age_days=document.age_days,
            is_stale=document.is_stale,
        )
