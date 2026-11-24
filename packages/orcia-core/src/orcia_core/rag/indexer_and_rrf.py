"""Differentiated 3-Regime Incremental Indexer & Vector/Header Primitives (`AD-8`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime

from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag._git_ast_indexer import index_git_ast_and_code_graph_impl
from orcia_core.rag.errors import DdlOnlyTransactionalDataError, NoActiveEmbeddingModelError
from orcia_core.rag.models import (
    CodeGraphEdgeEntity,
    KbChunkEntity,
    KbDocumentEntity,
)
from orcia_core.rag.vector_and_ast import (
    EMBEDDING_DIM,
    build_contextual_header,
    cosine_similarity,
)
from orcia_kernel.ids import new_uuid7_str

__all__ = [
    "ALLOWED_JIRA_REFERENCE_TYPES",
    "DifferentiatedIncrementalIndexer",
    "EMBEDDING_DIM",
    "FORBIDDEN_TRANSACTIONAL_SQL_RE",
    "REQUIRED_DDL_SQL_RE",
    "build_contextual_header",
    "cosine_similarity",
]

ALLOWED_JIRA_REFERENCE_TYPES: frozenset[str] = frozenset(
    {"Epic", "Story", "Resolved_Bug_Root_Cause", "Post_Mortem"}
)
_SQL_COMMENT_OR_STRING_RE = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/|'[^']*'")
FORBIDDEN_TRANSACTIONAL_SQL_RE = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+[\w.\"]+\s+SET|DELETE\s+FROM|COPY\s+[\w.\"]+|TRUNCATE\s+|MERGE\s+INTO)\b"
    r"|(?<!AS\s)\bSELECT\s+.+?\bFROM\b",
    re.IGNORECASE | re.DOTALL,
)
REQUIRED_DDL_SQL_RE = re.compile(r"\b(CREATE|ALTER|COMMENT\s+ON)\b", re.IGNORECASE)


class DifferentiatedIncrementalIndexer:
    """Implements the 3 indexing regimes (`DOC_PARENT_CHILD`, `CODE_AST_GRAPH`, `DB_DDL_ONLY`)."""

    @staticmethod
    async def index_confluence_parent_child(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        source_uri: str,
        title: str,
        hierarchy_path: str,
        markdown_sections: tuple[str, ...],
        revision_tag: str,
        embedding_port: EmbeddingPort | None = None,
        embedding_model_id: str | None = None,
        labels: tuple[str, ...] = ("orcia-kb",),
        page_status: str = "current",
        ontology_concepts: tuple[str, ...] = (),
        freshness_ttl_days: int = 90,
        age_days: int = 0,
    ) -> tuple[KbDocumentEntity | None, tuple[KbChunkEntity, ...]]:
        """Regime 1a: CQL-filtered Confluence page -> 1 Parent chunk + N Child chunks."""
        if page_status.lower() in ("draft", "archived") or "orcia-kb" not in labels:
            return None, ()

        if embedding_port is None:
            raise NoActiveEmbeddingModelError(detail_code="ERR_NO_ACTIVE_EMBEDDING_MODEL_INGEST")

        full_text = "\n\n".join(markdown_sections)
        sha256_hex = hashlib.sha256(f"{revision_tag}:{full_text}".encode()).hexdigest()
        doc_id = new_uuid7_str()
        doc = KbDocumentEntity(
            id=doc_id,
            doc_key=f"doc-{datasource_alias}-{title.lower().replace(' ', '-')}",
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            source_uri=source_uri,
            source_scheme="confluence",
            indexing_regime="DOC_PARENT_CHILD",
            title=title,
            revision_tag=revision_tag,
            content_sha256=sha256_hex,
            freshness_ttl_days=freshness_ttl_days,
            age_days=age_days,
            is_stale=age_days > freshness_ttl_days,
        )
        header = build_contextual_header(
            datasource_alias=datasource_alias,
            hierarchy_path=hierarchy_path,
            title=title,
            ontology_concepts=ontology_concepts,
        )
        parent_id = new_uuid7_str()
        parent_chunk = KbChunkEntity(
            id=parent_id,
            chunk_key=f"{doc.doc_key}-parent",
            document_id=doc_id,
            workspace_id=workspace_id,
            datasource_alias=datasource_alias,
            parent_chunk_id=None,
            chunk_role="PARENT",
            contextual_header=header,
            content_text=full_text,
            token_count=max(1024, len(full_text.split())),
            embedding=None,
        )

        child_texts = [f"{header}\n{section}" for section in markdown_sections]
        vectors = await embedding_port.embed_texts(child_texts)
        now_iso = datetime.now(UTC).isoformat()
        children = tuple(
            KbChunkEntity(
                id=new_uuid7_str(),
                chunk_key=f"{doc.doc_key}-child-{idx}",
                document_id=doc_id,
                workspace_id=workspace_id,
                datasource_alias=datasource_alias,
                parent_chunk_id=parent_id,
                chunk_role="CHILD",
                contextual_header=header,
                content_text=section,
                token_count=max(256, min(512, len(section.split()) + 256)),
                embedding=tuple(vec),
                embedding_model_id=embedding_model_id,
                embedding_generated_at=now_iso,
            )
            for idx, (section, vec) in enumerate(
                zip(markdown_sections, vectors, strict=True), start=1
            )
        )
        return doc, (parent_chunk, *children)

    @staticmethod
    async def index_jira_reference_issue(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        issue_key: str,
        issue_type: str,
        title: str,
        body_text: str,
        updated_tag: str,
        embedding_port: EmbeddingPort | None = None,
        embedding_model_id: str | None = None,
        ontology_concepts: tuple[str, ...] = (),
    ) -> tuple[KbDocumentEntity | None, tuple[KbChunkEntity, ...]]:
        """Regime 1b: JQL-filtered reference Jira issue -> 1 unified chunk (256-1024 tokens)."""
        if issue_type not in ALLOWED_JIRA_REFERENCE_TYPES:
            return None, ()

        if embedding_port is None:
            raise NoActiveEmbeddingModelError(detail_code="ERR_NO_ACTIVE_EMBEDDING_MODEL_INGEST")

        doc_id = new_uuid7_str()
        sha256_hex = hashlib.sha256(f"{updated_tag}:{body_text}".encode()).hexdigest()
        doc = KbDocumentEntity(
            id=doc_id,
            doc_key=f"doc-jira-{issue_key.lower()}",
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            source_uri=f"jira://{datasource_alias}/browse/{issue_key}",
            source_scheme="jira",
            indexing_regime="DOC_PARENT_CHILD",
            title=f"{issue_key}: {title}",
            revision_tag=updated_tag,
            content_sha256=sha256_hex,
        )
        header = build_contextual_header(
            datasource_alias=datasource_alias,
            hierarchy_path=f"Jira > {issue_type}",
            title=f"{issue_key} {title}",
            ontology_concepts=ontology_concepts,
        )
        vec = await embedding_port.embed_query(f"{header}\n{body_text}")
        now_iso = datetime.now(UTC).isoformat()
        chunk = KbChunkEntity(
            id=new_uuid7_str(),
            chunk_key=f"chunk-jira-{issue_key.lower()}",
            document_id=doc_id,
            workspace_id=workspace_id,
            datasource_alias=datasource_alias,
            parent_chunk_id=None,
            chunk_role="UNIFIED_JIRA",
            contextual_header=header,
            content_text=body_text,
            token_count=max(256, min(1024, len(body_text.split()) + 256)),
            embedding=tuple(vec),
            embedding_model_id=embedding_model_id,
            embedding_generated_at=now_iso,
        )
        return doc, (chunk,)

    @staticmethod
    def index_git_ast_and_code_graph(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        repo_uri: str,
        file_path: str,
        python_source: str,
        commit_sha: str,
        implements_concepts: dict[str, str] | None = None,
    ) -> tuple[KbDocumentEntity, tuple[KbChunkEntity, ...], tuple[CodeGraphEdgeEntity, ...]]:
        """Regime 2: Syntactic AST symbol chunking (`150-800` tokens) + Code Property Graph."""
        return index_git_ast_and_code_graph_impl(
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            repo_uri=repo_uri,
            file_path=file_path,
            python_source=python_source,
            commit_sha=commit_sha,
            implements_concepts=implements_concepts,
        )

    @staticmethod
    async def index_db_ddl_schema_only(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        db_uri: str,
        ddl_sql: str,
        schema_version: str,
        embedding_port: EmbeddingPort | None = None,
        embedding_model_id: str | None = None,
        ontology_concepts: tuple[str, ...] = (),
    ) -> tuple[KbDocumentEntity, tuple[KbChunkEntity, ...]]:
        """Regime 3: Strictly indexes DDL schema (`CREATE TABLE`), rejecting transactional rows."""
        stripped_sql = _SQL_COMMENT_OR_STRING_RE.sub(" ", ddl_sql)
        if FORBIDDEN_TRANSACTIONAL_SQL_RE.search(stripped_sql) or not REQUIRED_DDL_SQL_RE.search(
            stripped_sql
        ):
            raise DdlOnlyTransactionalDataError(instance=db_uri)

        if embedding_port is None:
            raise NoActiveEmbeddingModelError(detail_code="ERR_NO_ACTIVE_EMBEDDING_MODEL_INGEST")

        doc_id = new_uuid7_str()
        sha256_hex = hashlib.sha256(f"{schema_version}:{ddl_sql}".encode()).hexdigest()
        doc = KbDocumentEntity(
            id=doc_id,
            doc_key=f"doc-db-ddl-{datasource_alias}",
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            source_uri=db_uri,
            source_scheme="db",
            indexing_regime="DB_DDL_ONLY",
            title=f"DDL Schema {datasource_alias}",
            revision_tag=schema_version,
            content_sha256=sha256_hex,
        )
        header = build_contextual_header(
            datasource_alias=datasource_alias,
            hierarchy_path="Database > DDL Schema",
            title=datasource_alias,
            ontology_concepts=ontology_concepts,
        )
        vec = await embedding_port.embed_query(f"{header}\n{ddl_sql}")
        now_iso = datetime.now(UTC).isoformat()
        chunk = KbChunkEntity(
            id=new_uuid7_str(),
            chunk_key=f"chunk-db-ddl-{datasource_alias}",
            document_id=doc_id,
            workspace_id=workspace_id,
            datasource_alias=datasource_alias,
            parent_chunk_id=None,
            chunk_role="DDL_SCHEMA",
            contextual_header=header,
            content_text=ddl_sql,
            token_count=max(150, len(ddl_sql.split())),
            embedding=tuple(vec),
            embedding_model_id=embedding_model_id,
            embedding_generated_at=now_iso,
        )
        return doc, (chunk,)
