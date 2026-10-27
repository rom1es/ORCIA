"""Differentiated 3-Regime Incremental Indexer & Vector/Header Primitives (`AD-8`).

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import ast
import hashlib
import re

from orcia_core.rag.errors import DdlOnlyTransactionalDataError
from orcia_core.rag.models import (
    CodeGraphEdgeEntity,
    KbChunkEntity,
    KbDocumentEntity,
)
from orcia_core.rag.vector_and_ast import (
    EMBEDDING_DIM,
    build_contextual_header,
    compute_deterministic_halfvec_1024,
    cosine_similarity,
)
from orcia_core.rag.vector_and_ast import (
    chunk_ast_symbol as _chunk_ast_symbol,
)
from orcia_kernel.ids import new_uuid7_str

__all__ = [
    "ALLOWED_JIRA_REFERENCE_TYPES",
    "DifferentiatedIncrementalIndexer",
    "EMBEDDING_DIM",
    "FORBIDDEN_TRANSACTIONAL_SQL_RE",
    "REQUIRED_DDL_SQL_RE",
    "build_contextual_header",
    "compute_deterministic_halfvec_1024",
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
    def index_confluence_parent_child(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        source_uri: str,
        title: str,
        hierarchy_path: str,
        markdown_sections: tuple[str, ...],
        revision_tag: str,
        labels: tuple[str, ...] = ("orcia-kb",),
        page_status: str = "current",
        ontology_concepts: tuple[str, ...] = (),
        freshness_ttl_days: int = 90,
        age_days: int = 0,
    ) -> tuple[KbDocumentEntity | None, tuple[KbChunkEntity, ...]]:
        """Regime 1a: CQL-filtered Confluence page -> 1 Parent chunk + N Child chunks."""
        if page_status.lower() in ("draft", "archived") or "orcia-kb" not in labels:
            return None, ()

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
                embedding=compute_deterministic_halfvec_1024(f"{header}\n{section}"),
            )
            for idx, section in enumerate(markdown_sections, start=1)
        )
        return doc, (parent_chunk, *children)

    @staticmethod
    def index_jira_reference_issue(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        issue_key: str,
        issue_type: str,
        title: str,
        body_text: str,
        updated_tag: str,
        ontology_concepts: tuple[str, ...] = (),
    ) -> tuple[KbDocumentEntity | None, tuple[KbChunkEntity, ...]]:
        """Regime 1b: JQL-filtered reference Jira issue -> 1 unified chunk (256-1024 tokens)."""
        if issue_type not in ALLOWED_JIRA_REFERENCE_TYPES:
            return None, ()

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
            embedding=compute_deterministic_halfvec_1024(f"{header}\n{body_text}"),
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
        doc_id = new_uuid7_str()
        sha256_hex = hashlib.sha256(f"{commit_sha}:{python_source}".encode()).hexdigest()
        doc = KbDocumentEntity(
            id=doc_id,
            doc_key=f"doc-git-{datasource_alias}-{file_path.replace('/', '-')}",
            workspace_id=workspace_id,
            datasource_id=datasource_id,
            datasource_alias=datasource_alias,
            source_uri=f"{repo_uri}/blob/{commit_sha}/{file_path}",
            source_scheme="git",
            indexing_regime="CODE_AST_GRAPH",
            title=file_path,
            revision_tag=commit_sha,
            content_sha256=sha256_hex,
        )
        concept_map = implements_concepts or {}
        try:
            tree = ast.parse(python_source)
        except SyntaxError:
            header = build_contextual_header(
                datasource_alias=datasource_alias, hierarchy_path=file_path, title=file_path
            )
            fallback = KbChunkEntity(
                id=new_uuid7_str(),
                chunk_key=f"{doc.doc_key}-ast-module",
                document_id=doc_id,
                workspace_id=workspace_id,
                datasource_alias=datasource_alias,
                parent_chunk_id=None,
                chunk_role="AST_SYMBOL",
                contextual_header=header,
                content_text=python_source,
                token_count=max(150, min(800, len(python_source.split()) + 150)),
                embedding=compute_deterministic_halfvec_1024(f"{header}\n{python_source}"),
            )
            return doc, (fallback,), ()

        lines = python_source.splitlines()
        chunks: list[KbChunkEntity] = []
        edges: list[CodeGraphEdgeEntity] = []
        prefix = f"edge-{datasource_alias}-{file_path}"

        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    edges.append(
                        CodeGraphEdgeEntity(
                            id=new_uuid7_str(),
                            edge_key=f"{prefix}-import-{alias.name}",
                            workspace_id=workspace_id,
                            source_repo_uri=repo_uri,
                            source_symbol=file_path,
                            target_repo_uri=repo_uri,
                            target_symbol=alias.name,
                            edge_type="IMPORTS",
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                base_mod = node.module or ""
                targets = [f"{base_mod}.{a.name}".strip(".") for a in node.names] or [base_mod]
                for mod_name in targets:
                    edges.append(
                        CodeGraphEdgeEntity(
                            id=new_uuid7_str(),
                            edge_key=f"{prefix}-import-{mod_name}",
                            workspace_id=workspace_id,
                            source_repo_uri=repo_uri,
                            source_symbol=file_path,
                            target_repo_uri=repo_uri,
                            target_symbol=mod_name,
                            edge_type="IMPORTS",
                        )
                    )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                c_chunk, c_edges = _chunk_ast_symbol(
                    node=node,
                    qualname=node.name,
                    doc_id=doc_id,
                    doc_key=doc.doc_key,
                    workspace_id=workspace_id,
                    datasource_alias=datasource_alias,
                    repo_uri=repo_uri,
                    file_path=file_path,
                    lines=lines,
                    concept_map=concept_map,
                )
                chunks.append(c_chunk)
                edges.extend(c_edges)
                if isinstance(node, ast.ClassDef):
                    for sub in node.body:
                        if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            m_chunk, m_edges = _chunk_ast_symbol(
                                node=sub,
                                qualname=f"{node.name}.{sub.name}",
                                doc_id=doc_id,
                                doc_key=doc.doc_key,
                                workspace_id=workspace_id,
                                datasource_alias=datasource_alias,
                                repo_uri=repo_uri,
                                file_path=file_path,
                                lines=lines,
                                concept_map=concept_map,
                            )
                            chunks.append(m_chunk)
                            edges.extend(m_edges)
        return doc, tuple(chunks), tuple(edges)

    @staticmethod
    def index_db_ddl_schema_only(
        *,
        workspace_id: str,
        datasource_id: str,
        datasource_alias: str,
        db_uri: str,
        ddl_sql: str,
        schema_version: str,
        ontology_concepts: tuple[str, ...] = (),
    ) -> tuple[KbDocumentEntity, tuple[KbChunkEntity, ...]]:
        """Regime 3: Strictly indexes DDL schema (`CREATE TABLE`), rejecting transactional rows."""
        stripped_sql = _SQL_COMMENT_OR_STRING_RE.sub(" ", ddl_sql)
        if FORBIDDEN_TRANSACTIONAL_SQL_RE.search(stripped_sql) or not REQUIRED_DDL_SQL_RE.search(
            stripped_sql
        ):
            raise DdlOnlyTransactionalDataError(instance=db_uri)

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
            embedding=compute_deterministic_halfvec_1024(f"{header}\n{ddl_sql}"),
        )
        return doc, (chunk,)
